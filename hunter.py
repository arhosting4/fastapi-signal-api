# filename: hunter.py

import asyncio
import logging
import random # ★★★ نیا امپورٹ ★★★
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from utils import get_tradeable_pairs, get_real_time_quotes, fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from config import STRATEGY

logger = logging.getLogger(__name__)

FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]
MIN_CHANGE_PERCENT_FOR_ANALYSIS = STRATEGY["MIN_CHANGE_PERCENT_FOR_ANALYSIS"]

recently_analyzed = {}
ANALYSIS_COOLDOWN_SECONDS = 60 * 10 

async def hunt_for_signals_job():
    """
    ★★★ حتمی ورژن: فی منٹ کی حد کو کنٹرول کرنے کے لیے وقفے کے ساتھ ★★★
    """
    try:
        # ★★★ سب سے اہم تبدیلی: ایک بے ترتیب وقفہ شامل کریں ★★★
        # اس سے ہنٹر اور فیڈ بیک چیکر کے ایک ساتھ چلنے کا امکان ختم ہو جائے گا۔
        # یہ 1 سے 5 سیکنڈ کے درمیان کوئی بھی وقت ہو سکتا ہے۔
        initial_delay = random.uniform(1, 5)
        logger.info(f"🏹 ہنٹر شروع ہو رہا ہے... {initial_delay:.2f} سیکنڈ کا ابتدائی وقفہ۔")
        await asyncio.sleep(initial_delay)

        db = SessionLocal()
        active_signals = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
        
        pairs_for_prescan = [p for p in get_tradeable_pairs() if p not in active_signals]
        
        if not pairs_for_prescan:
            logger.info("شکار کے لیے کوئی نئے جوڑے دستیاب نہیں۔")
            db.close()
            return

        logger.info(f"🔬 پری اسکین شروع: {len(pairs_for_prescan)} جوڑوں کی نگرانی کی جا رہی ہے...")

        # بیچوں میں تقسیم کریں تاکہ ایک کال میں 7 سے زیادہ نہ ہوں
        batch_size = 7
        pair_batches = [pairs_for_prescan[i:i + batch_size] for i in range(0, len(pairs_for_prescan), batch_size)]

        all_quotes = {}
        for i, batch in enumerate(pair_batches):
            logger.info(f"بیچ {i+1}/{len(pair_batches)} کے لیے کوٹس حاصل کیے جا رہے ہیں...")
            quotes = await get_real_time_quotes(batch)
            if quotes:
                all_quotes.update(quotes)
            # ہر بیچ کے بعد تھوڑا وقفہ دیں
            if i < len(pair_batches) - 1:
                await asyncio.sleep(2)

        if not all_quotes:
            logger.warning("پری اسکین کے لیے کوئی کوٹس حاصل نہیں ہوئے۔ تلاش کا یہ دور ختم۔")
            db.close()
            return

        interesting_pairs = []
        current_time = asyncio.get_event_loop().time()

        for symbol, data in all_quotes.items():
            try:
                if symbol in recently_analyzed and current_time - recently_analyzed[symbol] < ANALYSIS_COOLDOWN_SECONDS:
                    continue
                percent_change = float(data.get("percent_change", "0.0"))
                if abs(percent_change) > MIN_CHANGE_PERCENT_FOR_ANALYSIS:
                    interesting_pairs.append(symbol)
                    logger.info(f"✅ [{symbol}] دلچسپ پایا گیا! حرکت: {percent_change:.2f}%")
            except (ValueError, TypeError) as e:
                logger.warning(f"[{symbol}] کے کوٹ ڈیٹا کو پارس کرنے میں خرابی: {e}")
                continue

        if not interesting_pairs:
            logger.info("کوئی بھی جوڑا گہرے تجزیے کے معیار پر پورا نہیں اترا۔")
            db.close()
            return
            
        logger.info(f"🏹 گہرا تجزیہ شروع: {len(interesting_pairs)} دلچسپ جوڑوں کا تجزیہ کیا جائے گا: {interesting_pairs}")

        for pair in interesting_pairs:
            recently_analyzed[pair] = current_time
            candles = await fetch_twelve_data_ohlc(pair)
            if not candles or len(candles) < 34:
                continue
            analysis_result = await generate_final_signal(db, pair, candles)
            if analysis_result and analysis_result.get("status") == "ok":
                confidence = analysis_result.get('confidence', 0)
                if confidence >= FINAL_CONFIDENCE_THRESHOLD:
                    update_result = crud.add_or_update_active_signal(db, analysis_result)
                    if update_result:
                        signal_obj = update_result.signal.as_dict()
                        task_type = "new_signal" if update_result.is_new else "signal_updated"
                        alert_task = send_telegram_alert if update_result.is_new else send_signal_update_alert
                        logger.info(f"🎯 سگنل پروسیس ہوا: {signal_obj['symbol']} ({task_type})")
                        asyncio.create_task(alert_task(signal_obj))
                        asyncio.create_task(manager.broadcast({"type": task_type, "data": signal_obj}))
                else:
                    logger.info(f"📊 [{pair}] سگنل مسترد: اعتماد ({confidence:.2f}%) تھریشولڈ سے کم ہے۔")

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        if 'db' in locals() and db.is_active:
            db.close()
        logger.info("🏹 ذہین سگنل کی تلاش کا دور مکمل ہوا۔")

