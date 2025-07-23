import logging
from datetime import datetime, timedelta

from ..database.database_config import SessionLocal
from ..database import database_crud as crud
from ..utils import fetch_twelve_data_ohlc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def check_active_signals():
    """
    Checks all active signals from the database against the current market price
    to determine their outcome (TP hit, SL hit, or expired).
    """
    logging.info("Starting active signals check cycle...")
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals(db)
        if not active_signals:
            logging.info("No active signals to check.")
            return

        logging.info(f"Checking {len(active_signals)} active signal(s)...")
        
        for signal in active_signals:
            outcome = None
            # Fetch the most recent price data
            # We only need a small amount of data to get the current price
            candles = await fetch_twelve_data_ohlc(signal.symbol, "1min", 1)
            if not candles:
                logging.warning(f"Could not fetch current price for {signal.symbol}. Skipping check for signal {signal.signal_id}.")
                continue
            
            current_price = float(candles[0]['close'])
            
            # Check for TP/SL hit
            if signal.signal_type.lower() == 'buy':
                if current_price >= signal.tp_price:
                    outcome = 'tp_hit'
                elif current_price <= signal.sl_price:
                    outcome = 'sl_hit'
            elif signal.signal_type.lower() == 'sell':
                if current_price <= signal.tp_price:
                    outcome = 'tp_hit'
                elif current_price >= signal.sl_price:
                    outcome = 'sl_hit'
            
            # Check for expiration (e.g., 4 hours for 1h timeframe signals)
            # This logic can be made more sophisticated
            expiration_hours = 4 
            if not outcome and (datetime.utcnow() > signal.created_at + timedelta(hours=expiration_hours)):
                outcome = 'expired'

            if outcome:
                logging.info(f"Outcome for signal {signal.signal_id} ({signal.symbol}): {outcome.upper()}")
                # 1. Add to completed trades
                crud.add_completed_trade(db, signal, outcome)
                # 2. Add feedback for the AI model
                feedback = 'correct' if outcome == 'tp_hit' else 'incorrect'
                crud.add_feedback_entry(db, signal.symbol, signal.timeframe, feedback)
                # 3. Remove from active signals
                crud.remove_active_signal(db, signal.signal_id)
                logging.info(f"Signal {signal.signal_id} processed and removed from active list.")

    except Exception as e:
        logging.error(f"An error occurred during the active signals check cycle: {e}", exc_info=True)
    finally:
        db.close()
        logging.info("Active signals check cycle finished.")
        
