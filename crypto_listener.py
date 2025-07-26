# filename: crypto_listener.py

import asyncio
import json
import logging
import websockets
from typing import List, Dict, Callable, Awaitable

# مقامی امپورٹس
from ai_engine_wrapper import process_data_for_ai

# لاگنگ سیٹ اپ
logger = logging.getLogger(__name__)

# --- کنفیگریشن ---
CRYPTO_PAIRS = ["btc", "eth", "ltc", "xrp", "bch"]
TIMEFRAMES = ["1m", "3m", "5m", "15m"]
BINANCE_WS_URL = "wss://stream.binance.com:9443/stream"

# --- خودکار اصلاح: مضبوط ری-کنکشن منطق ---
RECONNECT_DELAY_SECONDS = 5

def create_subscription_payload() -> Dict:
    """Binance WebSocket کے لیے سبسکرپشن پے لوڈ بناتا ہے۔"""
    streams = [f"{pair}usdt@kline_{tf}" for pair in CRYPTO_PAIRS for tf in TIMEFRAMES]
    logger.info(f"کل {len(streams)} WebSocket اسٹریمز کو سبسکرائب کیا جا رہا ہے۔")
    return {
        "method": "SUBSCRIBE",
        "params": streams,
        "id": 1
    }

async def binance_websocket_listener():
    """
    Binance WebSocket سے جڑتا ہے، کینڈل ڈیٹا سنتا ہے، اور اسے تجزیے کے لیے بھیجتا ہے۔
    کنکشن ٹوٹنے پر خود بخود دوبارہ جڑنے کی کوشش کرتا ہے۔
    """
    subscription_payload = create_subscription_payload()
    
    while True: # بیرونی لوپ ہمیشہ دوبارہ جڑنے کی کوشش کرتا رہے گا
        try:
            async with websockets.connect(BINANCE_WS_URL) as websocket:
                logger.info("Binance WebSocket سے کامیابی سے جڑ گیا۔")
                
                # اسٹریمز کو سبسکرائب کریں
                await websocket.send(json.dumps(subscription_payload))
                logger.info("سبسکرپشن کی درخواست بھیجی گئی۔")

                # آنے والے پیغامات کو سنیں
                while True:
                    message_str = await websocket.recv()
                    message = json.loads(message_str)

                    # صرف کینڈل ڈیٹا پر کارروائی کریں
                    if "stream" in message and "@kline_" in message["stream"]:
                        kline_data = message['data']['k']
                        
                        # صرف بند ہونے والی کینڈلز پر کارروائی کریں
                        if kline_data['x']:
                            symbol = kline_data['s']
                            timeframe = kline_data['i']
                            
                            logger.info(f"بند کینڈل موصول ہوئی: {symbol} ({timeframe})")
                            
                            # ڈیٹا کو AI انجن ریپر کو بھیجیں
                            # نوٹ: ہمیں AI انجن کے لیے کینڈلز کی تاریخ بھی درکار ہوگی۔
                            # ابھی کے لیے، ہم صرف علامت اور ٹائم فریم بھیج رہے ہیں۔
                            # بعد میں ہم یہاں سے ڈیٹا حاصل کرنے کی منطق شامل کریں گے۔
                            await process_data_for_ai(symbol=symbol, timeframe=timeframe, source="Binance")

        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"WebSocket کنکشن بند ہو گیا: {e}. {RECONNECT_DELAY_SECONDS} سیکنڈ میں دوبارہ جڑنے کی کوشش کی جائے گی۔")
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
        except Exception as e:
            logger.error(f"ایک غیر متوقع خرابی واقع ہوئی: {e}. {RECONNECT_DELAY_SECONDS} سیکنڈ میں دوبارہ جڑنے کی کوشش کی جائے گی۔")
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

if __name__ == '__main__':
    # اس فائل کو براہ راست چلانے پر ٹیسٹنگ کے لیے
    logging.basicConfig(level=logging.INFO)
    asyncio.run(binance_websocket_listener())
                          
