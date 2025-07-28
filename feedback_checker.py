# filename: feedback_checker.py

import asyncio
import json
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal
from utils import get_all_pairs, get_current_prices_from_api # ★★★ نیا امپورٹ ★★★
from websocket_manager import manager
# ★★★ trainerai کو امپورٹ کریں گے تاکہ فیڈ بیک بھیج سکیں (مستقبل کے لیے) ★★★
# import trainerai 

logger = logging.getLogger(__name__)

# مارکیٹ کی حالت کو محفوظ کرنے کے لیے فائل کا نام
MARKET_STATE_FILE = "market_state.json"

# ==============================================================================
# ★★★ نیا فنکشن: مارکیٹ کی حالت کو کیش کرنا ★★★
# ==============================================================================
def _update_market_state_cache(prices: Dict[str, float]):
    """
    تازہ ترین قیمتوں کو ایک JSON فائل میں محفوظ کرتا ہے تاکہ دوسرے ماڈیولز استعمال کر سکیں۔
    """
    try:
        # موجودہ ڈیٹا کو پڑھیں (اگر فائل موجود ہے)
        try:
            with open(MARKET_STATE_FILE, 'r') as f:
                state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            state = {}

        # ہر قیمت کے لیے، پچھلی قیمت اور ٹائم اسٹیمپ کو اپ ڈیٹ کریں
        for symbol, price in prices.items():
            if symbol not in state:
                state[symbol] = {}
            
            # پچھلی قیمت کو محفوظ کریں
            if 'current_price' in state[symbol]:
                state[symbol]['previous_price'] = state[symbol]['current_price']
            
            state[symbol]['current_price'] = price
            state[symbol]['timestamp'] = datetime.now(timezone.utc).isoformat()

        # اپ ڈیٹ شدہ حالت کو واپس فائل میں لکھیں
        with open(MARKET_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"مارکیٹ اسٹیٹ کیش کامیابی سے {len(prices)} جوڑوں کے ساتھ اپ ڈیٹ ہو گیا۔")

    except Exception as e:
        logger.error(f"مارکیٹ اسٹیٹ کیش اپ ڈیٹ کرنے میں خرابی: {e}", exc_info=True)


async def check_active_signals_job():
    """
    یہ جاب ہر 2 منٹ چلتی ہے، تمام جوڑوں کی قیمتیں لیتی ہے، مارکیٹ کی حالت کو کیش کرتی ہے،
    اور فعال سگنلز کے TP/SL کو چیک کرتی ہے۔
    """
    db = SessionLocal()
    try:
        # 1. ★★★ تمام ممکنہ جوڑوں کی فہرست حاصل کریں ★★★
        all_pairs = get_all_pairs()
        if not all_pairs:
            logger.warning("کوئی بھی جوڑا دستیاب نہیں، قیمت کی جانچ روکی جا رہی ہے۔")
            return

        # 2. ★★★ ان تمام جوڑوں کی تازہ ترین قیمتیں حاصل کریں ★★★
        live_prices = await get_current_prices_from_api(all_pairs)
        if not live_prices:
            logger.warning("API سے کوئی قیمت حاصل نہیں ہوئی۔ جانچ روکی جا رہی ہے۔")
            db.close()
            return
            
        # 3. ★★★ مارکیٹ کی حالت کو کیش کریں ★★★
        _update_market_state_cache(live_prices)

        # 4. ڈیٹا بیس سے تمام فعال سگنلز حاصل کریں
        active_signals = crud.get_all_active_signals_from_db(db)
        if not active_signals:
            logger.info("کوئی فعال سگنل نہیں، TP/SL کی جانچ کی ضرورت نہیں۔")
            db.close()
            return

        logger.info(f"{len(active_signals)} فعال سگنلز کی TP/SL جانچ شروع ہو رہی ہے۔")

        # 5. ہر فعال سگنل کو اس کی تازہ ترین قیمت کے ساتھ چیک کریں
        for signal in active_signals:
            current_price = live_prices.get(signal.symbol)
            if current_price is None:
                logger.warning(f"سگنل {signal.signal_id} ({signal.symbol}) کے لیے قیمت حاصل نہیں کی جا سکی۔")
                continue

            outcome = None
            feedback = None

            # TP/SL کی منطق
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

            # 6. اگر کوئی نتیجہ نکلے تو سگنل کو بند کریں
            if outcome:
                logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome} کے طور پر نشان زد کیا گیا ★★★")
                
                # (مستقبل کا کام: یہاں trainerai کو کال کریں گے)
                # trainerai.learn_from_outcome(signal, outcome)

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
            
