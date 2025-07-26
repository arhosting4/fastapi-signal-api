import httpx
import asyncio
import logging
from datetime import datetime, timedelta

# config.py پر انحصار ختم کر دیا گیا ہے
# import config
from signal_tracker import get_all_signals, remove_active_signal
from utils import get_current_price_twelve_data
from database_crud import add_completed_trade, add_feedback_entry
from models import SessionLocal

logger = logging.getLogger(__name__)

# ==============================================================================
# کنفیگریشن پیرامیٹرز براہ راست یہاں شامل کر دیے گئے ہیں
# ==============================================================================
EXPIRY_MINUTES = 15
# ==============================================================================

async def check_active_signals_job():
    """
    یہ جاب تمام فعال سگنلز کی جانچ کرتی ہے اور ان کے نتیجے کا اندازہ لگاتی ہے۔
    """
    active_signals = get_all_signals()
    if not active_signals:
        return

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
                        logger.warning(f"نامکمل سگنل ڈیٹا: {signal}")
                        continue

                    signal_time = datetime.fromisoformat(signal_time_str)
                    current_price = await get_current_price_twelve_data(symbol, client)
                    if current_price is None:
                        logger.warning(f"{symbol} کے لیے قیمت حاصل کرنے میں ناکامی")
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

                    if outcome is None and datetime.utcnow() - signal_time >= timedelta(minutes=EXPIRY_MINUTES):
                        outcome = "expired"
                        feedback = "incorrect"

                    if outcome:
                        add_completed_trade(db, signal, outcome)
                        add_feedback_entry(db, symbol, signal.get("timeframe", "15min"), feedback)
                        remove_active_signal(signal_id)
                        logger.info(f"سگنل {signal_id} کو {outcome} کے طور پر نشان زد کیا گیا")

                except Exception as e:
                    logger.error(f"سگنل {signal.get('signal_id')} پر کارروائی کے دوران خرابی: {e}")
    finally:
        db.close()
        
