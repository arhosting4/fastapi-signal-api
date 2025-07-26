# filename: crypto_listener.py

import asyncio
import json
import logging
import websockets
import httpx
import time
from typing import Dict

# مقامی امپورٹس
from ai_engine_wrapper import process_data_for_ai

# لاگنگ سیٹ اپ
logger = logging.getLogger(__name__)

# --- کنفیگریشن ---
CRYPTO_PAIRS = ["BTC-USDT", "ETH-USDT", "LTC-USDT", "XRP-USDT", "BCH-USDT"]
TIMEFRAMES = ["1m", "3m", "5m", "15m"]
RECONNECT_DELAY_SECONDS = 10
KUCOIN_API_ENDPOINT = "https://api.kucoin.com/api/v1/bullet-public"

# --- ★★★ خودکار اصلاح: بند کینڈل کی شناخت کے لیے ذہین منطق ★★★ ---
# ہر اسٹریم (مثلاً 'BTC-USDT_1m') کے لیے آخری کینڈل کا ٹائم اسٹیمپ محفوظ کرنے کے لیے ایک ڈکشنری
last_candle_timestamps: Dict[str, int] = {}
# --------------------------------------------------------------------

async def get_kucoin_ws_connection_details():
    """KuCoin سے ایک عارضی WebSocket کنکشن ٹوکن اور سرور کا پتہ حاصل کرتا ہے۔"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(KUCOIN_API_ENDPOINT, timeout=10)
        response.raise_for_status()
        data = response.json()['data']
        token = data['token']
        ws_server = data['instanceServers'][0]['endpoint']
        ping_interval = int(data['instanceServers'][0]['pingInterval']) / 1000
        ws_uri = f"{ws_server}?token={token}"
        logger.info("KuCoin سے WebSocket کنکشن کی تفصیلات کامیابی سے حاصل کی گئیں۔")
        return ws_uri, ping_interval
    except Exception as e:
        logger.error(f"KuCoin سے کنکشن ٹوکن حاصل کرنے میں ناکامی: {e}")
        return None, None

async def binance_websocket_listener():
    """KuCoin WebSocket سے جڑتا ہے اور بند کینڈلز کی درست شناخت کرتا ہے۔"""
    while True:
        ws_uri, ping_interval = await get_kucoin_ws_connection_details()
        if not ws_uri:
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
            continue

        try:
            async with websockets.connect(ws_uri, ping_interval=ping_interval) as websocket:
                logger.info(f"KuCoin WebSocket ({websocket.remote_address}) سے کامیابی سے جڑ گیا۔")
                
                topics = [f"/market/candles:{pair}_{tf}" for pair in CRYPTO_PAIRS for tf in TIMEFRAMES]
                sub_message = {"id": int(time.time()), "type": "subscribe", "topic": ",".join(topics), "response": True}
                await websocket.send(json.dumps(sub_message))
                logger.info(f"KuCoin پر {len(topics)} اسٹریمز کے لیے سبسکرپشن کی درخواست بھیجی گئی۔")

                while True:
                    message_str = await websocket.recv()
                    message = json.loads(message_str)

                    if message.get('type') == 'message' and 'candles' in message.get('topic', ''):
                        topic = message['topic']
                        candle_data = message['data']['candles']
                        current_candle_timestamp = int(candle_data[0])
                        
                        # --- ★★★ نئی منطق یہاں ہے ★★★ ---
                        # دیکھیں کہ کیا یہ اس اسٹریم کے لیے ایک نئی کینڈل ہے
                        last_known_timestamp = last_candle_timestamps.get(topic)
                        
                        if last_known_timestamp is None:
                            # اگر ہم نے اس اسٹریم کو پہلے نہیں دیکھا، تو اس کا ٹائم اسٹیمپ محفوظ کریں
                            last_candle_timestamps[topic] = current_candle_timestamp
                        elif current_candle_timestamp > last_known_timestamp:
                            # اگر موجودہ کینڈل کا ٹائم اسٹیمپ پچھلے سے زیادہ ہے،
                            # تو اس کا مطلب ہے کہ پچھلی کینڈل بند ہو چکی ہے اور یہ ایک نئی کینڈل ہے۔
                            
                            symbol_full, timeframe = topic.split(':')[-1].split('_')
                            logger.info(f"★★★ بند کینڈل کی شناخت ہوئی: {symbol_full} ({timeframe}) ★★★")
                            
                            # تجزیے کے لیے بھیجیں
                            formatted_symbol = symbol_full.replace('-', '')
                            await process_data_for_ai(symbol=formatted_symbol, timeframe=timeframe, source="Binance")
                            
                            # اس نئی کینڈل کے ٹائم اسٹیمپ کو محفوظ کریں
                            last_candle_timestamps[topic] = current_candle_timestamp

        except Exception as e:
            logger.error(f"KuCoin WebSocket کنکشن میں خرابی: {e}. {RECONNECT_DELAY_SECONDS} سیکنڈ میں دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

