# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

# مقامی امپورٹس
import database_crud as crud
from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ کنفیگریشن کو اپ ڈیٹ کیا گیا ★★★
# ==============================================================================
MAX_ACTIVE_SIGNALS = 5
# ★★★ آپ کی ہدایت کے مطابق، کم از کم اعتماد کی حد 70 مقرر کی گئی ہے ★★★
FINAL_CONFIDENCE_THRESHOLD = 70.0

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
        return analysis_result
    elif analysis_result:
        logger.info(f"📊 [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {analysis_result.get('reason', 'نامعلوم')}")
    
    return None

async def hunt_for_signals_job():
    """
    سگنل کی تلاش کا مرکزی کام جو شیڈیولر کے ذریعے چلایا جاتا ہے۔
    """
    db = SessionLocal()
    try:
        active_signals_count = crud.get_active_signals_count_from_db(db)
        if active_signals_count >= MAX_ACTIVE_SIGNALS:
            logger.info(f"فعال سگنلز کی زیادہ سے زیادہ حد ({active_signals_count}/{MAX_ACTIVE_SIGNALS}) تک پہنچ گئے ہیں۔ شکار روکا جا رہا ہے۔")
            return

        pairs = get_available_pairs()
        logger.info(f"🏹 سگنل کی تلاش شروع: ان جوڑوں کا تجزیہ کیا جائے گا: {pairs}")
        
        for pair in pairs:
            if crud.get_active_signals_count_from_db(db) >= MAX_ACTIVE_SIGNALS:
                logger.info("سگنل کی حد تک پہنچ گئے۔ شکار روکا جا رہا ہے۔")
                break
            
            analysis_result = await analyze_pair(db, pair)
            
            # ★★★ یہاں 70 کے اعتماد اسکور کی شرط کو سختی سے نافذ کیا گیا ہے ★★★
            if analysis_result and analysis_result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                
                new_signal = crud.add_or_update_active_signal(db, analysis_result)
                
                if new_signal:
                    if new_signal.is_new:
                        logger.info(f"🎯 ★★★ نیا سگنل ملا اور ڈیٹا بیس میں محفوظ کیا گیا: {new_signal.signal.symbol} - {new_signal.signal.signal_type} @ {new_signal.signal.entry_price} ★★★")
                        await send_telegram_alert(new_signal.signal.as_dict())
                        await manager.broadcast({
                            "type": "new_signal",
                            "data": new_signal.signal.as_dict()
                        })
                    else:
                        logger.info(f"🔄 ★★★ موجودہ سگنل اپ ڈیٹ ہوا: {new_signal.signal.symbol}, نیا اعتماد: {new_signal.signal.confidence:.2f}% ★★★")
                        await manager.broadcast({
                            "type": "signal_updated",
                            "data": new_signal.signal.as_dict()
                        })
            elif analysis_result:
                # یہ لاگ اس وقت دکھایا جائے گا جب سگنل بنے گا لیکن اس کا اعتماد 70 سے کم ہوگا
                confidence = analysis_result.get('confidence', 0)
                logger.info(f"📊 [{pair}] سگنل کو نظر انداز کیا گیا: اعتماد ({confidence:.2f}%) حد ({FINAL_CONFIDENCE_THRESHOLD}%) سے کم ہے۔")


    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("🏹 سگنل کی تلاش مکمل ہوئی۔")
                
