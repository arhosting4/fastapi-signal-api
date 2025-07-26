# filename: bybit_listener.py

import asyncio
import json
import logging
import websockets
from ai_engine_wrapper import process_data_for_ai

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')
logger = logging.getLogger(__name__)

# --- Bybit کنفیگریشن ---
BYBIT_WS_URL = "wss://stream.bybit.com/v5/public/spot"
CRYPTO_PAIRS = ["BTCUSDT", "ETHUSDT", "LTCUSDT", "XRPUSDT", "BCHUSDT"]
TIMEFRAMES = {"1m": "1", "3m": "3", "5m": "5", "15m": "15"} # Bybit کے لیے ٹائم فریم فارمیٹ

async def bybit_listener():
    """
    یہ فنکشن Bybit WebSocket سے مستقل طور پر جڑتا ہے، کینڈل ڈیٹا سنتا ہے،
    اور بند ہونے والی کینڈلز کو تجزیے کے لیے آگے بھیجتا ہے۔
    """
    logger.info(">>> Bybit WebSocket لسنر شروع ہو رہا ہے...")
    
    args = [f"kline.{TIMEFRAMES[tf]}.{pair}" for pair in CRYPTO_PAIRS for tf in TIMEFRAMES]
    
    subscribe_message = {
        "op": "subscribe",
        "args": args
    }

    while True: # خودکار طور پر دوبارہ جڑنے کے لیے لامتناہی لوپ
        try:
            async with websockets.connect(BYBIT_WS_URL, ping_interval=20) as websocket:
                logger.info(f"Bybit WebSocket ({BYBIT_WS_URL}) سے کامیابی سے جڑ گیا۔")
                
                await websocket.send(json.dumps(subscribe_message))
                logger.info(f"Bybit پر {len(args)} کینڈل اسٹریمز کے لیے سبسکرپشن کی درخواست بھیجی گئی۔")
                
                while True:
                    message_str = await websocket.recv()
                    message = json.loads(message_str)

                    if message.get("op") == "subscribe":
                        if message.get("success"):
                            logger.info(f"سبسکرپشن کامیاب: {message.get('ret_msg')}")
                        else:
                            logger.error(f"سبسکرپشن ناکام: {message.get('ret_msg')}")
                        continue

                    if "topic" in message and "kline" in message["topic"]:
                        for candle_data in message["data"]:
                            if candle_data.get("confirm"): # 'confirm: true' کا مطلب ہے کہ کینڈل بند ہو گئی ہے
                                topic_parts = message["topic"].split('.')
                                timeframe = topic_parts[1] + "m" # '1' کو '1m' میں تبدیل کریں
                                symbol = topic_parts[2]
                                
                                logger.info(f"★★★ Bybit پر بند کینڈل موصول ہوئی: {symbol} ({timeframe}) ★★★")
                                
                                # AI انجن کو بھیجنے کے لیے ڈیٹا کی تشکیل
                                candle_dict = {
                                    "open": float(candle_data["open"]),
                                    "high": float(candle_data["high"]),
                                    "low": float(candle_data["low"]),
                                    "close": float(candle_data["close"]),
                                    "volume": float(candle_data["volume"]),
                                    "turnover": float(candle_data["turnover"])
                                }
                                
                                # ایک الگ ٹاسک میں AI انجن کو کال کریں تاکہ WebSocket بلاک نہ ہو
                                asyncio.create_task(
                                    process_data_for_ai(symbol=symbol, timeframe=timeframe, source="Bybit", single_candle=candle_dict)
                                )

        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
            logger.warning(f"Bybit WebSocket کنکشن بند ہو گیا۔ 5 سیکنڈ میں دوبارہ جڑنے کی کوشش کی جائے گی۔ وجہ: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Bybit لسنر میں ایک غیر متوقع خرابی واقع ہوئی: {e}", exc_info=True)
            logger.info("15 سیکنڈ انتظار کے بعد دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(15)

