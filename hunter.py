# filename: hunter.py

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from src.database.models import SessionLocal

# --- اہم تبدیلی: اعتماد کی حد کو ایک مستقل میں بیان کیا گیا ---
# ہم اسے 70.0 سے کم کر کے 40.0 کر رہے ہیں تاکہ سسٹم کی جانچ کی جا سکے
CONFIDENCE_THRESHOLD = 40.0
MAX_ACTIVE_SIGNALS = 5

async def analyze_pair(db: Session, pair: str, tf: str) -> Optional[Dict[str, Any]]:
    """ایک مخصوص جوڑے اور ٹائم فریم کا تجزیہ کرتا ہے اور اگر معیار پر پورا اترے تو سگنل لوٹاتا ہے۔"""
    try:
        candles = await fetch_twelve_data_ohlc(pair, tf, 100)
        if not candles or len(candles) < 34:
            return None
        
        signal_result = await generate_final_signal(db, pair, candles, tf)

        if signal_result and signal_result.get("status") == "ok":
            confidence = signal_result.get("confidence", 0)
            # --- تبدیلی: اب 40.0 کی حد کے خلاف جانچ کی جائے گی ---
            if confidence >= CONFIDENCE_THRESHOLD:
                print(f"--- Signal Found: {pair} ({tf}) with confidence {confidence:.2f}% (Threshold: {CONFIDENCE_THRESHOLD}%) ---")
                return signal_result
            else:
                print(f"--- Signal Discarded: {pair} ({tf}) confidence {confidence:.2f}% is below threshold {CONFIDENCE_THRESHOLD}%. ---")

    except Exception as e:
        print(f"--- Hunter ERROR processing {pair} ({tf}): {e} ---")
    
    return None

async def hunt_for_signals_job():
    """
    مارکیٹ میں اعلیٰ معیار کے تجارتی سگنلز تلاش کرتا ہے اور انہیں ٹریکنگ کے لیے شامل کرتا ہے۔
    اب یہ متعدد سگنلز کو سنبھال سکتا ہے۔
    """
    print(f"--- [{datetime.now()}] Running Signal Hunter Job (Multi-Signal Mode) ---")
    
    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        print(f"--- Hunter paused: Maximum active signals ({MAX_ACTIVE_SIGNALS}) reached. ---")
        return

    available_pairs = get_available_pairs()
    tasks = []
    
    db = SessionLocal()
    try:
        for pair in available_pairs:
            for tf in ["1m", "5m", "15m"]:
                tasks.append(analyze_pair(db, pair, tf))
        
        # تمام تجزیے ایک ساتھ چلائیں
        potential_signals = await asyncio.gather(*tasks)
        
        # تمام درست سگنلز کو فلٹر کریں
        valid_signals = [s for s in potential_signals if s is not None]

        if valid_signals:
            # سگنلز کو اعتماد کے لحاظ سے ترتیب دیں اور بہترین سگنلز کو شامل کریں
            valid_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            for signal in valid_signals:
                if get_active_signals_count() < MAX_ACTIVE_SIGNALS:
                    print(f"--- !!! High-Confidence Signal ACCEPTED: {signal['symbol']} ({signal['timeframe']}) at {signal['confidence']:.2f}%. Making it live. !!! ---")
                    add_active_signal(signal)
                    await send_telegram_alert(signal)
                else:
                    print("--- Max active signals reached. No more signals will be added in this cycle. ---")
                    break # لوپ کو روک دیں اگر زیادہ سے زیادہ سگنلز کی حد پوری ہو گئی ہو
        else:
            print("--- No signals found meeting the confidence threshold in this hunt. ---")
            
    finally:
        db.close()
        
