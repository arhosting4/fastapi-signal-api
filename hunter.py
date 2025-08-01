# filename: hunter.py

import asyncio
import logging
from typing import List
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from utils import fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager
from config import STRATEGY, TRADING_PAIRS  # ★★★ TRADING_PAIRS کو یہاں امپورٹ کریں ★★★
from datetime import datetime # ★★★ datetime کو امپورٹ کریں ★★★

logger = logging.getLogger(__name__)

FINAL_CONFIDENCE_THRESHOLD = STRATEGY["FINAL_CONFIDENCE_THRESHOLD"]

def get_current_hunting_pairs(db: Session) -> List[str]:
    """
    شکاری انجن کے لیے جوڑوں کی متحرک فہرست تیار کرتا ہے۔
    یہ منطق اب براہ راست شکاری انجن کے اندر موجود ہے۔
    """
    today = datetime.utcnow().weekday()
    
    if today >= 5: # ہفتہ یا اتوار
        primary_pairs = TRADING_PAIRS.get("WEEKEND_PRIMARY", [])
        backup_pairs = TRADING_PAIRS.get("WEEKEND_BACKUP", [])
    else: # ہفتے کا دن
        primary_pairs = TRADING_PAIRS.get("WEEKDAY_PRIMARY", [])
        backup_pairs = TRADING_PAIRS.get("WEEKDAY_BACKUP", [])

    roster_size = len(primary_pairs)
    
    active_symbols = {s.symbol for s in crud.get_all_active_signals_from_db(db)}
    
    available_primary = [p for p in primary_pairs if p not in active_symbols]
    available_backup = [p for p in backup_pairs if p not in active_symbols]
    
    hunting_roster = available_primary
    
    needed = roster_size - len(hunting_roster)
    if needed > 0:
        hunting_roster.extend(available_backup[:needed])
        
    logger.info(f"🏹 شکاری روسٹر تیار: {hunting_roster}")
    return hunting_roster


async def hunt_for_signals_job():
    """
    یہ جاب ہر 3 منٹ چلتی ہے اور نئے سگنل تلاش کرتی ہے۔
    اب یہ روسٹر مینیجر پر انحصار نہیں کرتی۔
    """
    logger.info("🏹 شکاری انجن: نئے مواقع کی تلاش کا نیا دور شروع...")
    
    db = SessionLocal()
    try:
        # ★★★ یہاں تبدیلی کی گئی ہے ★★★
        pairs_to_analyze = get_current_hunting_pairs(db)
        
        if not pairs_to_analyze:
            logger.info("🏹 شکاری انجن: تجزیے کے لیے کوئی اہل جوڑا نہیں (شاید سب کے سگنل فعال ہیں)۔")
            return

        logger.info(f"🏹 شکاری انجن: {len(pairs_to_analyze)} جوڑوں کا متوازی تجزیہ شروع کیا جا رہا ہے: {pairs_to_analyze}")

        tasks = [analyze_single_pair(db, pair) for pair in pairs_to_analyze]
        await asyncio.gather(*tasks)

    except Exception as e:
        logger.error(f"شکاری انجن کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🏹 شکاری انجن: تلاش کا دور مکمل ہوا۔")


async def analyze_single_pair(db: Session, pair: str):
    """ایک جوڑے کا گہرا تجزیہ کرتا ہے اور سگنل بناتا ہے۔"""
    logger.info(f"🔬 [{pair}] کا گہرا تجزیہ کیا جا رہا ہے...")
    
    if crud.get_active_signal_by_symbol(db, pair):
        logger.info(f"🔬 [{pair}] تجزیہ روکا گیا: سگنل حال ہی میں فعال ہوا ہے۔")
        return

    candles = await fetch_twelve_data_ohlc(pair)
    if not candles:
        logger.warning(f"📊 [{pair}] تجزیہ روکا گیا: کینڈل ڈیٹا حاصل نہیں ہو سکا۔")
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
    
