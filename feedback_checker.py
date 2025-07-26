# filename: feedback_checker.py

import asyncio
import json
import logging
import httpx
import websockets
from datetime import datetime

from signal_tracker import get_all_signals, remove_active_signal, add_active_signal # ★★★ add_active_signal کو بھی امپورٹ کریں
from database_crud import add_completed_trade, add_feedback_entry
from models import SessionLocal
from key_manager import key_manager # ★★★ key_manager کو امپورٹ کریں

logger = logging.getLogger(__name__)

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ تمام WebSocket اور قیمت کی منطق اب اس فائل میں واپس آ گئی ہے ★★★
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

# قیمتوں کو ذخیرہ کرنے کے لیے ایک عالمی ڈکشنری
live_prices = {}

def get_current_price_for_symbol(symbol: str):
    """کسی علامت کے لیے تازہ ترین قیمت حاصل کرتا ہے۔"""
    return live_prices.get(symbol)

async def price_stream_logic():
    """Twelve Data WebSocket سے جڑنے اور قیمتیں حاصل کرنے کی منطق۔"""
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.error("کوئی بھی Twelve Data API کلید دستیاب نہیں۔ WebSocket شروع نہیں ہو سکتا۔")
        return

    uri = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={api_key}"
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logger.info("Twelve Data WebSocket سے کامیابی سے منسلک ہو گئے۔")
                
                # صرف BTC/USD کو سبسکرائب کریں
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "params": {"symbols": ["BTC/USD"]}
                }))

                async for message in websocket:
                    data = json.loads(message)
                    if data.get("event") == "price":
                        symbol = data.get("symbol")
                        price = data.get("price")
                        if symbol and price:
                            live_prices[symbol] = float(price)
                            
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
            logger.warning(f"WebSocket کنکشن بند ہوا۔ 10 سیکنڈ میں دوبارہ کوشش کی جائے گی۔ وجہ: {e}")
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"WebSocket میں نامعلوم خرابی: {e}", exc_info=True)
            await asyncio.sleep(10)


async def check_active_signals_job():
    """
    یہ جاب تمام فعال سگنلز کی جانچ کرتی ہے اور ان کے نتیجے کا اندازہ لگاتی ہے۔
    """
    active_signals = get_all_signals()
    if not active_signals:
        return

    db = SessionLocal()
    try:
        for signal in active_signals:
            try:
                symbol = signal.get("symbol")
                current_price = get_current_price_for_symbol(symbol)
                if current_price is None:
                    continue

                signal_id = signal.get("signal_id")
                signal_type = signal.get("signal")
                tp = signal.get("tp")
                sl = signal.get("sl")

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
                    add_completed_trade(db, signal, outcome)
                    add_feedback_entry(db, symbol, signal.get("timeframe", "15min"), feedback)
                    remove_active_signal(signal_id)
                    
            except Exception as e:
                logger.error(f"سگنل {signal.get('signal_id')} پر کارروائی کے دوران خرابی: {e}", exc_info=True)
    finally:
        db.close()
                
