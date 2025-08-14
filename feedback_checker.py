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
    logger.info("🛡️ نگران انجن (ورژن 3.0 - حتمی): نگرانی کا دور شروع...")
    
    try:
        with get_db_session() as db:
            # --- منطقی اصلاح: تمام فعال سگنلز کو ہمیشہ چیک کریں ---
            signals_to_check = crud.get_all_active_signals_from_db(db)
            if not signals_to_check:
                logger.info("🛡️ نگران: کوئی فعال سگنل موجود نہیں۔")
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
                    current_price = float(quote['price'])
                except (ValueError, TypeError):
                    logger.warning(f"🛡️ [{signal.symbol}] کے لیے قیمت کو فلوٹ میں تبدیل نہیں کیا جا سکا: '{quote['price']}'")
                    continue

                # تفصیلی لاگنگ جو پہلے غائب تھی
                logger.info(f"🛡️ جانچ: [{signal.symbol}] | قسم: {signal.signal_type} | TP: {signal.tp_price} | SL: {signal.sl_price} | موجودہ قیمت: {current_price}")

                # گریس پیریڈ کی نئی منطق: اگر سگنل نیا ہے تو صرف SL کو چیک کریں
                if signal.is_new:
                    signal.is_new = False
                    db.commit() # فوری طور پر حالت کو اپ ڈیٹ کریں
                    
                    sl = float(signal.sl_price)
                    if (signal.signal_type == "buy" and current_price <= sl) or \
                       (signal.signal_type == "sell" and current_price >= sl):
                        logger.warning(f"🛡️ [{signal.symbol}] گریس پیریڈ کے دوران SL ہٹ! سگنل بند کیا جا رہا ہے۔")
                        await _process_single_signal(db, signal, {"price": current_price})
                    else:
                        logger.info(f"🛡️ [{signal.symbol}] گریس پیریڈ میں ہے۔ TP کو نظر انداز کیا جا رہا ہے۔")
                    continue # اگلے سگنل پر جائیں

                # مکمل جانچ (اگر گریس پیریڈ میں نہیں ہے)
                is_close_to_tp = abs(current_price - signal.tp_price) <= abs(signal.entry_price - signal.tp_price) * PROXIMITY_THRESHOLD_PERCENT
                is_close_to_sl = abs(current_price - signal.sl_price) <= abs(signal.entry_price - signal.sl_price) * PROXIMITY_THRESHOLD_PERCENT

                if is_close_to_tp or is_close_to_sl:
                    logger.info(f"🛡️ [{signal.symbol}] قیمت ہدف کے قریب ہے۔ تفصیلی جانچ کی جا رہی ہے۔")
                    ohlc_data = await fetch_twelve_data_ohlc(signal.symbol, "1min", 2)
                    market_data = {"price": current_price}
                    if ohlc_data and ohlc_data[-1].high is not None and ohlc_data[-1].low is not None:
                        market_data['high'] = float(ohlc_data[-1].high)
                        market_data['low'] = float(ohlc_data[-1].low)
                    await _process_single_signal(db, signal, market_data)
                else:
                    await _process_single_signal(db, signal, {"price": current_price})

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🛡️ نگران انجن (ورژن 3.0): نگرانی کا دور مکمل ہوا۔")


async def _process_single_signal(db: Session, signal: ActiveSignal, market_data: Dict[str, Any]):
    # سگنل کو دوبارہ حاصل کریں تاکہ تازہ ترین حالت ملے
    live_signal = db.query(ActiveSignal).filter(ActiveSignal.id == signal.id).first()
    if not live_signal:
        logger.warning(f"سگنل {signal.symbol} پہلے ہی بند ہو چکا ہے، پروسیسنگ روکی گئی۔")
        return

    current_price = market_data.get('price')
    last_high = market_data.get('high')
    last_low = market_data.get('low')
    
    outcome, reason = None, None
    
    tp = float(live_signal.tp_price)
    sl = float(live_signal.sl_price)

    if live_signal.signal_type == "buy":
        if (last_high and last_high >= tp) or (current_price and current_price >= tp):
            outcome, reason = "tp_hit", "TP Hit"
        elif (last_low and last_low <= sl) or (current_price and current_price <= sl):
            outcome, reason = "sl_hit", "SL Hit"
    
    elif live_signal.signal_type == "sell":
        if (last_low and last_low <= tp) or (current_price and current_price <= tp):
            outcome, reason = "tp_hit", "TP Hit"
        elif (last_high and last_high >= sl) or (current_price and current_price >= sl):
            outcome, reason = "sl_hit", "SL Hit"

    if outcome:
        final_close_price = current_price if current_price is not None else (tp if outcome == 'tp_hit' else sl)
        logger.info(f"★★★ سگنل کا نتیجہ: {live_signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا۔ بند ہونے کی قیمت: {final_close_price} ★★★")
        
        asyncio.create_task(learn_from_outcome(db, live_signal, outcome))
        
        success = crud.close_and_archive_signal(db, live_signal.signal_id, outcome, float(final_close_price), reason)
        if success:
            asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": live_signal.signal_id}}))

