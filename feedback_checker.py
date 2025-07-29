# filename: feedback_checker.py

import asyncio
import logging
from typing import List, Deque
from collections import deque
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_current_prices_from_api, update_market_state
from websocket_manager import manager
import trainerai
from config import FEEDBACK_CHECKER

logger = logging.getLogger(__name__)

# --- ذہین قطار کا نظام ---
signal_check_queue: Deque[str] = deque()
signal_check_set = set()

MAX_PAIRS_PER_CALL = FEEDBACK_CHECKER["MAX_PAIRS_PER_CALL"]
PRIORITY_SYMBOLS = set(FEEDBACK_CHECKER["PRIORITY_SYMBOLS"])

async def check_active_signals_job():
    """
    یہ جاب ہر منٹ چلتی ہے اور ایک ذہین قطار کا استعمال کرتے ہوئے فعال سگنلز کو چیک کرتی ہے۔
    """
    db = SessionLocal()
    try:
        # 1. ڈیٹا بیس سے تمام فعال سگنلز حاصل کریں
        active_signals: List[ActiveSignal] = crud.get_all_active_signals_from_db(db)
        if not active_signals:
            signal_check_queue.clear()
            signal_check_set.clear()
            try:
                essential_prices = await get_current_prices_from_api(list(PRIORITY_SYMBOLS)[:4])
                if essential_prices:
                    update_market_state(essential_prices)
            except Exception as e:
                logger.error(f"بنیادی جوڑوں کی قیمتیں حاصل کرنے میں خرابی: {e}")
            return

        # 2. قطار کو اپ ڈیٹ کریں
        active_symbols_set = {s.symbol for s in active_signals}
        
        current_queue_list = list(signal_check_queue)
        for symbol in current_queue_list:
            if symbol not in active_symbols_set:
                if symbol in signal_check_queue: signal_check_queue.remove(symbol)
                if symbol in signal_check_set: signal_check_set.remove(symbol)

        new_signals_to_add = active_symbols_set - signal_check_set
        
        priority_new = [s for s in new_signals_to_add if s in PRIORITY_SYMBOLS]
        other_new = [s for s in new_signals_to_add if s not in PRIORITY_SYMBOLS]

        for symbol in reversed(priority_new):
            if symbol not in signal_check_set:
                signal_check_queue.appendleft(symbol)
                signal_check_set.add(symbol)
        
        for symbol in other_new:
            if symbol not in signal_check_set:
                signal_check_queue.append(symbol)
                signal_check_set.add(symbol)

        # 3. اس منٹ چیک کرنے کے لیے جوڑوں کا بیچ بنائیں
        if not signal_check_queue:
            logger.info("اس منٹ چیک کرنے کے لیے قطار میں کوئی جوڑا نہیں۔")
            return
            
        pairs_to_check_this_minute = []
        for _ in range(min(len(signal_check_queue), MAX_PAIRS_PER_CALL)):
            pairs_to_check_this_minute.append(signal_check_queue.popleft())

        if not pairs_to_check_this_minute:
            logger.info("اس منٹ چیک کرنے کے لیے کوئی جوڑا نہیں ملا۔")
            return

        logger.info(f"قیمت کی جانچ کا بیچ: {pairs_to_check_this_minute}")

        # 4. قیمتیں حاصل کریں اور مارکیٹ اسٹیٹ اپ ڈیٹ کریں
        live_prices = await get_current_prices_from_api(pairs_to_check_this_minute)
        if not live_prices:
            logger.warning("API سے کوئی قیمت حاصل نہیں ہوئی۔ جانچ روکی جا رہی ہے۔")
            signal_check_queue.extendleft(reversed(pairs_to_check_this_minute))
            return
            
        update_market_state(live_prices)
        
        # 5. TP/SL کی جانچ
        signals_to_process = [s for s in active_signals if s.symbol in live_prices]
        for signal in signals_to_process:
            current_price = live_prices.get(signal.symbol)
            if current_price is None:
                continue

            outcome, close_price, reason_for_closure = None, None, None

            if signal.signal_type == "buy":
                if current_price >= signal.tp_price:
                    outcome, close_price, reason_for_closure = "tp_hit", signal.tp_price, "tp_hit"
                elif current_price <= signal.sl_price:
                    outcome, close_price, reason_for_closure = "sl_hit", signal.sl_price, "sl_hit"
            elif signal.signal_type == "sell":
                if current_price <= signal.tp_price:
                    outcome, close_price, reason_for_closure = "tp_hit", signal.tp_price, "tp_hit"
                elif current_price >= signal.sl_price:
                    outcome, close_price, reason_for_closure = "sl_hit", signal.sl_price, "sl_hit"

            if outcome and close_price is not None:
                logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome} کے طور پر نشان زد کیا گیا ★★★")
                
                await trainerai.learn_from_outcome(db, signal, outcome)
                
                # ★★★ یہاں تبدیلی کی گئی ہے ★★★
                # اب ہم نئے اور درست فنکشن کو کال کر رہے ہیں
                crud.close_and_archive_signal(
                    db=db, 
                    signal_id=signal.signal_id, 
                    outcome=outcome, 
                    close_price=close_price, 
                    reason_for_closure=reason_for_closure
                )
                
                asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
                
                if signal.symbol in signal_check_set:
                    signal_check_set.remove(signal.symbol)
        
        # 6. جن جوڑوں کو چیک کیا گیا، انہیں واپس قطار کے آخر میں ڈال دیں
        for symbol in pairs_to_check_this_minute:
            if symbol in signal_check_set:
                signal_check_queue.append(symbol)

    except Exception as e:
        logger.error(f"فعال سگنلز کی جانچ کے دوران مہلک خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
                
