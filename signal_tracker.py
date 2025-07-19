import json
import os
from datetime import datetime

SIGNALS_FILE = "active_signals.json"
    """
    try:
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Prepare data for JSON serialization
        json_data = []
        for signal in signals_list:
            signal_dict = {
                "id": signal.get("id", 0),
                "symbol": signal.get("symbol", ""),
                "signal": signal.get("signal", ""),
                "timeframe": signal.get("timeframe", ""),
                "price": float(signal.get("price", 0)),
                "tp": float(signal.get("tp", 0)),
                "sl": float(signal.get("sl", 0)),
                "confidence": float(signal.get("confidence", 0)),
                "reason": signal.get("reason", ""),
                "tier": signal.get("tier", ""),
                "entry_time": signal.get("entry_time", datetime.utcnow().isoformat())
            }
            json_data.append(signal_dict)
        
        # Save to file
        with open(SIGNALS_FILE, "w") as f:
            json.dump(json_data, f, indent=2)
        
        print(f"--- Saved {len(json_data)} signals to {SIGNALS_FILE} ---")
        return True
        
    except Exception as e:
        print(f"--- ERROR saving signals to JSON: {e} ---")
        return False

def get_active_signals_from_json():
    """
    JSON file سے active signals کو retrieve کرتا ہے
    """
    try:
        if not os.path.exists(SIGNALS_FILE):
            print(f"--- {SIGNALS_FILE} not found, returning empty list ---")
            return []
        
        with open(SIGNALS_FILE, "r") as f:
            signals = json.load(f)
        
        print(f"--- Retrieved {len(signals)} signals from {SIGNALS_FILE} ---")
        return signals
        
    except Exception as e:
        print(f"--- ERROR reading signals from JSON: {e} ---")
        return []

def add_signal_to_json(signal_data):
    """
    ایک نیا signal JSON file میں add کرتا ہے
    """
    try:
        # Get existing signals
        existing_signals = get_active_signals_from_json()
        
        # Remove any existing signal for the same symbol and timeframe
        existing_signals = [
            s for s in existing_signals 
            if not (s.get("symbol") == signal_data.get("symbol") and 
                   s.get("timeframe") == signal_data.get("timeframe"))
        ]
        
        # Add new signal
        signal_dict = {
            "id": len(existing_signals) + 1,
            "symbol": signal_data.get("symbol", ""),
            "signal": signal_data.get("signal", ""),
            "timeframe": signal_data.get("timeframe", ""),
            "price": float(signal_data.get("price", 0)),
            "tp": float(signal_data.get("tp", 0)),
            "sl": float(signal_data.get("sl", 0)),
            "confidence": float(signal_data.get("confidence", 0)),
            "reason": signal_data.get("reason", ""),
            "tier": signal_data.get("tier", ""),
            "entry_time": datetime.utcnow().isoformat()
        }
        
        existing_signals.append(signal_dict)
        
        # Save updated list
        return save_signals_to_json(existing_signals)
        
    except Exception as e:
        print(f"--- ERROR adding signal to JSON: {e} ---")
        return False

def remove_signal_from_json(symbol, timeframe):
    """
    کسی specific symbol اور timeframe کے signal کو JSON file سے remove کرتا ہے
    """
    try:
        # Get existing signals
        existing_signals = get_active_signals_from_json()
        
        # Remove the specified signal
        updated_signals = [
            s for s in existing_signals 
            if not (s.get("symbol") == symbol and s.get("timeframe") == timeframe)
        ]
        
        # Save updated list
        if len(updated_signals) != len(existing_signals):
            save_signals_to_json(updated_signals)
            print(f"--- Removed signal for {symbol} {timeframe} ---")
            return True
        else:
            print(f"--- No signal found for {symbol} {timeframe} to remove ---")
            return False
        
    except Exception as e:
        print(f"--- ERROR removing signal from JSON: {e} ---")
        return False

def clear_all_signals():
    """
    تمام signals کو JSON file سے clear کرتا ہے
    """
    try:
        with open(SIGNALS_FILE, "w") as f:
            json.dump([], f)
        print("--- All signals cleared from JSON file ---")
        return True
        
    except Exception as e:
        print(f"--- ERROR clearing signals: {e} ---")
        return False
