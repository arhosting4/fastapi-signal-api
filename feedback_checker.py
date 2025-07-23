import logging
from datetime import datetime, timedelta

# --- Corrected Absolute Imports ---
from database_config import SessionLocal
from src.database import database_crud as crud
import utils

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def check_active_signals():
    """
    Checks all active signals from the database against the current market price.
    """
    logging.info("Starting active signals check cycle...")
    db = SessionLocal()
    try:
        active_signals = crud.get_all_active_signals(db)
        if not active_signals:
            logging.info("No active signals to check.")
            return
        
        for signal in active_signals:
            outcome = None
            candles = await utils.fetch_twelve_data_ohlc(signal.symbol, "1min", 1)
            if not candles:
                logging.warning(f"Could not fetch current price for {signal.symbol}.")
                continue
            
            current_price = float(candles[0]['close'])
            
            if signal.signal_type.lower() == 'buy':
                if current_price >= signal.tp_price: outcome = 'tp_hit'
                elif current_price <= signal.sl_price: outcome = 'sl_hit'
            elif signal.signal_type.lower() == 'sell':
                if current_price <= signal.tp_price: outcome = 'tp_hit'
                elif current_price >= signal.sl_price: outcome = 'sl_hit'
            
            expiration_hours = 4 
            if not outcome and (datetime.utcnow() > signal.created_at + timedelta(hours=expiration_hours)):
                outcome = 'expired'

            if outcome:
                logging.info(f"Outcome for signal {signal.signal_id} ({signal.symbol}): {outcome.upper()}")
                crud.add_completed_trade(db, signal, outcome)
                feedback = 'correct' if outcome == 'tp_hit' else 'incorrect'
                crud.add_feedback_entry(db, signal.symbol, signal.timeframe, feedback)
                crud.remove_active_signal(db, signal.signal_id)
    except Exception as e:
        logging.error(f"An error occurred during the active signals check cycle: {e}", exc_info=True)
    finally:
        db.close()
        logging.info("Active signals check cycle finished.")
        
