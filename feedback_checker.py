# filename: feedback_checker.py

import httpx
import asyncio
import logging
from datetime import datetime, timedelta

# مقامی امپورٹس
from signal_tracker import get_all_signals, remove_active_signal
from utils import get_current_price_twelve_data
from database_crud import add_completed_trade, add_feedback_entry
from models import SessionLocal
from websocket_manager import manager # <-- ★★★ نیا اور اہم امپورٹ ★★★

logger = logging.getLogger(__name__)

# کنفیگریشن
EXPIRY_MINUTES = 15

async def check_active_signals_job():
    """
    یہ جاب تمام فعال سگنلز کی جانچ کرتی ہے، ان کے نتیجے کا اندازہ لگاتی ہے،
    اور فرنٹ اینڈ کو سگنل بند ہونے کی اطلاع دیتی ہے۔
    """
    active_signals = get_all_signals()
    if not active_signals:
        return

    db = SessionLocal()
    try:
        async with httpx.AsyncClient() as client:
            # ایک ساتھ تمام سگنلز پر کام کرنے کے لیے ٹاسک بنائیں
            tasks = []
            for signal in active_signals:
                tasks.append(process_single_signal(db, signal, client))
            
            await asyncio.gather(*tasks)

    finally:
        db.close()

async def process_single_signal(db, signal, client):
    """ایک انفرادی سگنل پر کارروائی کرتا ہے۔"""
    try:
        signal_id = signal.get("signal_id")
        symbol = signal.get("symbol")
        signal_type = signal.get("signal")
        tp = signal.get("tp")
        sl = signal.get("sl")
        signal_time_str = signal.get("timestamp")

        if not all([signal_id, symbol, signal_type, tp, sl, signal_time_str]):
            logger.warning(f"نامکمل سگنل ڈیٹا: {signal}")
            return

        signal_time = datetime.fromisoformat(signal_time_str)
        current_price = await get_current_price_twelve_data(symbol, client)
        if current_price is None:
            logger.warning(f"[{symbol}] کے لیے قیمت حاصل کرنے میں ناکامی")
            return

        outcome = None
        feedback = None

        # نتیجے کا تعین
        if signal_type == "buy":
            if current_price >= tp: outcome, feedback = "tp_hit", "correct"
            elif current_price <= sl: outcome, feedback = "sl_hit", "incorrect"
        elif signal_type == "sell":
            if current_price <= tp: outcome, feedback = "tp_hit", "correct"
            elif current_price >= sl: outcome, feedback = "sl_hit", "incorrect"

        # میعاد ختم ہونے کی جانچ
        if outcome is None and datetime.utcnow() - signal_time >= timedelta(minutes=EXPIRY_MINUTES):
            outcome, feedback = "expired", "incorrect"

        # اگر کوئی نتیجہ نکل آیا ہے
        if outcome:
            logger.info(f"سگنل [{signal_id}] کا نتیجہ '{outcome}' ہے۔ اسے بند کیا جا رہا ہے۔")
            
            # 1. ڈیٹا بیس میں مکمل شدہ ٹریڈ شامل کریں (یہ history.html پر نظر آئے گی)
            add_completed_trade(db, signal, outcome)
            add_feedback_entry(db, symbol, signal.get("timeframe", "M5/M15"), feedback)
            
            # 2. فعال سگنلز کی فہرست سے ہٹائیں
            remove_active_signal(signal_id)
            
            # 3. ★★★ فرنٹ اینڈ کو اطلاع بھیجیں کہ سگنل بند ہو گیا ہے ★★★
            await manager.broadcast({
                "type": "signal_closed",
                "data": {"signal_id": signal_id}
            })
            logger.info(f"فرنٹ اینڈ کو سگنل [{signal_id}] کے بند ہونے کی اطلاع بھیج دی گئی۔")

    except Exception as e:
        logger.error(f"سگنل [{signal.get('signal_id')}] پر کارروائی کے دوران خرابی: {e}", exc_info=True)

