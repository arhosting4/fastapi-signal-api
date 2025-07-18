import asyncio
from typing import List, Dict, Any

# ہمارے پروجیکٹ کے ماڈیولز
from utils import fetch_twelve_data_ohlc
from fusion_engine import generate_final_signal
from signal_tracker import save_live_signal # یہ ایک نیا فنکشن ہوگا جسے ہم بنائیں گے

# وہ تمام جوڑے اور ٹائم فریم جنہیں ہم اسکین کرنا چاہتے ہیں
PAIRS_TO_SCAN = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
TIMEFRAMES_TO_SCAN = ["1m", "5m", "15m"]

async def hunt_for_signals_job():
    """
    یہ مرکزی پس منظر کی جاب ہے جو تمام جوڑوں اور ٹائم فریمز پر بہترین سگنل تلاش کرتی ہے۔
    """
    print("--- HUNTER JOB: Starting new hunt for trading signals... ---")
    
    all_possible_signals: List[Dict[str, Any]] = []

    # تمام جوڑوں اور ٹائم فریمز کے لیے ڈیٹا حاصل کریں اور سگنل بنائیں
    for pair in PAIRS_TO_SCAN:
        for tf in TIMEFRAMES_TO_SCAN:
            print(f"HUNTING on: {pair} - {tf}")
            
            # ڈیٹا حاصل کریں
            candles = await fetch_twelve_data_ohlc(pair, tf)
            
            if not candles or len(candles) < 50:
                print(f"Skipping {pair} - {tf} due to insufficient data.")
                continue
            
            # AI انجن سے ایک ممکنہ سگنل حاصل کریں
            # نوٹ: ہم fusion_engine کو بتائیں گے کہ ابھی سگنل کو محفوظ نہ کرے
            potential_signal = await generate_final_signal(pair, candles, tf, should_save_active=False)
            
            # صرف "buy" یا "sell" سگنلز پر غور کریں
            if potential_signal and potential_signal.get("signal") in ["buy", "sell"]:
                all_possible_signals.append(potential_signal)

    best_signal = None
    if not all_possible_signals:
        print("--- HUNTER JOB: No quality signals found in this cycle. ---")
        # اگر کوئی سگنل نہیں ملا، تو ایک "WAIT" سگنل محفوظ کریں
        best_signal = {
            "symbol": "N/A",
            "signal": "wait",
            "reason": "AI is actively scanning the markets for the next high-quality opportunity.",
            "timestamp": asyncio.get_event_loop().time()
        }
    else:
        # تمام ملنے والے سگنلز کو ان کے اعتماد کے اسکور کی بنیاد پر ترتیب دیں
        all_possible_signals.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        # سب سے زیادہ اعتماد والا سگنل منتخب کریں
        best_signal = all_possible_signals[0]
        print(f"--- HUNTER JOB: Best signal found! {best_signal.get('symbol')} ({best_signal.get('timeframe')}) with {best_signal.get('confidence')}% confidence. ---")

    # بہترین سگنل کو live_signal.json میں محفوظ کریں
    save_live_signal(best_signal)
  
