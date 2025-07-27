# filename: feedback_checker.py

import asyncio
import json
import logging
import websockets
from typing import Dict

# ★★★ database_crud سے تمام ضروری فنکشنز امپورٹ کریں ★★★
import database_crud as crud
from models import SessionLocal
from key_manager import key_manager
from websocket_manager import manager # ★★★ websocket_manager کو امپورٹ کریں

logger = logging.getLogger(__name__)

live_prices: Dict[str, float] = {}

def get_current_price_for_symbol(symbol: str):
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
                
                # BTC/USD اور دیگر اہم جوڑوں کو سبسکرائب کریں
                # نوٹ: آپ کو اپنے Twelve Data پلان کے مطابق جوڑوں کی تعداد کو ایڈجسٹ کرنا ہوگا
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
                            
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
            logger.warning(f"WebSocket کنکشن بند ہوا۔ 10 سیکنڈ میں دوبارہ کوشش کی جائے گی۔ وجہ: {e}")
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"WebSocket میں نامعلوم خرابی: {e}", exc_info=True)
            await asyncio.sleep(10)

async def check_active_signals_job():
    """
    یہ جاب ڈیٹا بیس سے تمام فعال سگنلز کی جانچ کرتی ہے اور ان کے نتیجے کا اندازہ لگاتی ہے۔
    """
    db = SessionLocal()
    try:
        # ★★★ RAM کی بجائے ڈیٹا بیس سے فعال سگنلز حاصل کریں ★★★
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
                    # 1. مکمل شدہ ٹریڈ شامل کریں
                    crud.add_completed_trade(db, signal, outcome)
                    # 2. فیڈ بیک شامل کریں
                    crud.add_feedback_entry(db, symbol, signal.timeframe, feedback)
                    # 3. فعال سگنل کو ڈیٹا بیس سے ہٹائیں
                    crud.remove_active_signal_from_db(db, signal_id)
                    
                    # ★★★ فرنٹ اینڈ کو سگنل بند ہونے کا نوٹیفکیشن بھیجیں ★★★
                    await manager.broadcast({
                        "type": "signal_closed",
                        "data": {"signal_id": signal_id}
                    })
                    
            except Exception as e:
                logger.error(f"سگنل {signal.signal_id} پر کارروائی کے دوران خرابی: {e}", exc_info=True)
    finally:
        db.close()
        
