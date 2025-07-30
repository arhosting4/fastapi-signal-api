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

MOMENTUM_FILE = "market_momentum.json"
PAIRS_TO_MONITOR = get_pairs_to_monitor()
BATCH_SIZE = 7

# ★★★ سب سے اہم تبدیلی: یہ یاد رکھے گا کہ اگلی باری کس کی ہے ★★★
next_batch_index = 0

async def check_active_signals_job():
    global next_batch_index
    logger.info("🛡️ نگران انجن: فعال سگنلز کی نگرانی اور ڈیٹا اکٹھا کرنا شروع...")
    
    # 1. اس بار کون سے جوڑوں کو چیک کرنا ہے، اس کا فیصلہ کریں
    start_index = next_batch_index * BATCH_SIZE
    end_index = start_index + BATCH_SIZE
    current_batch = PAIRS_TO_MONITOR[start_index:end_index]
    
    # اگلی باری کے لیے انڈیکس کو اپ ڈیٹ کریں
    next_batch_index = (next_batch_index + 1) % (len(PAIRS_TO_MONITOR) // BATCH_SIZE)

    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        
        # فعال سگنلز کو ہمیشہ چیک کریں، چاہے وہ اس بیچ میں نہ ہوں
        active_signal_pairs = {s.symbol for s in active_signals}
        
        # اس بیچ کے جوڑوں اور فعال سگنلز کو ملا کر حتمی فہرست بنائیں
        pairs_to_check_set = set(current_batch).union(active_signal_pairs)
        
        if not pairs_to_check_set:
            logger.info("🛡️ نگران انجن: نگرانی کے لیے کوئی جوڑا نہیں۔")
            return

        logger.info(f"🛡️ نگران انجن: اس دور میں {len(pairs_to_check_set)} جوڑوں کی نگرانی کی جا رہی ہے: {list(pairs_to_check_set)}")
        quotes = await get_real_time_quotes(list(pairs_to_check_set))

        if not quotes:
            logger.warning("🛡️ نگران انجن: اس منٹ کوئی قیمت/کوٹ حاصل نہیں ہوا۔")
            return

        if active_signals:
            await check_signals_for_tp_sl(db, active_signals, quotes)

        # صرف ان جوڑوں کا ڈیٹا محفوظ کریں جو نگرانی کی فہرست میں ہیں
        save_market_momentum(quotes)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🛡️ نگران انجن: نگرانی کا دور مکمل ہوا۔")

async def check_signals_for_tp_sl(db: Session, signals: List[ActiveSignal], quotes: Dict[str, Any]):
    for signal in signals:
        quote_data = quotes.get(signal.symbol)
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
            crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
            asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))

def save_market_momentum(quotes: Dict[str, Any]):
    try:
        try:
            with open(MOMENTUM_FILE, 'r') as f: market_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): market_data = {}

        now_iso = datetime.utcnow().isoformat()
        successful_quotes = 0
        for symbol, data in quotes.items():
            if symbol in PAIRS_TO_MONITOR and "percent_change" in data and data.get("percent_change") is not None:
                if symbol not in market_data: market_data[symbol] = []
                try:
                    market_data[symbol].append({"time": now_iso, "change": float(data["percent_change"])})
                    market_data[symbol] = market_data[symbol][-5:] 
                    successful_quotes += 1
                except (ValueError, TypeError): continue
        
        if successful_quotes > 0:
            with open(MOMENTUM_FILE, 'w') as f: json.dump(market_data, f)
            logger.info(f"✅ نگران انجن: {successful_quotes} جوڑوں کا ڈیٹا کامیابی سے محفوظ کیا گیا۔")

    except Exception as e:
        logger.error(f"مارکیٹ کی حرکت کا ڈیٹا محفوظ کرنے میں خرابی: {e}", exc_info=True)
        
