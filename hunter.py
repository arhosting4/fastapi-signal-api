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

MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 70.0

async def hunt_for_signals_job():
    logger.info("=============================================")
    logger.info(">>> سگنل کی تلاش کا کام (v2.1 - دو قدمی فلٹرنگ) شروع ہو رہا ہے...")
    logger.info("=============================================")

    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔")
        return

    pairs = get_available_pairs()
    db = SessionLocal()
    
    try:
        # --- مرحلہ 1: تمام جوڑوں کے لیے M15 مواقع متوازی طور پر چیک کریں ---
        logger.info(f"مرحلہ 1: {len(pairs)} جوڑوں کے لیے M15 مواقع کی متوازی جانچ۔")
        m15_fetch_tasks = [fetch_twelve_data_ohlc(pair, "15min") for pair in pairs]
        m15_results = await asyncio.gather(*m15_fetch_tasks)

        candidate_pairs = []
        for i, m15_candles in enumerate(m15_results):
            if m15_candles and len(m15_candles) >= 34:
                trend = check_m15_opportunity(pairs[i], m15_candles)
                if trend:
                    candidate_pairs.append({"symbol": pairs[i], "m15_trend": trend})
        
        if not candidate_pairs:
            logger.info("مرحلہ 1 مکمل: کسی بھی جوڑے پر M15 کا کوئی واضح موقع نہیں ملا۔")
            return

        logger.info(f"مرحلہ 2: {len(candidate_pairs)} امیدوار جوڑوں کا مکمل تجزیہ شروع کیا جا رہا ہے۔")

        # --- مرحلہ 2: امیدوار جوڑوں کا ایک ایک کرکے مکمل تجزیہ کریں ---
        for candidate in candidate_pairs:
            if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
                logger.info("سگنل کی حد تک پہنچ گئے۔ تجزیہ روکا جا رہا ہے۔")
                break

            symbol = candidate["symbol"]
            m15_trend = candidate["m15_trend"]

            # M5 ڈیٹا حاصل کریں
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
            
            # API کی حد سے بچنے کے لیے ہر مکمل تجزیے کے بعد چھوٹا سا وقفہ
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        logger.info(">>> سگنل کی تلاش کا کام مکمل ہوا۔")
        logger.info("=============================================")
        
