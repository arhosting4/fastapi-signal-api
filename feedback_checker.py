# filename: feedback_checker.py

import asyncio
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Generator

from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_real_time_quotes, fetch_twelve_data_ohlc
from websocket_manager import manager
from roster_manager import get_split_monitoring_roster
from trainerai import learn_from_outcome

logger = logging.getLogger(__name__)

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
    فعال سگنلز کی نگرانی کرتا ہے، TP/SL ہٹس کو چیک کرتا ہے، اور گریس پیریڈ کو منظم کرتا ہے۔
    """
    logger.info("🛡️ نگران انجن: فعال سگنلز کی نگرانی کا دور شروع...")
    
    try:
        with get_db_session() as db:
            active_signals_in_db = crud.get_all_active_signals_from_db(db)
            if not active_signals_in_db:
                logger.info("🛡️ نگران انجن: کوئی فعال سگنل موجود نہیں۔ نگرانی کا دور ختم۔")
                return

            # سگنلز کو گریس پیریڈ سے نکالیں اور چیک کرنے کے لیے اہل سگنلز کی فہرست بنائیں
            signals_to_check_now, made_grace_period_change = _manage_grace_period(active_signals_in_db)
            
            if made_grace_period_change:
                db.commit()
            
            if not signals_to_check_now:
                logger.info("🛡️ نگران انجن: چیک کرنے کے لیے کوئی اہل فعال سگنل نہیں (سب گریس پیریڈ میں ہو سکتے ہیں)۔")
                return
            
            # قیمت کا ڈیٹا حاصل کریں
            latest_quotes_memory = await _fetch_market_data(db, signals_to_check_now)
            if not latest_quotes_memory:
                logger.warning("🛡️ نگران انجن: TP/SL چیک کرنے کے لیے کوئی مارکیٹ ڈیٹا حاصل نہیں ہوا۔")
                return

            logger.info(f"🛡️ نگران انجن: {len(signals_to_check_now)} اہل فعال سگنلز کو چیک کیا جا رہا ہے...")
            await _process_signal_outcomes(db, signals_to_check_now, latest_quotes_memory)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🛡️ نگران انجن: نگرانی کا دور مکمل ہوا۔")

def _manage_grace_period(signals: List[ActiveSignal]) -> (List[ActiveSignal], bool):
    """
    سگنلز کو گریس پیریڈ سے نکالتا ہے اور چیک کرنے کے لیے اہل سگنلز کی فہرست واپس کرتا ہے۔
    """
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

async def _fetch_market_data(db: Session, signals_to_check: List[ActiveSignal]) -> Dict[str, Dict[str, Any]]:
    """
    نگرانی کے لیے ضروری مارکیٹ ڈیٹا (OHLC یا کوٹس) حاصل کرتا ہے۔
    """
    symbols_to_check = {s.symbol for s in signals_to_check}
    active_symbols_for_ohlc, inactive_symbols_for_quote = get_split_monitoring_roster(db, symbols_to_check)
    
    latest_quotes_memory: Dict[str, Dict[str, Any]] = {}

    # OHLC ڈیٹا حاصل کریں
    if active_symbols_for_ohlc:
        logger.info(f"🛡️ نگران: {len(active_symbols_for_ohlc)} فعال سگنلز کے لیے درست کینڈل ڈیٹا حاصل کیا جا رہا ہے...")
        ohlc_tasks = [fetch_twelve_data_ohlc(symbol) for symbol in active_symbols_for_ohlc]
        results = await asyncio.gather(*ohlc_tasks)
        for candles in results:
            if candles:
                latest_candle = candles[-1]
                latest_quotes_memory[latest_candle.symbol] = latest_candle.dict()

    # فوری قیمت کا ڈیٹا حاصل کریں
    if inactive_symbols_for_quote:
        logger.info(f"🛡️ نگران: {len(inactive_symbols_for_quote)} غیر فعال جوڑوں کے لیے فوری قیمت حاصل کی جا رہی ہے...")
        quotes = await get_real_time_quotes(inactive_symbols_for_quote)
        if quotes:
            latest_quotes_memory.update(quotes)
            
    return latest_quotes_memory

async def _process_signal_outcomes(db: Session, signals: List[ActiveSignal], quotes_memory: Dict[str, Any]):
    """
    ہر سگنل کو اس کی تازہ ترین قیمت کے خلاف چیک کرتا ہے اور نتیجہ پر کارروائی کرتا ہے۔
    """
    signals_closed_count = 0
    for signal in signals:
        quote_data = quotes_memory.get(signal.symbol)
        if not quote_data:
            continue

        # قیمت کی اقدار کو محفوظ طریقے سے نکالیں
        try:
            high = float(quote_data.get('high', quote_data.get('price')))
            low = float(quote_data.get('low', quote_data.get('price')))
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"🛡️ {signal.symbol} کے لیے درست قیمت کا ڈیٹا نہیں ملا۔")
            continue
        
        outcome, close_price, reason = None, None, None
        
        # TP/SL کی منطق
        if signal.signal_type == "buy":
            if high >= signal.tp_price: 
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit_by_high"
            elif low <= signal.sl_price: 
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_low"
        elif signal.signal_type == "sell":
            if low <= signal.tp_price: 
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit_by_low"
            elif high >= signal.sl_price: 
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_high"

        if outcome:
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا ({reason}) ★★★")
            
            # AI کو سیکھنے کا حکم پس منظر میں دیں تاکہ نگرانی کا عمل بلاک نہ ہو
            asyncio.create_task(learn_from_outcome(db, signal, outcome))
            
            # سگنل کو بند اور آرکائیو کریں
            success = crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
            if success:
                signals_closed_count += 1
                # فرنٹ اینڈ کو اپ ڈیٹ کرنے کے لیے ویب ساکٹ پیغام بھیجیں
                asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
    
    if signals_closed_count > 0:
        logger.info(f"🛡️ نگران انجن: کل {signals_closed_count} سگنل بند کیے گئے۔")
            
