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
from trainerai import learn_from_outcome

logger = logging.getLogger(__name__)

PROXIMITY_THRESHOLD_PERCENT = 0.20

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def check_active_signals_job():
    logger.info("🛡️ نگران انجن (ورژن 2.0 - مضبوط): نگرانی کا دور شروع...")
    
    try:
        with get_db_session() as db:
            active_signals = crud.get_all_active_signals_from_db(db)
            if not active_signals:
                logger.info("🛡️ نگران: کوئی فعال سگنل موجود نہیں۔")
                return

            signals_to_check, made_change = _manage_grace_period(active_signals)
            if made_change:
                db.commit()
            
            if not signals_to_check:
                logger.info("🛡️ نگران: چیک کرنے کے لیے کوئی اہل سگنل نہیں (سب گریس پیریڈ میں ہیں)۔")
                return

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
                    # --- سب سے اہم اصلاح: قیمت کو فلوٹ میں تبدیل کرنا ---
                    current_price = float(quote['price'])
                except (ValueError, TypeError):
                    logger.warning(f"🛡️ [{signal.symbol}] کے لیے قیمت کو فلوٹ میں تبدیل نہیں کیا جا سکا: '{quote['price']}'")
                    continue

                # تفصیلی لاگنگ
                logger.info(f"🛡️ جانچ: [{signal.symbol}] | قسم: {signal.signal_type} | TP: {signal.tp_price} | SL: {signal.sl_price} | موجودہ قیمت: {current_price}")

                is_close_to_tp = abs(current_price - signal.tp_price) <= abs(signal.entry_price - signal.tp_price) * PROXIMITY_THRESHOLD_PERCENT
                is_close_to_sl = abs(current_price - signal.sl_price) <= abs(signal.entry_price - signal.sl_price) * PROXIMITY_THRESHOLD_PERCENT

                if is_close_to_tp or is_close_to_sl:
                    logger.info(f"🛡️ [{signal.symbol}] قیمت ہدف کے قریب ہے۔ تفصیلی جانچ کی جا رہی ہے۔")
                    ohlc_data = await fetch_twelve_data_ohlc(signal.symbol, "1min", 2)
                    market_data = {"price": current_price}
                    if ohlc_data:
                        market_data['high'] = float(ohlc_data[-1].high)
                        market_data['low'] = float(ohlc_data[-1].low)
                    await _process_single_signal(db, signal, market_data)
                else:
                    await _process_single_signal(db, signal, {"price": current_price})

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🛡️ نگران انجن (ورژن 2.0): نگرانی کا دور مکمل ہوا۔")


def _manage_grace_period(signals: List[ActiveSignal]) -> (List[ActiveSignal], bool):
    signals_to_check, grace_period_changed = [], False
    for signal in signals:
        if signal.is_new:
            signal.is_new = False
            grace_period_changed = True
        else:
            signals_to_check.append(signal)
    return signals_to_check, grace_period_changed


async def _process_single_signal(db: Session, signal: ActiveSignal, market_data: Dict[str, Any]):
    current_price = market_data.get('price')
    last_high = market_data.get('high')
    last_low = market_data.get('low')
    
    outcome, reason = None, None
    
    # --- منطق کا دوبارہ جائزہ اور جبری فلوٹ میں تبدیلی ---
    tp = float(signal.tp_price)
    sl = float(signal.sl_price)

    if signal.signal_type == "buy":
        if (last_high and float(last_high) >= tp) or (current_price and float(current_price) >= tp):
            outcome, reason = "tp_hit", "TP Hit"
        elif (last_low and float(last_low) <= sl) or (current_price and float(current_price) <= sl):
            outcome, reason = "sl_hit", "SL Hit"
    
    elif signal.signal_type == "sell":
        if (last_low and float(last_low) <= tp) or (current_price and float(current_price) <= tp):
            outcome, reason = "tp_hit", "TP Hit"
        elif (last_high and float(last_high) >= sl) or (current_price and float(current_price) >= sl):
            outcome, reason = "sl_hit", "SL Hit"

    if outcome:
        final_close_price = current_price if current_price is not None else (tp if outcome == 'tp_hit' else sl)
        logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا۔ بند ہونے کی قیمت: {final_close_price} ★★★")
        
        # اس بات کو یقینی بنائیں کہ یہ سگنل دوبارہ پروسیس نہ ہو
        if crud.get_active_signal_by_symbol(db, signal.symbol) is None:
            logger.warning(f"سگنل {signal.symbol} پہلے ہی بند ہو چکا ہے، دوبارہ کوشش نہیں کی جائے گی۔")
            return

        asyncio.create_task(learn_from_outcome(db, signal, outcome))
        
        success = crud.close_and_archive_signal(db, signal.signal_id, outcome, float(final_close_price), reason)
        if success:
            asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
                
