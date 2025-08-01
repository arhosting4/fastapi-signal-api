# filename: feedback_checker.py

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_real_time_quotes  # ★★★ صرف یہ فنکشن استعمال ہوگا ★★★
from websocket_manager import manager
from trainerai import learn_from_outcome

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    یہ فنکشن اب انتہائی آسان ہے:
    1. تمام فعال سگنلز حاصل کرتا ہے۔
    2. ان کی تازہ ترین قیمتیں ایک ہی API کال میں حاصل کرتا ہے۔
    3. قیمت کی بنیاد پر TP/SL کو چیک کرتا ہے۔
    """
    logger.info("🛡️ نگران انجن: نگرانی کا نیا، آسان دور شروع...")
    
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        
        if not active_signals:
            logger.info("🛡️ نگران انجن: کوئی فعال سگنل موجود نہیں۔")
            return

        # --- مرحلہ 1: تمام فعال سگنلز کی علامتیں حاصل کریں ---
        symbols_to_check = list({s.symbol for s in active_signals})
        
        # --- مرحلہ 2: تمام قیمتیں ایک ساتھ حاصل کریں ---
        logger.info(f"🛡️ نگران: {len(symbols_to_check)} جوڑوں کے لیے حقیقی وقت کی قیمتیں حاصل کی جا رہی ہیں...")
        latest_quotes = await get_real_time_quotes(symbols_to_check)

        if not latest_quotes:
            logger.warning("🛡️ نگران انجن: قیمتیں حاصل کرنے میں ناکامی۔ دور ختم کیا جا رہا ہے۔")
            return
            
        logger.info(f"✅ قیمت کی یادداشت اپ ڈیٹ ہوئی۔ کل {len(latest_quotes)} جوڑوں کا ڈیٹا ہے۔")

        # --- مرحلہ 3: قیمت کی بنیاد پر TP/SL چیک کریں ---
        await check_signals_for_tp_sl(db, active_signals, latest_quotes)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🛡️ نگران انجن: نگرانی کا دور مکمل ہوا۔")


async def check_signals_for_tp_sl(db: Session, signals: List[ActiveSignal], quotes: Dict[str, Any]):
    """
    یہ فنکشن اب صرف حقیقی وقت کی قیمت کی بنیاد پر سگنلز کو چیک کرتا ہے۔
    """
    signals_closed_count = 0
    for signal in signals:
        if signal.symbol not in quotes:
            continue

        quote_data = quotes.get(signal.symbol)
        if not quote_data or 'price' not in quote_data:
            continue
        
        try:
            current_price = float(quote_data['price'])
        except (ValueError, TypeError):
            continue

        outcome, close_price, reason = None, None, None
        
        # --- براہ راست قیمت کا موازنہ ---
        if signal.signal_type == "buy":
            if current_price >= signal.tp_price: 
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit_by_price"
            elif current_price <= signal.sl_price: 
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_price"
        elif signal.signal_type == "sell":
            if current_price <= signal.tp_price: 
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit_by_price"
            elif current_price >= signal.sl_price: 
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit_by_price"

        if outcome:
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا ({reason}) ★★★")
            
            await learn_from_outcome(db, signal, outcome)
            
            success = crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
            if success:
                signals_closed_count += 1
                asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
    
    if signals_closed_count > 0:
        logger.info(f"🛡️ نگران انجن: کل {signals_closed_count} سگنل بند کیے گئے۔")
        
