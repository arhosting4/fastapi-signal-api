# filename: ai_engine_wrapper.py

import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

# مقامی امپورٹس
from models import SessionLocal
from fusion_engine import generate_final_signal
from utils import fetch_twelve_data_ohlc, fetch_binance_ohlc # Binance کو فال بیک کے طور پر رکھیں
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from websocket_manager import manager

logger = logging.getLogger(__name__)
MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 60.0

# ★★★ خودکار اصلاح: ہر جوڑے اور ٹائم فریم کے لیے کینڈلز کو محفوظ کرنے کے لیے عالمی کیش ★★★
CANDLE_CACHE = {}
CACHE_SIZE = 100 # ہر فہرست میں 100 کینڈلز محفوظ کریں

async def process_data_for_ai(symbol: str, timeframe: str, source: str, single_candle: Dict = None):
    """
    یہ مرکزی گیٹ وے ہے جو مختلف ذرائع سے ڈیٹا لیتا ہے، کینڈلز کو منظم کرتا ہے،
    اور پھر انہیں تجزیے کے لیے AI انجن کو بھیجتا ہے۔
    """
    global CANDLE_CACHE
    cache_key = f"{symbol}_{timeframe}"

    if source == "Bybit" and single_candle:
        if cache_key not in CANDLE_CACHE:
            CANDLE_CACHE[cache_key] = []
        
        CANDLE_CACHE[cache_key].append(single_candle)
        
        # کیش کو مقررہ سائز پر برقرار رکھیں
        if len(CANDLE_CACHE[cache_key]) > CACHE_SIZE:
            CANDLE_CACHE[cache_key].pop(0)
        
        # اگر ہمارے پاس تجزیے کے لیے کافی کینڈلز ہیں تو ہی آگے بڑھیں
        if len(CANDLE_CACHE[cache_key]) < 35: # کم از کم 35 کینڈلز کی ضرورت ہے
            logger.info(f"[{cache_key}] کے لیے کینڈلز جمع کی جا رہی ہیں۔ کل: {len(CANDLE_CACHE[cache_key])}/{CACHE_SIZE}")
            return
        
        candles = list(CANDLE_CACHE[cache_key]) # تجزیے کے لیے ایک کاپی بنائیں
        logger.info(f"[{cache_key}] کے لیے {len(candles)} کینڈلز AI انجن کو بھیجی جا رہی ہیں...")

    else: # سونے یا فال بیک کے لیے پرانی منطق
        logger.info(f"[{symbol}] کے لیے {source} سے تاریخی کینڈلز حاصل کی جا رہی ہیں...")
        if source == "TwelveData":
            candles = await fetch_twelve_data_ohlc(symbol, timeframe)
        elif source == "Binance":
            candles = await fetch_binance_ohlc(symbol, timeframe)
        else:
            logger.error(f"نامعلوم ڈیٹا کا ذریعہ: {source}")
            return

    if not candles or len(candles) < 35:
        logger.warning(f"[{symbol}] ({timeframe}) کے لیے تجزیہ روکا جا رہا ہے، ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
        return

    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔ تجزیہ روکا جا رہا ہے۔")
        return

    db = SessionLocal()
    try:
        signal_result = await generate_final_signal(db, symbol, timeframe, candles)
        if signal_result and signal_result.get("status") == "ok" and signal_result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
            add_active_signal(signal_result)
            logger.info(f"★★★ نیا سگنل ملا: {signal_result} ★★★")
            await send_telegram_alert(signal_result)
            await manager.broadcast({"type": "new_signal", "data": signal_result})
        elif signal_result:
            logger.info(f"[{symbol}] ({timeframe}) کے لیے کوئی سگنل نہیں بنا۔ وجہ: {signal_result.get('reason', 'نامعلوم')}")
    finally:
        db.close()
        
