# filename: crypto_listener.py

import asyncio
import json
import logging
import websockets
import httpx  # <-- ★★★ نیا امپورٹ: ٹوکن حاصل کرنے کے لیے
import time

# مقامی امپورٹس
from ai_engine_wrapper import process_data_for_ai

# لاگنگ سیٹ اپ
logger = logging.getLogger(__name__)

# --- کنفیگریشن ---
# KuCoin کے لیے علامتوں کو '-' کے ساتھ فارمیٹ کیا جاتا ہے
CRYPTO_PAIRS = ["BTC-USDT", "ETH-USDT", "LTC-USDT", "XRP-USDT", "BCH-USDT"]
TIMEFRAMES = ["1m", "3m", "5m", "15m"]
RECONNECT_DELAY_SECONDS = 10

# --- ★★★ خودکار اصلاح: KuCoin API کا استعمال ★★★ ---
KUCOIN_API_ENDPOINT = "https://api.kucoin.com/api/v1/bullet-public"

async def get_kucoin_ws_connection_details():
    """
    KuCoin سے ایک عارضی WebSocket کنکشن ٹوکن اور سرور کا پتہ حاصل کرتا ہے۔
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(KUCOIN_API_ENDPOINT, timeout=10)
            response.raise_for_status()
            data = response.json()['data']
            
            token = data['token']
            ws_server = data['instanceServers'][0]['endpoint']
            ping_interval = int(data['instanceServers'][0]['pingInterval']) / 1000
            
            # مکمل WebSocket URI بنائیں
            ws_uri = f"{ws_server}?token={token}"
            logger.info("KuCoin سے WebSocket کنکشن کی تفصیلات کامیابی سے حاصل کی گئیں۔")
            return ws_uri, ping_interval
            
    except Exception as e:
        logger.error(f"KuCoin سے کنکشن ٹوکن حاصل کرنے میں ناکامی: {e}")
        return None, None

async def binance_websocket_listener(): # فنکشن کا نام وہی رکھا تاکہ app.py میں تبدیلی نہ کرنی پڑے
    """
    اب یہ KuCoin WebSocket سے جڑتا ہے، کینڈل ڈیٹا سنتا ہے، اور اسے تجزیے کے لیے بھیجتا ہے۔
    """
    while True:
        ws_uri, ping_interval = await get_kucoin_ws_connection_details()
        
        if not ws_uri:
            logger.info(f"{RECONNECT_DELAY_SECONDS} سیکنڈ بعد دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
            continue

        try:
            async with websockets.connect(ws_uri, ping_interval=ping_interval) as websocket:
                logger.info(f"KuCoin WebSocket ({websocket.remote_address}) سے کامیابی سے جڑ گیا۔")
                
                # تمام جوڑوں اور ٹائم فریمز کے لیے سبسکرائب کریں
                topics = [f"/market/candles:{pair}_{tf}" for pair in CRYPTO_PAIRS for tf in TIMEFRAMES]
                sub_message = {
                    "id": int(time.time()),
                    "type": "subscribe",
                    "topic": ",".join(topics),
                    "privateChannel": False,
                    "response": True
                }
                await websocket.send(json.dumps(sub_message))
                logger.info(f"KuCoin پر {len(topics)} اسٹریمز کے لیے سبسکرپشن کی درخواست بھیجی گئی۔")

                while True:
                    message_str = await websocket.recv()
                    message = json.loads(message_str)

                    if message.get('type') == 'message' and 'candles' in message.get('topic', ''):
                        # KuCoin ہر کینڈل کے بند ہونے پر نہیں، بلکہ ہر ٹِک پر ڈیٹا بھیجتا ہے۔
                        # ہمیں صرف بند کینڈل پر کارروائی کرنی ہے۔
                        # KuCoin کا ڈیٹا فارمیٹ: [time, open, close, high, low, volume, turnover]
                        candle_data = message['data']['candles']
                        symbol_full, timeframe = message['topic'].split(':')[-1].split('_')
                        
                        # KuCoin ہر سیکنڈ ڈیٹا بھیجتا ہے، ہمیں صرف ہر منٹ کے آخر میں کارروائی کرنی ہے
                        # یہ ایک سادہ چیک ہے کہ کیا کینڈل کا وقت ایک منٹ کا ملٹیپل ہے
                        candle_timestamp = int(candle_data[0])
                        if candle_timestamp % 60 == 0:
                            logger.info(f"KuCoin سے بند کینڈل کا ڈیٹا موصول ہوا: {symbol_full} ({timeframe})")
                            # علامت کو ہمارے معیاری فارمیٹ میں تبدیل کریں (مثلاً BTC-USDT سے BTCUSDT)
                            formatted_symbol = symbol_full.replace('-', '')
                            await process_data_for_ai(symbol=formatted_symbol, timeframe=timeframe, source="Binance") # ذریعہ Binance ہی رکھیں تاکہ utils.py کام کرے

        except Exception as e:
            logger.error(f"KuCoin WebSocket کنکشن میں خرابی: {e}. {RECONNECT_DELAY_SECONDS} سیکنڈ میں دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                    
