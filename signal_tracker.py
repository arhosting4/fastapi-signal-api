import json
import os
from datetime import datetime

TRACKER_FILE = "signal_tracker.json"
TRACKER_DIR = "data" # Directory to store tracker data

# Ensure the tracker directory exists
os.makedirs(TRACKER_DIR, exist_ok=True)
TRACKER_FILE_PATH = os.path.join(TRACKER_DIR, TRACKER_FILE)

# Initialize tracker file if not exist
if not os.path.exists(TRACKER_FILE_PATH):
    try:
        with open(TRACKER_FILE_PATH, "w") as f:
            json.dump([], f) # Initialize with an empty list
        print(f"✅ Created empty signal tracker file: {TRACKER_FILE_PATH}")
    except Exception as e:
        print(f"⚠️ Error creating signal tracker file: {e}")

def add_active_signal(signal_data: dict):
    """
    Adds a new active signal to the tracker.

    Parameters:
        signal_data (dict): The dictionary containing the signal result from fusion_engine.
    """
    try:
        with open(TRACKER_FILE_PATH, "r") as f:
            active_signals = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        active_signals = []
        print(f"⚠️ Signal tracker file {TRACKER_FILE_PATH} was empty or corrupted, re-initializing.")

    # Add a unique ID and timestamp to the signal
    signal_id = f"{signal_data['symbol'].replace('/', '_')}_{datetime.utcnow().timestamp()}"
    signal_data['id'] = signal_id
    signal_data['status'] = 'active' # Set initial status to active
    signal_data['timestamp'] = datetime.utcnow().isoformat()

    active_signals.append(signal_data)

    try:
        with open(TRACKER_FILE_PATH, "w") as f:
            json.dump(active_signals, f, indent=2)
        print(f"✅ New active signal added to tracker: {signal_id}")
    except Exception as e:
        print(f"⚠️ Error saving active signal: {e}")

def get_active_signals() -> list:
    """
    Retrieves all active signals from the tracker.

    Returns:
        list: A list of active signal dictionaries.
    """
    try:
        with open(TRACKER_FILE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def update_signal_status(signal_id: str, new_status: str):
    """
    Updates the status of a signal in the tracker (e.g., to 'correct', 'incorrect', 'expired').

    Parameters:
        signal_id (str): The unique ID of the signal.
        new_status (str): The new status of the signal.
    """
    try:
        with open(TRACKER_FILE_PATH, "r") as f:
            active_signals = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return

    # Find the signal and update its status
    signal_found = False
    for signal in active_signals:
        if signal.get('id') == signal_id:
            signal['status'] = new_status
            signal_found = True
            break
    
    # Remove non-active signals from the tracker
    updated_signals = [s for s in active_signals if s.get('status') == 'active']

    if signal_found:
        try:
            with open(TRACKER_FILE_PATH, "w") as f:
                json.dump(updated_signals, f, indent=2)
            print(f"✅ Signal {signal_id} status updated to {new_status} and removed from active list.")
        except Exception as e:
            print(f"⚠️ Error updating signal status: {e}")
