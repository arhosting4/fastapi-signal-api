# filename: feedback_checker.py

import asyncio
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_current_prices_from_api
from websocket_manager import manager
import trainerai

logger = logging.getLogger(__name__)
MARKET_STATE_FILE = "market_state.json"
MAX_PAIRS_PER_CALL = 8

def get_feedback_essential_pairs() -> List[str]:
    """
    نگرانی کے لیے بنیادی جوڑوں کی فہرست واپس کرتا ہے۔
    """
    primary_pairs = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
    weekend_pairs = ["BTC/USD", "ETH/USD"]
    is_weekend = datetime.utcnow().weekday() >= 5
    return weekend_pairs if is_weekend else primary_pairs

async def check_active_signals_job():
    """
    یہ جاب ہر منٹ چلتی ہے اور فعال سگنلز کو TP/SL کے لیے چیک کرتی ہے،
    اور نتیجہ آنے پر AI کو فیڈ بیک بھیجتی ہے۔
    """
    db = SessionLocal()
    try:
        active_signals: List[ActiveSignal] = crud.get_all_active_signals_from_db(db)
        
        pairs_to_check = set(s.symbol for s in active_signals)
        pairs_to_check.update(get_feedback_essential_pairs())
        
        final_list_to_check = sorted(list(pairs_to_check))[:MAX_PAIRS_PER_CALL]
        
        if not final_list_to_check:
            return

        live_prices = await get_current_prices_from_api(final_list_to_check)

        if not live_prices:
            logger.warning("API سے کوئی قیمت حاصل نہیں ہوئی۔ جانچ روکی جا رہی ہے۔")
            return

        # مارکیٹ کی حالت کو اپ ڈیٹ کریں (یہ hunter.py کے لیے ہے)
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
            close_price = None
            reason_for_closure = None

            if signal.signal_type == "buy":
                if current_price >= signal.tp_price:
                    outcome = "tp_hit"
                    feedback = "correct"
                    close_price = signal.tp_price
                    reason_for_closure = "tp_hit"
                elif current_price <= signal.sl_price:
                    outcome = "sl_hit"
                    feedback = "incorrect"
                    close_price = signal.sl_price
                    reason_for_closure = "sl_hit"
            elif signal.signal_type == "sell":
                if current_price <= signal.tp_price:
                    outcome = "tp_hit"
                    feedback = "correct"
                    close_price = signal.tp_price
                    reason_for_closure = "tp_hit"
                elif current_price >= signal.sl_price:
                    outcome = "sl_hit"
                    feedback = "incorrect"
                    close_price = signal.sl_price
                    reason_for_closure = "sl_hit"

            if outcome and close_price is not None:
                logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome} کے طور پر نشان زد کیا گیا ★★★")
                
                # ★★★ AI کے سیکھنے کا عمل شروع کریں ★★★
                trainerai.learn_from_outcome(db, signal, outcome)
                
                # ★★★ تفصیلی معلومات کے ساتھ مکمل شدہ ٹریڈ شامل کریں ★★★
                crud.add_completed_trade(db, signal, outcome, close_price, reason_for_closure)
                
                crud.add_feedback_entry(db, signal.symbol, signal.timeframe, feedback)
                crud.delete_active_signal(db, signal.signal_id)
                await manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}})
                
    except Exception as e:
        logger.error(f"فعال سگنلز کی جانچ کے دوران مہلک خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
            
