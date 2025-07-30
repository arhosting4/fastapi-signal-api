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
from utils import get_real_time_quotes
from websocket_manager import manager
from config import TRADING_PAIRS

logger = logging.getLogger(__name__)

MOMENTUM_FILE = "market_momentum.json"
# نگرانی کے لیے اہم جوڑوں کی فہرست (کنفیگریشن سے)
PAIRS_TO_MONITOR = TRADING_PAIRS["PAIRS_TO_MONITOR"]

# ==============================================================================
# ★★★ نگران انجن کا کام (ہر 2 منٹ بعد) ★★★
# ==============================================================================
async def check_active_signals_job():
    """
    یہ جاب ہر 2 منٹ چلتی ہے، فعال سگنلز کی نگرانی کرتی ہے اور اہم جوڑوں کا ڈیٹا اکٹھا کرتی ہے۔
    """
    logger.info("🛡️ نگران انجن: فعال سگنلز کی نگرانی اور ڈیٹا اکٹھا کرنا شروع...")
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        
        # جن جوڑوں کی قیمتیں چیک کرنی ہیں ان کی حتمی فہرست بنائیں
        active_signal_pairs = {s.symbol for s in active_signals}
        pairs_to_check_set = active_signal_pairs.union(set(PAIRS_TO_MONITOR))
        
        if not pairs_to_check_set:
            logger.info("🛡️ نگران انجن: نگرانی کے لیے کوئی جوڑا نہیں۔")
            return

        # ایک ہی API کال میں تمام قیمتیں حاصل کریں
        quotes = await get_real_time_quotes(list(pairs_to_check_set))
        if not quotes:
            logger.warning("🛡️ نگران انجن: اس منٹ کوئی قیمت/کوٹ حاصل نہیں ہوا۔")
            return

        # 1. فعال سگنلز کو TP/SL کے لیے چیک کریں
        if active_signals:
            await check_signals_for_tp_sl(db, active_signals, quotes)

        # 2. مارکیٹ کی حرکت کا ڈیٹا محفوظ کریں
        save_market_momentum(quotes)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🛡️ نگران انجن: نگرانی کا دور مکمل ہوا۔")

async def check_signals_for_tp_sl(db: Session, signals: List[ActiveSignal], quotes: Dict[str, Any]):
    """فعال سگنلز کو TP/SL کے لیے چیک کرتا ہے۔"""
    for signal in signals:
        quote_data = quotes.get(signal.symbol)
        if not quote_data or "price" not in quote_data:
            continue
        
        try:
            current_price = float(quote_data["price"])
        except (ValueError, TypeError):
            continue

        outcome, close_price, reason = None, None, None
        if signal.signal_type == "buy":
            if current_price >= signal.tp_price:
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit"
            elif current_price <= signal.sl_price:
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit"
        elif signal.signal_type == "sell":
            if current_price <= signal.tp_price:
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit"
            elif current_price >= signal.sl_price:
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit"

        if outcome:
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome} کے طور پر نشان زد کیا گیا ★★★")
            # یہاں ہم trainerai کو کال نہیں کر رہے کیونکہ وہ hunter کا حصہ ہے
            crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
            asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))

def save_market_momentum(quotes: Dict[str, Any]):
    """مارکیٹ کی حرکت کا ڈیٹا JSON فائل میں محفوظ کرتا ہے۔"""
    try:
        try:
            with open(MOMENTUM_FILE, 'r') as f:
                market_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            market_data = {}

        now_iso = datetime.utcnow().isoformat()
        successful_quotes = 0
        for symbol, data in quotes.items():
            # صرف ان جوڑوں کا ڈیٹا محفوظ کریں جو نگرانی کی فہرست میں ہیں
            if symbol in PAIRS_TO_MONITOR and "percent_change" in data and data.get("percent_change") is not None:
                if symbol not in market_data: market_data[symbol] = []
                try:
                    market_data[symbol].append({"time": now_iso, "change": float(data["percent_change"])})
                    # صرف آخری 10 منٹ کا ڈیٹا رکھیں (ہر 2 منٹ کی 5 اینٹریز)
                    market_data[symbol] = market_data[symbol][-5:] 
                    successful_quotes += 1
                except (ValueError, TypeError):
                    continue
        
        if successful_quotes > 0:
            with open(MOMENTUM_FILE, 'w') as f:
                json.dump(market_data, f)
            logger.info(f"✅ نگران انجن: {successful_quotes} جوڑوں کا ڈیٹا کامیابی سے محفوظ کیا گیا۔")

    except Exception as e:
        logger.error(f"مارکیٹ کی حرکت کا ڈیٹا محفوظ کرنے میں خرابی: {e}", exc_info=True)
                
