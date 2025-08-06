# filename: hunter.py

import asyncio
import logging
from contextlib import contextmanager
from typing import Generator, Dict, Any
import pandas as pd
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from utils import fetch_twelve_data_ohlc
from fusion_engine import run_analysis_pipeline
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from roster_manager import get_hunting_roster
from config import strategy_settings, api_settings
from riskguardian import get_market_analysis

logger = logging.getLogger(__name__)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def hunt_for_signals_job():
    """
    یہ جاب مارکیٹ کا تجزیہ کرتی ہے، حکمت عملی کا انتخاب کرتی ہے، اور نئے سگنل تلاش کرتی ہے۔
    """
    logger.info("🏹 شکاری انجن: نئے مواقع کی تلاش کا نیا دور شروع...")
    
    try:
        with get_db_session() as db:
            pairs_to_analyze = get_hunting_roster(db)
        
        if not pairs_to_analyze:
            logger.info("🏹 شکاری انجن: تجزیے کے لیے کوئی اہل جوڑا نہیں۔")
            return

        # 1. مارکیٹ کا مجموعی تجزیہ کریں
        all_pairs_data = await fetch_all_market_data(pairs_to_analyze)
        market_analysis = get_market_analysis(all_pairs_data)
        
        active_strategy = "Scalper" # فی الحال صرف ایک حکمت عملی ہے
        if market_analysis["risk_level"] == "High":
            logger.warning("🔥 مارکیٹ کا رسک بہت زیادہ ہے۔ شکاری انجن اس دور کو چھوڑ رہا ہے۔")
            return

        logger.info(f"♟️ ماسٹر مائنڈ فیصلہ: مارکیٹ کا نظام = {market_analysis['risk_level']}۔ حکمت عملی فعال: {active_strategy}")

        # 2. ہر جوڑے کا متوازی تجزیہ کریں
        tasks = [
            analyze_single_pair(pair, all_pairs_data.get(pair, []), active_strategy, market_analysis["parameters"])
            for pair in pairs_to_analyze
        ]
        await asyncio.gather(*tasks)

    except Exception as e:
        logger.error(f"شکاری انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🏹 شکاری انجن: تلاش کا دور مکمل ہوا۔")

async def fetch_all_market_data(symbols: list) -> Dict[str, Any]:
    """
    تمام جوڑوں کے لیے 15 منٹ اور 1 گھنٹے کا ڈیٹا حاصل کرتا ہے۔
    """
    data = {}
    tasks_15m = [fetch_twelve_data_ohlc(s, "15min", 100) for s in symbols]
    tasks_1h = [fetch_twelve_data_ohlc(s, "1h", 50) for s in symbols]
    
    results_15m = await asyncio.gather(*tasks_15m)
    results_1h = await asyncio.gather(*tasks_1h)

    for i, symbol in enumerate(symbols):
        df_15m = pd.DataFrame([c.dict() for c in results_15m[i]]) if results_15m[i] else pd.DataFrame()
        df_1h = pd.DataFrame([c.dict() for c in results_1h[i]]) if results_1h[i] else pd.DataFrame()
        data[symbol] = [df_1h, df_15m] # پہلے بڑا ٹائم فریم

    return data

async def analyze_single_pair(pair: str, dataframes: list, strategy: str, params: dict):
    """
    ایک انفرادی جوڑے کا گہرا تجزیہ کرتا ہے۔
    """
    if len(dataframes) < 2 or dataframes[0].empty or dataframes[1].empty:
        logger.warning(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی مارکیٹ ڈیٹا۔")
        return

    df_1h, df_15m = dataframes[0], dataframes[1]

    with get_db_session() as db:
        analysis_result = run_analysis_pipeline(db, pair, df_15m, df_1h, strategy, params)
    
    if analysis_result and analysis_result.get("status") == "ok":
        confidence = analysis_result.get('confidence', 0)
        
        if confidence >= strategy_settings.FINAL_CONFIDENCE_THRESHOLD:
            with get_db_session() as db:
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
            
