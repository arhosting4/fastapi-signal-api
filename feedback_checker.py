# filename: feedback_checker.py

import asyncio
import json
import logging
import websockets
from typing import Dict

import database_crud as crud
from models import SessionLocal
from key_manager import key_manager
from websocket_manager import manager

logger = logging.getLogger(__name__)

live_prices: Dict[str, float] = {}

def get_current_price_for_symbol(symbol: str):
    return live_prices.get(symbol)

async def price_stream_logic():
    """Twelve Data WebSocket سے جڑنے اور قیمتیں حاصل کرنے کی منطق۔"""
    while True:
        api_key = key_manager.get_api_key()
        if not api_key:
            logger.error("کوئی بھی Twelve Data API کلید دستیاب نہیں۔ WebSocket 1 منٹ بعد دوبارہ کوشش کرے گا۔")
            await asyncio.sleep(60)
            continue

        uri = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={api_key}"
        
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"Twelve Data WebSocket سے کامیابی سے منسلک ہو گئے (کلید: {api_key[:8]}...)")
                
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "params": {"symbols": ["BTC/USD", "EUR/USD", "XAU/USD", "GBP/USD"]}
                }))

                async for message in websocket:
                    data = json.loads(message)
                    if data.get("event") == "price":
                        symbol = data.get("symbol")
                        price = data.get("price")
                        if symbol and price:
                            live_prices[symbol] = float(price)
                    elif data.get("event") == "subscribe-status":
                        # اگر سبسکرپشن ناکام ہو (مثلاً غلط کلید)
                        if data.get("status") == "error":
                            logger.error(f"WebSocket سبسکرپشن میں خرابی (کلید: {api_key[:8]}...): {data.get('message')}")
                            # اس کلید کو محدود کریں اور لوپ کو توڑ دیں تاکہ اگلی کلید کے ساتھ کوشش کی جا سکے
                            key_manager.mark_key_as_limited(api_key, duration_seconds=300) # 5 منٹ کے لیے محدود کریں
                            break
                            
        except websockets.exceptions.InvalidStatusCode as e:
            # اگر کنکشن کی کوشش ناکام ہو (مثلاً 401 Unauthorized)
            logger.error(f"WebSocket کنکشن ناکام (کلید: {api_key[:8]}...)، اسٹیٹس کوڈ: {e.status_code}۔ کلید کو محدود کیا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key, duration_seconds=300) # 5 منٹ کے لیے محدود کریں
            await asyncio.sleep(5) # اگلی کوشش سے پہلے تھوڑا انتظار کریں
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
            logger.warning(f"WebSocket کنکشن بند ہوا۔ 10 سیکنڈ میں دوبارہ کوشش کی جائے گی۔ وجہ: {e}")
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"WebSocket میں نامعلوم خرابی: {e}", exc_info=True)
            await asyncio.sleep(10)

# check_active_signals_job فنکشن میں کوئی تبدیلی نہیں ہے، وہ ویسے ہی رہے گا۔
async def check_active_signals_job():
    """
    یہ جاب ڈیٹا بیس سے تمام فعال سگنلز کی جانچ کرتی ہے اور ان کے نتیجے کا اندازہ لگاتی ہے۔
    """
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        if not active_signals:
            return

        for signal in active_signals:
            try:
                symbol = signal.symbol
                current_price = get_current_price_for_symbol(symbol)
                if current_price is None:
                    logger.warning(f"سگنل {signal.signal_id} کے لیے قیمت دستیاب نہیں ہے۔")
                    continue

                signal_id = signal.signal_id
                signal_type = signal.signal_type
                tp = signal.tp_price
                sl = signal.sl_price

                outcome = None
                feedback = None

                if signal_type == "buy":
                    if current_price >= tp:
                        outcome = "tp_hit"
                        feedback = "correct"
                    elif current_price <= sl:
                        outcome = "sl_hit"
                        feedback = "incorrect"
                elif signal_type == "sell":
                    if current_price <= tp:
                        outcome = "tp_hit"
                        feedback = "correct"
                    elif current_price >= sl:
                        outcome = "sl_hit"
                        feedback = "incorrect"

                if outcome:
                    logger.info(f"★★★ سگنل کا نتیجہ: {signal_id} کو {outcome} کے طور پر نشان زد کیا گیا ★★★")
                    crud.add_completed_trade(db, signal, outcome)
                    crud.add_feedback_entry(db, symbol, signal.timeframe, feedback)
                    crud.remove_active_signal_from_db(db, signal_id)
                    
                    await manager.broadcast({
                        "type": "signal_closed",
                        "data": {"signal_id": signal_id}
                    })
                    
            except Exception as e:
                logger.error(f"سگنل {signal.signal_id} پر کارروائی کے دوران خرابی: {e}", exc_info=True)
    finally:
        db.close()
