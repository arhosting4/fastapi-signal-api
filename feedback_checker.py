# filename: feedback_checker.py

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_real_time_quotes, fetch_twelve_data_ohlc
from websocket_manager import manager
from roster_manager import get_split_monitoring_roster

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    یہ فنکشن اب دو اہم کام کرتا ہے:
    1. روسٹر مینیجر سے نگرانی کی متحرک فہرست حاصل کرتا ہے۔
    2. ان جوڑوں کی قیمتیں لا کر 'مرکزی یادداشت' کو اپ ڈیٹ کرتا ہے اور فعال سگنلز کو چیک کرتا ہے۔
    ★★★ اب یہ "گریس پیریڈ" پروٹوکول کا بھی استعمال کرتا ہے۔ ★★★
    """
    logger.info("🛡️ نگران انجن: نگرانی کا نیا، ذہین دور شروع...")
    
    db = SessionLocal()
    try:
        active_signals_in_db = crud.get_all_active_signals_from_db(db)
        
        if not active_signals_in_db:
            logger.info("🛡️ نگران انجن: کوئی فعال سگنل موجود نہیں۔")
            return

        # --- گریس پیریڈ کی منطق ---
        signals_to_check_now = []
        made_grace_period_change = False
        for signal in active_signals_in_db:
            if signal.is_new:
                logger.info(f"🛡️ سگنل {signal.symbol} گریس پیریڈ میں ہے۔ اسے اگلی بار چیک کیا جائے گا۔")
                signal.is_new = False
                made_grace_period_change = True
            else:
                signals_to_check_now.append(signal)
        
        # ★★★ یہاں تبدیلی کی گئی ہے ★★★
        # اگر کوئی بھی فلیگ تبدیل ہوا ہے، تو اسے ڈیٹا بیس میں محفوظ کریں
        if made_grace_period_change:
            db.commit()
        
        if not signals_to_check_now:
            logger.info("🛡️ نگران انجن: چیک کرنے کے لیے کوئی اہل فعال سگنل نہیں (سب گریس پیریڈ میں ہو سکتے ہیں)۔")
            # یہاں سے stats_update بھیجنے کی ضرورت نہیں کیونکہ یہ کام اب فرنٹ اینڈ خود کر رہا ہے
            return
        
        # --- ڈیٹا حاصل کرنے کی منطق ---
        symbols_to_check = {s.symbol for s in signals_to_check_now}
        
        active_symbols_for_ohlc, inactive_symbols_for_quote = get_split_monitoring_roster(db, symbols_to_check)
        
        latest_quotes_memory: Dict[str, Dict[str, Any]] = {}

        if active_symbols_for_ohlc:
            logger.info(f"🛡️ نگران: {len(active_symbols_for_ohlc)} فعال سگنلز کے لیے درست کینڈل ڈیٹا حاصل کیا جا رہا ہے...")
            ohlc_tasks = [fetch_twelve_data_ohlc(symbol) for symbol in active_symbols_for_ohlc]
            results = await asyncio.gather(*ohlc_tasks)
            for candles in results:
                if candles:
                    latest_candle = candles[-1]
                    latest_quotes_memory[latest_candle.symbol] = latest_candle.dict()

        if inactive_symbols_for_quote:
            logger.info(f"🛡️ نگران: {len(inactive_symbols_for_quote)} غیر فعال جوڑوں کے لیے فوری قیمت حاصل کی جا رہی ہے...")
            quotes = await get_real_time_quotes(inactive_symbols_for_quote)
            if quotes:
                latest_quotes_memory.update(quotes)
        
        if not latest_quotes_memory:
            logger.warning("🛡️ نگران انجن: TP/SL چیک کرنے کے لیے کوئی ڈیٹا حاصل نہیں ہوا۔")
            return

        logger.info(f"✅ مرکزی یادداشت اپ ڈیٹ ہوئی۔ کل یادداشت میں {len(latest_quotes_memory)} جوڑوں کا ڈیٹا ہے۔")
        
        logger.info(f"🛡️ نگران انجن: {len(signals_to_check_now)} اہل فعال سگنلز کو چیک کیا جا رہا ہے...")
        await check_signals_for_tp_sl(db, signals_to_check_now, latest_quotes_memory)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🛡️ نگران انجن: نگرانی کا دور مکمل ہوا۔")


async def check_signals_for_tp_sl(db: Session, signals: List[ActiveSignal], quotes_memory: Dict[str, Any]):
    """یہ فنکشن تمام فعال سگنلز کو مرکزی یادداشت سے چیک کرتا ہے۔"""
    signals_closed_count = 0
    for signal in signals:
        if signal.symbol not in quotes_memory:
            continue

        quote_data = quotes_memory.get(signal.symbol)
        if not quote_data: continue
        
        current_high = quote_data.get('high')
        current_low = quote_data.get('low')
        
        if current_high is None or current_low is None:
            price = quote_data.get('price')
            if price is None: continue
            try:
                current_high = float(price)
                current_low = float(price)
            except (ValueError, TypeError): continue
        
        outcome, close_price, reason = None, None, None
        
        if signal.signal_type == "buy":
            if current_high >= signal.tp_price: 
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit_by_high"
            elif current_low <= signal.sl_price: 
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_low"
        elif signal.signal_type == "sell":
            if current_low <= signal.tp_price: 
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit_by_low"
            elif current_high >= signal.sl_price: 
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_high"

        if outcome:
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا ({reason}) ★★★")
            success = crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
            if success:
                signals_closed_count += 1
                asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
    
    if signals_closed_count > 0:
        logger.info(f"🛡️ نگران انجن: کل {signals_closed_count} سگنل بند کیے گئے۔")
            
