# filename: hunter.py

import asyncio
import logging
import random
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

async def analyze_and_process_pair(db: Session, pair: str):
    """ایک جوڑے کا مکمل تجزیہ کرتا ہے اور نتیجہ واپس کرتا ہے۔"""
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34:
        logger.info(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا۔")
        return

    analysis_result = await generate_final_signal(db, pair, candles)
    
    if analysis_result and analysis_result.get("status") == "ok":
        confidence = analysis_result.get('confidence', 0)
        log_message = (
            f"📊 [{pair}] تجزیہ مکمل: سگنل = {analysis_result.get('signal', 'N/A').upper()}, "
            f"اعتماد = {confidence:.2f}%, پیٹرن = {analysis_result.get('pattern', 'N/A')}"
        )
        logger.info(log_message)
        
        if confidence >= FINAL_CONFIDENCE_THRESHOLD:
            update_result = crud.add_or_update_active_signal(db, analysis_result)
            if update_result:
                signal_obj = update_result.signal.as_dict()
                task_type = "new_signal" if update_result.is_new else "signal_updated"
                alert_task = send_telegram_alert if update_result.is_new else send_signal_update_alert
                logger.info(f"🎯 ★★★ سگنل پروسیس ہوا: {signal_obj['symbol']} ({task_type}) ★★★")
                asyncio.create_task(alert_task(signal_obj))
                asyncio.create_task(manager.broadcast({"type": task_type, "data": signal_obj}))
        else:
            logger.info(f"📉 [{pair}] سگنل مسترد: اعتماد ({confidence:.2f}%) تھریشولڈ ({FINAL_CONFIDENCE_THRESHOLD}%) سے کم ہے۔")
            
    elif analysis_result:
        logger.info(f"ℹ️ [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {analysis_result.get('reason', 'نامعلوم')}")

async def hunt_for_signals_job():
    db = SessionLocal()
    try:
        initial_delay = random.uniform(1, 5)
        await asyncio.sleep(initial_delay)

        active_signals = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
        pairs_for_prescan = [p for p in get_tradeable_pairs() if p not in active_signals]
        
        if not pairs_for_prescan:
            return

        logger.info(f"🔬 پری اسکین شروع: {len(pairs_for_prescan)} جوڑوں کی نگرانی کی جا رہی ہے...")
        
        batch_size = 7
        pair_batches = [pairs_for_prescan[i:i + batch_size] for i in range(0, len(pairs_for_prescan), batch_size)]
        all_quotes = {}
        for i, batch in enumerate(pair_batches):
            quotes = await get_real_time_quotes(batch)
            if quotes: all_quotes.update(quotes)
            if i < len(pair_batches) - 1: await asyncio.sleep(2)

        if not all_quotes:
            return

        interesting_pairs = []
        current_time = asyncio.get_event_loop().time()
        for symbol, data in all_quotes.items():
            if symbol in recently_analyzed and current_time - recently_analyzed[symbol] < ANALYSIS_COOLDOWN_SECONDS:
                continue
            try:
                if abs(float(data.get("percent_change", "0.0"))) > MIN_CHANGE_PERCENT_FOR_ANALYSIS:
                    interesting_pairs.append(symbol)
            except (ValueError, TypeError):
                continue

        if not interesting_pairs:
            logger.info("✅ کوئی بھی جوڑا گہرے تجزیے کے معیار پر پورا نہیں اترا۔")
            return
            
        logger.info(f"🏹 گہرا تجزیہ شروع: {len(interesting_pairs)} دلچسپ جوڑوں کا تجزیہ کیا جائے گا: {interesting_pairs}")

        analysis_tasks = [analyze_and_process_pair(db, pair) for pair in interesting_pairs]
        await asyncio.gather(*analysis_tasks)

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        # ★★★ یہاں سے اضافی بریکٹ ہٹا دی گئی ہے ★★★
        logger.info("🏹 ذہین سگنل کی تلاش کا دور مکمل ہوا۔")
        
