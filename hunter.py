# filename: hunter.py

import asyncio
import logging
from contextlib import contextmanager
from typing import Generator, Dict, Any
import json

from sqlalchemy.orm import Session
import pandas as pd

# مقامی امپورٹس
import database_crud as crud
from utils import fetch_twelve_data_ohlc, convert_candles_to_dataframe
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager
from roster_manager import get_hunting_roster
from config import api_settings

# --- اپ گریڈ شدہ امپورٹس ---
import regime_analyzer
from strategy_scalper import generate_adaptive_analysis # پرانا، قابلِ اعتماد فنکشن
from fusion_engine import generate_final_signal      # ہمارا مرکزی دماغ

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
    یہ جاب وقفے وقفے سے چلتی ہے، تجزیے کے لیے جوڑوں کا انتخاب کرتی ہے،
    اور ہر جوڑے کے لیے تجزیاتی پائپ لائن چلاتی ہے۔
    """
    logger.info("🏹 شکاری انجن (فیوژن 2.0): نئے مواقع کی تلاش کا نیا دور شروع...")
    
    try:
        with get_db_session() as db:
            pairs_to_analyze = get_hunting_roster(db)
        
        if not pairs_to_analyze:
            logger.info("🏹 شکاری انجن: تجزیے کے لیے کوئی اہل جوڑا نہیں۔ تلاش کا دور ختم۔")
            return

        personalities = load_asset_personalities()
        
        tasks = [
            analyze_single_pair(pair, personalities) 
            for pair in pairs_to_analyze
        ]
        await asyncio.gather(*tasks)

    except Exception as e:
        logger.error(f"شکاری انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🏹 شکاری انجن (فیوژن 2.0): تلاش کا دور مکمل ہوا۔")

async def analyze_single_pair(pair: str, personalities: Dict):
    """
    ایک انفرادی جوڑے کے لیے تمام ضروری تجزیے کرتا ہے اور حتمی فیصلے کے لیے
    تمام معلومات کو فیوژن انجن کو بھیجتا ہے۔
    """
    logger.info(f"🔬 [{pair}] کا تجزیہ شروع کیا جا رہا ہے...")
    
    try:
        with get_db_session() as db:
            if crud.get_active_signal_by_symbol(db, pair):
                logger.info(f"🔬 [{pair}] تجزیہ روکا گیا: اس جوڑے کا سگنل پہلے سے فعال ہے۔")
                return

        candles = await fetch_twelve_data_ohlc(pair, "15min", 200)
        
        if not candles or len(candles) < 150:
            logger.warning(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
            return

        df = convert_candles_to_dataframe(candles)
        
        # --- تمام تجزیے الگ الگ کریں ---
        
        # 1. بنیادی تکنیکی تجزیہ
        symbol_personality = personalities.get(pair, personalities.get("DEFAULT", {}))
        technical_analysis = generate_adaptive_analysis(df, symbol_personality)
        
        # 2. مارکیٹ کی حالت کا تجزیہ
        market_regime = regime_analyzer.get_market_regime(df)

        # 3. تمام معلومات کو حتمی فیصلے کے لیے فیوژن انجن کو بھیجیں
        with get_db_session() as db:
            final_signal = await generate_final_signal(
                db, 
                pair, 
                df, 
                technical_analysis, 
                market_regime,
                symbol_personality
            )
        
        # --- نتیجہ پروسیس کریں ---
        if final_signal and final_signal.get("status") == "ok":
            logger.info(f"✅ [{pair}] فیوژن انجن نے سگنل منظور کیا! اعتماد: {final_signal.get('confidence'):.1f}%")
            
            with get_db_session() as db:
                update_result = crud.add_or_update_active_signal(db, final_signal)
            
            if update_result:
                signal_obj = update_result.signal.as_dict()
                asyncio.create_task(send_telegram_alert(signal_obj))
                asyncio.create_task(manager.broadcast({"type": "new_signal", "data": signal_obj}))
        else:
            reason = final_signal.get("reason", "کوئی سگنل نہیں") if final_signal else "کوئی سگنل نہیں"
            logger.info(f"ℹ️ [{pair}] کوئی سگنل نہیں بنا۔ وجہ: {reason}")

    except Exception as e:
        logger.error(f"🔬 [{pair}] کے تجزیے کے دوران ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
            
