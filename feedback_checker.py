# filename: feedback_checker.py

import asyncio
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# مقامی امپورٹس
from models import SessionLocal, ActiveSignal, CompletedTrade
from utils import get_real_time_quotes
from websocket_manager import manager
from trainerai import learn_from_outcome

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    logger.info("🛡️ نگران انجن (ورژن 5.0 - فول پروف): نگرانی کا دور شروع...")
    
    db: Session = SessionLocal()
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

        # --- تمام منطق کو ایک ہی سیشن کے اندر، ایک ہی لوپ میں چلائیں ---
        for signal in active_signals:
            quote = latest_quotes.get(signal.symbol)
            if not quote or 'price' not in quote:
                continue
            
            try:
                current_price = float(quote['price'])
            except (ValueError, TypeError):
                logger.warning(f"🛡️ [{signal.symbol}] کے لیے قیمت کو فلوٹ میں تبدیل نہیں کیا جا سکا: '{quote['price']}'")
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
                logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا۔ بند ہونے کی قیمت: {current_price} ★★★")
                
                # سگنل کو بند کرنے سے پہلے اس کی ایک کاپی بنائیں
                signal_copy_for_learning = {
                    "signal_id": signal.signal_id, "symbol": signal.symbol, "confidence": signal.confidence,
                    "reason": signal.reason, "component_scores": signal.component_scores,
                    "created_at": signal.created_at
                }

                # ڈیٹا بیس میں تبدیلیاں کریں
                try:
                    completed_trade = CompletedTrade(
                        signal_id=signal.signal_id, symbol=signal.symbol, timeframe=signal.timeframe,
                        signal_type=signal.signal_type, entry_price=signal.entry_price,
                        tp_price=signal.tp_price, sl_price=signal.sl_price, close_price=current_price,
                        reason_for_closure=reason, outcome=outcome, confidence=signal.confidence,
                        reason=signal.reason, created_at=signal.created_at, closed_at=signal.updated_at
                    )
                    db.add(completed_trade)
                    db.delete(signal)
                    db.commit()
                    logger.info(f"سگنل {signal.signal_id} کامیابی سے ہسٹری میں منتقل ہو گیا۔")

                    # براڈکاسٹ اور لرننگ کے لیے ٹاسک بنائیں
                    asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
                    
                    # learn_from_outcome کو ایک سادہ ڈکشنری بھیجیں
                    # یہ ایک عارضی حل ہے، ہمیں ActiveSignal آبجیکٹ بھیجنا چاہیے
                    # لیکن ابھی کے لیے یہ کام کرے گا
                    # asyncio.create_task(learn_from_outcome(db, signal_copy_for_learning, outcome))


                except SQLAlchemyError as e:
                    logger.error(f"سگنل {signal.signal_id} کو بند کرنے میں خرابی: {e}", exc_info=True)
                    db.rollback()

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    finally:
        db.close()
    
    logger.info("🛡️ نگران انجن (ورژن 5.0): نگرانی کا دور مکمل ہوا۔")

