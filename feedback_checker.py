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
from utils import get_real_time_quotes, get_pairs_to_monitor
from websocket_manager import manager

logger = logging.getLogger(__name__)

# --- نگرانی کے لیے بنیادی ترتیبات ---
MOMENTUM_FILE = "market_momentum.json"
PAIRS_TO_MONITOR = get_pairs_to_monitor()
BATCH_SIZE = 7

# ★★★ مرکزی یادداشت: تمام جوڑوں کی تازہ ترین قیمتیں یہاں محفوظ ہوں گی ★★★
latest_quotes_memory: Dict[str, Dict[str, Any]] = {}

# یہ یاد رکھے گا کہ اگلی باری کس بیچ کی ہے
next_batch_index = 0

async def check_active_signals_job():
    """
    یہ فنکشن اب دو اہم کام کرتا ہے:
    1. باری باری 7 جوڑوں کی قیمتیں لا کر 'مرکزی یادداشت' کو اپ ڈیٹ کرتا ہے۔
    2. ہر بار، تمام فعال سگنلز کو 'مرکزی یادداشت' کی بنیاد پر چیک کرتا ہے۔
    """
    global next_batch_index, latest_quotes_memory
    logger.info("🛡️ نگران انجن: نگرانی کا نیا دور شروع...")

    # 1. اس دور کے لیے 7 جوڑوں کا بیچ منتخب کریں
    start_index = next_batch_index * BATCH_SIZE
    end_index = start_index + BATCH_SIZE
    current_batch = PAIRS_TO_MONITOR[start_index:end_index]
    
    # اگلی باری کے لیے انڈیکس کو اپ ڈیٹ کریں
    total_batches = (len(PAIRS_TO_MONITOR) + BATCH_SIZE - 1) // BATCH_SIZE
    next_batch_index = (next_batch_index + 1) % total_batches

    if not current_batch:
        logger.info("🛡️ نگران انجن: نگرانی کے لیے کوئی جوڑا نہیں۔")
        return

    # 2. صرف منتخب کردہ 7 جوڑوں کی قیمتیں حاصل کریں
    logger.info(f"🛡️ نگران انجن: {len(current_batch)} جوڑوں کی قیمتیں حاصل کی جا رہی ہیں: {current_batch}")
    new_quotes = await get_real_time_quotes(current_batch)

    # 3. مرکزی یادداشت کو نئی قیمتوں سے اپ ڈیٹ کریں
    if new_quotes:
        latest_quotes_memory.update(new_quotes)
        logger.info(f"✅ مرکزی یادداشت اپ ڈیٹ ہوئی۔ کل یادداشت میں {len(latest_quotes_memory)} جوڑوں کا ڈیٹا ہے۔")
        # مارکیٹ کی حرکت کا ڈیٹا بھی محفوظ کریں
        save_market_momentum(new_quotes)
    else:
        logger.warning("🛡️ نگران انجن: اس دور میں کوئی نئی قیمت حاصل نہیں ہوئی۔")

    # 4. اب، تمام فعال سگنلز کو مرکزی یادداشت کی بنیاد پر چیک کریں
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        if not active_signals:
            logger.info("🛡️ نگران انجن: کوئی فعال سگنل موجود نہیں۔")
            return
        
        if not latest_quotes_memory:
            logger.warning("🛡️ نگران انجن: TP/SL چیک کرنے کے لیے مرکزی یادداشت میں کوئی ڈیٹا نہیں۔")
            return

        logger.info(f"🛡️ نگران انجن: {len(active_signals)} فعال سگنلز کو مرکزی یادداشت سے چیک کیا جا رہا ہے...")
        await check_signals_for_tp_sl(db, active_signals, latest_quotes_memory)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🛡️ نگران انجن: نگرانی کا دور مکمل ہوا۔")


async def check_signals_for_tp_sl(db: Session, signals: List[ActiveSignal], quotes_memory: Dict[str, Any]):
    """
    یہ فنکشن اب تمام فعال سگنلز کو مرکزی یادداشت سے چیک کرتا ہے۔
    """
    signals_closed_count = 0
    for signal in signals:
        # اگر سگنل کا جوڑا یادداشت میں نہیں ہے، تو اسے نظر انداز کر دیں
        if signal.symbol not in quotes_memory:
            continue

        quote_data = quotes_memory.get(signal.symbol)
        if not quote_data or "price" not in quote_data: continue
        
        try:
            current_price = float(quote_data["price"])
        except (ValueError, TypeError): continue

        outcome, close_price, reason = None, None, None
        if signal.signal_type == "buy":
            if current_price >= signal.tp_price: outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit"
            elif current_price <= signal.sl_price: outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit"
        elif signal.signal_type == "sell":
            if current_price <= signal.tp_price: outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit"
            elif current_price >= signal.sl_price: outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit"

        if outcome:
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome} کے طور پر نشان زد کیا گیا ★★★")
            success = crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
            if success:
                signals_closed_count += 1
                # UI کو اپ ڈیٹ کرنے کے لیے براڈکاسٹ کریں
                asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
    
    if signals_closed_count > 0:
        logger.info(f"🛡️ نگران انجن: کل {signals_closed_count} سگنل بند کیے گئے۔")


def save_market_momentum(quotes: Dict[str, Any]):
    """
    یہ فنکشن صرف نئی حاصل کردہ قیمتوں کی بنیاد پر مارکیٹ کی حرکت کو محفوظ کرتا ہے۔
    """
    try:
        try:
            with open(MOMENTUM_FILE, 'r') as f: market_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): market_data = {}

        now_iso = datetime.utcnow().isoformat()
        successful_quotes = 0
        for symbol, data in quotes.items():
            if "percent_change" in data and data.get("percent_change") is not None:
                if symbol not in market_data: market_data[symbol] = []
                try:
                    market_data[symbol].append({"time": now_iso, "change": float(data["percent_change"])})
                    # صرف آخری 5 منٹ کا ڈیٹا رکھیں
                    market_data[symbol] = market_data[symbol][-5:] 
                    successful_quotes += 1
                except (ValueError, TypeError): continue
        
        if successful_quotes > 0:
            with open(MOMENTUM_FILE, 'w') as f: json.dump(market_data, f)
            logger.info(f"✅ نگران انجن: {successful_quotes} جوڑوں کی حرکت کا ڈیٹا کامیابی سے محفوظ کیا گیا۔")

    except Exception as e:
        logger.error(f"مارکیٹ کی حرکت کا ڈیٹا محفوظ کرنے میں خرابی: {e}", exc_info=True)

