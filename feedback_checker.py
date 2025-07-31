# filename: feedback_checker.py

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_real_time_quotes, fetch_twelve_data_ohlc
from websocket_manager import manager
from roster_manager import get_split_monitoring_roster # ★★★ نیا اور اہم امپورٹ ★★★

logger = logging.getLogger(__name__)

# یہ متغیر اب تمام جوڑوں کی تازہ ترین قیمتوں کو یادداشت میں رکھے گا
latest_quotes_memory: Dict[str, Dict[str, Any]] = {}

async def check_active_signals_job():
    """
    یہ فنکشن اب ایک ذہین، دو قدمی نگرانی کا عمل چلاتا ہے:
    1. فعال سگنلز کے لیے درست کینڈل ڈیٹا (/time_series) حاصل کرتا ہے۔
    2. غیر فعال بنیادی جوڑوں کے لیے فوری قیمت (/quote) حاصل کرتا ہے۔
    3. اس ڈیٹا کی بنیاد پر TP/SL کی قابل اعتماد جانچ کرتا ہے۔
    """
    global latest_quotes_memory
    logger.info("🛡️ نگران انجن: نگرانی کا نیا، ذہین دور شروع...")

    db = SessionLocal()
    try:
        # 1. جوڑوں کو دو حصوں میں تقسیم کریں
        active_symbols, inactive_symbols = get_split_monitoring_roster(db)
        
        # 2. متوازی طور پر دونوں اقسام کا ڈیٹا حاصل کریں
        tasks = []
        # فعال سگنلز کے لیے درست کینڈل ڈیٹا حاصل کرنے کے ٹاسک
        if active_symbols:
            logger.info(f"🛡️ نگران: {len(active_symbols)} فعال سگنلز کے لیے درست کینڈل ڈیٹا حاصل کیا جا رہا ہے...")
            tasks.extend([fetch_twelve_data_ohlc(symbol) for symbol in active_symbols])
        
        # غیر فعال جوڑوں کے لیے فوری قیمت حاصل کرنے کا ٹاسک
        if inactive_symbols:
            logger.info(f"🛡️ نگران: {len(inactive_symbols)} غیر فعال جوڑوں کے لیے فوری قیمت حاصل کی جا رہی ہے...")
            tasks.append(get_real_time_quotes(inactive_symbols))

        if not tasks:
            logger.info("🛡️ نگران: نگرانی کے لیے کوئی جوڑا نہیں۔ دور ختم۔")
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 3. حاصل کردہ ڈیٹا کو پروسیس کریں اور مرکزی یادداشت کو اپ ڈیٹ کریں
        new_quotes_data = {}
        for result in results:
            if isinstance(result, Exception) or not result:
                continue
            
            # نتیجہ /quote سے آیا ہے (ڈکشنری کی صورت میں)
            if isinstance(result, dict):
                new_quotes_data.update(result)
            # نتیجہ /time_series سے آیا ہے (فہرست کی صورت میں)
            elif isinstance(result, list) and result:
                latest_candle = result[-1] # آخری کینڈل
                symbol = latest_candle.symbol
                new_quotes_data[symbol] = {
                    "symbol": symbol,
                    "price": latest_candle.close,
                    "high": latest_candle.high,
                    "low": latest_candle.low,
                    "open": latest_candle.open,
                    "datetime": latest_candle.datetime
                }

        if new_quotes_data:
            latest_quotes_memory.update(new_quotes_data)
            logger.info(f"✅ مرکزی یادداشت اپ ڈیٹ ہوئی۔ کل یادداشت میں {len(latest_quotes_memory)} جوڑوں کا ڈیٹا ہے۔")
        else:
            logger.warning("🛡️ نگران انجن: اس دور میں کوئی نئی قیمت حاصل نہیں ہوئی۔")

        # 4. اب، تمام فعال سگنلز کو مرکزی یادداشت کی بنیاد پر چیک کریں
        if not active_symbols:
            logger.info("🛡️ نگران انجن: کوئی فعال سگنل موجود نہیں۔")
            return
            
        logger.info(f"🛡️ نگران انجن: {len(active_symbols)} فعال سگنلز کو مرکزی یادداشت سے چیک کیا جا رہا ہے...")
        active_signals = crud.get_all_active_signals_from_db(db)
        await check_signals_for_tp_sl(db, active_signals, latest_quotes_memory)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🛡️ نگران انجن: نگرانی کا دور مکمل ہوا۔")


async def check_signals_for_tp_sl(db: Session, signals: List[ActiveSignal], quotes_memory: Dict[str, Any]):
    """
    یہ فنکشن کینڈل کی پوری رینج (High/Low) کی بنیاد پر TP/SL کو چیک کرتا ہے۔
    """
    signals_closed_count = 0
    for signal in signals:
        if signal.symbol not in quotes_memory:
            continue

        quote_data = quotes_memory.get(signal.symbol)
        # یقینی بنائیں کہ ہمارے پاس high اور low ڈیٹا موجود ہے
        if not quote_data or "high" not in quote_data or "low" not in quote_data:
            logger.warning(f"سگنل {signal.symbol} کے لیے مکمل کینڈل ڈیٹا (high/low) دستیاب نہیں۔ جانچ روکی جا رہی ہے۔")
            continue
        
        try:
            candle_high = float(quote_data["high"])
            candle_low = float(quote_data["low"])
        except (ValueError, TypeError):
            continue

        outcome, close_price, reason = None, None, None
        
        # ★★★ نئی اور قابل اعتماد TP/SL منطق ★★★
        if signal.signal_type == "buy":
            # TP تب ہٹ ہوگا جب کینڈل کی اونچائی TP قیمت کو چھو لے
            if candle_high >= signal.tp_price:
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit_by_high"
            # SL تب ہٹ ہوگا جب کینڈل کی نیچائی SL قیمت کو چھو لے
            elif candle_low <= signal.sl_price:
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_low"
        
        elif signal.signal_type == "sell":
            # TP تب ہٹ ہوگا جب کینڈل کی نیچائی TP قیمت کو چھو لے
            if candle_low <= signal.tp_price:
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit_by_low"
            # SL تب ہٹ ہوگا جب کینڈل کی اونچائی SL قیمت کو چھو لے
            elif candle_high >= signal.sl_price:
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_high"

        if outcome:
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا ({reason}) ★★★")
            success = crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
            if success:
                signals_closed_count += 1
                asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
    
    if signals_closed_count > 0:
        logger.info(f"🛡️ نگران انجن: کل {signals_closed_count} سگنل بند کیے گئے۔")

