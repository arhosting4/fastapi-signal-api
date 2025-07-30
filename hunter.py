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
from utils import get_tradeable_pairs, get_real_time_quotes, fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from config import STRATEGY

logger = logging.getLogger(__name__)

FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]
MOMENTUM_FILE = "market_momentum.json"
ANALYSIS_CANDIDATE_COUNT = 4 # کتنے بہترین جوڑوں کا تجزیہ کرنا ہے

# ==============================================================================
# ★★★ اپرنٹس کا کام: ہر منٹ ڈیٹا اکٹھا کرنا ★★★
# ==============================================================================
async def collect_market_data_job():
    """ہر منٹ چلتا ہے اور مارکیٹ کی حرکت کو ایک فائل میں محفوظ کرتا ہے۔"""
    logger.info("👨‍🎓 اپرنٹس: مارکیٹ ڈیٹا اکٹھا کیا جا رہا ہے...")
    
    try:
        with open(MOMENTUM_FILE, 'r') as f:
            market_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        market_data = {}

    pairs_to_check = get_tradeable_pairs()
    if not pairs_to_check: return

    quotes = await get_real_time_quotes(pairs_to_check)
    if not quotes:
        logger.warning("اپرنٹس: اس منٹ کوئی قیمت حاصل نہیں ہوئی۔")
        return

    now_iso = datetime.utcnow().isoformat()
    for symbol, data in quotes.items():
        if "percent_change" in data:
            if symbol not in market_data:
                market_data[symbol] = []
            
            try:
                market_data[symbol].append({
                    "time": now_iso,
                    "change": float(data["percent_change"])
                })
                # صرف پچھلے 10 منٹ کا ڈیٹا رکھیں
                market_data[symbol] = market_data[symbol][-10:]
            except (ValueError, TypeError):
                continue

    try:
        with open(MOMENTUM_FILE, 'w') as f:
            json.dump(market_data, f)
        logger.info(f"✅ اپرنٹس: {len(quotes)} جوڑوں کا ڈیٹا کامیابی سے محفوظ کیا گیا۔")
    except IOError as e:
        logger.error(f"مومنٹم فائل لکھنے میں خرابی: {e}")

# ==============================================================================
# ★★★ ماسٹر کا کام: ہر 5 منٹ بعد تجزیہ کرنا ★★★
# ==============================================================================
async def analyze_market_data_job():
    """ہر 5 منٹ بعد چلتا ہے، بہترین جوڑوں کا انتخاب کرتا ہے اور ان کا گہرا تجزیہ کرتا ہے۔"""
    logger.info("👑 ماسٹر: پچھلے 5 منٹ کے ڈیٹا کا تجزیہ شروع...")
    
    try:
        with open(MOMENTUM_FILE, 'r') as f:
            market_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("ماسٹر: تجزیہ کے لیے کوئی ڈیٹا فائل نہیں ملی۔")
        return

    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    candidate_scores = {}

    for symbol, history in market_data.items():
        recent_history = [h for h in history if datetime.fromisoformat(h['time']) > five_minutes_ago]
        if len(recent_history) < 3:
            continue

        df = pd.DataFrame(recent_history)
        total_change = df['change'].sum()
        consistency = df['change'].apply(np.sign).mean()
        
        score = abs(total_change) * (abs(consistency) ** 2)
        candidate_scores[symbol] = score

    if not candidate_scores:
        logger.info("👑 ماسٹر: کوئی بھی جوڑا مستحکم حرکت کے معیار پر پورا نہیں اترا۔")
        return

    sorted_candidates = sorted(candidate_scores.items(), key=lambda item: item[1], reverse=True)
    pairs_to_analyze = [item[0] for item in sorted_candidates[:ANALYSIS_CANDIDATE_COUNT]]
    
    logger.info(f"👑 ماسٹر: گہرے تجزیے کے لیے {len(pairs_to_analyze)} بہترین امیدوار منتخب کیے گئے: {pairs_to_analyze}")

    db = SessionLocal()
    try:
        active_signals = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
        final_list = [p for p in pairs_to_analyze if p not in active_signals]
        
        if final_list:
            analysis_tasks = [analyze_single_pair(db, pair) for pair in final_list]
            await asyncio.gather(*analysis_tasks)
    except Exception as e:
        logger.error(f"ماسٹر کے تجزیے کے دوران خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("👑 ماسٹر: تجزیے کا دور مکمل ہوا۔")

async def analyze_single_pair(db: Session, pair: str):
    """یہ فنکشن صرف ایک جوڑے کا تجزیہ کرتا ہے"""
    logger.info(f"🔬 [{pair}] کا گہرا تجزیہ کیا جا رہا ہے...")
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34:
        logger.info(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا۔")
        return

    analysis_result = await generate_final_signal(db, pair, candles)
    
    if analysis_result and analysis_result.get("status") == "ok":
        confidence = analysis_result.get('confidence', 0)
        log_message = (
            f"📊 [{pair}] تجزیہ مکمل: سگنل = {analysis_result.get('signal', 'N/A').upper()}, "
            f"اعتماد = {confidence:.2f}%"
        )
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
    
