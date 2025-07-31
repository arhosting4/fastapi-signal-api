# filename: hunter.py

import asyncio
import logging
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from utils import fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from config import STRATEGY
from roster_manager import get_hunting_roster # ★★★ نیا اور اہم امپورٹ ★★★

logger = logging.getLogger(__name__)

FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]

# ==============================================================================
# ★★★ شکاری انجن کا کام (متحرک روسٹر اور متوازی تجزیے کے ساتھ) ★★★
# ==============================================================================
async def hunt_for_signals_job():
    """
    یہ جاب ہر 3 منٹ چلتی ہے، متحرک روسٹر کی بنیاد پر نئے سگنل تلاش کرتی ہے۔
    یہ تمام اہل جوڑوں کا تجزیہ متوازی طور پر کرتی ہے۔
    """
    logger.info("🏹 شکاری انجن: نئے مواقع کی تلاش کا نیا دور شروع...")
    
    db = SessionLocal()
    try:
        # ★★★ تبدیلی: روسٹر مینیجر سے تجزیے کے لیے جوڑوں کی تازہ ترین فہرست حاصل کریں ★★★
        pairs_to_analyze = get_hunting_roster(db)
        
        if not pairs_to_analyze:
            logger.info("🏹 شکاری انجن: تجزیے کے لیے کوئی اہل جوڑا نہیں (شاید سب کے سگنل فعال ہیں یا کنفیگریشن خالی ہے)۔")
            return

        logger.info(f"🏹 شکاری انجن: {len(pairs_to_analyze)} جوڑوں کا متوازی تجزیہ شروع کیا جا رہا ہے: {pairs_to_analyze}")

        # تمام جوڑوں کا تجزیہ ایک ساتھ (concurrently) کرنے کے لیے ٹاسک بنائیں
        tasks = [analyze_single_pair(db, pair) for pair in pairs_to_analyze]
        await asyncio.gather(*tasks)

    except Exception as e:
        logger.error(f"شکاری انجن کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🏹 شکاری انجن: تلاش کا دور مکمل ہوا۔")

async def analyze_single_pair(db: Session, pair: str):
    """
    ایک انفرادی جوڑے کا گہرا تجزیہ کرتا ہے اور اگر معیار پر پورا اترے تو سگنل بناتا ہے۔
    """
    logger.info(f"🔬 [{pair}] کا گہرا تجزیہ کیا جا رہا ہے...")
    
    # یہ چیک اب ضروری نہیں کیونکہ روسٹر مینیجر یہ کام کر رہا ہے، 
    # لیکن ایک اضافی حفاظتی تہہ کے طور پر رکھنا اچھا ہے۔
    if crud.get_active_signal_by_symbol(db, pair):
        logger.info(f"🔬 [{pair}] تجزیہ روکا گیا: سگنل حال ہی میں فعال ہوا ہے۔")
        return

    # OHLC ڈیٹا حاصل کریں
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34: # 34 ایک محفوظ کم از کم حد ہے
        logger.warning(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
        return

    # فیوژن انجن سے حتمی تجزیہ حاصل کریں
    analysis_result = await generate_final_signal(db, pair, candles)
    
    if analysis_result and analysis_result.get("status") == "ok":
        confidence = analysis_result.get('confidence', 0)
        log_message = (f"📊 [{pair}] تجزیہ مکمل: سگنل = {analysis_result.get('signal', 'N/A').upper()}, "
                       f"اعتماد = {confidence:.2f}%")
        logger.info(log_message)
        
        # اگر اعتماد کی حد پوری ہو تو سگنل کو ڈیٹا بیس میں شامل/اپ ڈیٹ کریں
        if confidence >= FINAL_CONFIDENCE_THRESHOLD:
            update_result = crud.add_or_update_active_signal(db, analysis_result)
            if update_result:
                signal_obj = update_result.signal.as_dict()
                task_type = "new_signal" if update_result.is_new else "signal_updated"
                
                # الرٹ بھیجنے کے لیے مناسب فنکشن کا انتخاب کریں
                alert_task = send_telegram_alert if update_result.is_new else send_signal_update_alert
                
                logger.info(f"🎯 ★★★ سگنل پروسیس ہوا: {signal_obj['symbol']} ({task_type}) ★★★")
                
                # الرٹ اور ویب ساکٹ پیغامات کو پس منظر میں بھیجیں
                asyncio.create_task(alert_task(signal_obj))
                asyncio.create_task(manager.broadcast({"type": task_type, "data": signal_obj}))
        else:
            logger.info(f"📉 [{pair}] سگنل مسترد: اعتماد ({confidence:.2f}%) تھریشولڈ ({FINAL_CONFIDENCE_THRESHOLD}%) سے کم ہے۔")
            
    elif analysis_result:
        logger.info(f"ℹ️ [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {analysis_result.get('reason', 'نامعلوم')}")
        
