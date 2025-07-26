# filename: feedback_checker.py

import logging
from datetime import datetime, timedelta

# مقامی امپورٹس
from signal_tracker import get_all_signals, remove_active_signal
from database_crud import add_completed_trade, add_feedback_entry
from models import SessionLocal
from price_stream import get_price_from_cache # ★★★ اہم تبدیلی ★★★

logger = logging.getLogger(__name__)
EXPIRY_MINUTES = 15

async def check_active_signals_job():
    """
    یہ جاب تمام فعال سگنلز کی جانچ کرتی ہے اور ان کے نتیجے کا اندازہ لگاتی ہے۔
    اب یہ قیمت حاصل کرنے کے لیے مقامی کیش کا استعمال کرتی ہے۔
    """
    active_signals = get_all_signals()
    if not active_signals:
        return

    db = SessionLocal()
    try:
        for signal in active_signals:
            try:
                signal_id = signal.get("signal_id")
                symbol = signal.get("symbol")
                signal_type = signal.get("signal")
                tp = signal.get("tp")
                sl = signal.get("sl")
                signal_time_str = signal.get("timestamp")

                # ★★★ اہم تبدیلی: API کال کی بجائے مقامی کیش سے قیمت حاصل کریں ★★★
                current_price = get_price_from_cache(symbol)
                
                if current_price is None:
                    # اگر قیمت ابھی تک کیش میں نہیں ہے تو اس سگنل کو چھوڑ دیں
                    logger.warning(f"{symbol} کے لیے قیمت ابھی تک WebSocket کیش میں دستیاب نہیں۔ اگلی بار چیک کیا جائے گا۔")
                    continue

                outcome = None
                feedback = None

                # TP/SL کی منطق ویسی ہی رہے گی
                if signal_type == "buy":
                    if current_price >= tp:
                        outcome = "tp_hit"; feedback = "correct"
                    elif current_price <= sl:
                        outcome = "sl_hit"; feedback = "incorrect"
                elif signal_type == "sell":
                    if current_price <= tp:
                        outcome = "tp_hit"; feedback = "correct"
                    elif current_price >= sl:
                        outcome = "sl_hit"; feedback = "incorrect"

                # ایکسپائری کی منطق ویسی ہی رہے گی
                signal_time = datetime.fromisoformat(signal_time_str)
                if outcome is None and datetime.utcnow() - signal_time >= timedelta(minutes=EXPIRY_MINUTES):
                    outcome = "expired"; feedback = "incorrect"

                if outcome:
                    add_completed_trade(db, signal, outcome)
                    add_feedback_entry(db, symbol, signal.get("timeframe", "15min"), feedback)
                    remove_active_signal(signal_id)
                    logger.info(f"سگنل {signal_id} کو {outcome} کے طور پر نشان زد کیا گیا (قیمت: {current_price})")

            except Exception as e:
                logger.error(f"سگنل {signal.get('signal_id')} پر کارروائی کے دوران خرابی: {e}")
    finally:
        db.close()
        
