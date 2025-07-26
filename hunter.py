# filename: hunter.py

import asyncio
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# مقامی امپورٹس
from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from models import SessionLocal
from websocket_manager import manager

# ★★★ لاگر کو یہاں حاصل کریں ★★★
logger = logging.getLogger(__name__)

# کنفیگریشن
MAX_ACTIVE_SIGNALS = 5
FINAL_CONFIDENCE_THRESHOLD = 60.0

async def analyze_pair(db: Session, pair: str) -> Optional[Dict[str, Any]]:
    """ایک تجارتی جوڑے کا تجزیہ کرتا ہے اور اگر کوئی سگنل ملے تو اسے واپس کرتا ہے۔"""
    candles = await fetch_twelve_data_ohlc(pair)
    if not candles or len(candles) < 34:
        # ★★★ تفصیلی لاگ: ڈیٹا ناکافی ہے ★★★
        logger.info(f"📊 [{pair}] تجزیہ روکا گیا: ناکافی کینڈل ڈیٹا ({len(candles) if candles else 0})۔")
        return None

    signal_result = await generate_final_signal(db, pair, candles)
    
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★★★ اہم تبدیلی: ہر تجزیے کے بعد ایک تفصیلی رپورٹ لاگ کریں ★★★
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    if signal_result and signal_result.get("status") == "ok":
        # یہ لاگ تب ظاہر ہوگا جب ایک ممکنہ سگنل بنے گا (چاہے اس کا اعتماد کم ہو)
        confidence = signal_result.get('confidence', 0)
        log_message = (
            f"📊 [{pair}] تجزیہ مکمل: سگنل = {signal_result.get('signal', 'N/A').upper()}, "
            f"اعتماد = {confidence:.2f}%, پیٹرن = {signal_result.get('pattern', 'N/A')}, "
            f"رسک = {signal_result.get('risk', 'N/A')}"
        )
        logger.info(log_message)
        return signal_result
    elif signal_result:
        # یہ لاگ تب ظاہر ہوگا جب کوئی سگنل نہیں بنے گا
        logger.info(f"📊 [{pair}] تجزیہ مکمل: کوئی سگنل نہیں بنا۔ وجہ: {signal_result.get('reason', 'نامعلوم')}")
    
    return None

async def hunt_for_signals_job():
    """
    سگنل کی تلاش کا مرکزی کام جو شیڈیولر کے ذریعے چلایا جاتا ہے۔
    """
    # ★★★ یہ لاگ اب "ہارٹ بیٹ" جاب سے آئے گا، اس لیے یہاں سے ہٹا دیا گیا ہے ★★★
    
    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        logger.info("فعال سگنلز کی زیادہ سے زیادہ حد تک پہنچ گئے ہیں۔ شکار روکا جا رہا ہے۔")
        return

    pairs = get_available_pairs()
    logger.info(f"🏹 سگنل کی تلاش شروع: ان جوڑوں کا تجزیہ کیا جائے گا: {pairs}")
    db = SessionLocal()
    
    try:
        all_results = []
        for pair in pairs:
            if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
                logger.info("سگنل کی حد تک پہنچ گئے۔ شکار روکا جا رہا ہے۔")
                break
            
            result = await analyze_pair(db, pair)
            if result:
                all_results.append(result)

        # صرف سب سے زیادہ اعتماد والے سگنل کو منتخب کریں
        if all_results:
            best_signal = max(all_results, key=lambda x: x.get('confidence', 0))
            
            if best_signal.get("confidence", 0) >= FINAL_CONFIDENCE_THRESHOLD:
                add_active_signal(best_signal)
                # ★★★ یہ ہے ہمارا حتمی "ہارٹ بیٹ" لاگ جو صرف سگنل بننے پر ظاہر ہوگا ★★★
                logger.info(f"🎯 ★★★ [HEARTBEAT] نیا سگنل ملا اور بھیجا گیا: {best_signal['symbol']} - {best_signal['signal']} @ {best_signal['price']} ★★★")
                
                await send_telegram_alert(best_signal)
                await manager.broadcast({
                    "type": "new_signal",
                    "data": best_signal
                })

    except Exception as e:
        logger.error(f"سگنل کی تلاش کے کام میں مہلک خرابی: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("🏹 سگنل کی تلاش مکمل ہوئی۔")
        
