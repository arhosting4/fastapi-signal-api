# filename: feedback_checker.py

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_real_time_quotes
from websocket_manager import manager
from trainerai import learn_from_outcome

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    یہ فنکشن اب درست ترتیب کے ساتھ کام کرتا ہے:
    1. تمام فعال سگنلز حاصل کرتا ہے۔
    2. گریس پیریڈ والے سگنلز کو الگ کرتا ہے۔
    3. صرف اہل سگنلز کی قیمتیں حاصل کرتا ہے۔
    4. قیمت کی بنیاد پر TP/SL کو چیک کرتا ہے۔
    """
    logger.info("🛡️ نگران انجن: نگرانی کا نیا، درست دور شروع...")
    
    db = SessionLocal()
    try:
        all_active_signals = crud.get_all_active_signals_from_db(db)
        
        if not all_active_signals:
            logger.info("🛡️ نگران انجن: کوئی فعال سگنل موجود نہیں۔")
            return

        # --- مرحلہ 1: گریس پیریڈ والے سگنلز کو الگ کریں ---
        signals_to_check_now = []
        made_grace_period_change = False
        for signal in all_active_signals:
            if signal.is_new:
                logger.info(f"🛡️ سگنل {signal.symbol} گریس پیریڈ میں ہے۔ اس کا فلیگ اپ ڈیٹ کیا جا رہا ہے۔")
                signal.is_new = False
                made_grace_period_change = True
            else:
                signals_to_check_now.append(signal)
        
        # اگر کوئی فلیگ تبدیل ہوا ہے تو ڈیٹا بیس میں محفوظ کریں
        if made_grace_period_change:
            db.commit()

        # --- مرحلہ 2: اگر کوئی اہل سگنل نہیں تو دور ختم کریں ---
        if not signals_to_check_now:
            logger.info("🛡️ نگران انجن: چیک کرنے کے لیے کوئی اہل فعال سگنل نہیں (سب گریس پیریڈ میں تھے)۔")
            return

        # --- مرحلہ 3: صرف اہل سگنلز کی قیمتیں حاصل کریں ---
        symbols_to_check = list({s.symbol for s in signals_to_check_now})
        logger.info(f"🛡️ نگران: {len(symbols_to_check)} اہل جوڑوں کے لیے حقیقی وقت کی قیمتیں حاصل کی جا رہی ہیں...")
        latest_quotes = await get_real_time_quotes(symbols_to_check)

        if not latest_quotes:
            logger.warning("🛡️ نگران انجن: قیمتیں حاصل کرنے میں ناکامی۔ دور ختم کیا جا رہا ہے۔")
            return
            
        logger.info(f"✅ قیمت کی یادداشت اپ ڈیٹ ہوئی۔ کل {len(latest_quotes)} جوڑوں کا ڈیٹا ہے۔")

        # --- مرحلہ 4: اہل سگنلز پر TP/SL چیک کریں ---
        logger.info(f"🛡️ نگران: {len(signals_to_check_now)} اہل سگنلز پر TP/SL کی جانچ کی جا رہی ہے...")
        await check_signals_for_tp_sl(db, signals_to_check_now, latest_quotes)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🛡️ نگران انجن: نگرانی کا دور مکمل ہوا۔")


async def check_signals_for_tp_sl(db: Session, signals: List[ActiveSignal], quotes: Dict[str, Any]):
    """
    یہ فنکشن اب صرف اہل سگنلز کو چیک کرتا ہے۔
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
    else:
        logger.info("🛡️ نگران: کسی بھی سگنل کا TP/SL ہٹ نہیں ہوا۔")
    
