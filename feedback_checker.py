# filename: feedback_checker.py

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

import database_crud as crud
from config import trading_settings
from models import ActiveSignal, SessionLocal
from roster_manager import get_split_monitoring_roster
from trainerai import learn_from_outcome
from utils import fetch_twelve_data_ohlc, get_real_time_quotes
from websocket_manager import manager

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    logger.info("🛡️ نگران انجن: فعال سگنلز کی نگرانی کا دور شروع...")
    db = SessionLocal()
    try:
        active_signals_in_db = crud.get_all_active_signals_from_db(db)
        if not active_signals_in_db:
            logger.info("🛡️ نگران انجن: کوئی فعال سگنل موجود نہیں۔")
            return

        signals_to_check_now = []
        made_grace_period_change = False

        for signal in active_signals_in_db:
            if signal.is_new:
                logger.info(f"🛡️ سگنل {signal.symbol} گریس پیریڈ میں ہے۔ اسے اگلی بار چیک کیا جائے گا۔")
                signal.is_new = False
                made_grace_period_change = True
            else:
                signals_to_check_now.append(signal)
        
        if made_grace_period_change:
            db.commit()
        
        if not signals_to_check_now:
            logger.info("🛡️ نگران انجن: چیک کرنے کے لیے کوئی اہل فعال سگنل نہیں (سب گریس پیریڈ میں ہو سکتے ہیں)۔")
            return
        
        symbols_to_check = {s.symbol for s in signals_to_check_now}
        active_symbols_for_ohlc, inactive_symbols_for_quote = get_split_monitoring_roster(db, symbols_to_check)
        
        latest_quotes_memory: Dict[str, Dict[str, Any]] = {}

        if active_symbols_for_ohlc:
            ohlc_tasks = [fetch_twelve_data_ohlc(symbol) for symbol in active_symbols_for_ohlc]
            results = await asyncio.gather(*ohlc_tasks)
            for candles in results:
                if candles:
                    latest_candle = candles[-1]
                    latest_quotes_memory[latest_candle.symbol] = latest_candle.dict()

        if inactive_symbols_for_quote:
            quotes = await get_real_time_quotes(inactive_symbols_for_quote)
            if quotes:
                latest_quotes_memory.update(quotes)
        
        if not latest_quotes_memory:
            logger.warning("🛡️ نگران انجن: TP/SL چیک کرنے کے لیے کوئی ڈیٹا حاصل نہیں ہوا۔")
            return

        await check_signals_for_tp_sl(db, signals_to_check_now, latest_quotes_memory)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()

async def check_signals_for_tp_sl(db: Session, signals: List[ActiveSignal], quotes_memory: Dict[str, Any]):
    signals_closed_count = 0
    for signal in signals:
        quote_data = quotes_memory.get(signal.symbol)
        if not quote_data: continue
        
        current_high = quote_data.get('high')
        current_low = quote_data.get('low')
        actual_close_price = quote_data.get('close') or quote_data.get('price')

        if current_high is None or current_low is None or actual_close_price is None: continue
        
        try:
            current_high, current_low, actual_close_price = float(current_high), float(current_low), float(actual_close_price)
        except (ValueError, TypeError): continue

        outcome, reason = None, None
        
        if signal.signal_type == "buy":
            if current_high >= signal.tp_price: outcome, reason = "tp_hit", "tp_hit_by_high"
            elif current_low <= signal.sl_price: outcome, reason = "sl_hit", "sl_hit_by_low"
        elif signal.signal_type == "sell":
            if current_low <= signal.tp_price: outcome, reason = "tp_hit", "tp_hit_by_low"
            elif current_high >= signal.sl_price: outcome, reason = "sl_hit", "sl_hit_by_high"

        if outcome:
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا ({reason}) ★★★")
            await learn_from_outcome(db, signal, outcome)
            success = crud.close_and_archive_signal(db, signal.signal_id, outcome, actual_close_price, reason)
            if success:
                signals_closed_count += 1
                asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
            
