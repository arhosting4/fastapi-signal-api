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
from config import strategy_settings, api_settings
from riskguardian import get_market_regime

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے مستقل اقدار ---
FINAL_CONFIDENCE_THRESHOLD = strategy_settings.FINAL_CONFIDENCE_THRESHOLD
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
    یہ جاب وقفے وقفے سے چلتی ہے، مارکیٹ کے نظام کا تعین کرتی ہے اور ایک انکولی اسکیلپنگ حکمت عملی چلاتی ہے۔
    """
    logger.info("🏹 شکاری انجن: نئے مواقع کی تلاش کا نیا دور شروع...")
    
    try:
        with get_db_session() as db:
            pairs_to_analyze = get_hunting_roster(db)
        
        if not pairs_to_analyze:
            logger.info("🏹 شکاری انجن: تجزیے کے لیے کوئی اہل جوڑا نہیں۔ تلاش کا دور ختم۔")
            return

        # مرحلہ 1: مارکیٹ کے نظام کا تعین کریں
        h1_tasks = [fetch_twelve_data_ohlc(pair, "1h", 50) for pair in pairs_to_analyze]
        h1_results = await asyncio.gather(*h1_tasks)
        
        ohlc_data_map = {
            pair: pd.DataFrame([c.dict() for c in candles])
            for pair, candles in zip(pairs_to_analyze, h1_results) if candles
        }
        
        market_regime_data = get_market_regime(ohlc_data_map)
        
        logger.info(f"♟️ ماسٹر مائنڈ فیصلہ: مارکیٹ کا نظام = {market_regime_data['regime']} (VIX: {market_regime_data['vix_score']})۔ انکولی اسکیلپنگ فعال۔")

        if market_regime_data["regime"] == "Stormy":
            logger.info("🛑 ٹریڈنگ معطل: انتہائی غیر مستحکم مارکیٹ (Stormy Regime)۔")
            return

        # مرحلہ 2: انکولی اسکیلپنگ حکمت عملی کے مطابق تجزیہ کریں
        personalities = load_asset_personalities()
        
        tasks = [
            analyze_single_pair(pair, market_regime_data, personalities) 
            for pair in pairs_to_analyze
        ]
        await asyncio.gather(*tasks)

    except Exception as e:
        logger.error(f"شکاری انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info("🏹 شکاری انجن: تلاش کا دور مکمل ہوا۔")

async def analyze_single_pair(pair: str, market_regime: Dict, personalities: Dict):
    """
    ایک انفرادی جوڑے کا گہرا تجزیہ کرتا ہے اور اگر معیار پر پورا اترے تو سگنل بناتا ہے۔
    """
    logger.info(f"🔬 [{pair}] کا انکولی اسکیلپنگ تجزیہ شروع کیا جا رہا ہے...")
    
    try:
        symbol_personality = personalities.get(pair, personalities.get("DEFAULT", {}))

        with get_db_session() as db:
            if crud.get_active_signal_by_symbol(db, pair):
                logger.info(f"🔬 [{pair}] تجزیہ روکا گیا: اس جوڑے کا سگنل پہلے سے فعال ہے۔")
                return

            timeframe = "15min"
            candles = await fetch_twelve_data_ohlc(pair, timeframe, api_settings.CANDLE_COUNT)
            
            if not candles or len(candles) < 34:
                logger.warning(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
                return

            # فیوژن انجن سے حتمی تجزیہ حاصل کریں
            analysis_result = await generate_final_signal(db, pair, candles, market_regime, symbol_personality)
        
        if not analysis_result:
            logger.error(f"🔬 [{pair}] تجزیہ ناکام: فیوژن انجن نے کوئی نتیجہ واپس نہیں کیا۔")
            return

        if analysis_result.get("status") == "ok":
            confidence = analysis_result.get('confidence', 0)
            log_message = (f"📊 [{pair}] تجزیہ مکمل: سگنل = {analysis_result.get('signal', 'N/A').upper()}, "
                           f"اعتماد = {confidence:.2f}%")
            logger.info(log_message)
            
            # غیر مستحکم مارکیٹ میں زیادہ اعتماد کی ضرورت ہوگی
            required_confidence = FINAL_CONFIDENCE_THRESHOLD + 10 if market_regime['regime'] == 'Volatile' else FINAL_CONFIDENCE_THRESHOLD

            if confidence >= required_confidence:
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
                logger.info(f"📉 [{pair}] سگنل مسترد: اعتماد ({confidence:.2f}%) مطلوبہ حد ({required_confidence}%) سے کم ہے۔")
                
        elif analysis_result.get("status") != "no-signal":
            logger.warning(f"ℹ️ [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {analysis_result.get('reason', 'نامعلوم')}")

    except Exception as e:
        logger.error(f"🔬 [{pair}] کے تجزیے کے دوران ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
            
