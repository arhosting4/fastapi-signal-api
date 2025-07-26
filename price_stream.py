# filename: price_stream.py

import asyncio
import json
import logging
import websockets
import os
from typing import Dict, Optional, List

from utils import get_available_pairs

logger = logging.getLogger(__name__)

# Twelve Data API کی کلید
API_KEY = os.getenv("TWELVE_DATA_API_KEY_1") # ہم صرف ایک کلید استعمال کریں گے

# قیمتوں کو ذخیرہ کرنے کے لیے ایک عالمی کیش
PRICE_CACHE: Dict[str, float] = {}

def get_price_from_cache(symbol: str) -> Optional[float]:
    """مقامی کیش سے کسی علامت کی قیمت حاصل کرتا ہے۔"""
    return PRICE_CACHE.get(symbol)

async def start_price_websocket():
    """Twelve Data کے ساتھ WebSocket کنکشن شروع کرتا ہے اور قیمتوں کو سنتا ہے۔"""
    if not API_KEY:
        logger.error("WebSocket کے لیے Twelve Data API کلید (TWELVE_DATA_API_KEY_1) سیٹ نہیں ہے۔")
        return

    # ہمیں صرف ان جوڑوں کی قیمتیں چاہئیں جن پر ہم ٹریڈ کرتے ہیں
    symbols = ",".join(get_available_pairs())
    uri = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={API_KEY}"
    
    while True: # کنکشن ٹوٹنے پر دوبارہ کوشش کرنے کے لیے لوپ
        try:
            async with websockets.connect(uri) as websocket:
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
                                # قیمت کو مقامی کیش میں اپ ڈیٹ کریں
                                PRICE_CACHE[symbol] = float(price)
                                logger.debug(f"قیمت اپ ڈیٹ: {symbol} = {price}")
                    except json.JSONDecodeError:
                        logger.warning(f"ایک نامعلوم WebSocket پیغام موصول ہوا: {message}")
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            logger.error(f"WebSocket کنکشن بند ہو گیا: {e}۔ 5 سیکنڈ میں دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"WebSocket میں ایک غیر متوقع خرابی واقع ہوئی: {e}۔ 10 سیکنڈ میں دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(10)

