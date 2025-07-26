# filename: ai_engine_wrapper.py

import logging
from typing import List, Dict, Any

# مقامی امپورٹس
from utils import fetch_binance_ohlc, fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager

logger = logging.getLogger(__name__)

# کنفیگریشن
MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 60.0

async def process_data_for_ai(symbol: str, timeframe: str, source: str):
    """
    یہ مرکزی گیٹ وے فنکشن ہے جو ڈیٹا حاصل کرتا ہے اور AI انجن کو بھیجتا ہے۔
    """
    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        logger.info(f"فعال سگنلز کی حد ({MAX_ACTIVE_SIGNALS}) تک پہنچ گئے ہیں۔ [{symbol}] کا تجزیہ روکا جا رہا ہے۔")
        return

    logger.info(f"[{symbol}] ({timeframe}) کے لیے تاریخی کینڈلز حاصل کی جا رہی ہیں، ذریعہ: {source}...")
    
    candles: List[Dict[str, Any]] = []
    if source == "TwelveData":
        candles = await fetch_twelve_data_ohlc(symbol, timeframe)
    elif source == "Binance": # KuCoin کے لیے بھی یہی استعمال ہوگا
        candles = await fetch_binance_ohlc(symbol, timeframe)

    if not candles or len(candles) < 34:
        logger.warning(f"[{symbol}] ({timeframe}) کے لیے تجزیہ روکا جا رہا ہے۔ AI کے لیے ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
        return

    logger.info(f"[{symbol}] ({timeframe}) کے لیے AI فیوژن انجن کو {len(candles)} کینڈلز بھیجی جا رہی ہیں...")
    
    db = SessionLocal()
    try:
        # ★★★ خودکار اصلاح: اب fusion_engine کو ہمیشہ معیاری ڈکشنری کی فہرست ہی ملے گی ★★★
        signal_result = await generate_final_signal(db, symbol, timeframe, candles)
        
        if signal_result and signal_result.get("status") == "ok":
            if signal_result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                add_active_signal(signal_result)
                logger.info(f"★★★ نیا سگنل ملا: {signal_result['symbol']} ({signal_result['timeframe']}) - {signal_result['signal']} @ {signal_result['price']} ★★★")
                
                await send_telegram_alert(signal_result)
                await manager.broadcast({"type": "new_signal", "data": signal_result})
            else:
                logger.info(f"[{symbol}] سگنل کا اعتماد ({signal_result.get('confidence')}) حد سے کم ہے۔")
        elif signal_result:
            logger.info(f"[{symbol}] کے لیے کوئی سگنل نہیں بنا۔ وجہ: {signal_result.get('reason', 'نامعلوم')}")
    
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے AI انجن میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()

