# filename: ai_engine_wrapper.py

import logging
from typing import Optional
from sqlalchemy.orm import Session

# مقامی امپورٹس
from fusion_engine import generate_final_signal
from utils import fetch_twelve_data_ohlc, fetch_binance_ohlc
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from websocket_manager import manager
from models import SessionLocal

logger = logging.getLogger(__name__)

# کنفیگریشن
MAX_ACTIVE_SIGNALS = 10 # ہم اب زیادہ سگنلز کو سنبھال سکتے ہیں
FINAL_CONFIDENCE_THRESHOLD = 65.0 # معیار کو تھوڑا سخت کیا گیا

async def process_data_for_ai(symbol: str, timeframe: str, source: str):
    """
    مختلف ذرائع سے آنے والے ڈیٹا کو وصول کرتا ہے، AI تجزیہ چلاتا ہے، اور سگنل بھیجتا ہے۔
    """
    logger.info(f"AI ریپر کو ڈیٹا موصول ہوا: علامت={symbol}, ٹائم فریم={timeframe}, ذریعہ={source}")
    
    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔ تجزیہ روکا جا رہا ہے۔")
        return

    candles = None
    db = SessionLocal()
    
    try:
        # مرحلہ 1: ذریعہ کی بنیاد پر کینڈل ڈیٹا حاصل کریں
        if source == "Binance":
            # Binance کے لیے علامت کو فارمیٹ کریں (مثلاً BTCUSDT سے BTC/USDT)
            formatted_symbol = f"{symbol[:-4]}/{symbol[-4:]}"
            candles = await fetch_binance_ohlc(formatted_symbol, timeframe, limit=100)
            
        elif source == "TwelveData":
            candles = await fetch_twelve_data_ohlc(symbol, timeframe)

        # مرحلہ 2: اگر کینڈلز ملیں تو AI انجن کو بھیجیں
        if candles and len(candles) >= 34: # یقینی بنائیں کہ تجزیے کے لیے کافی ڈیٹا ہے
            logger.info(f"AI فیوژن انجن کو {len(candles)} کینڈلز بھیجی جا رہی ہیں...")
            signal_result = await generate_final_signal(db, candles[0].symbol, candles, timeframe)
            
            if signal_result and signal_result.get("status") == "ok" and signal_result.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                add_active_signal(signal_result)
                logger.info(f"★★★ نیا سگنل ملا: {signal_result['symbol']} ({signal_result['timeframe']}) - {signal_result['signal']} @ {signal_result['price']} ★★★")
                
                # ٹیلیگرام اور WebSocket پر اطلاع بھیجیں
                await send_telegram_alert(signal_result)
                await manager.broadcast({
                    "type": "new_signal",
                    "data": signal_result
                })
        else:
            logger.warning(f"{symbol} ({timeframe}) کے لیے ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔ AI تجزیہ روکا جا رہا ہے۔")
    
    except Exception as e:
        logger.error(f"AI انجن ریپر میں خرابی: {e}", exc_info=True)
    finally:
        db.close()
        
