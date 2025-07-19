import json
import os
from datetime import datetime

SIGNALS_FILE = "active_signals.json"

def save_signals_to_json(signals_list):
    try:
        os.makedirs("data", exist_ok=True)
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
        
        with open(SIGNALS_FILE, "w") as f:
            json.dump(json_data, f, indent=2)
        
        print(f"--- Saved {len(json_data)} signals to {SIGNALS_FILE} ---")
        return True
        
    except Exception as e:
        print(f"--- ERROR saving signals to JSON: {e} ---")
        return False

def get_active_signals_from_json():
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

def set_active_signals(signals_list):
    try:
        formatted_signals = []
        for signal in signals_list:
            if isinstance(signal, dict):
                formatted_signals.append(signal)
            else:
                signal_dict = {
                    "id": getattr(signal, 'id', 0),
                    "symbol": getattr(signal, 'symbol', ''),
                    "signal": getattr(signal, 'signal', ''),
                    "timeframe": getattr(signal, 'timeframe', ''),
                    "price": float(getattr(signal, 'entry_price', 0)),
                    "tp": float(getattr(signal, 'tp', 0)),
                    "sl": float(getattr(signal, 'sl', 0)),
                    "confidence": float(getattr(signal, 'confidence', 0)),
                    "reason": getattr(signal, 'reason', ''),
                    "tier": getattr(signal, 'tier', ''),
                    "entry_time": getattr(signal, 'entry_time', datetime.utcnow()).isoformat() if hasattr(signal, 'entry_time') else datetime.utcnow().isoformat()
                }
                formatted_signals.append(signal_dict)
        
        return save_signals_to_json(formatted_signals)
        
    except Exception as e:
        print(f"--- ERROR in set_active_signals: {e} ---")
        return False

def add_signal_to_json(signal_data):
    try:
        existing_signals = get_active_signals_from_json()
        
        existing_signals = [
            s for s in existing_signals 
            if not (s.get("symbol") == signal_data.get("symbol") and 
                   s.get("timeframe") == signal_data.get("timeframe"))
        ]
        
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
        return save_signals_to_json(existing_signals)
        
    except Exception as e:
        print(f"--- ERROR adding signal to JSON: {e} ---")
        return False

def remove_signal_from_json(symbol, timeframe):
    try:
        existing_signals = get_active_signals_from_json()
        
        updated_signals = [
            s for s in existing_signals 
            if not (s.get("symbol") == symbol and s.get("timeframe") == timeframe)
        ]
        
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
    try:
        with open(SIGNALS_FILE, "w") as f:
            json.dump([], f)
        print("--- All signals cleared from JSON file ---")
        return True
        
    except Exception as e:
        print(f"--- ERROR clearing signals: {e} ---")
        return False
    
