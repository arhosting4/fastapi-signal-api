# filename: feedback_checker.py

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

import database_crud as crud
from models import SessionLocal
from utils import get_real_time_quotes # صرف یہی ایک فنکشن استعمال ہوگا
from websocket_manager import manager

logger = logging.getLogger(__name__)

async def check_active_signals_job():
    """
    یہ نگران انجن کا حتمی، ذہین، اور موثر ورژن ہے۔ یہ ایک ہی API کال سے ملنے والی
    موجودہ، بلند ترین، اور کم ترین قیمتوں کو چیک کرتا ہے تاکہ کوئی بھی TP/SL ہٹ مس نہ ہو۔
    """
    logger.info("🛡️ نگران انجن (حتمی اور موثر ورژن): نگرانی کا دور شروع...")
    
    signals_to_close = []
    
    with SessionLocal() as db:
        active_signals = crud.get_all_active_signals_from_db(db)
        
        if not active_signals:
            logger.info("🛡️ نگران: کوئی فعال سگنل موجود نہیں، نگرانی کا دور ختم۔")
            return

        logger.info(f"🛡️ نگران: {len(active_signals)} فعال سگنلز ملے، جانچ شروع کی جا رہی ہے...")
        
        symbols_to_check = list({s.symbol for s in active_signals})
        
        # --- مرحلہ 1: تمام جوڑوں کے لیے ایک ہی بار میں قیمت کا ڈیٹا حاصل کریں ---
        latest_quotes = await get_real_time_quotes(symbols_to_check)

        if not latest_quotes:
            logger.warning("🛡️ نگران: کوئی مارکیٹ قیمتیں حاصل نہیں ہوئیں۔")
            return

        for signal in active_signals:
            quote = latest_quotes.get(signal.symbol)
            
            # --- مرحلہ 2: اسی ایک API جواب سے تمام ضروری قیمتیں نکالیں ---
            if not quote or 'high' not in quote or 'low' not in quote:
                logger.warning(f"🛡️ [{signal.symbol}] کے لیے مکمل قیمت کا ڈیٹا (high/low) نہیں ملا۔")
                continue
            
            try:
                # آج کی بلند ترین اور کم ترین قیمت
                daily_high = float(quote['high'])
                daily_low = float(quote['low'])
            except (ValueError, TypeError):
                logger.warning(f"🛡️ [{signal.symbol}] کے لیے high/low قیمت کو فلوٹ میں تبدیل نہیں کیا جا سکا۔")
                continue

            logger.info(f"🛡️ جانچ: [{signal.symbol}] | TP: {signal.tp_price:.5f} | SL: {signal.sl_price:.5f} | آج کی High: {daily_high:.5f} | آج کی Low: {daily_low:.5f}")

            outcome, reason, close_price = None, None, None
            tp, sl = float(signal.tp_price), float(signal.sl_price)

            if signal.signal_type == "buy":
                if daily_high >= tp: 
                    outcome, reason, close_price = "tp_hit", "TP Hit (Daily High)", tp
                elif daily_low <= sl: 
                    outcome, reason, close_price = "sl_hit", "SL Hit (Daily Low)", sl
            elif signal.signal_type == "sell":
                if daily_low <= tp: 
                    outcome, reason, close_price = "tp_hit", "TP Hit (Daily Low)", tp
                elif daily_high >= sl: 
                    outcome, reason, close_price = "sl_hit", "SL Hit (Daily High)", sl

            if outcome:
                signals_to_close.append({
                    "signal_id": signal.signal_id,
                    "outcome": outcome,
                    "close_price": close_price,
                    "reason": reason
                })

    # --- مرحلہ 3: بند ہونے والے سگنلز کو پروسیس کریں ---
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

    logger.info("🛡️ نگران انجن (حتمی اور موثر ورژن): نگرانی کا دور مکمل ہوا۔")
