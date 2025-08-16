import asyncio
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Generator
from datetime import datetime

from sqlalchemy.orm import Session

import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_real_time_quotes
from websocket_manager import manager
from trainerai import learn_from_outcome
from roster_manager import get_forex_pairs, get_crypto_pairs

logger = logging.getLogger(__name__)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def check_active_signals_job():
    """
    ایک خود مختار نگران انجن جو دن کے لحاظ سے اپنے کام کو ایڈجسٹ کرتا ہے۔
    - ہفتے کے دنوں میں: فاریکس اور کرپٹو دونوں کی نگرانی کرتا ہے۔
    - اختتام ہفتہ پر: صرف کرپٹو کی نگرانی کرتا ہے اور باقی رہ جانے والے فاریکس سگنلز کو بند کرتا ہے۔
    """
    logger.info("🛡️ خود مختار نگران انجن (ورژن 5.0): نگرانی کا دور شروع...")
    is_weekend = datetime.utcnow().weekday() >= 5  # 5 = Saturday, 6 = Sunday

    try:
        with get_db_session() as db:
            all_active_signals = crud.get_all_active_signals_from_db(db)
            if not all_active_signals:
                logger.info("🛡️ کوئی فعال سگنل موجود نہیں۔")
                return

            forex_pairs = get_forex_pairs()
            signals_to_monitor = []
            
            # ★★★ مرکزی ذہانت یہاں ہے ★★★
            if is_weekend:
                logger.info("📅 اختتام ہفتہ موڈ فعال۔ صرف کرپٹو کی نگرانی کی جائے گی۔")
                for signal in all_active_signals:
                    if signal.symbol in forex_pairs:
                        # اگر ویک اینڈ پر کوئی فاریکس سگنل فعال ہے تو اسے بند کر دیں
                        logger.warning(f"🚨 ویک اینڈ پر فعال فاریکس سگنل [{signal.symbol}] ملا۔ اسے زبردستی بند کیا جا رہا ہے۔")
                        await close_signal(db, signal, "weekend_force_close", signal.entry_price)
                    else:
                        # یہ ایک کرپٹو سگنل ہے، اسے نگرانی کے لیے شامل کریں
                        signals_to_monitor.append(signal)
            else:
                # ہفتے کے دنوں میں تمام سگنلز کی نگرانی کریں
                logger.info("📅 ہفتے کا دن موڈ فعال۔ تمام سگنلز کی نگرانی کی جائے گی۔")
                signals_to_monitor = all_active_signals

            if not signals_to_monitor:
                logger.info("🛡️ نگرانی کے لیے کوئی اہل سگنل نہیں۔")
                return

            logger.info(f"🛡️ {len(signals_to_monitor)} اہل سگنلز کی نگرانی کی جا رہی ہے...")
            
            symbols_to_check = [s.symbol for s in signals_to_monitor]
            latest_quotes = await get_real_time_quotes(symbols_to_check)

            if not latest_quotes:
                logger.warning("🛡️ کوئی مارکیٹ قیمتیں حاصل نہیں ہوئیں۔")
                return

            for signal in signals_to_monitor:
                market_data = latest_quotes.get(signal.symbol)
                if not market_data or 'price' not in market_data:
                    logger.warning(f"🛡️ [{signal.symbol}] کے لیے قیمت کا ڈیٹا نہیں ملا۔")
                    continue
                
                current_price = float(market_data['price'])
                logger.info(f"🛡️ جانچ: [{signal.symbol}] | TP: {signal.tp_price} | SL: {signal.sl_price} | موجودہ قیمت: {current_price}")

                outcome, close_price = None, None
                
                if signal.signal_type == "buy":
                    if current_price >= signal.tp_price:
                        outcome, close_price = "tp_hit", signal.tp_price
                    elif current_price <= signal.sl_price:
                        outcome, close_price = "sl_hit", signal.sl_price
                
                elif signal.signal_type == "sell":
                    if current_price <= signal.tp_price:
                        outcome, close_price = "tp_hit", signal.tp_price
                    elif current_price >= signal.sl_price:
                        outcome, close_price = "sl_hit", signal.sl_price

                if outcome:
                    await close_signal(db, signal, outcome, close_price)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🛡️ خود مختار نگران انجن: نگرانی کا دور مکمل ہوا۔")


async def close_signal(db: Session, signal: ActiveSignal, outcome: str, close_price: float):
    """
    ایک سگنل کو بند کرنے، ٹرینر کو مطلع کرنے، اور براڈکاسٹ کرنے کے لیے مرکزی فنکشن۔
    """
    logger.info(f"★★★ سگنل {signal.signal_id} کو {outcome.upper()} کے طور پر بند کیا جا رہا ہے ★★★")
    
    # TrainerAI کو کال کریں (اگر نتیجہ TP یا SL ہٹ ہے)
    if outcome in ["tp_hit", "sl_hit"]:
        try:
            logger.info(f"🧠 [{signal.symbol}] کے نتیجے کو سیکھنے کے لیے TrainerAI کو بھیجا جا رہا ہے...")
            asyncio.create_task(learn_from_outcome(db, signal, outcome))
            logger.info(f"🧠 TrainerAI کے لیے ٹاسک کامیابی سے بن گیا۔")
        except Exception as e:
            logger.error(f"🧠 TrainerAI کو کال کرنے میں خرابی: {e}", exc_info=True)

    # ڈیٹا بیس میں سگنل کو بند اور آرکائیو کریں
    success = crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, outcome)
    if success:
        logger.info(f"🗄️ سگنل {signal.signal_id} کامیابی سے ہسٹری میں منتقل ہو گیا۔")
        # فرنٹ اینڈ کو اپ ڈیٹ بھیجیں
        await manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}})
                        
