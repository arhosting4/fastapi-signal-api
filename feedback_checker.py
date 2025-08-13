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

# --- API کالز کو کم کرنے کے لیے نیا پیرامیٹر ---
# قیمت TP/SL کے کتنے فیصد قریب ہو تو تفصیلی جانچ کی جائے
PROXIMITY_THRESHOLD_PERCENT = 0.20  # 20%

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def check_active_signals_job():
    logger.info("🛡️ ذہین نگران انجن: نگرانی کا دور شروع...")
    
    try:
        with get_db_session() as db:
            active_signals = crud.get_all_active_signals_from_db(db)
            if not active_signals:
                logger.info("🛡️ نگران انجن: کوئی فعال سگنل موجود نہیں۔")
                return

            signals_to_check, made_change = _manage_grace_period(active_signals)
            if made_change:
                db.commit()
            
            if not signals_to_check:
                logger.info("🛡️ نگران انجن: چیک کرنے کے لیے کوئی اہل سگنل نہیں (سب گریس پیریڈ میں ہیں)۔")
                return

            # مرحلہ 1: سستی API کال - تمام سگنلز کے لیے صرف قیمتیں حاصل کریں
            symbols = list({s.symbol for s in signals_to_check})
            latest_quotes = await get_real_time_quotes(symbols)

            if not latest_quotes:
                logger.warning("🛡️ نگران انجن: کوئی مارکیٹ قیمتیں حاصل نہیں ہوئیں۔")
                return

            signals_needing_deep_check = []
            market_data_for_deep_check = {}

            # مرحلہ 2: چیک کریں کہ کون سے سگنلز کو تفصیلی جانچ کی ضرورت ہے
            for signal in signals_to_check:
                quote = latest_quotes.get(signal.symbol)
                if not quote or 'price' not in quote:
                    continue
                
                current_price = float(quote['price'])
                
                # کیا قیمت TP یا SL کے قریب ہے؟
                is_close_to_tp = abs(current_price - signal.tp_price) <= abs(signal.entry_price - signal.tp_price) * PROXIMITY_THRESHOLD_PERCENT
                is_close_to_sl = abs(current_price - signal.sl_price) <= abs(signal.entry_price - signal.sl_price) * PROXIMITY_THRESHOLD_PERCENT

                if is_close_to_tp or is_close_to_sl:
                    logger.info(f"🛡️ [{signal.symbol}] قیمت ہدف کے قریب ہے۔ تفصیلی جانچ کی جا رہی ہے۔")
                    signals_needing_deep_check.append(signal)
                    market_data_for_deep_check[signal.symbol] = {"price": current_price}
                else:
                    # فوری قیمت کی بنیاد پر نتیجہ چیک کریں
                    await _process_single_signal(db, signal, {"price": current_price})

            # مرحلہ 3: صرف قریبی سگنلز کے لیے مہنگی API کال کریں
            if signals_needing_deep_check:
                symbols_for_ohlc = [s.symbol for s in signals_needing_deep_check]
                logger.info(f"🛡️ نگران: {len(symbols_for_ohlc)} علامتوں کے لیے کینڈل ڈیٹا حاصل کیا جا رہا ہے...")
                ohlc_results = await asyncio.gather(*[fetch_twelve_data_ohlc(s, "1min", 2) for s in symbols_for_ohlc])

                for candles in ohlc_results:
                    if candles:
                        last_candle = candles[-1]
                        symbol = last_candle.symbol
                        market_data_for_deep_check[symbol]['high'] = last_candle.high
                        market_data_for_deep_check[symbol]['low'] = last_candle.low
                
                for signal in signals_needing_deep_check:
                    data = market_data_for_deep_check.get(signal.symbol)
                    if data:
                        await _process_single_signal(db, signal, data)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🛡️ ذہین نگران انجن: نگرانی کا دور مکمل ہوا۔")


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
    
    outcome, close_price, reason = None, None, None
    
    if signal.signal_type == "buy":
        if (last_high and last_high >= signal.tp_price) or (current_price and current_price >= signal.tp_price):
            outcome, reason = "tp_hit", "TP Hit"
        elif (last_low and last_low <= signal.sl_price) or (current_price and current_price <= signal.sl_price):
            outcome, reason = "sl_hit", "SL Hit"
    
    elif signal.signal_type == "sell":
        if (last_low and last_low <= signal.tp_price) or (current_price and current_price <= signal.tp_price):
            outcome, reason = "tp_hit", "TP Hit"
        elif (last_high and last_high >= signal.sl_price) or (current_price and current_price >= signal.sl_price):
            outcome, reason = "sl_hit", "SL Hit"

    if outcome:
        final_close_price = current_price if current_price is not None else (signal.tp_price if outcome == 'tp_hit' else signal.sl_price)
        logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا۔ بند ہونے کی قیمت: {final_close_price} ★★★")
        
        asyncio.create_task(learn_from_outcome(db, signal, outcome))
        
        success = crud.close_and_archive_signal(db, signal.signal_id, outcome, final_close_price, reason)
        if success:
            asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))

