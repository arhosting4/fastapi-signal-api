# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
# ★★★ ہمارے نئے، اپ ڈیٹ شدہ utils سے امپورٹس ★★★
from utils import get_tradeable_pairs, get_real_time_quotes, fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from config import STRATEGY

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے متغیرات ---
FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]
MIN_CHANGE_PERCENT_FOR_ANALYSIS = STRATEGY["MIN_CHANGE_PERCENT_FOR_ANALYSIS"]

# ★★★ نیا: ایک چھوٹی سی میموری تاکہ بار بار ایک ہی جوڑے کا تجزیہ نہ ہو ★★★
recently_analyzed = {}
ANALYSIS_COOLDOWN_SECONDS = 60 * 10 # 10 منٹ

async def hunt_for_signals_job():
    """
    ★★★ مکمل طور پر اصلاح شدہ اور ذہین ہنٹر (اسمارٹ ٹرائیڈنٹ ورژن) ★★★
    یہ اب ایک کم خرچ "پری اسکین" کرتا ہے اور صرف دلچسپ جوڑوں کا گہرا تجزیہ کرتا ہے۔
    """
    db = SessionLocal()
    try:
        active_signals = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
        
        # 1. پری اسکین کے لیے تمام قابلِ تجارت جوڑوں کی فہرست حاصل کریں
        pairs_for_prescan = [p for p in get_tradeable_pairs() if p not in active_signals]
        
        if not pairs_for_prescan:
            logger.info("شکار کے لیے کوئی نئے جوڑے دستیاب نہیں۔ تمام جوڑوں پر سگنل فعال ہیں۔")
            return

        logger.info(f"🔬 پری اسکین شروع: {len(pairs_for_prescan)} جوڑوں کی نگرانی کی جا رہی ہے...")

        # 2. کم خرچ API کال کے ذریعے تمام جوڑوں کے کوٹس حاصل کریں
        quotes = await get_real_time_quotes(pairs_for_prescan)
        if not quotes:
            logger.warning("پری اسکین کے لیے کوٹس حاصل کرنے میں ناکامی۔ تلاش کا یہ دور ختم۔")
            return

        # 3. دلچسپ جوڑوں کی فہرست بنائیں (جن میں حرکت ہو رہی ہے)
        interesting_pairs = []
        current_time = asyncio.get_event_loop().time()

        for symbol, data in quotes.items():
            try:
                # چیک کریں کہ آیا اس جوڑے کا حال ہی میں تجزیہ ہوا ہے
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
            return
            
        logger.info(f"🏹 گہرا تجزیہ شروع: {len(interesting_pairs)} دلچسپ جوڑوں کا تجزیہ کیا جائے گا: {interesting_pairs}")

        # 4. اب صرف دلچسپ جوڑوں کے لیے مہنگی `/time_series` کال کریں
        for pair in interesting_pairs:
            recently_analyzed[pair] = current_time # اسے تجزیہ شدہ کے طور پر نشان زد کریں
            
            candles = await fetch_twelve_data_ohlc(pair)
            
            if not candles or len(candles) < 34:
                logger.info(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا۔")
                continue

            analysis_result = await generate_final_signal(db, pair, candles)
            
            if analysis_result and analysis_result.get("status") == "ok":
                confidence = analysis_result.get('confidence', 0)
                
                if confidence >= FINAL_CONFIDENCE_THRESHOLD:
                    update_result = crud.add_or_update_active_signal(db, analysis_result)
                    if update_result:
                        signal_obj = update_result.signal.as_dict()
                        if update_result.is_new:
                            logger.info(f"🎯 ★★★ نیا سگنل ملا: {signal_obj['symbol']} ★★★")
                            asyncio.create_task(send_telegram_alert(signal_obj))
                            asyncio.create_task(manager.broadcast({"type": "new_signal", "data": signal_obj}))
                        else:
                            logger.info(f"🔄 ★★★ سگنل اپ ڈیٹ ہوا: {signal_obj['symbol']} ★★★")
                            asyncio.create_task(send_signal_update_alert(signal_obj))
                            asyncio.create_task(manager.broadcast({"type": "signal_updated", "data": signal_obj}))
                else:
                    logger.info(f"📊 [{pair}] سگنل مسترد: اعتماد ({confidence:.2f}%) تھریشولڈ سے کم ہے۔")

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🏹 ذہین سگنل کی تلاش کا دور مکمل ہوا۔")

