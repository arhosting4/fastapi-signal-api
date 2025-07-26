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
LAST_HEARTBEAT: float = time.time()

def get_price_from_cache(symbol: str) -> Optional[float]:
    return PRICE_CACHE.get(symbol)

def get_last_heartbeat() -> float:
    global LAST_HEARTBEAT
    return LAST_HEARTBEAT

async def start_price_websocket():
    global LAST_HEARTBEAT
    if not API_KEY:
        logger.error("WebSocket کے لیے Twelve Data API کلید (TWELVE_DATA_API_KEY_1) سیٹ نہیں ہے۔")
        return

    symbols = ",".join(get_available_pairs())
    uri = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={API_KEY}"
    
    # ★★★ سب سے اہم تبدیلی: متغیرات کو لوپ سے باہر منتقل کر دیا گیا ہے ★★★
    last_summary_time = time.time()
    reconnect_count = 0
    
    while True:
        try:
            async with websockets.connect(uri, ping_interval=30, ping_timeout=20) as websocket:
                # کنکشن کامیاب ہونے پر لاگ کریں
                if reconnect_count > 0:
                    logger.info(f"WebSocket کنکشن کامیابی سے بحال ہو گیا۔")
                else:
                    logger.info(f"Twelve Data WebSocket سے کامیابی سے منسلک ہو گئے۔")
                
                # کاؤنٹر کو دوبارہ صفر کر دیں
                reconnect_count = 0
                
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "params": {"symbols": symbols}
                }))

                async for message in websocket:
                    LAST_HEARTBEAT = time.time()
                    try:
                        data = json.loads(message)
                        if data.get("event") == "price":
                            symbol, price = data.get("symbol"), data.get("price")
                            if symbol and price:
                                PRICE_CACHE[symbol] = float(price)
                        elif data.get("event") == "heartbeat":
                            logger.debug("WebSocket Heartbeat موصول ہوا۔")
                    except json.JSONDecodeError:
                        pass
        
        except websockets.exceptions.ConnectionClosed as e:
            reconnect_count += 1
            current_time = time.time()
            
            # ہر 5 منٹ (300 سیکنڈ) بعد خلاصہ لاگ کریں
            if current_time - last_summary_time > 300:
                logger.warning(f"WebSocket پچھلے 5 منٹ میں {reconnect_count} بار دوبارہ منسلک ہوا۔ یہ ایک متوقع عمل ہے۔")
                last_summary_time = current_time
                reconnect_count = 0
            else:
                logger.debug(f"WebSocket کنکشن بند ہوا۔ دوبارہ کوشش کی جا رہی ہے۔ وجہ: {e}")

            await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"WebSocket میں ایک غیر متوقع خرابی واقع ہوئی: {e}۔ 15 سیکنڈ میں دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(15)
                    
