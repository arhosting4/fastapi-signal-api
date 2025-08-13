# filename: feedback_checker.py

import asyncio
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Generator

from sqlalchemy.orm import Session
import pandas as pd

import database_crud as crud
from models import SessionLocal, ActiveSignal
# --- دونوں فنکشنز کو واپس لایا گیا ---
from utils import get_real_time_quotes, fetch_twelve_data_ohlc, convert_candles_to_dataframe
from websocket_manager import manager
from trainerai import learn_from_outcome
from roster_manager import get_split_monitoring_roster # تقسیم کرنے والی منطق واپس لائی گئی
from config import api_settings

logger = logging.getLogger(__name__)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def check_active_signals_job():
    logger.info("🛡️ نگران انجن (فینکس): فعال سگنلز کی نگرانی کا دور شروع...")
    
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
            
            # --- ذہین ڈیٹا حاصل کرنے کا عمل واپس لایا گیا ---
            market_data = await _fetch_intelligent_market_data(db, signals_to_check_now)

            if not market_data:
                logger.warning("🛡️ نگران انجن: TP/SL چیک کرنے کے لیے کوئی مارکیٹ ڈیٹا حاصل نہیں ہوا۔")
                return

            logger.info(f"🛡️ نگران انجن: {len(signals_to_check_now)} اہل فعال سگنلز کو چیک کیا جا رہا ہے...")
            await _process_signal_outcomes(db, signals_to_check_now, market_data)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🛡️ نگران انجن (فینکس): نگرانی کا دور مکمل ہوا۔")

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

async def _fetch_intelligent_market_data(db: Session, signals: List[ActiveSignal]) -> Dict[str, Dict[str, Any]]:
    """
    API کی حد سے بچنے کے لیے ذہانت سے مارکیٹ ڈیٹا حاصل کرتا ہے۔
    """
    symbols_to_check = {s.symbol for s in signals}
    # roster_manager کا استعمال کرتے ہوئے جوڑوں کو تقسیم کریں
    ohlc_pairs, quote_pairs = get_split_monitoring_roster(db, symbols_to_check)
    
    market_data: Dict[str, Dict[str, Any]] = {}

    # OHLC ڈیٹا حاصل کریں
    if ohlc_pairs:
        logger.info(f"🛡️ نگران: {len(ohlc_pairs)} جوڑوں کے لیے OHLC ڈیٹا حاصل کیا جا رہا ہے۔")
        tasks = [fetch_twelve_data_ohlc(pair, "1min", 2) for pair in ohlc_pairs] # 1 منٹ کا ڈیٹا
        results = await asyncio.gather(*tasks)
        for candles in results:
            if candles:
                # تازہ ترین کینڈل کی قیمت کو استعمال کریں
                latest_candle = candles[-1]
                market_data[latest_candle.symbol] = {"price": latest_candle.close}

    # Quote ڈیٹا حاصل کریں
    if quote_pairs:
        logger.info(f"🛡️ نگران: {len(quote_pairs)} جوڑوں کے لیے فوری قیمت حاصل کی جا رہی ہے۔")
        quotes = await get_real_time_quotes(quote_pairs)
        if quotes:
            for symbol, data in quotes.items():
                if 'price' in data:
                    market_data[symbol] = {"price": float(data['price'])}
            
    return market_data

async def _process_signal_outcomes(db: Session, signals: List[ActiveSignal], market_data: Dict[str, Any]):
    # یہ فنکشن اب "پروجیکٹ اسنائپر" والے ورژن جیسا ہی رہے گا
    signals_closed_count = 0
    for signal in signals:
        quote_data = market_data.get(signal.symbol)
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
            if current_price >= signal.tp_price: 
                outcome, close_price, reason = "tp_hit", current_price, "tp_hit_by_price"
            elif current_price <= signal.sl_price: 
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_price"
        elif signal.signal_type == "sell":
            if current_price <= signal.tp_price: 
                outcome, close_price, reason = "tp_hit", current_price, "tp_hit_by_price"
            elif current_price >= signal.sl_price: 
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
    
