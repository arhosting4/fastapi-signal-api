# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime # datetime امپورٹ کریں

# مقامی امپورٹس
from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
# ★★★ signal_tracker کی جگہ database_crud استعمال کریں ★★★
import database_crud as crud
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

# کنفیگریشن
MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 60.0

async def analyze_pair(db: Session, pair: str) -> Optional[Dict[str, Any]]:
    """ایک تجارتی جوڑے کا تجزیہ کرتا ہے اور اگر کوئی سگنل ملے تو اسے واپس کرتا ہے۔"""
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34:
        logger.info(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
        return None

    signal_result = await generate_final_signal(db, pair, candles)
    
    if signal_result and signal_result.get("status") == "ok":
        confidence = signal_result.get('confidence', 0)
        log_message = (
            f"📊 [{pair}] تجزیہ مکمل: سگنل = {signal_result.get('signal', 'N/A').upper()}, "
            f"اعتماد = {confidence:.2f}%, پیٹرن = {signal_result.get('pattern', 'N/A')}, "
            f"رسک = {signal_result.get('risk', 'N/A')}"
        )
        logger.info(log_message)
        return signal_result
    elif signal_result:
        logger.info(f"📊 [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {signal_result.get('reason', 'نامعلوم')}")
    
    return None

async def hunt_for_signals_job():
    """
    سگنل کی تلاش کا مرکزی کام جو شیڈیولر کے ذریعے چلایا جاتا ہے۔
    """
    db = SessionLocal()
    try:
        active_signals_count = crud.get_active_signals_count_from_db(db)
        if active_signals_count >= MAX_ACTIVE_SIGNALS:
            logger.info(f"فعال سگنلز کی زیادہ سے زیادہ حد ({active_signals_count}) تک پہنچ گئے ہیں۔ شکار روکا جا رہا ہے۔")
            return

        pairs = get_available_pairs()
        logger.info(f"🏹 سگنل کی تلاش شروع: ان جوڑوں کا تجزیہ کیا جائے گا: {pairs}")
        
        all_results = []
        for pair in pairs:
            # ہر جوڑے کے تجزیے سے پہلے دوبارہ گنتی کریں
            if crud.get_active_signals_count_from_db(db) >= MAX_ACTIVE_SIGNALS:
                logger.info("سگنل کی حد تک پہنچ گئے۔ شکار روکا جا رہا ہے۔")
                break
            
            result = await analyze_pair(db, pair)
            if result and result.get("status") == "ok":
                all_results.append(result)

        if all_results:
            best_signal = max(all_results, key=lambda x: x.get('confidence', 0))
            
            if best_signal.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                # ★★★ سگنل کو ڈیٹا بیس میں شامل کریں ★★★
                signal_id = f"{best_signal['symbol']}_{best_signal['timeframe']}_{datetime.utcnow().timestamp()}"
                best_signal['signal_id'] = signal_id
                
                db_signal = crud.add_active_signal_to_db(db, best_signal)
                if db_signal:
                    logger.info(f"🎯 ★★★ نیا سگنل ملا اور ڈیٹا بیس میں محفوظ کیا گیا: {best_signal['symbol']} - {best_signal['signal']} @ {best_signal['price']} ★★★")
                    
                    # الرٹس بھیجیں
                    await send_telegram_alert(best_signal)
                    await manager.broadcast({
                        "type": "new_signal",
                        "data": best_signal
                    })
                else:
                    logger.error(f"سگنل {best_signal['symbol']} کو ڈیٹا بیس میں محفوظ کرنے میں ناکامی۔")

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("🏹 سگنل کی تلاش مکمل ہوئی۔")
        
