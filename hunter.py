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
from models import SessionLocal, ActiveSignal
from websocket_manager import manager
from config import STRATEGY

logger = logging.getLogger(__name__)

FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]
MOMENTUM_FILE = "market_momentum.json"
ANALYSIS_CANDIDATE_COUNT = 4

# ==============================================================================
# ★★★ اپرنٹس کا کام (اب فیڈ بیک چیکر کی ذمہ داری کے ساتھ) ★★★
# ==============================================================================
async def collect_market_data_job():
    """ہر منٹ چلتا ہے، ایک ہی API کال میں فعال سگنلز کو چیک کرتا ہے اور مارکیٹ ڈیٹا محفوظ کرتا ہے۔"""
    logger.info("👨‍🎓 اپرنٹس: مارکیٹ ڈیٹا اکٹھا اور فعال سگنلز کی جانچ شروع...")
    
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        
        # تمام ضروری جوڑوں کی ایک منفرد فہرست بنائیں
        tradeable_pairs = set(get_tradeable_pairs())
        active_signal_pairs = {s.symbol for s in active_signals}
        all_pairs_to_check = list(tradeable_pairs.union(active_signal_pairs))

        if not all_pairs_to_check:
            logger.info("اپرنٹس: چیک کرنے کے لیے کوئی جوڑا نہیں۔")
            return

        # صرف ایک API کال کریں
        quotes = await get_real_time_quotes(all_pairs_to_check)
        if not quotes:
            logger.warning("اپرنٹس: اس منٹ کوئی قیمت/کوٹ حاصل نہیں ہوا۔")
            return

        # 1. فعال سگنلز کی قیمتیں چیک کریں (فیڈ بیک چیکر کی منطق)
        if active_signals:
            await check_signals_for_tp_sl(db, active_signals, quotes)

        # 2. مارکیٹ کا ڈیٹا اکٹھا کریں (اپرنٹس کی منطق)
        try:
            with open(MOMENTUM_FILE, 'r') as f:
                market_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            market_data = {}

        now_iso = datetime.utcnow().isoformat()
        for symbol, data in quotes.items():
            if "percent_change" in data and data.get("percent_change") is not None:
                if symbol not in market_data: market_data[symbol] = []
                try:
                    market_data[symbol].append({"time": now_iso, "change": float(data["percent_change"])})
                    market_data[symbol] = market_data[symbol][-10:]
                except (ValueError, TypeError): continue
        
        with open(MOMENTUM_FILE, 'w') as f:
            json.dump(market_data, f)
        logger.info(f"✅ اپرنٹس: {len(quotes)} جوڑوں کا ڈیٹا کامیابی سے محفوظ کیا گیا۔")

    except Exception as e:
        logger.error(f"اپرنٹس کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()

async def check_signals_for_tp_sl(db: Session, signals: List[ActiveSignal], quotes: Dict[str, Any]):
    """فعال سگنلز کو TP/SL کے لیے چیک کرتا ہے۔"""
    for signal in signals:
        quote_data = quotes.get(signal.symbol)
        if not quote_data or "price" not in quote_data:
            continue
        
        current_price = float(quote_data["price"])

        outcome, close_price, reason = None, None, None
        if signal.signal_type == "buy":
            if current_price >= signal.tp_price:
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit"
            elif current_price <= signal.sl_price:
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit"
        elif signal.signal_type == "sell":
            if current_price <= signal.tp_price:
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit"
            elif current_price >= signal.sl_price:
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit"

        if outcome:
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome} کے طور پر نشان زد کیا گیا ★★★")
            crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
            asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))

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
    finally:
        if db.is_active:
            db.close()
        logger.info("👑 ماسٹر: تجزیے کا دور مکمل ہوا۔")

async def analyze_single_pair(db: Session, pair: str):
    """یہ فنکشن صرف ایک جوڑے کا تجزیہ کرتا ہے۔"""
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
        
