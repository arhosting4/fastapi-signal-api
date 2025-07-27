# filename: feedback_checker.py

import asyncio
import json
import logging
import websockets  # ★★★ یہ لائن غائب تھی ★★★
from typing import Dict, List

import database_crud as crud
from models import SessionLocal
from key_manager import key_manager
from websocket_manager import manager
from utils import get_multiple_prices_twelve_data

logger = logging.getLogger(__name__)

# یہ ڈکشنری اب بھی WebSocket سے آنے والی قیمتوں کو رکھے گی
live_prices_ws: Dict[str, float] = {}

# WebSocket پر سبسکرائب کیے جانے والے جوڑے
WEBSOCKET_SYMBOLS = ["BTC/USD"]

async def price_stream_logic():
    """
    صرف اجازت یافتہ جوڑوں (WEBSOCKET_SYMBOLS) کے لیے WebSocket سے قیمتیں حاصل کرتا ہے۔
    """
    while True:
        api_key = key_manager.get_api_key()
        if not api_key:
            logger.error("WebSocket کے لیے کوئی API کلید دستیاب نہیں۔ 1 منٹ بعد دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(60)
            continue

        uri = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={api_key}"
        
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"WebSocket سے منسلک (کلید: {api_key[:8]}...)")
                
                subscribe_payload = {"action": "subscribe", "params": {"symbols": WEBSOCKET_SYMBOLS}}
                await websocket.send(json.dumps(subscribe_payload))

                async for message in websocket:
                    data = json.loads(message)
                    if data.get("event") == "price":
                        symbol = data.get("symbol")
                        price = data.get("price")
                        if symbol and price:
                            live_prices_ws[symbol] = float(price)
                    elif data.get("event") == "subscribe-status" and data.get("status") == "error":
                        logger.error(f"WebSocket سبسکرپشن میں خرابی (کلید: {api_key[:8]}...): {data.get('message')}")
                        key_manager.mark_key_as_limited(api_key, duration_seconds=300)
                        break
                            
        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"WebSocket کنکشن ناکام (کلید: {api_key[:8]}...), اسٹیٹس کوڈ: {e.status_code}۔")
            key_manager.mark_key_as_limited(api_key, duration_seconds=300)
            await asyncio.sleep(5)
        except Exception as e:
            logger.warning(f"WebSocket کنکشن میں مسئلہ: {e}۔ 10 سیکنڈ میں دوبارہ کوشش کی جائے گی۔")
            await asyncio.sleep(10)

async def check_active_signals_job():
    """
    ہائبرڈ سسٹم کا استعمال کرتے ہوئے فعال سگنلز کی جانچ کرتا ہے۔
    """
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        if not active_signals:
            return

        symbols_for_rest_api = [
            signal.symbol for signal in active_signals 
            if signal.symbol not in WEBSOCKET_SYMBOLS
        ]
        
        prices_from_rest = {}
        if symbols_for_rest_api:
            unique_symbols = list(set(symbols_for_rest_api))
            prices_from_rest = await get_multiple_prices_twelve_data(unique_symbols)

        all_current_prices = live_prices_ws.copy()
        all_current_prices.update(prices_from_rest)

        for signal in active_signals:
            symbol = signal.symbol
            current_price = all_current_prices.get(symbol)

            if current_price is None:
                logger.warning(f"سگنل {signal.signal_id} ({symbol}) کے لیے قیمت حاصل نہیں کی جا سکی۔")
                continue

            signal_id = signal.signal_id
            signal_type = signal.signal_type
            tp = signal.tp_price
            sl = signal.sl_price
            outcome = None
            feedback = None

            if signal_type == "buy":
                if current_price >= tp:
                    outcome = "tp_hit"; feedback = "correct"
                elif current_price <= sl:
                    outcome = "sl_hit"; feedback = "incorrect"
            elif signal_type == "sell":
                if current_price <= tp:
                    outcome = "tp_hit"; feedback = "correct"
                elif current_price >= sl:
                    outcome = "sl_hit"; feedback = "incorrect"

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
        logger.error(f"فعال سگنلز کی جانچ کے دوران مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        
