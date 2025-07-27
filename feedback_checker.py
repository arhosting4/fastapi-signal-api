# filename: feedback_checker.py

import asyncio
import json
import logging
from typing import List, Dict, Any

import httpx
from sqlalchemy.orm import Session

# مقامی امپورٹس
# ==============================================================================
# ★★★ بنیادی غلطی کا ازالہ: نئے ڈیٹا بیس کے ڈھانچے کے مطابق اپ ڈیٹ کیا گیا ★★★
# ==============================================================================
import database_crud as crud
from models import SessionLocal
from utils import get_current_prices_from_api
from websocket_manager import manager

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    یہ جاب ہر منٹ چلتی ہے، ڈیٹا بیس سے تمام فعال سگنلز حاصل کرتی ہے،
    ان کی تازہ ترین قیمتیں API سے لیتی ہے، اور TP/SL کو چیک کرتی ہے۔
    """
    db = SessionLocal()
    try:
        # 1. ڈیٹا بیس سے تمام فعال سگنلز حاصل کریں
        active_signals = crud.get_all_active_signals_from_db(db)
        if not active_signals:
            # اگر کوئی فعال سگنل نہیں ہے تو کچھ نہ کریں
            return

        # 2. تمام فعال سگنلز کی علامتوں کی ایک فہرست بنائیں
        symbols_to_check = list(set([s.symbol for s in active_signals]))
        if not symbols_to_check:
            return

        logger.info(f"قیمت کی جانچ شروع: ان جوڑوں کے لیے قیمتیں حاصل کی جا رہی ہیں: {symbols_to_check}")

        # 3. API سے ان تمام علامتوں کی تازہ ترین قیمتیں حاصل کریں
        live_prices = await get_current_prices_from_api(symbols_to_check)
        if not live_prices:
            logger.warning("API سے کوئی قیمت حاصل نہیں ہوئی۔ جانچ روکی جا رہی ہے۔")
            return

        # 4. ہر فعال سگنل کو اس کی تازہ ترین قیمت کے ساتھ چیک کریں
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

            # 5. اگر کوئی نتیجہ نکلے تو سگنل کو بند کریں
            if outcome:
                logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome} کے طور پر نشان زد کیا گیا ★★★")
                
                # مکمل شدہ ٹریڈ کو تاریخ میں شامل کریں
                crud.add_completed_trade(db, signal, outcome)
                
                # فیڈ بیک اندراج شامل کریں
                crud.add_feedback_entry(db, signal.symbol, signal.timeframe, feedback)
                
                # فعال سگنل کو ڈیٹا بیس سے ڈیلیٹ کریں
                crud.delete_active_signal(db, signal.signal_id)
                
                # فرنٹ اینڈ کو بتائیں کہ سگنل بند ہو گیا ہے
                await manager.broadcast({
                    "type": "signal_closed",
                    "data": {"signal_id": signal.signal_id}
                })
                
    except Exception as e:
        logger.error(f"فعال سگنلز کی جانچ کے دوران مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        
