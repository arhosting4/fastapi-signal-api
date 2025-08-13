# filename: feedback_checker.py

import asyncio
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Generator

from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal
# --- ہم دونوں فنکشنز کا بہترین استعمال کریں گے ---
from utils import get_real_time_quotes, fetch_twelve_data_ohlc
from websocket_manager import manager
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
    فعال سگنلز کی نگرانی کرتا ہے، حقیقی وقت کی قیمتوں اور پچھلی کینڈل کے ہائی/لو دونوں کی بنیاد پر TP/SL ہٹس کو چیک کرتا ہے۔
    """
    logger.info("🛡️ نگران انجن (ججمنٹ): فعال سگنلز کی نگرانی کا دور شروع...")
    
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
            
            # --- دوہری ڈیٹا کا حصول ---
            logger.info(f"🛡️ نگران: {len(symbols_to_check)} علامتوں کے لیے حقیقی وقت کی قیمتیں اور کینڈل ڈیٹا حاصل کیا جا رہا ہے...")
            quote_task = get_real_time_quotes(symbols_to_check)
            # ہم صرف پچھلی 1 مکمل شدہ کینڈل کا ڈیٹا لیں گے
            ohlc_task = asyncio.gather(*[fetch_twelve_data_ohlc(s, "1min", 2) for s in symbols_to_check])
            
            latest_quotes, ohlc_results = await asyncio.gather(quote_task, ohlc_task)

            market_data = {}
            if latest_quotes:
                for symbol, data in latest_quotes.items():
                    if 'price' in data:
                        market_data[symbol] = {"price": float(data['price'])}

            if ohlc_results:
                for candles in ohlc_results:
                    if candles and len(candles) > 0:
                        # پچھلی مکمل شدہ کینڈل
                        last_candle = candles[-1]
                        symbol = last_candle.symbol
                        if symbol not in market_data:
                            market_data[symbol] = {}
                        market_data[symbol]['high'] = last_candle.high
                        market_data[symbol]['low'] = last_candle.low

            if not market_data:
                logger.warning("🛡️ نگران انجن: TP/SL چیک کرنے کے لیے کوئی مارکیٹ ڈیٹا حاصل نہیں ہوا۔")
                return

            logger.info(f"🛡️ نگران انجن: {len(signals_to_check_now)} اہل فعال سگنلز کو چیک کیا جا رہا ہے...")
            await _process_signal_outcomes(db, signals_to_check_now, market_data)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🛡️ نگران انجن (ججمنٹ): نگرانی کا دور مکمل ہوا۔")

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

async def _process_signal_outcomes(db: Session, signals: List[ActiveSignal], market_data: Dict[str, Any]):
    """
    ہر سگنل کو دوہری جانچ (real-time quote + last candle's high/low) کی بنیاد پر چیک کرتا ہے۔
    """
    signals_closed_count = 0
    for signal in signals:
        data = market_data.get(signal.symbol)
        if not data:
            logger.warning(f"🛡️ {signal.symbol} کے لیے نگرانی کا ڈیٹا نہیں ملا۔")
            continue

        try:
            current_price = data.get('price')
            last_high = data.get('high')
            last_low = data.get('low')
        except (ValueError, TypeError):
            logger.warning(f"🛡️ {signal.symbol} کے لیے قیمت کو فلوٹ میں تبدیل نہیں کیا جا سکا۔")
            continue
        
        outcome, close_price, reason = None, None, None
        
        if signal.signal_type == "buy":
            # TP کی جانچ: یا تو موجودہ قیمت TP کو چھوئے، یا پچھلی کینڈل کا ہائی چھو چکا ہو
            if (current_price and current_price >= signal.tp_price) or (last_high and last_high >= signal.tp_price):
                outcome, close_price, reason = "tp_hit", current_price or signal.tp_price, "tp_hit"
            # SL کی جانچ: یا تو موجودہ قیمت SL کو چھوئے، یا پچھلی کینڈل کا لو چھو چکا ہو
            elif (current_price and current_price <= signal.sl_price) or (last_low and last_low <= signal.sl_price):
                outcome, close_price, reason = "sl_hit", current_price or signal.sl_price, "sl_hit"
        
        elif signal.signal_type == "sell":
            # TP کی جانچ
            if (current_price and current_price <= signal.tp_price) or (last_low and last_low <= signal.tp_price):
                outcome, close_price, reason = "tp_hit", current_price or signal.tp_price, "tp_hit"
            # SL کی جانچ
            elif (current_price and current_price >= signal.sl_price) or (last_high and last_high >= signal.sl_price):
                outcome, close_price, reason = "sl_hit", current_price or signal.sl_price, "sl_hit"

        if outcome:
            # اگر قیمت موجود نہیں ہے تو طے شدہ قیمت استعمال کریں
            final_close_price = close_price if close_price is not None else (signal.tp_price if outcome == 'tp_hit' else signal.sl_price)
            
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا ({reason})۔ بند ہونے کی قیمت: {final_close_price} ★★★")
            
            asyncio.create_task(learn_from_outcome(db, signal, outcome))
            
            success = crud.close_and_archive_signal(db, signal.signal_id, outcome, final_close_price, reason)
            if success:
                signals_closed_count += 1
                asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
    
    if signals_closed_count > 0:
        logger.info(f"🛡️ نگران انجن: کل {signals_closed_count} سگنل بند کیے گئے۔")
            
