# filename: feedback_checker.py

import asyncio
import json
import logging
from typing import List, Dict, Any

import httpx
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal # ActiveSignal کو امپورٹ کریں
from utils import get_current_prices_from_api, get_all_pairs
from websocket_manager import manager
import trainerai # ★★★ ٹرینر کو امپورٹ کریں ★★★

logger = logging.getLogger(__name__)
MARKET_STATE_FILE = "market_state.json"

async def check_active_signals_job():
    """
    یہ جاب ہر منٹ چلتی ہے، تمام فعال سگنلز کی قیمتوں کو چیک کرتی ہے،
    مارکیٹ کی حالت کو اپ ڈیٹ کرتی ہے، اور نتائج کو ٹرینر کو بھیجتی ہے۔
    """
    db = SessionLocal()
    try:
        active_signals: List[ActiveSignal] = crud.get_all_active_signals_from_db(db)
        
        # قیمتوں کو حاصل کرنے کے لیے تمام ضروری جوڑوں کی فہرست بنائیں
        essential_pairs = set(s.symbol for s in active_signals)
        essential_pairs.update(get_all_pairs())
        
        if not essential_pairs:
            return

        live_prices = await get_current_prices_from_api(list(essential_pairs))

        if not live_prices:
            logger.warning("API سے کوئی قیمت حاصل نہیں ہوئی۔ جانچ روکی جا رہی ہے۔")
            return

        # مارکیٹ کی حالت کو اپ ڈیٹ کریں (کوئی تبدیلی نہیں)
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
                
                # ★★★ ٹرینر کو فیڈ بیک بھیجیں (سب سے اہم قدم) ★★★
                # نوٹ: ہم سگنل کو ڈیلیٹ کرنے سے پہلے فیڈ بیک بھیجتے ہیں تاکہ ٹرینر کے پاس مکمل ڈیٹا ہو
                trainerai.learn_from_outcome(db, signal, outcome)
                
                # اب باقی کام کریں
                crud.add_completed_trade(db, signal, outcome)
                crud.add_feedback_entry(db, signal.symbol, signal.timeframe, feedback)
                crud.delete_active_signal(db, signal.signal_id)
                
                await manager.broadcast({
                    "type": "signal_closed",
                    "data": {"signal_id": signal.signal_id}
                })
                
    except Exception as e:
        logger.error(f"فعال سگنلز کی جانچ کے دوران مہلک خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()

