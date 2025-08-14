# filename: feedback_checker.py

import asyncio
import logging
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# مقامی امپورٹس
from models import SessionLocal, ActiveSignal, CompletedTrade
from utils import get_real_time_quotes
from websocket_manager import manager
from trainerai import learn_from_outcome

logger = logging.getLogger(__name__)

# ==============================================================================
#  مرحلہ 2: غیر-ایسنک فنکشن جو صرف ڈیٹا بیس کا کام کرے گا
# ==============================================================================
def process_triggered_signals(signals_to_close: List[Dict[str, Any]]):
    """
    یہ فنکشن صرف ڈیٹا بیس کی کارروائیوں کو سنبھالتا ہے۔ یہ async نہیں ہے۔
    """
    if not signals_to_close:
        return

    db: Session = SessionLocal()
    try:
        closed_signal_ids = []
        for signal_data in signals_to_close:
            signal_id = signal_data["signal_id"]
            outcome = signal_data["outcome"]
            close_price = signal_data["close_price"]
            reason = signal_data["reason"]

            signal_to_delete = db.query(ActiveSignal).filter(ActiveSignal.signal_id == signal_id).first()
            if not signal_to_delete:
                logger.warning(f"سگنل {signal_id} پہلے ہی بند ہو چکا ہے، نظر انداز کیا جا رہا ہے۔")
                continue

            logger.info(f"★★★ سگنل {signal_id} کو {outcome.upper()} کے طور پر بند کیا جا رہا ہے ★★★")

            # ڈیٹا بیس میں اندراجات کریں
            completed_trade = CompletedTrade(
                signal_id=signal_to_delete.signal_id, symbol=signal_to_delete.symbol,
                timeframe=signal_to_delete.timeframe, signal_type=signal_to_delete.signal_type,
                entry_price=signal_to_delete.entry_price, tp_price=signal_to_delete.tp_price,
                sl_price=signal_to_delete.sl_price, close_price=close_price,
                reason_for_closure=reason, outcome=outcome, confidence=signal_to_delete.confidence,
                reason=signal_to_delete.reason, created_at=signal_to_delete.created_at,
                closed_at=signal_to_delete.updated_at
            )
            db.add(completed_trade)
            db.delete(signal_to_delete)
            
            closed_signal_ids.append(signal_id)
        
        if closed_signal_ids:
            db.commit()
            logger.info(f"{len(closed_signal_ids)} سگنلز کامیابی سے ہسٹری میں منتقل ہو گئے۔")
            # اب براڈکاسٹ کریں
            for sid in closed_signal_ids:
                asyncio.run(manager.broadcast({"type": "signal_closed", "data": {"signal_id": sid}}))

    except SQLAlchemyError as e:
        logger.error(f"سگنلز کو بند کرنے میں ڈیٹا بیس کی خرابی: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

# ==============================================================================
#  مرحلہ 1: مرکزی async فنکشن جو صرف سگنلز کی شناخت کرے گا
# ==============================================================================
async def check_active_signals_job():
    logger.info("🛡️ نگران انجن (ورژن 6.0 - آرکیٹیکچرل فکس): نگرانی کا دور شروع...")
    
    db: Session = SessionLocal()
    signals_to_process_later = []
    try:
        active_signals = db.query(ActiveSignal).all()
        
        if not active_signals:
            logger.info("🛡️ نگران: کوئی فعال سگنل موجود نہیں۔")
            return

        logger.info(f"🛡️ نگران: {len(active_signals)} فعال سگنلز ملے، جانچ شروع کی جا رہی ہے...")
        
        symbols_to_check = list({s.symbol for s in active_signals})
        latest_quotes = await get_real_time_quotes(symbols_to_check)

        if not latest_quotes:
            logger.warning("🛡️ نگران: کوئی مارکیٹ قیمتیں حاصل نہیں ہوئیں۔")
            return

        for signal in active_signals:
            quote = latest_quotes.get(signal.symbol)
            if not quote or 'price' not in quote:
                continue
            
            try:
                current_price = float(quote['price'])
            except (ValueError, TypeError):
                continue

            logger.info(f"🛡️ جانچ: [{signal.symbol}] | قسم: {signal.signal_type} | TP: {signal.tp_price} | SL: {signal.sl_price} | موجودہ قیمت: {current_price}")

            outcome, reason = None, None
            tp, sl = float(signal.tp_price), float(signal.sl_price)

            if signal.signal_type == "buy":
                if current_price >= tp: outcome, reason = "tp_hit", "TP Hit"
                elif current_price <= sl: outcome, reason = "sl_hit", "SL Hit"
            elif signal.signal_type == "sell":
                if current_price <= tp: outcome, reason = "tp_hit", "TP Hit"
                elif current_price >= sl: outcome, reason = "sl_hit", "SL Hit"

            if outcome:
                signals_to_process_later.append({
                    "signal_id": signal.signal_id,
                    "outcome": outcome,
                    "close_price": current_price,
                    "reason": reason
                })

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    finally:
        db.close()
    
    # تمام شناخت شدہ سگنلز کو پروسیسنگ کے لیے بھیجیں
    if signals_to_process_later:
        process_triggered_signals(signals_to_process_later)
    
    logger.info("🛡️ نگران انجن (ورژن 6.0): نگرانی کا دور مکمل ہوا۔")
        
