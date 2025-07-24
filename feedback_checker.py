import logging
from datetime import datetime, timedelta

# براہ راست امپورٹس
from database_config import SessionLocal
import database_crud as crud
import signal_tracker
import utils

def check_active_signals():
    """
    Checks all active signals to see if they have hit TP/SL or expired.
    Records the outcome in the database.
    """
    logging.info("Starting active signals check cycle...")
    active_signals = signal_tracker.get_all_signals() # یہاں تبدیلی کی گئی ہے
    
    if not active_signals:
        logging.info("No active signals to check.")
        return

    db = SessionLocal()
    try:
        for signal in active_signals:
            symbol = signal["symbol"]
            current_price_data = utils.get_current_price_twelve_data(symbol)
            
            if not current_price_data:
                logging.warning(f"Could not get current price for {symbol} to check signal {signal["signal_id"]}.")
                continue

            current_price = current_price_data["price"]
            outcome = None
            
            # Check for TP/SL hit
            if signal["signal_type"] == "BUY":
                if current_price >= signal["tp_price"]:
                    outcome = "tp_hit"
                elif current_price <= signal["sl_price"]:
                    outcome = "sl_hit"
            elif signal["signal_type"] == "SELL":
                if current_price <= signal["tp_price"]:
                    outcome = "tp_hit"
                elif current_price >= signal["sl_price"]:
                    outcome = "sl_hit"

            # Check for expiration (e.g., 15 minutes for scalping signals)
            expiration_time = signal["created_at"] + timedelta(minutes=15)
            if not outcome and datetime.utcnow() > expiration_time:
                outcome = "expired"

            # If an outcome is determined, process it
            if outcome:
                logging.info(f"Signal {signal["signal_id"]} for {symbol} finished with outcome: {outcome}.")
                
                # Record the completed trade
                crud.add_completed_trade(db, signal_data=signal, outcome=outcome)
                
                # Record feedback (correct if TP hit, incorrect otherwise)
                feedback = "correct" if outcome == "tp_hit" else "incorrect"
                crud.add_feedback_entry(db, symbol=signal["symbol"], timeframe=signal["timeframe"], feedback=feedback)
                
                # Remove from active tracker
                signal_tracker.remove_active_signal(signal["signal_id"])
    
    except Exception as e:
        logging.error(f"An error occurred during the feedback check cycle: {e}", exc_info=True)
    finally:
        db.close()
        logging.info("Active signals check cycle finished.")
        
