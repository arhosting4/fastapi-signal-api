# filename: feedback_checker.py

import asyncio
import json
import logging
from typing import List, Dict, Any
from datetime import datetime # ★★★ datetime کو امپورٹ کریں ★★★

import httpx
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal
# ★★★ utils سے صرف ضروری فنکشن امپورٹ کریں ★★★
from utils import get_current_prices_from_api
from websocket_manager import manager
import trainerai

logger = logging.getLogger(__name__)
MARKET_STATE_FILE = "market_state.json"
MAX_PAIRS_PER_CALL = 8

# ★★★ ضروری منطق اب اسی فائل میں موجود ہے ★★★
def get_feedback_essential_pairs() -> List[str]:
    """
    نگرانی کے لیے بنیادی جوڑوں کی فہرست واپس کرتا ہے۔
    یہ فنکشن اب utils.py پر منحصر نہیں ہے۔
    """
    # بنیادی جوڑے جو عام دنوں میں چیک ہوں گے
    primary_pairs = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
    # ویک اینڈ پر چیک ہونے والے جوڑے
    weekend_pairs = ["BTC/USD", "ETH/USD"]
    
    # ہفتے کا دن چیک کریں (0=پیر, 6=اتوار)
    is_weekend = datetime.utcnow().weekday() >= 5
    return weekend_pairs if is_weekend else primary_pairs

async def check_active_signals_job():
    """
    یہ جاب ہر منٹ چلتی ہے اور ایک ہی API کال میں صرف ضروری جوڑوں کی قیمتوں کو چیک کرتی ہے۔
    (حتمی اور خود مختار ورژن)
    """
    db = SessionLocal()
    try:
        active_signals: List[ActiveSignal] = crud.get_all_active_signals_from_db(db)
        
        # ★★★ نئی، ذہین اور موثر فہرست سازی (اب مکمل طور پر خود مختار) ★★★
        # 1. فعال سگنلز کے جوڑے حاصل کریں
        pairs_to_check = set(s.symbol for s in active_signals)
        # 2. ہمارے بنیادی جوڑوں کو بھی شامل کریں (اسی فائل کے فنکشن سے)
        pairs_to_check.update(get_feedback_essential_pairs())
        
        # 3. حتمی فہرست کو 8 کی حد تک محدود کریں
        final_list_to_check = sorted(list(pairs_to_check))[:MAX_PAIRS_PER_CALL]
        
        if not final_list_to_check:
            return

        logger.info(f"قیمت کی جانچ شروع: ان {len(final_list_to_check)} ضروری جوڑوں کے لیے ایک ہی کال کی جا رہی ہے: {final_list_to_check}")
        
        live_prices = await get_current_prices_from_api(final_list_to_check)

        if not live_prices:
            logger.warning("API سے کوئی قیمت حاصل نہیں ہوئی۔ جانچ روکی جا رہی ہے۔")
            return

        # مارکیٹ کی حالت کو اپ ڈیٹ کریں
        try:
            with open(MARKET_STATE_FILE, 'r') as f:
                previous_state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            previous_state = {}
        current_state = {}
        for symbol, price in live_prices.items():
            current_state[symbol] = {
                "current_price": price,
                "previous_price": previous_state.get(symbol, {}).get("current_price", price)
            }
        with open(MARKET_STATE_FILE, 'w') as f:
            json.dump(current_state, f)
        
        if not active_signals:
            return
            
        # TP/SL کی جانچ
        for signal in active_signals:
            current_price = live_prices.get(signal.symbol)
            if current_price is None:
                continue

            outcome = None
            feedback = None

            if signal.signal_type == "buy":
                if current_price >= signal.tp_price:
                    outcome = "tp_hit"
                    feedback = "correct"
                elif current_price <= signal.sl_price:
                    outcome = "sl_hit"
                    feedback = "incorrect"
            elif signal.signal_type == "sell":
                if current_price <= signal.tp_price:
                    outcome = "tp_hit"
                    feedback = "correct"
                elif current_price >= signal.sl_price:
                    outcome = "sl_hit"
                    feedback = "incorrect"

            if outcome:
                logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome} کے طور پر نشان زد کیا گیا ★★★")
                trainerai.learn_from_outcome(db, signal, outcome)
                crud.add_completed_trade(db, signal, outcome)
                crud.add_feedback_entry(db, signal.symbol, signal.timeframe, feedback)
                crud.delete_active_signal(db, signal.signal_id)
                await manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}})
                
    except Exception as e:
        logger.error(f"فعال سگنلز کی جانچ کے دوران مہلک خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
                
