# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# مقامی امپورٹس
from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
import database_crud as crud  # ★★★ crud کو امپورٹ کریں ★★★
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

# کنفیگریشن
MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 80.0

async def analyze_pair(db: Session, pair: str) -> Optional[Dict[str, Any]]:
    """ایک تجارتی جوڑے کا تجزیہ کرتا ہے اور اگر کوئی سگنل ملے تو اسے واپس کرتا ہے۔"""
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34:
        logger.info(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا۔")
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
    """سگنل کی تلاش کا مرکزی کام جو شیڈیولر کے ذریعے چلایا جاتا ہے۔"""
    db = SessionLocal()
    try:
        # ★★★ یہاں درست فنکشن کا نام استعمال کریں ★★★
        if crud.get_active_signals_count(db) >= MAX_ACTIVE_SIGNALS:
            logger.info(f"فعال سگنلز کی زیادہ سے زیادہ حد ({MAX_ACTIVE_SIGNALS}) تک پہنچ گئے ہیں۔ شکار روکا جا رہا ہے۔")
            return

        pairs_to_check = get_available_pairs()
        logger.info(f"🏹 سگنل کی تلاش شروع: ان جوڑوں کا تجزیہ کیا جائے گا: {pairs_to_check}")

        for pair in pairs_to_check:
            # ہر جوڑے کے لیے چیک کریں کہ آیا اس کا سگنل پہلے سے موجود ہے
            existing_signal = crud.get_active_signal_by_symbol(db, pair)
            
            # تجزیہ کے لیے کینڈلز حاصل کریں
            analysis_result = await analyze_pair(db, pair)
            if not analysis_result:
                continue

            if existing_signal:
                # اگر سگنل پہلے سے موجود ہے اور نیا تجزیہ بھی اسی سمت میں ہے
                if analysis_result.get('signal') == existing_signal.signal_type:
                    # صرف اعتماد کو اپ ڈیٹ کریں اگر نیا اعتماد زیادہ ہو
                    if analysis_result.get('confidence', 0) > existing_signal.confidence:
                        logger.info(f"🔄 [{pair}] سگنل اپ ڈیٹ: اعتماد {existing_signal.confidence:.2f}% سے {analysis_result['confidence']:.2f}% ہو گیا۔")
                        updated_signal = crud.add_or_update_active_signal(db, analysis_result)
                        await manager.broadcast({
                            "type": "signal_updated",
                            "data": updated_signal.as_dict()
                        })
            else:
                # اگر کوئی فعال سگنل نہیں ہے اور نیا سگنل تھریشولڈ سے اوپر ہے
                if analysis_result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                    logger.info(f"🎯 ★★★ نیا سگنل ملا: {analysis_result['symbol']} - {analysis_result['signal']} @ {analysis_result['price']} ★★★")
                    new_signal = crud.add_or_update_active_signal(db, analysis_result)
                    
                    await send_telegram_alert(new_signal.as_dict())
                    await manager.broadcast({
                        "type": "new_signal",
                        "data": new_signal.as_dict()
                    })
                    # ایک بار میں ایک ہی نیا سگنل بنائیں تاکہ API کی حد سے بچا جا سکے
                    break

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("🏹 سگنل کی تلاش مکمل ہوئی۔")
        
