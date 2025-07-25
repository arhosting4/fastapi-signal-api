# filename: hunter.py

import asyncio
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import check_m15_opportunity, generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

# ★★★ گلوبل لاکنگ میکانزم ★★★
# یہ متغیر اس بات کو یقینی بنائے گا کہ ایک وقت میں صرف ایک ہی ہنٹ جاب چلے
HUNT_JOB_RUNNING = False

MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 70.0

async def hunt_for_signals_job():
    """
    یہ مرکزی جاب ہے جو ہر 5 منٹ بعد چلتی ہے اور "گلوبل لاک" کا استعمال کرتی ہے۔
    """
    global HUNT_JOB_RUNNING

    # --- لاکنگ کی منطق ---
    if HUNT_JOB_RUNNING:
        logger.warning(">>> ہنٹ جاب پہلے سے ہی چل رہی ہے۔ اس نئے عمل کو روکا جا رہا ہے۔")
        return
    
    HUNT_JOB_RUNNING = True
    logger.info("=============================================")
    logger.info(">>> ہنٹ جاب (v2.4 - گلوبل لاک کے ساتھ) شروع ہو رہی ہے...")
    logger.info("=============================================")

    db = SessionLocal()
    try:
        if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
            logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔")
            return

        pairs = get_available_pairs()
        
        # --- مرحلہ 1: صرف M15 ڈیٹا حاصل کریں (متوازی طور پر) ---
        logger.info(f"مرحلہ 1: {len(pairs)} جوڑوں کے لیے صرف M15 ڈیٹا حاصل کیا جا رہا ہے۔")
        m15_fetch_tasks = [fetch_twelve_data_ohlc(pair, "15min") for pair in pairs]
        m15_results = await asyncio.gather(*m15_fetch_tasks, return_exceptions=True)

        # --- مرحلہ 2: ہر جوڑے پر M15 موقع کی انفرادی جانچ کریں ---
        candidate_pairs = []
        for i, m15_candles in enumerate(m15_results):
            symbol = pairs[i]
            if not isinstance(m15_candles, Exception) and m15_candles and len(m15_candles) >= 34:
                trend = check_m15_opportunity(symbol, m15_candles)
                if trend:
                    candidate_pairs.append({"symbol": symbol, "m15_trend": trend})

        if not candidate_pairs:
            logger.info("مرحلہ 1 مکمل: کسی بھی جوڑے پر M15 کا کوئی واضح موقع نہیں ملا۔")
            return

        logger.info(f"مرحلہ 2: {len(candidate_pairs)} امیدوار جوڑوں کا مکمل تجزیہ شروع کیا جا رہا ہے۔")
        for candidate in candidate_pairs:
            if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
                break

            symbol = candidate["symbol"]
            m15_trend = candidate["m15_trend"]
            
            m5_candles = await fetch_twelve_data_ohlc(symbol, "5min")
            if not m5_candles or len(m5_candles) < 34:
                logger.warning(f"[{symbol}] کے لیے ناکافی M5 ڈیٹا، نظر انداز کیا جا رہا ہے۔")
                continue

            signal_result = await generate_final_signal(db, symbol, m15_trend, m5_candles)

            if signal_result and signal_result.get("status") == "ok" and signal_result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                add_active_signal(signal_result)
                logger.info(f"★★★ نیا سگنل ملا: {signal_result['symbol']} - {signal_result['signal']} @ {signal_result['price']} ★★★")
                await send_telegram_alert(signal_result)
                await manager.broadcast({"type": "new_signal", "data": signal_result})

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        # --- لاک کو غیر فعال کریں ---
        HUNT_JOB_RUNNING = False
        if db.is_active:
            db.close()
        logger.info(">>> ہنٹ جاب مکمل ہوئی۔ لاک کو جاری کر دیا گیا ہے۔")
        logger.info("=============================================")

