# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

# مقامی امپورٹس
import database_crud as crud
# ★★★ نئے، ذہین فنکشنز کو امپورٹ کریں ★★★
from utils import fetch_twelve_data_ohlc, get_pairs_to_hunt
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

# کنفیگریشن
MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 70.0

async def analyze_pair(db: Session, pair: str) -> Optional[Dict[str, Any]]:
    """ایک تجارتی جوڑے کا تجزیہ کرتا ہے اور اگر کوئی سگنل ملے تو اسے واپس کرتا ہے۔"""
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 50: # کینڈل کی ضرورت کو 50 کر دیں
        logger.info(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا۔")
        return None

    analysis_result = await generate_final_signal(db, pair, candles)
    
    if analysis_result and analysis_result.get("status") == "ok":
        confidence = analysis_result.get('confidence', 0)
        log_message = (
            f"📊 [{pair}] تجزیہ مکمل: سگنل = {analysis_result.get('signal', 'N/A').upper()}, "
            f"اعتماد = {confidence:.2f}%, پیٹرن = {analysis_result.get('pattern', 'N/A')}, "
            f"رسک = {analysis_result.get('risk', 'N/A')}"
        )
        logger.info(log_message)
        return analysis_result
    elif analysis_result:
        reason = analysis_result.get('reason', 'نامعلوم')
        logger.info(f"📊 [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {reason}")
    
    return None

# ==============================================================================
# ★★★ مکمل طور پر نیا اور ذہین hunt_for_signals_job فنکشن ★★★
# ==============================================================================
async def hunt_for_signals_job():
    """
    سگنل کی تلاش کا مرکزی کام جو ایک ذہین، ترجیحات پر مبنی حکمت عملی استعمال کرتا ہے۔
    """
    db = SessionLocal()
    try:
        # 1. فعال سگنلز کی تعداد چیک کریں
        active_signals_count = crud.get_active_signals_count_from_db(db)
        if active_signals_count >= MAX_ACTIVE_SIGNALS:
            logger.info(f"فعال سگنلز کی زیادہ سے زیادہ حد ({active_signals_count}/{MAX_ACTIVE_SIGNALS}) تک پہنچ گئے ہیں۔ شکار روکا جا رہا ہے۔")
            return

        # 2. فعال سگنلز کی علامتوں کی فہرست حاصل کریں
        active_signals = crud.get_all_active_signals_from_db(db)
        active_symbols = [s.symbol for s in active_signals]

        # 3. ★★★ اسٹریٹجک کمانڈ سینٹر سے شکار کے لیے جوڑوں کی فہرست حاصل کریں ★★★
        pairs_to_hunt = get_pairs_to_hunt(active_symbols)
        
        if not pairs_to_hunt:
            logger.info("شکار کے لیے کوئی فارغ جوڑا دستیاب نہیں۔ تلاش روکی جا رہی ہے۔")
            return

        logger.info(f"🏹 ذہین سگنل کی تلاش شروع: ان جوڑوں کا تجزیہ کیا جائے گا: {pairs_to_hunt}")
        
        # 4. ان منتخب جوڑوں کا تجزیہ کریں
        for pair in pairs_to_hunt:
            # ہر جوڑے کے لیے دوبارہ چیک کریں تاکہ لوپ کے دوران حد سے تجاوز نہ ہو
            if crud.get_active_signals_count_from_db(db) >= MAX_ACTIVE_SIGNALS:
                logger.info("سگنل کی حد تک پہنچ گئے۔ شکار روکا جا رہا ہے۔")
                break
            
            analysis_result = await analyze_pair(db, pair)
            
            if analysis_result and analysis_result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                
                result = crud.add_or_update_active_signal(db, analysis_result)
                
                if result:
                    signal_obj = result.signal.as_dict()
                    # datetime آبجیکٹ کو JSON کے لیے اسٹرنگ میں تبدیل کریں
                    signal_obj['created_at'] = signal_obj['created_at'].isoformat()
                    signal_obj['updated_at'] = signal_obj['updated_at'].isoformat()

                    if result.is_new:
                        logger.info(f"🎯 ★★★ نیا سگنل ملا اور محفوظ کیا گیا: {result.signal.symbol} - {result.signal.signal_type} ★★★")
                        await send_telegram_alert(signal_obj)
                        await manager.broadcast({
                            "type": "new_signal",
                            "data": signal_obj
                        })
                    else:
                        logger.info(f"🔄 ★★★ موجودہ سگنل اپ ڈیٹ ہوا: {result.signal.symbol}, نیا اعتماد: {result.signal.confidence:.2f}% ★★★")
                        await manager.broadcast({
                            "type": "signal_updated",
                            "data": signal_obj
                        })

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("🏹 ذہین سگنل کی تلاش مکمل ہوئی۔")
                        
