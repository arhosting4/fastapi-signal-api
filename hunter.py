# filename: hunter.py

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

# مقامی امپورٹس
import database_crud as crud
from utils import fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from config import STRATEGY

logger = logging.getLogger(__name__)

FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]
MOMENTUM_FILE = "market_momentum.json"
ANALYSIS_CANDIDATE_COUNT = 4

# ==============================================================================
# ★★★ شکاری انجن کا کام (ہر 5 منٹ بعد) ★★★
# ==============================================================================
async def hunt_for_signals_job():
    """
    یہ جاب ہر 5 منٹ چلتی ہے، مارکیٹ کے ڈیٹا کا تجزیہ کرتی ہے اور نئے سگنل تلاش کرتی ہے۔
    """
    logger.info("🏹 شکاری انجن: نئے مواقع کی تلاش شروع...")
    try:
        with open(MOMENTUM_FILE, 'r') as f:
            market_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("🏹 شکاری انجن: تجزیہ کے لیے کوئی ڈیٹا فائل نہیں ملی۔")
        return

    # پچھلے 5 منٹ کے ڈیٹا کی بنیاد پر بہترین امیدواروں کا انتخاب کریں
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    candidate_scores = {}
    for symbol, history in market_data.items():
        # صرف وہ اینٹریز لیں جو پچھلے 5 منٹ میں آئی ہیں
        recent_history = [h for h in history if datetime.fromisoformat(h['time']) > five_minutes_ago]
        if len(recent_history) < 2: continue # کم از کم 2 ڈیٹا پوائنٹس ہونے چاہئیں

        df = pd.DataFrame(recent_history)
        total_change = df['change'].sum()
        # مستقل مزاجی کا اسکور (تمام حرکتیں ایک ہی سمت میں ہیں یا نہیں)
        consistency = abs(df['change'].apply(np.sign).mean())
        
        # اسکور کا فارمولا: کل تبدیلی * مستقل مزاجی کا مربع
        score = abs(total_change) * (consistency ** 2)
        candidate_scores[symbol] = score

    if not candidate_scores:
        logger.info("🏹 شکاری انجن: کوئی بھی جوڑا مستحکم حرکت کے معیار پر پورا نہیں اترا۔")
        return

    # امیدواروں کو اسکور کے لحاظ سے ترتیب دیں
    sorted_candidates = sorted(candidate_scores.items(), key=lambda item: item[1], reverse=True)
    pairs_to_analyze = [item[0] for item in sorted_candidates[:ANALYSIS_CANDIDATE_COUNT]]
    
    logger.info(f"🏹 شکاری انجن: گہرے تجزیے کے لیے {len(pairs_to_analyze)} بہترین امیدوار منتخب کیے گئے: {pairs_to_analyze}")

    db = SessionLocal()
    try:
        active_signals = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
        final_list = [p for p in pairs_to_analyze if p not in active_signals]
        
        if final_list:
            # ایک وقت میں ایک جوڑے کا تجزیہ کریں تاکہ API پر بوجھ نہ پڑے
            for pair in final_list:
                await analyze_single_pair(db, pair)
                await asyncio.sleep(2) # ہر تجزیے کے بعد 2 سیکنڈ کا وقفہ
    finally:
        if db.is_active:
            db.close()
        logger.info("🏹 شکاری انجن: تلاش کا دور مکمل ہوا۔")

async def analyze_single_pair(db: Session, pair: str):
    """ایک جوڑے کا گہرا تجزیہ کرتا ہے اور سگنل بناتا ہے۔"""
    logger.info(f"🔬 [{pair}] کا گہرا تجزیہ کیا جا رہا ہے...")
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34:
        logger.info(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا۔")
        return

    analysis_result = await generate_final_signal(db, pair, candles)
    
    if analysis_result and analysis_result.get("status") == "ok":
        confidence = analysis_result.get('confidence', 0)
        log_message = (f"📊 [{pair}] تجزیہ مکمل: سگنل = {analysis_result.get('signal', 'N/A').upper()}, "
                       f"اعتماد = {confidence:.2f}%")
        logger.info(log_message)
        
        if confidence >= FINAL_CONFIDENCE_THRESHOLD:
            update_result = crud.add_or_update_active_signal(db, analysis_result)
            if update_result:
                signal_obj = update_result.signal.as_dict()
                task_type = "new_signal" if update_result.is_new else "signal_updated"
                alert_task = send_telegram_alert if update_result.is_new else send_signal_update_alert
                logger.info(f"🎯 ★★★ سگنل پروسیس ہوا: {signal_obj['symbol']} ({task_type}) ★★★")
                asyncio.create_task(alert_task(signal_obj))
                asyncio.create_task(manager.broadcast({"type": task_type, "data": signal_obj}))
        else:
            logger.info(f"📉 [{pair}] سگنل مسترد: اعتماد ({confidence:.2f}%) تھریشولڈ سے کم ہے۔")
            
    elif analysis_result:
        logger.info(f"ℹ️ [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {analysis_result.get('reason', 'نامعلوم')}")
    
