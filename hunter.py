# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

# مقامی امپورٹس
import database_crud as crud
from utils import get_pairs_to_hunt, fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from messenger import send_telegram_alert, send_signal_update_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

# ★★★ نئی ذہین حد بندی کی کنفیگریشن ★★★
MAX_FOREX_SIGNALS = 4
MAX_CRYPTO_SIGNALS = 2
FINAL_CONFIDENCE_THRESHOLD = 70.0

async def analyze_pair(db: Session, pair: str) -> Optional[Dict[str, Any]]:
    """ایک تجارتی جوڑے کا تجزیہ کرتا ہے اور اگر کوئی سگنل ملے تو اسے واپس کرتا ہے۔"""
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34:
        logger.info(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا۔")
        return None

    analysis_result = await generate_final_signal(db, pair, candles)
    
    if analysis_result and analysis_result.get("status") == "ok":
        confidence = analysis_result.get('confidence', 0)
        log_message = (
            f"📊 [{pair}] تجزیہ مکمل: سگنل = {analysis_result.get('signal', 'N/A').upper()}, "
            f"اعتماد = {confidence:.2f}%, پیٹرن = {analysis_result.get('pattern', 'N/A')}, "
            f"رسک = {analysis_result.get('risk', 'N/A')}"
        )
        logger.info(log_message)
        
        if confidence >= FINAL_CONFIDENCE_THRESHOLD:
            return analysis_result
        else:
            logger.info(f"📊 [{pair}] سگنل مسترد: اعتماد ({confidence:.2f}%) تھریشولڈ ({FINAL_CONFIDENCE_THRESHOLD}%) سے کم ہے۔")
            
    elif analysis_result:
        logger.info(f"📊 [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {analysis_result.get('reason', 'نامعلوم')}")
    
    return None

async def hunt_for_signals_job():
    """
    سگنل کی تلاش کا مرکزی کام جو اب فاریکس اور کرپٹو کے لیے الگ الگ حدیں استعمال کرتا ہے۔
    """
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        
        # ★★★ ذہین حد بندی کا نفاذ ★★★
        active_forex_count = sum(1 for s in active_signals if "USD" in s.symbol and "BTC" not in s.symbol and "ETH" not in s.symbol)
        active_crypto_count = sum(1 for s in active_signals if "BTC" in s.symbol or "ETH" in s.symbol)

        if active_forex_count >= MAX_FOREX_SIGNALS and active_crypto_count >= MAX_CRYPTO_SIGNALS:
            logger.info(f"تمام سگنلز کی حد پوری ہو گئی (فاریکس: {active_forex_count}/{MAX_FOREX_SIGNALS}, کرپٹو: {active_crypto_count}/{MAX_CRYPTO_SIGNALS})۔ شکار روکا جا رہا ہے۔")
            return

        pairs_to_hunt = get_pairs_to_hunt([s.symbol for s in active_signals])
        logger.info(f"🏹 ذہین سگنل کی تلاش شروع: ان جوڑوں کا تجزیہ کیا جائے گا: {pairs_to_hunt}")
        
        for pair in pairs_to_hunt:
            is_crypto = "BTC" in pair or "ETH" in pair or "SOL" in pair
            
            # ہر قسم کی حد کو انفرادی طور پر چیک کریں
            if is_crypto and active_crypto_count >= MAX_CRYPTO_SIGNALS:
                logger.info(f"کرپٹو سگنلز کی حد ({active_crypto_count}/{MAX_CRYPTO_SIGNALS}) پوری ہو گئی۔ {pair} کو چھوڑا جا رہا ہے۔")
                continue
            if not is_crypto and active_forex_count >= MAX_FOREX_SIGNALS:
                logger.info(f"فاریکس سگنلز کی حد ({active_forex_count}/{MAX_FOREX_SIGNALS}) پوری ہو گئی۔ {pair} کو چھوڑا جا رہا ہے۔")
                continue

            analysis_result = await analyze_pair(db, pair)
            
            if analysis_result:
                update_result = crud.add_or_update_active_signal(db, analysis_result)
                
                if update_result:
                    signal_obj = update_result.signal.as_dict()
                    
                    if update_result.is_new:
                        logger.info(f"🎯 ★★★ نیا سگنل ملا اور ڈیٹا بیس میں محفوظ کیا گیا: {signal_obj['symbol']} ★★★")
                        # نئے سگنل ملنے پر کاؤنٹ کو اپ ڈیٹ کریں
                        if is_crypto: active_crypto_count += 1
                        else: active_forex_count += 1
                        
                        await send_telegram_alert(signal_obj)
                        await manager.broadcast({"type": "new_signal", "data": signal_obj})
                    else:
                        logger.info(f"🔄 ★★★ موجودہ سگنل اپ ڈیٹ ہوا: {signal_obj['symbol']}, نیا اعتماد: {signal_obj['confidence']:.2f}% ★★★")
                        await send_signal_update_alert(signal_obj)
                        await manager.broadcast({"type": "signal_updated", "data": signal_obj})

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🏹 ذہین سگنل کی تلاش مکمل ہوئی۔")
        
