# filename: feedback_checker.py

import asyncio
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Generator

from sqlalchemy.orm import Session

import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_real_time_quotes
from websocket_manager import manager
from trainerai import learn_from_outcome

logger = logging.getLogger(__name__)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def check_active_signals_job():
    logger.info("🛡️ نگران انجن (اسنائپر): فعال سگنلز کی نگرانی کا دور شروع...")
    
    try:
        with get_db_session() as db:
            active_signals_in_db = crud.get_all_active_signals_from_db(db)
            if not active_signals_in_db:
                logger.info("🛡️ نگران انجن: کوئی فعال سگنل موجود نہیں۔ نگرانی کا دور ختم۔")
                return

            signals_to_check_now, made_grace_period_change = _manage_grace_period(active_signals_in_db)
            
            if made_grace_period_change:
                db.commit()
            
            if not signals_to_check_now:
                logger.info("🛡️ نگران انجن: چیک کرنے کے لیے کوئی اہل فعال سگنل نہیں (سب گریس پیریڈ میں ہیں)۔")
                return
            
            symbols_to_check = list({s.symbol for s in signals_to_check_now})
            logger.info(f"🛡️ نگران: {len(symbols_to_check)} علامتوں کے لیے حقیقی وقت کی قیمتیں حاصل کی جا رہی ہیں...")
            latest_quotes = await get_real_time_quotes(symbols_to_check)

            if not latest_quotes:
                logger.warning("🛡️ نگران انجن: TP/SL چیک کرنے کے لیے کوئی مارکیٹ ڈیٹا حاصل نہیں ہوا۔")
                return

            logger.info(f"🛡️ نگران انجن: {len(signals_to_check_now)} اہل فعال سگنلز کو چیک کیا جا رہا ہے...")
            await _process_signal_outcomes(db, signals_to_check_now, latest_quotes)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🛡️ نگران انجن (اسنائپر): نگرانی کا دور مکمل ہوا۔")

def _manage_grace_period(signals: List[ActiveSignal]) -> (List[ActiveSignal], bool):
    signals_to_check = []
    grace_period_changed = False
    for signal in signals:
        if signal.is_new:
            logger.info(f"🛡️ سگنل {signal.symbol} گریس پیریڈ میں ہے۔ اسے اگلی بار چیک کیا جائے گا۔")
            signal.is_new = False
            grace_period_changed = True
        else:
            signals_to_check.append(signal)
    return signals_to_check, grace_period_changed

async def _process_signal_outcomes(db: Session, signals: List[ActiveSignal], quotes: Dict[str, Any]):
    signals_closed_count = 0
    for signal in signals:
        quote_data = quotes.get(signal.symbol)
        if not quote_data or 'price' not in quote_data:
            logger.warning(f"🛡️ {signal.symbol} کے لیے درست قیمت کا ڈیٹا نہیں ملا۔")
            continue

        try:
            current_price = float(quote_data['price'])
        except (ValueError, TypeError):
            logger.warning(f"🛡️ {signal.symbol} کے لیے قیمت کو فلوٹ میں تبدیل نہیں کیا جا سکا۔")
            continue
        
        outcome, close_price, reason = None, None, None
        
        if signal.signal_type == "buy":
            # --- "پروجیکٹ اسنائپر" کی منطق یہاں ہے ---
            if current_price >= signal.tp_price: 
                # TP کو اصل قیمت پر بند کریں جو TP سے زیادہ یا برابر ہے
                outcome, close_price, reason = "tp_hit", current_price, "tp_hit_by_price"
            elif current_price <= signal.sl_price: 
                # SL کو طے شدہ قیمت پر ہی بند کریں تاکہ نقصان زیادہ نہ ہو
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_price"
        elif signal.signal_type == "sell":
            # --- "پروجیکٹ اسنائپر" کی منطق یہاں ہے ---
            if current_price <= signal.tp_price: 
                # TP کو اصل قیمت پر بند کریں جو TP سے کم یا برابر ہے
                outcome, close_price, reason = "tp_hit", current_price, "tp_hit_by_price"
            elif current_price >= signal.sl_price: 
                # SL کو طے شدہ قیمت پر ہی بند کریں
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_price"

        if outcome:
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا ({reason})۔ بند ہونے کی قیمت: {close_price} ★★★")
            
            asyncio.create_task(learn_from_outcome(db, signal, outcome))
            
            success = crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
            if success:
                signals_closed_count += 1
                asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
    
    if signals_closed_count > 0:
        logger.info(f"🛡️ نگران انجن: کل {signals_closed_count} سگنل بند کیے گئے۔")
            
