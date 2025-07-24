# filename: feedback_checker.py
import httpx
import asyncio
import logging
from datetime import datetime, timedelta

import config
from signal_tracker import get_all_signals, remove_active_signal
from utils import get_current_price_twelve_data
from database_crud import add_completed_trade, add_feedback_entry
from models import SessionLocal

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    یہ کام تمام فعال سگنلز کی جانچ کرتا ہے اور ان کے نتیجے (TP/SL/Expired) کا جائزہ لیتا ہے۔
    یہ APScheduler کے ذریعے ہر منٹ چلتا ہے۔
    """
    active_signals = get_all_signals()
    if not active_signals:
        return

    logger.info(f"فیڈ بیک چیکر کام چل رہا ہے... {len(active_signals)} فعال سگنلز کا جائزہ لیا جا رہا ہے۔")

    db = SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            for signal in active_signals:
                try:
                    signal_id = signal.get("signal_id")
                    symbol = signal.get("symbol")
                    signal_type = signal.get("signal")
                    tp = signal.get("tp")
                    sl = signal.get("sl")
                    signal_time_str = signal.get("timestamp")

                    if not all([signal_id, symbol, signal_type, tp, sl, signal_time_str]):
                        logger.warning(f"نامکمل سگنل ڈیٹا، نظر انداز کیا جا رہا ہے: {signal}")
                        continue

                    signal_time = datetime.fromisoformat(signal_time_str)
                    current_price = await get_current_price_twelve_data(symbol, client)
                    if current_price is None:
                        logger.warning(f"{symbol} کے لیے قیمت حاصل کرنے میں ناکام۔")
                        continue

                    outcome = None
                    feedback = None

                    if signal_type == "buy":
                        if current_price >= tp:
                            outcome = "tp_hit"
                            feedback = "correct"
                        elif current_price <= sl:
                            outcome = "sl_hit"
                            feedback = "incorrect"
                    elif signal_type == "sell":
                        if current_price <= tp:
                            outcome = "tp_hit"
                            feedback = "correct"
                        elif current_price >= sl:
                            outcome = "sl_hit"
                            feedback = "incorrect"

                    # میعاد ختم ہونے کی جانچ
                    if outcome is None and datetime.utcnow() - signal_time >= timedelta(minutes=config.EXPIRY_MINUTES):
                        outcome = "expired"
                        feedback = "incorrect" # میعاد ختم ہونے والے سگنل کو غلط سمجھا جاتا ہے

                    # اگر نتیجہ طے ہو جائے تو ریکارڈ کریں اور ہٹا دیں
                    if outcome:
                        logger.info(f"سگنل {signal_id} ({symbol}) کو {outcome} کے طور پر نشان زد کیا گیا۔ قیمت: {current_price}")
                        add_completed_trade(db, signal, outcome)
                        add_feedback_entry(db, symbol, signal.get("timeframe", config.PRIMARY_TIMEFRAME), feedback)
                        remove_active_signal(signal_id)

                except Exception as e:
                    logger.error(f"سگنل {signal.get('signal_id')} پر کارروائی کرتے ہوئے خرابی: {e}", exc_info=True)
    finally:
        db.close()
        
