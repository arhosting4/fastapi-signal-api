# filename: feedback_checker.py

import httpx
import asyncio
import logging
from datetime import datetime, timedelta

from price_stream import get_current_price_for_symbol
from signal_tracker import get_all_signals, remove_active_signal
from database_crud import add_completed_trade, add_feedback_entry
from models import SessionLocal

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    یہ جاب تمام فعال سگنلز کی جانچ کرتی ہے اور ان کے نتیجے کا اندازہ لگاتی ہے۔
    ایک سگنل اب صرف TP یا SL پر ہی بند ہوگا۔
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

                if not all([signal_id, symbol, signal_type, tp, sl]):
                    logger.warning(f"نامکمل سگنل ڈیٹا: {signal}")
                    continue

                # قیمت اب Twelve Data WebSocket سے حاصل کی جائے گی
                current_price = get_current_price_for_symbol(symbol)
                if current_price is None:
                    # اگر قیمت دستیاب نہیں ہے، تو اگلے سگنل پر جائیں
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

                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
                # ★★★ اہم اور حتمی تبدیلی: "Expired" والی منطق کو مکمل طور پر ہٹا دیا گیا ہے ★★★
                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

                if outcome:
                    logger.info(f"★★★ سگنل کا نتیجہ: {signal_id} کو {outcome} کے طور پر نشان زد کیا گیا ★★★")
                    add_completed_trade(db, signal, outcome)
                    add_feedback_entry(db, symbol, signal.get("timeframe", "15min"), feedback)
                    remove_active_signal(signal_id)
                    
            except Exception as e:
                logger.error(f"سگنل {signal.get('signal_id')} پر کارروائی کے دوران خرابی: {e}", exc_info=True)
    finally:
        db.close()
        
