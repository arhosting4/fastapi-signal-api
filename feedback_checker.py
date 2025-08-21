# filename: feedback_checker.py

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session

import database_crud as crud
from models import SessionLocal
from utils import fetch_twelve_data_ohlc
from websocket_manager import manager

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    یہ نگران انجن کا حتمی، مکمل، اور درست ورژن ہے۔ یہ سگنل بننے کے بعد کی High/Low
    اور موجودہ قیمت، تینوں کو چیک کرتا ہے تاکہ کوئی بھی TP/SL ہٹ مس نہ ہو۔
    """
    logger.info("🛡️ نگران انجن (مکمل ورژن): نگرانی کا دور شروع...")
    
    signals_to_close = []
    
    with SessionLocal() as db:
        active_signals = crud.get_all_active_signals_from_db(db)
        
        if not active_signals:
            logger.info("🛡️ نگران: کوئی فعال سگنل موجود نہیں، نگرانی کا دور ختم۔")
            return

        logger.info(f"🛡️ نگران: {len(active_signals)} فعال سگنلز ملے، جانچ شروع کی جا رہی ہے...")
        
        for signal in active_signals:
            try:
                now_utc = datetime.now(timezone.utc)
                signal_created_at_utc = signal.created_at.replace(tzinfo=timezone.utc)
                minutes_since_creation = (now_utc - signal_created_at_utc).total_seconds() / 60
                minutes_to_check = min(int(minutes_since_creation) + 2, 15)

                candles = await fetch_twelve_data_ohlc(signal.symbol, "1min", minutes_to_check)
                
                if not candles:
                    logger.warning(f"🛡️ [{signal.symbol}] کے لیے کینڈل ڈیٹا نہیں ملا۔")
                    continue

                relevant_candles = [c for c in candles if c.datetime.replace(tzinfo=timezone.utc) > signal_created_at_utc]

                if not relevant_candles:
                    logger.info(f"🛡️ [{signal.symbol}] کے لیے کوئی نئی کینڈل نہیں بنی۔")
                    continue
                
                # --- یہ ہے فیصلہ کن تبدیلی ---
                # ماضی اور حال، دونوں کو حاصل کریں
                recent_high = max(c.high for c in relevant_candles)
                recent_low = min(c.low for c in relevant_candles)
                current_price = relevant_candles[-1].close # سب سے تازہ ترین بند قیمت

                logger.info(
                    f"🛡️ جانچ: [{signal.symbol}] | TP: {signal.tp_price:.5f} | SL: {signal.sl_price:.5f} | "
                    f"بعد کی High: {recent_high:.5f} | بعد کی Low: {recent_low:.5f} | موجودہ: {current_price:.5f}"
                )

                outcome, reason, close_price = None, None, None
                tp, sl = float(signal.tp_price), float(signal.sl_price)

                if signal.signal_type == "buy":
                    # تینوں شرائط کو چیک کریں
                    if recent_high >= tp: 
                        outcome, reason, close_price = "tp_hit", "TP Hit (High Price)", tp
                    elif current_price >= tp:
                        outcome, reason, close_price = "tp_hit", "TP Hit (Current Price)", current_price
                    elif recent_low <= sl: 
                        outcome, reason, close_price = "sl_hit", "SL Hit (Low Price)", sl
                    elif current_price <= sl:
                        outcome, reason, close_price = "sl_hit", "SL Hit (Current Price)", current_price

                elif signal.signal_type == "sell":
                    # تینوں شرائط کو چیک کریں
                    if recent_low <= tp: 
                        outcome, reason, close_price = "tp_hit", "TP Hit (Low Price)", tp
                    elif current_price <= tp:
                        outcome, reason, close_price = "tp_hit", "TP Hit (Current Price)", current_price
                    elif recent_high >= sl: 
                        outcome, reason, close_price = "sl_hit", "SL Hit (High Price)", sl
                    elif current_price >= sl:
                        outcome, reason, close_price = "sl_hit", "SL Hit (Current Price)", current_price

                if outcome:
                    signals_to_close.append({
                        "signal_id": signal.signal_id,
                        "outcome": outcome,
                        "close_price": close_price,
                        "reason": reason
                    })
            except Exception as e:
                logger.error(f"🛡️ سگنل {signal.symbol} کی جانچ میں خرابی: {e}", exc_info=True)

    if signals_to_close:
        with SessionLocal() as db:
            closed_signal_ids_for_broadcast = []
            for signal_data in signals_to_close:
                signal_id = signal_data["signal_id"]
                logger.info(f"★★★ سگنل {signal_id} کو {signal_data['outcome'].upper()} کے طور پر بند کیا جا رہا ہے ★★★")
                
                success = crud.close_and_archive_signal(
                    db, signal_id, signal_data["outcome"], 
                    signal_data["close_price"], signal_data["reason"]
                )
                if success:
                    closed_signal_ids_for_broadcast.append(signal_id)
            
            if closed_signal_ids_for_broadcast:
                async def do_broadcast():
                    for sid in closed_signal_ids_for_broadcast:
                        await manager.broadcast({"type": "signal_closed", "data": {"signal_id": sid}})
                
                asyncio.create_task(do_broadcast())

    logger.info("🛡️ نگران انجن (مکمل ورژن): نگرانی کا دور مکمل ہوا۔")
                
