# filename: hunter.py

import asyncio
from datetime import datetime
from typing import List, Dict, Any

from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
# --- اہم تبدیلی: signal_tracker سے نئے فنکشنز امپورٹ کیے گئے ---
from signal_tracker import set_live_signals, add_active_signals, get_active_signals_count
from messenger import send_telegram_alert
from src.database.models import SessionLocal

MAX_ACTIVE_SIGNALS = 10  # زیادہ سگنلز کے لیے حد بڑھا دی گئی
CONFIDENCE_THRESHOLD = 70.0  # کم از کم اعتماد کی حد

async def hunt_for_signals_job():
    print(f"--- [{datetime.now()}] Running Signal Hunter Job (Multi-Signal Mode) ---")
    
    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        print(f"--- Hunter paused: Maximum active signals ({MAX_ACTIVE_SIGNALS}) reached. ---")
        return

    available_pairs = get_available_pairs()
    # --- اہم تبدیلی: ایک سگنل کی بجائے تمام اعلیٰ اعتماد والے سگنلز کو ذخیرہ کریں ---
    high_confidence_signals: List[Dict[str, Any]] = []

    db = SessionLocal()
    try:
        # تمام جوڑوں اور ٹائم فریمز کے لیے غیر مطابقت پذیر ٹاسک بنائیں
        tasks = []
        for pair in available_pairs:
            for tf in ["5m", "15m", "1h"]: # زیادہ مستحکم ٹائم فریمز پر توجہ مرکوز کی گئی
                tasks.append(analyze_pair(db, pair, tf))
        
        # تمام ٹاسک کو متوازی طور پر چلائیں
        results = await asyncio.gather(*tasks)
        
        # نتائج کو فلٹر کریں اور اہل سگنلز کو جمع کریں
        for signal_result in results:
            if signal_result:
                high_confidence_signals.append(signal_result)

    finally:
        db.close()

    if high_confidence_signals:
        # اعتماد کے لحاظ سے سگنلز کو ترتیب دیں
        high_confidence_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        print(f"--- !!! FOUND {len(high_confidence_signals)} HIGH-CONFIDENCE SIGNALS (>{CONFIDENCE_THRESHOLD}%) !!! ---")
        
        # --- اہم تبدیلی: تمام اہل سگنلز کو لائیو کریں اور الرٹ بھیجیں ---
        set_live_signals(high_confidence_signals)  # تمام سگنلز کو ایک ساتھ کیش کریں
        add_active_signals(high_confidence_signals) # تمام سگنلز کو فعال ٹریکر میں شامل کریں

        for signal in high_confidence_signals:
            print(f"  -> Signal: {signal['symbol']} ({signal['timeframe']}) | Confidence: {signal['confidence']:.2f}%")
            await send_telegram_alert(signal) # ہر سگنل کے لیے الگ الرٹ
            await asyncio.sleep(1) # ٹیلیگرام API کی لمٹس سے بچنے کے لیے
    else:
        print("--- No signals found meeting the confidence threshold in this hunt. ---")
        set_live_signals([]) # اگر کوئی سگنل نہ ملے تو کیش خالی کریں

async def analyze_pair(db: Session, pair: str, tf: str) -> Optional[Dict[str, Any]]:
    """
    ایک مخصوص جوڑے اور ٹائم فریم کا تجزیہ کرتا ہے اور اگر اعتماد کی حد پوری ہو تو سگنل لوٹاتا ہے۔
    """
    try:
        candles = await fetch_twelve_data_ohlc(pair, tf, 100)
        if not candles or len(candles) < 50:
            return None
        
        signal_result = await generate_final_signal(db, pair, candles, tf)

        if signal_result and signal_result.get("status") == "ok":
            confidence = signal_result.get("confidence", 0)
            if confidence >= CONFIDENCE_THRESHOLD:
                return signal_result
    except Exception as e:
        print(f"--- Hunter ERROR processing {pair} ({tf}): {e} ---")
    return None
            
