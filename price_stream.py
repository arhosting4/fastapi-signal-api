# filename: price_stream.py

import asyncio
import json
import logging
import time
import websockets
import os
from typing import Dict, Optional

from utils import get_available_pairs

logger = logging.getLogger(__name__)

API_KEY = os.getenv("TWELVE_DATA_API_KEY_1")
PRICE_CACHE: Dict[str, float] = {}
# ★★★ نیا: آخری دل کی دھڑکن کا وقت ذخیرہ کرنے کے لیے ★★★
LAST_HEARTBEAT: float = time.time()

def get_price_from_cache(symbol: str) -> Optional[float]:
    """مقامی کیش سے کسی علامت کی قیمت حاصل کرتا ہے۔"""
    return PRICE_CACHE.get(symbol)

def get_last_heartbeat() -> float:
    """آخری دل کی دھڑکن کا وقت واپس کرتا ہے۔"""
    global LAST_HEARTBEAT
    return LAST_HEARTBEAT

async def start_price_websocket():
    """
    Twelve Data کے ساتھ WebSocket کنکشن شروع کرتا ہے اور دل کی دھڑکن کو اپ ڈیٹ کرتا ہے۔
    """
    global LAST_HEARTBEAT
    if not API_KEY:
        logger.error("WebSocket کے لیے Twelve Data API کلید (TWELVE_DATA_API_KEY_1) سیٹ نہیں ہے۔")
        return

    symbols = ",".join(get_available_pairs())
    uri = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={API_KEY}"
    
    while True:
        try:
            async with websockets.connect(uri, ping_interval=30, ping_timeout=20) as websocket:
                logger.info(f"Twelve Data WebSocket سے کامیابی سے منسلک ہو گئے۔")
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "params": {"symbols": symbols}
                }))

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        # ★★★ اہم: جب بھی کوئی پیغام آئے، دل کی دھڑکن اپ ڈیٹ کریں ★★★
                        LAST_HEARTBEAT = time.time()

                        if data.get("event") == "price":
                            symbol = data.get("symbol")
                            price = data.get("price")
                            if symbol and price:
                                PRICE_CACHE[symbol] = float(price)
                        elif data.get("event") == "heartbeat":
                            logger.debug("WebSocket Heartbeat موصول ہوا۔")
                    except json.JSONDecodeError:
                        pass # نامعلوم پیغامات کو خاموشی سے نظر انداز کریں
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket کنکشن معمول کے مطابق بند ہوا۔ 10 سیکنڈ میں دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"WebSocket میں ایک غیر متوقع خرابی واقع ہوئی: {e}۔ 15 سیکنڈ میں دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(15)
            
