# filename: feedback_checker.py

import asyncio
import logging
from typing import Dict, List

import database_crud as crud
from models import SessionLocal
from websocket_manager import manager
from utils import get_multiple_prices_twelve_data

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    صرف REST API کا استعمال کرتے ہوئے فعال سگنلز کی جانچ کرتا ہے۔
    """
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals_from_db(db)
        if not active_signals:
            return

        # 1. تمام فعال جوڑوں کی فہرست بنائیں
        symbols_to_fetch = [signal.symbol for signal in active_signals]
        
        # 2. REST API سے تمام قیمتیں حاصل کریں
        all_current_prices = {}
        if symbols_to_fetch:
            unique_symbols = list(set(symbols_to_fetch))
            logger.info(f"ان جوڑوں کے لیے قیمتیں حاصل کی جا رہی ہیں: {unique_symbols}")
            all_current_prices = await get_multiple_prices_twelve_data(unique_symbols)

        # 3. ہر سگنل کو چیک کریں
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
        logger.error(f"فعال سگنلز کی جانچ کے دوران مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        
