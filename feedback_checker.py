# filename: feedback_checker.py

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

# مقامی امپورٹس
import database_crud as crud
from models import SessionLocal, ActiveSignal
from utils import get_real_time_quotes
from websocket_manager import manager
from roster_manager import get_monitoring_roster # ★★★ نیا اور اہم امپورٹ ★★★

logger = logging.getLogger(__name__)

MOMENTUM_FILE = "market_momentum.json"

# یہ متغیر اب تمام جوڑوں کی تازہ ترین قیمتوں کو یادداشت میں رکھے گا
latest_quotes_memory: Dict[str, Dict[str, Any]] = {}

async def check_active_signals_job():
    """
    یہ فنکشن اب دو اہم کام کرتا ہے:
    1. روسٹر مینیجر سے نگرانی کی متحرک فہرست حاصل کرتا ہے۔
    2. ان جوڑوں کی قیمتیں لا کر 'مرکزی یادداشت' کو اپ ڈیٹ کرتا ہے اور پھر اس یادداشت
       کی بنیاد پر تمام فعال سگنلز کو TP/SL کے لیے چیک کرتا ہے۔
    """
    global latest_quotes_memory
    logger.info("🛡️ نگران انجن: نگرانی کا نیا دور شروع...")

    db = SessionLocal()
    try:
        # 1. نگرانی کے لیے متحرک فہرست حاصل کریں
        pairs_to_monitor = get_monitoring_roster(db)
        
        if not pairs_to_monitor:
            logger.info("🛡️ نگران انجن: نگرانی کے لیے کوئی جوڑا نہیں۔ دور ختم۔")
            return

        # 2. تمام جوڑوں کی قیمتیں ایک ساتھ (ایک ہی API کال میں) حاصل کریں
        logger.info(f"🛡️ نگران انجن: {len(pairs_to_monitor)} جوڑوں کی قیمتیں حاصل کی جا رہی ہیں: {pairs_to_monitor}")
        new_quotes = await get_real_time_quotes(pairs_to_monitor)

        # 3. مرکزی یادداشت کو نئی قیمتوں سے اپ ڈیٹ کریں
        if new_quotes:
            latest_quotes_memory.update(new_quotes)
            logger.info(f"✅ مرکزی یادداشت اپ ڈیٹ ہوئی۔ کل یادداشت میں {len(latest_quotes_memory)} جوڑوں کا ڈیٹا ہے۔")
            save_market_momentum(new_quotes) # مارکیٹ کی حرکت کو محفوظ کریں
        else:
            logger.warning("🛡️ نگران انجن: اس دور میں کوئی نئی قیمت حاصل نہیں ہوئی۔")

        # 4. اب، تمام فعال سگنلز کو مرکزی یادداشت کی بنیاد پر چیک کریں
        active_signals = crud.get_all_active_signals_from_db(db)
        if not active_signals:
            logger.info("🛡️ نگران انجن: کوئی فعال سگنل موجود نہیں۔")
            return
        
        if not latest_quotes_memory:
            logger.warning("🛡️ نگران انجن: TP/SL چیک کرنے کے لیے مرکزی یادداشت میں کوئی ڈیٹا نہیں۔")
            return

        logger.info(f"🛡️ نگران انجن: {len(active_signals)} فعال سگنلز کو مرکزی یادداشت سے چیک کیا جا رہا ہے...")
        await check_signals_for_tp_sl(db, active_signals, latest_quotes_memory)

    except Exception as e:
        logger.error(f"🛡️ نگران انجن کے کام میں خرابی: {e}", exc_info=True)
    finally:
        if db.is_active:
            db.close()
        logger.info("🛡️ نگران انجن: نگرانی کا دور مکمل ہوا۔")


async def check_signals_for_tp_sl(db: Session, signals: List[ActiveSignal], quotes_memory: Dict[str, Any]):
    """
    یہ فنکشن تمام فعال سگنلز کو مرکزی یادداشت (quotes_memory) میں موجود قیمتوں سے چیک کرتا ہے۔
    """
    signals_closed_count = 0
    for signal in signals:
        # اگر سگنل کی علامت یادداشت میں نہیں ہے، تو اسے چھوڑ دیں
        if signal.symbol not in quotes_memory:
            continue

        quote_data = quotes_memory.get(signal.symbol)
        if not quote_data or "price" not in quote_data:
            continue
        
        try:
            current_price = float(quote_data["price"])
        except (ValueError, TypeError):
            continue

        outcome, close_price, reason = None, None, None
        
        # TP/SL کی منطق
        if signal.signal_type == "buy":
            if current_price >= signal.tp_price:
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit"
            elif current_price <= signal.sl_price:
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit"
        elif signal.signal_type == "sell":
            if current_price <= signal.tp_price:
                outcome, close_price, reason = "tp_hit", signal.tp_price, "tp_hit"
            elif current_price >= signal.sl_price:
                outcome, close_price, reason = "sl_hit", signal.sl_price, "sl_hit"

        # اگر کوئی نتیجہ نکلا ہے تو سگنل کو بند کریں
        if outcome:
            logger.info(f"★★★ سگنل کا نتیجہ: {signal.signal_id} کو {outcome.upper()} کے طور پر نشان زد کیا گیا ★★★")
            success = crud.close_and_archive_signal(db, signal.signal_id, outcome, close_price, reason)
            if success:
                signals_closed_count += 1
                # پس منظر میں ویب ساکٹ پر پیغام بھیجیں
                asyncio.create_task(manager.broadcast({"type": "signal_closed", "data": {"signal_id": signal.signal_id}}))
    
    if signals_closed_count > 0:
        logger.info(f"🛡️ نگران انجن: کل {signals_closed_count} سگنل بند کیے گئے۔")


def save_market_momentum(quotes: Dict[str, Any]):
    """
    یہ فنکشن صرف نئی حاصل کردہ قیمتوں کی بنیاد پر مارکیٹ کی حرکت کو ایک JSON فائل میں محفوظ کرتا ہے۔
    """
    try:
        try:
            with open(MOMENTUM_FILE, 'r') as f:
                market_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            market_data = {}

        now_iso = datetime.utcnow().isoformat()
        successful_quotes = 0
        for symbol, data in quotes.items():
            if "percent_change" in data and data.get("percent_change") is not None:
                if symbol not in market_data:
                    market_data[symbol] = []
                try:
                    # ہر علامت کے لیے آخری 10 تبدیلیاں محفوظ کریں
                    market_data[symbol].append({"time": now_iso, "change": float(data["percent_change"])})
                    market_data[symbol] = market_data[symbol][-10:] 
                    successful_quotes += 1
                except (ValueError, TypeError):
                    continue
        
        if successful_quotes > 0:
            with open(MOMENTUM_FILE, 'w') as f:
                json.dump(market_data, f)
            logger.debug(f"✅ نگران انجن: {successful_quotes} جوڑوں کی حرکت کا ڈیٹا کامیابی سے محفوظ کیا گیا۔")

    except Exception as e:
        logger.error(f"مارکیٹ کی حرکت کا ڈیٹا محفوظ کرنے میں خرابی: {e}", exc_info=True)
                
