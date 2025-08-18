import asyncio
import logging
from contextlib import contextmanager
from typing import Generator, Dict, Any, List
import json

from sqlalchemy.orm import Session
import pandas as pd

import database_crud as crud
from utils import fetch_polygon_ohlcv
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from roster_manager import get_hunting_roster
from config import strategy_settings, api_settings
from riskguardian import get_market_regime

logger = logging.getLogger(__name__)

# --- کنفیگریشن اور عالمی متغیرات ---
FINAL_CONFIDENCE_THRESHOLD = strategy_settings.FINAL_CONFIDENCE_THRESHOLD
PERSONALITIES_FILE = "asset_personalities.json"
# ★★★ نیا: مسلسل تجزیے کے لیے عالمی قطار ★★★
hunting_queue: List[str] = []

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

# ★★★ نیا، مسلسل تجزیہ والا ہنٹر انجن ★★★
async def hunt_for_signals_job():
    """
    یہ جاب ہر منٹ چلتی ہے، قطار سے چند جوڑوں کو اٹھاتی ہے اور ان کا تجزیہ کرتی ہے۔
    """
    global hunting_queue
    
    # اگر قطار خالی ہے، تو اسے دوبارہ بھریں
    if not hunting_queue:
        logger.info("🏹 شکار کی قطار خالی ہے۔ نئے روسٹر سے بھری جا رہی ہے...")
        with get_db_session() as db:
            hunting_queue = get_hunting_roster(db)
        
        if not hunting_queue:
            logger.info("🏹 تجزیے کے لیے کوئی اہل جوڑا نہیں۔ اگلی بار دوبارہ کوشش کی جائے گی۔")
            return
        logger.info(f"🏹 شکار کی قطار کامیابی سے بھری گئی۔ کل {len(hunting_queue)} جوڑے۔")

    # قطار سے اگلے 4 جوڑے نکالیں
    pairs_to_process = hunting_queue[:4]
    hunting_queue = hunting_queue[4:] # قطار سے ان جوڑوں کو ہٹا دیں

    if not pairs_to_process:
        logger.info("🏹 اس چکر میں تجزیہ کرنے کے لیے کوئی جوڑا نہیں۔")
        return

    logger.info(f"🏹 مسلسل تجزیہ کا چکر: {len(pairs_to_process)} جوڑوں ({', '.join(pairs_to_process)}) کا تجزیہ کیا جا رہا ہے۔")
    
    try:
        # مارکیٹ کے نظام کا تعین (صرف ایک بار، پہلے جوڑے پر)
        df_regime = await fetch_polygon_ohlcv(pairs_to_process[0], "1h", 50)
        market_regime_data = get_market_regime({pairs_to_process[0]: df_regime} if df_regime is not None else {})
        
        if market_regime_data["regime"] == "Stormy":
            logger.warning("🛑 ٹریڈنگ معطل: انتہائی غیر مستحکم مارکیٹ۔ قطار صاف کی جا رہی ہے۔")
            hunting_queue = [] # طوفانی مارکیٹ میں قطار کو صاف کر دیں
            return

        personalities = load_asset_personalities()
        
        tasks = [
            analyze_single_pair(pair, market_regime_data, personalities) 
            for pair in pairs_to_process
        ]
        await asyncio.gather(*tasks)

    except Exception as e:
        logger.error(f"شکاری انجن کے کام میں ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
    
    logger.info(f"🏹 مسلسل تجزیہ کا چکر مکمل۔ قطار میں باقی: {len(hunting_queue)} جوڑے۔")

async def analyze_single_pair(pair: str, market_regime: Dict, personalities: Dict):
    """
    ایک انفرادی جوڑے کا گہرا تجزیہ کرتا ہے۔
    """
    logger.info(f"🔬 [{pair}] کا تجزیہ شروع کیا جا رہا ہے...")
    
    try:
        symbol_personality = personalities.get(pair, personalities.get("DEFAULT", {}))
        timeframe = api_settings.PRIMARY_TIMEFRAME
        
        df_candles = await fetch_polygon_ohlcv(pair, timeframe, api_settings.CANDLE_COUNT)
        
        # ★★★ تبدیلی: اب ہم صرف یہ چیک کرتے ہیں کہ ڈیٹا خالی تو نہیں ★★★
        if df_candles is None or df_candles.empty:
            logger.warning(f"📊 [{pair}] تجزیہ روکا گیا: Polygon سے کوئی ڈیٹا نہیں ملا۔")
            return

        with get_db_session() as db:
            analysis_result = await generate_final_signal(db, pair, df_candles, market_regime, symbol_personality)
        
        if not analysis_result:
            logger.error(f"🔬 [{pair}] تجزیہ ناکام: فیوژن انجن نے کوئی نتیجہ واپس نہیں کیا۔")
            return

        if analysis_result.get("status") == "ok":
            confidence = analysis_result.get('confidence', 0)
            logger.info(f"📊 [{pair}] تجزیہ مکمل: سگنل = {analysis_result.get('signal', 'N/A').upper()}, اعتماد = {confidence:.2f}%")
            
            required_confidence = FINAL_CONFIDENCE_THRESHOLD + 10 if market_regime['regime'] == 'Volatile' else FINAL_CONFIDENCE_THRESHOLD

            if confidence >= required_confidence:
                with get_db_session() as db:
                    update_result = crud.add_or_update_active_signal(db, analysis_result)
                
                if update_result:
                    signal_obj = update_result.signal.as_dict()
                    task_type = "new_signal" if update_result.is_new else "signal_updated"
                    logger.info(f"🎯 ★★★ سگنل پروسیس ہوا: {signal_obj['symbol']} ({task_type}) ★★★")
                    
                    asyncio.create_task(send_telegram_alert(signal_obj))
                    asyncio.create_task(manager.broadcast({"type": task_type, "data": signal_obj}))
            else:
                logger.info(f"📉 [{pair}] سگنل مسترد: اعتماد ({confidence:.2f}%) مطلوبہ حد ({required_confidence}%) سے کم ہے۔")
                
        elif analysis_result.get("status") != "no-signal":
            logger.warning(f"ℹ️ [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {analysis_result.get('reason', 'نامعلوم')}")

    except Exception as e:
        logger.error(f"🔬 [{pair}] کے تجزیے کے دوران ایک غیر متوقع خرابی پیش آئی: {e}", exc_info=True)
