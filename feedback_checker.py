# filename: feedback_checker.py

import asyncio
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Generator

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# مقامی امپورٹس
# --- ہم CRUD پر انحصار ختم کر رہے ہیں ---
from models import SessionLocal, ActiveSignal, CompletedTrade # براہ راست ماڈلز استعمال کریں
from utils import get_real_time_quotes, fetch_twelve_data_ohlc
from websocket_manager import manager
from trainerai import learn_from_outcome

logger = logging.getLogger(__name__)

# --- براہ راست ڈیٹا بیس کے فنکشنز ---

def get_all_active_signals_direct(db: Session) -> List[ActiveSignal]:
    """براہ راست ڈیٹا بیس سے تمام فعال سگنلز حاصل کرتا ہے۔"""
    try:
        return db.query(ActiveSignal).all()
    except SQLAlchemyError as e:
        logger.error(f"براہ راست فعال سگنلز حاصل کرنے میں خرابی: {e}", exc_info=True)
        return []

def close_and_archive_signal_direct(db: Session, signal_id: str, outcome: str, close_price: float, reason: str) -> bool:
    """براہ راست سگنل کو بند اور آرکائیو کرتا ہے۔"""
    try:
        signal_to_delete = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()
        if not signal_to_delete:
            logger.warning(f"بند کرنے کے لیے سگنل {signal_id} نہیں ملا۔")
            return False

        completed_trade = CompletedTrade(
            signal_id=signal_to_delete.signal_id, symbol=signal_to_delete.symbol,
            timeframe=signal_to_delete.timeframe, signal_type=signal_to_delete.signal_type,
            entry_price=signal_to_delete.entry_price, tp_price=signal_to_delete.tp_price,
            sl_price=signal_to_delete.sl_price, close_price=close_price,
            reason_for_closure=reason, outcome=outcome, confidence=signal_to_delete.confidence,
            reason=signal_to_delete.reason, created_at=signal_to_delete.created_at,
            closed_at=signal_to_delete.updated_at # Use updated_at for close time
        )
        db.add(completed_trade)
        db.delete(signal_to_delete)
        db.commit()
        logger.info(f"سگنل {signal_id} کامیابی سے ہسٹری میں منتقل ہو گیا۔")
        return True
    except SQLAlchemyError as e:
        logger.error(f"سگنل {signal_id} کو بند کرنے میں خرابی: {e}", exc_info=True)
        db.rollback()
        return False

# --- مرکزی جاب ---

async def check_active_signals_job():
    logger.info("🛡️ نگران انجن (ورژن 4.0 - خود مختار): نگرانی کا دور شروع...")
    
    db = SessionLocal()
    try:
        signals_to_check = get_all_active_signals_direct(db)
        
        if not signals_to_check:
            logger.info("🛡️ نگران: کوئی فعال سگنل موجود نہیں۔")
            return

        logger.info(f"🛡️ نگران: {len(signals_to_check)} فعال سگنلز ملے، جانچ شروع کی جا رہی ہے...")
        
        symbols = list({s.symbol for s in signals_to_check})
        latest_quotes = await get_real_time_quotes(symbols)

        if not latest_quotes:
            logger.warning("🛡️ نگران: کوئی مارکیٹ قیمتیں حاصل نہیں ہوئیں۔")
            return

        for signal in signals_to_check:
            quote = latest_quotes.get(signal.symbol)
            if not quote or 'price' not in quote:
                continue
            
            try:
                current_price = float(quote['price'])
            except (ValueError, TypeError):
                logger.warning(f"🛡️ [{signal.symbol}] کے لیے قیمت کو فلوٹ میں تبدیل نہیں کیا جا سکا: '{quote['price']}'")
                continue

            logger.info(f"🛡️ جانچ: [{signal.symbol}] | قسم: {signal.signal_type} | TP: {signal.tp_price} | SL: {signal.sl_price} | موجودہ قیمت: {current_price}")

            await _process_single_signal(db, signal, {"price": current_price})

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    finally:
        db.close() # سیشن کو ہمیشہ بند کریں
    
    logger.info("🛡️ نگران انجن (ورژن 4.0): نگرانی کا دور مکمل ہوا۔")


async def _process_single_signal(db: Session, signal: ActiveSignal, market_data: Dict[str, Any]):
    live_signal = db.query(ActiveSignal).filter(ActiveSignal.id == signal.id).first()
    if not live_signal:
        return

    current_price = market_data.get('price')
    outcome, reason = None, None
    tp, sl = float(live_signal.tp_price), float(live_signal.sl_price)

    if live_signal.signal_type == "buy":
        if current_price >= tp: outcome, reason = "tp_hit", "TP Hit"
        elif current_price <= sl: outcome, reason = "sl_hit", "SL Hit"
    elif live_signal.signal_type == "sell":
        if current_price <= tp: outcome, reason = "tp_hit", "TP Hit"
        elif current_price >= sl: outcome, reason = "sl_hit", "SL Hit"

    if outcome:
        logger.info(f"★★★ سگنل کا نتیجہ: {live_signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا۔ بند ہونے کی قیمت: {current_price} ★★★")
        
        # یہ فنکشنز اب بھی کام کریں گے کیونکہ وہ صرف ڈیٹا استعمال کرتے ہیں
        asyncio.create_task(learn_from_outcome(db, live_signal, outcome))
        
        success = close_and_archive_signal_direct(db, live_signal.signal_id, outcome, float(current_price), reason)
        if success:
            asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": live_signal.signal_id}}))
    
