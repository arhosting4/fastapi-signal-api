# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

# مقامی امپورٹس
import database_crud as crud
from utils import get_pairs_to_hunt, fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from config import STRATEGY

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے متغیرات ---
FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]

async def analyze_pair(db: Session, pair: str) -> Optional[Dict[str, Any]]:
    """ایک تجارتی جوڑے کا تجزیہ کرتا ہے اور اگر کوئی سگنل ملے تو اسے واپس کرتا ہے۔"""
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34:
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
        
        if confidence >= FINAL_CONFIDENCE_THRESHOLD:
            return analysis_result
        else:
            logger.info(f"📊 [{pair}] سگنل مسترد: اعتماد ({confidence:.2f}%) تھریشولڈ ({FINAL_CONFIDENCE_THRESHOLD}%) سے کم ہے۔")
            
    elif analysis_result:
        logger.info(f"📊 [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {analysis_result.get('reason', 'نامعلوم')}")
    
    return None

async def hunt_for_signals_job():
    """
    سگنل کی تلاش کا مرکزی کام جو اب سگنلز کی تعداد پر کوئی حد نہیں لگاتا۔
    """
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        
        pairs_to_hunt = get_pairs_to_hunt([s.symbol for s in active_signals])
        if not pairs_to_hunt:
            logger.info("شکار کے لیے کوئی نئے جوڑے دستیاب نہیں۔ تلاش روکی جا رہی ہے۔")
            return

        logger.info(f"🏹 ذہین سگنل کی تلاش شروع: ان جوڑوں کا تجزیہ کیا جائے گا: {pairs_to_hunt}")
        
        for pair in pairs_to_hunt:
            analysis_result = await analyze_pair(db, pair)
            
            if analysis_result:
                update_result = crud.add_or_update_active_signal(db, analysis_result)
                
                if update_result:
                    signal_obj = update_result.signal.as_dict()
                    
                    if update_result.is_new:
                        logger.info(f"🎯 ★★★ نیا سگنل ملا۔ پس منظر میں الرٹ بھیجا جا رہا ہے: {signal_obj['symbol']} ★★★")
                        asyncio.create_task(send_telegram_alert(signal_obj))
                        asyncio.create_task(manager.broadcast({"type": "new_signal", "data": signal_obj}))
                    else:
                        logger.info(f"🔄 ★★★ موجودہ سگنل اپ ڈیٹ ہوا۔ پس منظر میں الرٹ بھیجا جا رہا ہے: {signal_obj['symbol']} ★★★")
                        asyncio.create_task(send_signal_update_alert(signal_obj))
                        asyncio.create_task(manager.broadcast({"type": "signal_updated", "data": signal_obj}))

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🏹 ذہین سگنل کی تلاش مکمل ہوئی۔")
        
