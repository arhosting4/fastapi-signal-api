# filename: hunter.py

import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from utils import fetch_twelve_data_ohlc, get_available_pairs
from fusion_engine import generate_final_signal
from signal_tracker import add_active_signal, get_active_signals_count
from messenger import send_telegram_alert
from src.database.models import SessionLocal

# --- "اسمارٹ ہنٹنگ" کی نئی ترتیبات ---
PRIMARY_TIMEFRAME = "15m"
SECONDARY_TIMEFRAMES = ["5m", "30m"]
SCOUTING_THRESHOLD = 55.0  # اسکاؤٹنگ کے لیے کم از کم اعتماد
CONFLUENCE_BONUS = 15.0     # ہم آہنگی کی صورت میں بونس
FINAL_CONFIDENCE_THRESHOLD = 70.0 # حتمی سگنل کے لیے کم از کم اعتماد (اسے بعد میں بڑھایا جا سکتا ہے)
MAX_ACTIVE_SIGNALS = 5

async def analyze_pair_timeframe(db: Session, pair: str, tf: str) -> Optional[Dict[str, Any]]:
    """ایک مخصوص جوڑے اور ٹائم فریم کا تجزیہ کرتا ہے۔"""
    try:
        candles = await fetch_twelve_data_ohlc(pair, tf, 100)
        if not candles or len(candles) < 34:
            return None
        
        # generate_final_signal کو درست پیرامیٹرز کے ساتھ کال کریں
        signal_result = await generate_final_signal(db, pair, candles, tf)
        
        if signal_result and signal_result.get("status") == "ok":
            return signal_result
    except Exception as e:
        print(f"--- Hunter Sub-Process ERROR processing {pair} ({tf}): {e} ---")
    return None

async def hunt_for_signals_job():
    """
    "اسمارٹ ہنٹنگ" کی حکمت عملی کا استعمال کرتے ہوئے سگنلز تلاش کرتا ہے۔
    مرحلہ 1: بنیادی ٹائم فریم پر اسکاؤٹنگ۔
    مرحلہ 2: بہترین مواقع کے لیے ثانوی ٹائم فریمز پر گہرا غوطہ۔
    مرحلہ 3: ہم آہنگی کی بنیاد پر اعتماد کو بڑھانا۔
    """
    print(f"--- Running Smart Hunting Job (Primary TF: {PRIMARY_TIMEFRAME}) ---")
    
    if get_active_signals_count() >= MAX_ACTIVE_SIGNALS:
        print(f"--- Hunter paused: Maximum active signals ({MAX_ACTIVE_SIGNALS}) reached. ---")
        return

    available_pairs = get_available_pairs()
    final_signals_to_consider = []
    db = SessionLocal()

    try:
        # --- مرحلہ 1: اسکاؤٹنگ رن ---
        print(f"--- [Scouting Phase] Analyzing all pairs on {PRIMARY_TIMEFRAME}... ---")
        scouted_opportunities = []
        for pair in available_pairs:
            primary_signal = await analyze_pair_timeframe(db, pair, PRIMARY_TIMEFRAME)
            if primary_signal and primary_signal.get("confidence", 0) >= SCOUTING_THRESHOLD:
                scouted_opportunities.append(primary_signal)
                print(f"--- [Scouting] Opportunity found for {pair} on {PRIMARY_TIMEFRAME}. Confidence: {primary_signal['confidence']}% ---")
        
        if not scouted_opportunities:
            print("--- [Scouting Phase] No significant opportunities found. Ending hunt. ---")
            return

        # --- مرحلہ 2 & 3: گہرا غوطہ اور ہم آہنگی کی جانچ ---
        print(f"--- [Deep Dive Phase] Analyzing scouted opportunities on {SECONDARY_TIMEFRAMES}... ---")
        for primary_signal in scouted_opportunities:
            pair = primary_signal["symbol"]
            primary_direction = primary_signal["signal"]
            
            confluence_found = True
            for tf in SECONDARY_TIMEFRAMES:
                secondary_signal = await analyze_pair_timeframe(db, pair, tf)
                # اگر کسی بھی ثانوی ٹائم فریم پر سگنل کی سمت مختلف ہو تو ہم آہنگی ناکام ہو جاتی ہے
                if not secondary_signal or secondary_signal.get("signal") != primary_direction:
                    confluence_found = False
                    print(f"--- [Deep Dive] No confluence for {pair} on {tf}. ---")
                    break
            
            # --- مرحلہ 4: اعتماد میں اضافہ ---
            if confluence_found:
                print(f"--- [Confluence Found!] Strong agreement for {pair} across all timeframes. Applying bonus. ---")
                primary_signal["confidence"] += CONFLUENCE_BONUS
                primary_signal["reason"] += f" Multi-timeframe confluence ({PRIMARY_TIMEFRAME}, {', '.join(SECONDARY_TIMEFRAMES)}) provides strong confirmation."
                final_signals_to_consider.append(primary_signal)

        # --- حتمی فیصلہ ---
        if not final_signals_to_consider:
            print("--- [Final Decision] No signals passed the deep dive phase. ---")
            return
            
        # تمام اہل سگنلز کو بھیجیں جو حتمی حد سے تجاوز کرتے ہیں
        for signal in final_signals_to_consider:
            if signal["confidence"] >= FINAL_CONFIDENCE_THRESHOLD:
                print(f"--- !!! HIGH-CONFIDENCE SIGNAL FOUND: {signal['symbol']} ({signal['timeframe']}) at {signal['confidence']:.2f}%. Sending alert. !!! ---")
                add_active_signal(signal)
                await send_telegram_alert(signal)
            else:
                print(f"--- Signal for {signal['symbol']} did not meet final threshold of {FINAL_CONFIDENCE_THRESHOLD}%. Confidence was {signal['confidence']:.2f}%. ---")

    finally:
        db.close()
        print("--- Smart Hunting Job Finished. ---")
        
