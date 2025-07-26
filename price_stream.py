# filename: price_stream.py

import asyncio
import json
import logging
import websockets
import os
from typing import Dict, Optional

from utils import get_available_pairs

logger = logging.getLogger(__name__)

API_KEY = os.getenv("TWELVE_DATA_API_KEY_1")
PRICE_CACHE: Dict[str, float] = {}

def get_price_from_cache(symbol: str) -> Optional[float]:
    """مقامی کیش سے کسی علامت کی قیمت حاصل کرتا ہے۔"""
    return PRICE_CACHE.get(symbol)

async def start_price_websocket():
    """
    Twelve Data کے ساتھ WebSocket کنکشن شروع کرتا ہے اور اسے زندہ رکھنے کے لیے پنگ بھیجتا ہے۔
    """
    if not API_KEY:
        logger.error("WebSocket کے لیے Twelve Data API کلید (TWELVE_DATA_API_KEY_1) سیٹ نہیں ہے۔")
        return

    symbols = ",".join(get_available_pairs())
    uri = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={API_KEY}"
    
    while True:
        try:
            async with websockets.connect(
                uri, 
                ping_interval=30, # ★★★ اہم تبدیلی: ہر 30 سیکنڈ میں خودکار پنگ بھیجیں ★★★
                ping_timeout=20
            ) as websocket:
                logger.info(f"Twelve Data WebSocket سے کامیابی سے منسلک ہو گئے۔ {symbols} کو سبسکرائب کیا جا رہا ہے۔")
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "params": {"symbols": symbols}
                }))

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("event") == "price":
                            symbol = data.get("symbol")
                            price = data.get("price")
                            if symbol and price:
                                PRICE_CACHE[symbol] = float(price)
                                logger.debug(f"قیمت اپ ڈیٹ: {symbol} = {price}")
                        # Twelve Data کی طرف سے آنے والے heartbeat/pong پیغامات کو نظر انداز کریں
                        elif data.get("event") == "heartbeat":
                            logger.debug("WebSocket Heartbeat موصول ہوا۔ کنکشن زندہ ہے۔")
                    except json.JSONDecodeError:
                        logger.warning(f"ایک نامعلوم WebSocket پیغام موصول ہوا: {message}")
        
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            logger.error(f"WebSocket کنکشن بند ہو گیا: {e}۔ 5 سیکنڈ میں دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"WebSocket میں ایک غیر متوقع خرابی واقع ہوئی: {e}۔ 10 سیکنڈ میں دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(10)
            
