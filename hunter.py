# filename: hunter.py

import asyncio
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from utils import fetch_twelve_data_ohlc, get_available_pairs
# fusion_engine سے دونوں فنکشنز امپورٹ کریں
from fusion_engine import check_m15_opportunity, generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 70.0

async def hunt_for_signals_job():
    """
    یہ مرکزی جاب ہے جو ہر 5 منٹ بعد چلتی ہے اور "اسمارٹ ہنٹر" منطق کا استعمال کرتی ہے۔
    """
    logger.info("=============================================")
    logger.info(">>> اسمارٹ ہنٹر جاب (v2.3) شروع ہو رہی ہے...")
    logger.info("=============================================")

    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔ جاب روکی جا رہی ہے۔")
        return

    pairs = get_available_pairs()
    db = SessionLocal()
    
    try:
        # --- مرحلہ 1: صرف M15 ڈیٹا حاصل کریں (متوازی طور پر) ---
        # یہ ہر 5 منٹ میں صرف 4 API کالز کرے گا۔
        logger.info(f"مرحلہ 1: {len(pairs)} جوڑوں کے لیے صرف M15 ڈیٹا حاصل کیا جا رہا ہے۔")
        m15_fetch_tasks = [fetch_twelve_data_ohlc(pair, "15min") for pair in pairs]
        m15_results = await asyncio.gather(*m15_fetch_tasks, return_exceptions=True)

        # --- مرحلہ 2: ہر جوڑے پر M15 موقع کی انفرادی جانچ کریں ---
        for i, m15_candles in enumerate(m15_results):
            symbol = pairs[i]

            # اگر API کال میں کوئی خرابی ہوئی ہو تو اسے نظر انداز کریں
            if isinstance(m15_candles, Exception) or not m15_candles or len(m15_candles) < 34:
                if isinstance(m15_candles, Exception):
                    logger.error(f"[{symbol}] M15 ڈیٹا حاصل کرنے میں خرابی: {m15_candles}")
                else:
                    logger.warning(f"[{symbol}] کے لیے ناکافی M15 ڈیٹا، نظر انداز کیا جا رہا ہے۔")
                continue

            # M15 پر موقع چیک کریں
            m15_trend = check_m15_opportunity(symbol, m15_candles)

            # ★★★ مرکزی منطق: اگر M15 پر موقع ہے، تو ہی M5 چیک کریں ★★★
            if m15_trend:
                logger.info(f"[{symbol}] پر M15 موقع ({m15_trend}) ملا۔ اب M5 کا تجزیہ کیا جائے گا۔")
                
                # ایکٹیو سگنلز کی حد دوبارہ چیک کریں
                if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
                    logger.info("سگنل کی حد تک پہنچ گئے، مزید تجزیہ روکا جا رہا ہے۔")
                    break

                # صرف اس ایک جوڑے کے لیے M5 ڈیٹا حاصل کریں (ایک اضافی API کال)
                m5_candles = await fetch_twelve_data_ohlc(symbol, "5min")
                if not m5_candles or len(m5_candles) < 34:
                    logger.warning(f"[{symbol}] کے لیے ناکافی M5 ڈیٹا، نظر انداز کیا جا رہا ہے۔")
                    continue

                # مکمل تجزیہ
                signal_result = await generate_final_signal(db, symbol, m15_trend, m5_candles)

                if signal_result and signal_result.get("status") == "ok" and signal_result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                    add_active_signal(signal_result)
                    logger.info(f"★★★ نیا سگنل ملا: {signal_result['symbol']} - {signal_result['signal']} @ {signal_result['price']} ★★★")
                    await send_telegram_alert(signal_result)
                    await manager.broadcast({"type": "new_signal", "data": signal_result})
            else:
                logger.info(f"[{symbol}] پر M15 کا کوئی موقع نہیں ملا۔ نظر انداز کیا جا رہا ہے۔")

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info(">>> اسمارٹ ہنٹر جاب مکمل ہوئی۔")
        logger.info("=============================================")

