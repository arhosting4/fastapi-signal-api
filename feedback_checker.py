# filename: feedback_checker.py

import asyncio
import logging
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal
from utils import get_current_prices_from_api # ★★★ اب یہ امپورٹ کام کرے گا ★★★
from websocket_manager import manager

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    یہ جاب ہر منٹ چلتی ہے، ڈیٹا بیس سے تمام فعال سگنلز حاصل کرتی ہے،
    ان کی تازہ ترین قیمتیں API سے لیتی ہے، اور TP/SL کو چیک کرتی ہے۔
    """
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        
        if not active_signals:
            return

        logger.info(f"📈 پرائس چیک شروع: {len(active_signals)} فعال سگنلز کی نگرانی کی جا رہی ہے۔")

        symbols_to_check = list(set([s.symbol for s in active_signals]))
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
                    
                    crud.add_completed_trade_from_active(db, signal, outcome)
                    crud.add_feedback_entry(db, signal.symbol, signal.timeframe, feedback)
                    
                    signal_id_to_broadcast = signal.signal_id
                    db.delete(signal)
                    db.commit() # ★★★ ہر سگنل کو بند کرنے کے بعد فوری کمٹ کریں ★★★
                    
                    await manager.broadcast({
                        "type": "signal_closed",
                        "data": {"signal_id": signal_id_to_broadcast}
                    })
                    
            except Exception as e:
                logger.error(f"سگنل {signal.signal_id} پر کارروائی کے دوران خرابی: {e}", exc_info=True)
                db.rollback()

    except Exception as e:
        logger.error(f"فعال سگنلز کی جانچ کے دوران مہلک خرابی: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
        
