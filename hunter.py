# filename: hunter.py

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
# --- اہم اور فوری اصلاح: Session کو امپورٹ کریں تاکہ NameError حل ہو ---
from sqlalchemy.orm import Session

from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import set_live_signals, add_active_signals, get_active_signals_count
from messenger import send_telegram_alert
from src.database.models import SessionLocal

MAX_ACTIVE_SIGNALS = 10
CONFIDENCE_THRESHOLD = 70.0

async def hunt_for_signals_job():
    print(f"--- [{datetime.now()}] Running Signal Hunter Job (Multi-Signal Mode) ---")
    
    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        print(f"--- Hunter paused: Maximum active signals ({MAX_ACTIVE_SIGNALS}) reached. ---")
        return

    available_pairs = get_available_pairs()
    high_confidence_signals: List[Dict[str, Any]] = []

    db = SessionLocal()
    try:
        tasks = []
        for pair in available_pairs:
            for tf in ["5m", "15m", "1h"]:
                tasks.append(analyze_pair(db, pair, tf))
        
        results = await asyncio.gather(*tasks)
        
        for signal_result in results:
            if signal_result:
                high_confidence_signals.append(signal_result)

    finally:
        db.close()

    if high_confidence_signals:
        high_confidence_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        print(f"--- !!! FOUND {len(high_confidence_signals)} HIGH-CONFIDENCE SIGNALS (>{CONFIDENCE_THRESHOLD}%) !!! ---")
        
        set_live_signals(high_confidence_signals)
        add_active_signals(high_confidence_signals)

        for signal in high_confidence_signals:
            print(f"  -> Signal: {signal['symbol']} ({signal['timeframe']}) | Confidence: {signal['confidence']:.2f}%")
            await send_telegram_alert(signal)
            await asyncio.sleep(1)
    else:
        print("--- No signals found meeting the confidence threshold in this hunt. ---")
        set_live_signals([])

# --- اس فنکشن کی تعریف میں Session کا استعمال کیا گیا تھا، جسے اب امپورٹ کر لیا گیا ہے ---
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
    
