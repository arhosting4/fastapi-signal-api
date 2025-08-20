# filename: hunter.py

import asyncio
import logging
from contextlib import contextmanager
from typing import Generator, Dict, Any
import json

from sqlalchemy.orm import Session
import pandas as pd

import database_crud as crud
from utils import fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from roster_manager import get_hunting_roster
from config import api_settings

logger = logging.getLogger(__name__)

PERSONALITIES_FILE = "asset_personalities.json"

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def load_asset_personalities() -> Dict:
    try:
        with open(PERSONALITIES_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.error(f"{PERSONALITIES_FILE} نہیں ملی یا خراب ہے۔ ڈیفالٹ شخصیت استعمال کی جائے گی۔")
        return {}

async def hunt_for_signals_job():
    """
    یہ جاب اب ایک ایک کرکے ہر جوڑے کا تجزیہ کرے گی تاکہ وسائل کی ٹکراؤ سے بچا جا سکے۔
    """
    logger.info("🏹 شکاری انجن (حتمی ورژن): نئے مواقع کی تلاش کا نیا دور شروع...")
    
    try:
        with get_db_session() as db:
            pairs_to_analyze = get_hunting_roster(db)
        
        if not pairs_to_analyze:
            logger.info("🏹 شکاری انجن: تجزیے کے لیے کوئی اہل جوڑا نہیں۔ تلاش کا دور ختم۔")
            return

        personalities = load_asset_personalities()
        
        for pair in pairs_to_analyze:
            try:
                await analyze_single_pair(pair, personalities)
                await asyncio.sleep(2) 
            except Exception as e:
                logger.error(f"🔬 [{pair}] کے تجزیے کے دوران ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"شکاری انجن کے کام میں ایک سنگین خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🏹 شکاری انجن (حتمی ورژن): تلاش کا دور مکمل ہوا۔")

async def analyze_single_pair(pair: str, personalities: Dict):
    """
    ایک انفرادی جوڑے کا گہرا تجزیہ کرتا ہے اور اگر معیار پر پورا اترے تو سگنل بناتا ہے۔
    """
    logger.info(f"🔬 [{pair}] کا تجزیہ شروع کیا جا رہا ہے...")
    
    symbol_personality = personalities.get(pair, personalities.get("DEFAULT", {}))

    with get_db_session() as db:
        if crud.get_active_signal_by_symbol(db, pair):
            logger.info(f"🔬 [{pair}] تجزیہ روکا گیا: اس جوڑے کا سگنل پہلے سے فعال ہے۔")
            return

        timeframe = "15min"
        # --- یہ ہے پہلی تبدیلی ---
        candles = await fetch_twelve_data_ohlc(pair, timeframe, 101) # 101 کی درخواست کریں تاکہ 100 ضرور ملیں
        
        # --- یہ ہے دوسری تبدیلی ---
        if not candles or len(candles) < 99: # کم از کم 99 کینڈلز کی شرط
            logger.warning(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
            return

        analysis_result = await generate_final_signal(db, pair, candles, symbol_personality)
    
    if not analysis_result:
        logger.error(f"🔬 [{pair}] تجزیہ ناکام: فیوژن انجن نے کوئی نتیجہ واپس نہیں کیا۔")
        return

    if analysis_result.get("status") == "ok":
        confidence = analysis_result.get('confidence', 0)
        log_message = (f"📊 [{pair}] تجزیہ مکمل: سگنل = {analysis_result.get('signal', 'N/A').upper()}, "
                       f"اعتماد = {confidence:.2f}%")
        logger.info(log_message)
        
        with get_db_session() as db:
            update_result = crud.add_or_update_active_signal(db, analysis_result)
        
        if update_result:
            signal_obj = update_result.signal.as_dict()
            task_type = "new_signal" if update_result.is_new else "signal_updated"
            
            alert_task = send_telegram_alert if update_result.is_new else send_signal_update_alert
            
            logger.info(f"🎯 ★★★ سگنل پروسیس ہوا: {signal_obj['symbol']} ({task_type}) ★★★")
            
            asyncio.create_task(alert_task(signal_obj))
            asyncio.create_task(manager.broadcast({"type": task_type, "data": signal_obj}))
            
    elif analysis_result.get("status") != "no-signal":
        logger.warning(f"ℹ️ [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {analysis_result.get('reason', 'نامعلوم')}")
            
