import asyncio
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Generator

from sqlalchemy.orm import Session

import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_real_time_quotes
from websocket_manager import manager
from trainerai import learn_from_outcome # <--- یقینی بنائیں کہ یہ امپورٹ موجود ہے

logger = logging.getLogger(__name__)

# ... (get_db_session فنکشن ویسے ہی رہے گا) ...
@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    ایک ڈیٹا بیس سیشن فراہم کرنے کے لیے ایک کانٹیکسٹ مینیجر۔
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def check_active_signals_job():
    """
    فعال سگنلز کی نگرانی کرتا ہے اور TP/SL ہٹس کو چیک کرتا ہے۔
    """
    logger.info("🛡️ نگران انجن (حتمی ورژن): نگرانی کا دور شروع...")
    
    try:
        with get_db_session() as db:
            active_signals = crud.get_all_active_signals_from_db(db)
            if not active_signals:
                logger.info("🛡️ نگران: کوئی فعال سگنل موجود نہیں۔")
                return

            logger.info(f"🛡️ نگران: {len(active_signals)} فعال سگنلز ملے، جانچ شروع کی جا رہی ہے...")
            
            symbols_to_check = list({s.symbol for s in active_signals})
            latest_quotes = await get_real_time_quotes(symbols_to_check)

            if not latest_quotes:
                logger.warning("🛡️ نگران: کوئی مارکیٹ قیمتیں حاصل نہیں ہوئیں۔")
                return

            signals_closed_count = 0
            for signal in active_signals:
                market_data = latest_quotes.get(signal.symbol)
                if not market_data or 'price' not in market_data:
                    logger.warning(f"🛡️ [{signal.symbol}] کے لیے قیمت کا ڈیٹا نہیں ملا۔")
                    continue
                
                current_price = float(market_data['price'])
                logger.info(f"🛡️ جانچ: [{signal.symbol}] | TP: {signal.tp_price} | SL: {signal.sl_price} | موجودہ قیمت: {current_price}")

                outcome, close_price, reason = None, None, None
                
                if signal.signal_type == "buy":
                    if current_price >= signal.tp_price:
                        outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit"
                    elif current_price <= signal.sl_price:
                        outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit"
                
                elif signal.signal_type == "sell":
                    if current_price <= signal.tp_price:
                        outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit"
                    elif current_price >= signal.sl_price:
                        outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit"

                if outcome:
                    logger.info(f"★★★ سگنل {signal.signal_id} کو {outcome.upper()} کے طور پر بند کیا جا رہا ہے ★★★")
                    
                    # ★★★ مرکزی تبدیلی یہاں ہے ★★★
                    # TrainerAI کو کال کریں اور اس کا لاگ شامل کریں
                    try:
                        logger.info(f"🧠 [{signal.symbol}] کے نتیجے کو سیکھنے کے لیے TrainerAI کو بھیجا جا رہا ہے...")
                        # ہم اسے ایک الگ ٹاسک میں چلائیں گے تاکہ یہ مرکزی کام کو نہ روکے
                        asyncio.create_task(learn_from_outcome(db, signal, outcome))
                        logger.info(f"🧠 TrainerAI کے لیے ٹاسک کامیابی سے بن گیا۔")
                    except Exception as e:
                        logger.error(f"🧠 TrainerAI کو کال کرنے میں خرابی: {e}", exc_info=True)

                    success = crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
                    if success:
                        signals_closed_count += 1
                        asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
            
            if signals_closed_count > 0:
                logger.info(f"{signals_closed_count} سگنلز کامیابی سے ہسٹری میں منتقل ہو گئے۔")

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🛡️ نگران انجن (حتمی ورژن): نگرانی کا دور مکمل ہوا۔")
                
