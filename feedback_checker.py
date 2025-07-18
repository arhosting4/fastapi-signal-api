import httpx
import asyncio
from datetime import datetime, timedelta
import yfinance as yf

# ہمارے اپنے پروجیکٹ کی فائلیں امپورٹ کریں
from signal_tracker import get_all_signals, update_signal_status
from feedback_memory import save_feedback

async def check_active_signals_job():
    """
    یہ وہ مرکزی فنکشن ہے جو پس منظر میں چلے گا۔
    یہ فعال سگنلز کو چیک کرے گا اور ان کے TP/SL کی نگرانی کرے گا۔
    """
    print(f"--- [{datetime.now()}] Running Background Signal Checker Job ---")
    
    all_signals = get_all_signals()
    # صرف وہی سگنل چیک کریں جو 'active' ہیں
    active_signals = [s for s in all_signals if s.get('status') == 'active']

    if not active_signals:
        print("No active signals to check.")
        return

    print(f"Found {len(active_signals)} active signals to check.")

    for signal in active_signals:
        signal_id = signal.get("id")
        symbol = signal.get("symbol")
        signal_type = signal.get("signal")
        tp = signal.get("tp")
        sl = signal.get("sl")
        timeframe = signal.get("timeframe") # فیڈ بیک کے لیے ٹائم فریم بھی حاصل کریں

        if not all([signal_id, symbol, signal_type, tp, sl, timeframe]):
            print(f"Skipping invalid signal data: {signal_id}")
            continue

        # yfinance سے تازہ ترین قیمت حاصل کریں
        y_symbol = "GC=F" if symbol == "XAU/USD" else symbol
        try:
            # ہم تیز ترین ڈیٹا کے لیے '1m' انٹرول استعمال کریں گے
            data = yf.Ticker(y_symbol).history(period="1d", interval="1m")
            if data.empty:
                print(f"Warning: No price data returned for {symbol}.")
                continue
            current_price = data['Close'].iloc[-1]
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            continue # اگر قیمت نہ ملے تو اگلے سگنل پر جائیں
        
        print(f"Checking: {signal_id} | {symbol} | Price: {current_price:.5f} | TP: {tp:.5f} | SL: {sl:.5f}")

        new_status = None
        feedback = None

        if signal_type == "buy":
            if current_price >= tp:
                new_status, feedback = "tp_hit", "correct"
            elif current_price <= sl:
                new_status, feedback = "sl_hit", "incorrect"
        
        elif signal_type == "sell":
            if current_price <= tp:
                new_status, feedback = "tp_hit", "correct"
            elif current_price >= sl:
                new_status, feedback = "sl_hit", "incorrect"

        if new_status:
            print(f"✅ OUTCOME: Signal {signal_id} resulted in '{new_status}' at price {current_price:.5f}.")
            # سگنل کی حیثیت کو اپ ڈیٹ کریں
            update_signal_status(signal_id, new_status, current_price)
            # AI کو سکھانے کے لیے فیڈ بیک محفوظ کریں
            save_feedback(symbol, feedback, timeframe)

    print(f"--- [{datetime.now()}] Signal Checker Job Finished ---")
    
