# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

import database_crud as crud
from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

# کنفیگریشن
MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 60.0
CONFIDENCE_INCREASE_THRESHOLD = 5.0 # اعتماد میں کم از کم 5 پوائنٹس کا اضافہ ہونا چاہیے

async def analyze_pair(db: Session, pair: str) -> None:
    """
    ایک تجارتی جوڑے کا تجزیہ کرتا ہے اور یا تو نیا سگنل بناتا ہے یا موجودہ کو اپ ڈیٹ کرتا ہے۔
    """
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34:
        logger.info(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
        return

    potential_signal = await generate_final_signal(db, pair, candles)
    if not potential_signal or potential_signal.get("status") != "ok":
        logger.info(f"📊 [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {potential_signal.get('reason', 'نامعلوم')}")
        return

    logger.info(
        f"📊 [{pair}] تجزیہ مکمل: ممکنہ سگنل = {potential_signal.get('signal', 'N/A').upper()}, "
        f"اعتماد = {potential_signal.get('confidence', 0):.2f}%, پیٹرن = {potential_signal.get('pattern', 'N/A')}, "
        f"رسک = {potential_signal.get('risk', 'N/A')}"
    )

    # ★★★ ذہین سگنل مینجمنٹ کی منطق ★★★
    existing_signal = crud.get_active_signal_by_symbol(db, pair)

    if existing_signal:
        # کیس 1: سگنل پہلے سے موجود ہے
        is_same_direction = existing_signal.signal_type == potential_signal.get('signal')
        is_confidence_higher = potential_signal.get('confidence', 0) > (existing_signal.confidence + CONFIDENCE_INCREASE_THRESHOLD)

        if is_same_direction and is_confidence_higher:
            logger.info(f"📈 [{pair}] سگنل کی تصدیق! اعتماد {existing_signal.confidence:.2f}% سے {potential_signal['confidence']:.2f}% تک بڑھ رہا ہے۔")
            updated_signal = crud.update_active_signal_confidence(
                db, existing_signal.signal_id, potential_signal['confidence'], potential_signal['reason']
            )
            if updated_signal:
                updated_signal_dict = updated_signal.as_dict()
                await send_signal_update_alert(updated_signal_dict)
                await manager.broadcast({"type": "signal_updated", "data": updated_signal_dict})
        else:
            logger.info(f"📊 [{pair}] کے لیے ایک فعال سگنل پہلے سے موجود ہے۔ کوئی کارروائی نہیں کی گئی۔")

    else:
        # کیس 2: کوئی فعال سگنل نہیں ہے، نیا بنائیں
        if potential_signal.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
            if crud.get_active_signals_count_from_db(db) >= MAX_ACTIVE_SIGNALS:
                logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔ نیا سگنل نہیں بنایا جا رہا۔")
                return
            
            potential_signal['signal_id'] = f"{pair}_{potential_signal['timeframe']}_{datetime.utcnow().timestamp()}"
            new_signal = crud.add_active_signal_to_db(db, potential_signal)
            
            if new_signal:
                logger.info(f"🎯 ★★★ نیا سگنل ملا اور ڈیٹا بیس میں محفوظ کیا گیا: {new_signal.symbol} - {new_signal.signal_type} @ {new_signal.entry_price} ★★★")
                new_signal_dict = new_signal.as_dict()
                await send_telegram_alert(new_signal_dict)
                await manager.broadcast({"type": "new_signal", "data": new_signal_dict})

async def hunt_for_signals_job():
    """
    سگنل کی تلاش کا مرکزی کام جو شیڈیولر کے ذریعے چلایا جاتا ہے۔
    """
    db = SessionLocal()
    try:
        if crud.get_active_signals_count_from_db(db) >= MAX_ACTIVE_SIGNALS:
            logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔ شکار روکا جا رہا ہے۔")
            return

        pairs = get_available_pairs()
        logger.info(f"🏹 سگنل کی تلاش شروع: ان جوڑوں کا تجزیہ کیا جائے گا: {pairs}")
        
        tasks = [analyze_pair(db, pair) for pair in pairs]
        await asyncio.gather(*tasks)

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("🏹 سگنل کی تلاش مکمل ہوئی۔")
        
