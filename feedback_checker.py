# filename: feedback_checker.py

import asyncio
import json
import logging
import httpx
from datetime import datetime
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud  # ★★★ نیا امپورٹ ★★★
from models import SessionLocal, ActiveSignal
from key_manager import key_manager
from utils import get_current_prices_from_api # ★★★ نیا امپورٹ ★★★
from websocket_manager import manager

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    یہ جاب ہر منٹ چلتی ہے، ڈیٹا بیس سے تمام فعال سگنلز حاصل کرتی ہے،
    ان کی تازہ ترین قیمتیں API سے لیتی ہے، اور TP/SL کو چیک کرتی ہے۔
    """
    db = SessionLocal()
    try:
        # ★★★ بنیادی غلطی کا ازالہ: ڈیٹا بیس سے فعال سگنلز حاصل کریں ★★★
        active_signals = crud.get_all_active_signals_from_db(db)
        
        if not active_signals:
            # اگر کوئی فعال سگنل نہیں ہے تو خاموشی سے باہر نکل جائیں
            return

        logger.info(f"📈 پرائس چیک شروع: {len(active_signals)} فعال سگنلز کی نگرانی کی جا رہی ہے۔")

        # تمام فعال سگنلز کے لیے علامتوں کی ایک منفرد فہرست بنائیں
        symbols_to_check = list(set([s.symbol for s in active_signals]))
        
        # API سے ان علامتوں کے لیے تازہ ترین قیمتیں حاصل کریں
        live_prices = await get_current_prices_from_api(symbols_to_check)

        if not live_prices:
            logger.warning("API سے کوئی قیمت حاصل نہیں ہوئی۔ پرائس چیک روکا جا رہا ہے۔")
            return

        for signal in active_signals:
            try:
                current_price = live_prices.get(signal.symbol)
                if current_price is None:
                    logger.warning(f"سگنل {signal.signal_id} ({signal.symbol}) کے لیے قیمت حاصل نہیں کی جا سکی۔")
                    continue

                logger.info(f"  - [{signal.symbol}] سگنل ID: {signal.signal_id}, موجودہ قیمت: {current_price}, TP: {signal.tp_price}, SL: {signal.sl_price}")

                outcome = None
                feedback = None

                if signal.signal_type.lower() == "buy":
                    if current_price >= signal.tp_price:
                        outcome = "TP Hit"
                        feedback = "correct"
                    elif current_price <= signal.sl_price:
                        outcome = "SL Hit"
                        feedback = "incorrect"
                elif signal.signal_type.lower() == "sell":
                    if current_price <= signal.tp_price:
                        outcome = "TP Hit"
                        feedback = "correct"
                    elif current_price >= signal.sl_price:
                        outcome = "SL Hit"
                        feedback = "incorrect"

                if outcome:
                    logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو '{outcome}' کے طور پر نشان زد کیا گیا ★★★")
                    
                    # 1. سگنل کو مکمل شدہ ٹریڈز میں شامل کریں
                    crud.add_completed_trade_from_active(db, signal, outcome)
                    
                    # 2. فیڈ بیک اندراج شامل کریں
                    crud.add_feedback_entry(db, signal.symbol, signal.timeframe, feedback)
                    
                    # 3. فعال سگنل کو حذف کریں
                    db.delete(signal)
                    
                    # 4. فرنٹ اینڈ کو اطلاع دیں
                    await manager.broadcast({
                        "type": "signal_closed",
                        "data": {"signal_id": signal.signal_id}
                    })
                    
            except Exception as e:
                logger.error(f"سگنل {signal.signal_id} پر کارروائی کے دوران خرابی: {e}", exc_info=True)
        
        # تمام تبدیلیوں کو ایک ساتھ ڈیٹا بیس میں محفوظ کریں
        db.commit()

    except Exception as e:
        logger.error(f"فعال سگنلز کی جانچ کے دوران مہلک خرابی: {e}", exc_info=True)
        db.rollback() # کسی بھی خرابی کی صورت میں تمام تبدیلیوں کو واپس لے لیں
    finally:
        db.close()
        
