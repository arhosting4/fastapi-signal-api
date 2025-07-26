# filename: crypto_listener.py

import asyncio
import json
import logging
import websockets
import socket # <-- ★★★ نیا امپورٹ: DNS مسائل کو بائی پاس کرنے کے لیے
from typing import List, Dict

# مقامی امپورٹس
from ai_engine_wrapper import process_data_for_ai

# لاگنگ سیٹ اپ
logger = logging.getLogger(__name__)

# --- کنفیگریشن ---
CRYPTO_PAIRS = ["btc", "eth", "ltc", "xrp", "bch"]
TIMEFRAMES = ["1m", "3m", "5m", "15m"]
RECONNECT_DELAY_SECONDS = 10 # دوبارہ کوشش کے لیے تاخیر کو تھوڑا بڑھایا گیا

# --- ★★★ خودکار اصلاح: DNS مسائل کو مکمل طور پر بائی پاس کرنے کی حکمت عملی ★★★ ---
# ہم ڈومین کو پہلے IP ایڈریس میں تبدیل کریں گے
HOSTNAME = "stream.binance.vision"
PORT = 9443

def get_websocket_uri() -> str:
    """
    ڈومین نام کو IP ایڈریس میں تبدیل کرتا ہے تاکہ DNS کی خرابیوں سے بچا جا سکے۔
    """
    try:
        # getaddrinfo ایک قابل اعتماد طریقہ ہے جو IPv4 اور IPv6 دونوں کو سنبھالتا ہے
        addr_info = socket.getaddrinfo(HOSTNAME, PORT, proto=socket.IPPROTO_TCP)
        # ہم ملنے والے پہلے پتے کو استعمال کریں گے
        ip_address = addr_info[0][4][0]
        uri = f"wss://{ip_address}:{PORT}/stream"
        logger.info(f"کامیابی سے '{HOSTNAME}' کو IP ایڈریس '{ip_address}' میں تبدیل کر دیا گیا۔ URI: {uri}")
        return uri
    except socket.gaierror as e:
        logger.error(f"DNS ریزولوشن ناکام: '{HOSTNAME}' کا IP ایڈریس حاصل نہیں کیا جا سکا۔ خرابی: {e}")
        # اگر IP حاصل نہ ہو سکے تو فال بیک کے طور پر پرانا URL استعمال کریں
        return f"wss://{HOSTNAME}:{PORT}/stream"

# ------------------------------------------------------------------------------------

def create_subscription_payload() -> Dict:
    """Binance WebSocket کے لیے سبسکرپشن پے لوڈ بناتا ہے۔"""
    streams = [f"{pair}usdt@kline_{tf}" for pair in CRYPTO_PAIRS for tf in TIMEFRAMES]
    logger.info(f"کل {len(streams)} WebSocket اسٹریمز کو سبسکرائب کیا جا رہا ہے۔")
    return { "method": "SUBSCRIBE", "params": streams, "id": 1 }

async def binance_websocket_listener():
    """
    Binance WebSocket سے جڑتا ہے، کینڈل ڈیٹا سنتا ہے، اور اسے تجزیے کے لیے بھیجتا ہے۔
    """
    subscription_payload = create_subscription_payload()
    
    while True:
        websocket_uri = get_websocket_uri() # ہر کوشش پر تازہ URI حاصل کریں
        try:
            async with websockets.connect(websocket_uri, ping_interval=20, ping_timeout=20) as websocket:
                logger.info(f"Binance WebSocket ({websocket.remote_address}) سے کامیابی سے جڑ گیا۔")
                await websocket.send(json.dumps(subscription_payload))
                logger.info("سبسکرپشن کی درخواست بھیجی گئی۔")

                while True:
                    message_str = await websocket.recv()
                    message = json.loads(message_str)
                    if "stream" in message and "@kline_" in message["stream"]:
                        kline_data = message['data']['k']
                        if kline_data['x']:
                            symbol, timeframe = kline_data['s'], kline_data['i']
                            logger.info(f"بند کینڈل موصول ہوئی: {symbol} ({timeframe})")
                            await process_data_for_ai(symbol=symbol, timeframe=timeframe, source="Binance")

        except Exception as e:
            logger.error(f"WebSocket کنکشن میں خرابی: {e}. {RECONNECT_DELAY_SECONDS} سیکنڈ میں دوبارہ جڑنے کی کوشش کی جائے گی۔")
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

