# filename: feedback_checker.py

import asyncio
import logging
from sqlalchemy.orm import Session
from models import SessionLocal, ActiveSignal
from utils import get_real_time_quotes
from trainerai import learn_from_outcome
from datetime import datetime

logger = logging.getLogger(__name__)

async def check_signal_outcome(db: Session, signal: ActiveSignal):
    """
    Checks a single active signal: fetches latest quote, and if TP/SL hit, updates state and learns.
    """
    try:
        quote_data = await get_real_time_quotes([signal.symbol])
        if not quote_data or signal.symbol not in quote_data:
            logger.warning(f"[{signal.symbol}] Live quote not available — skipping feedback.")
            return

        current_price = float(quote_data[signal.symbol].get('price', 0))
        if not current_price:
            logger.warning(f"[{signal.symbol}] Live price is 0 — skipping.")
            return

        component = signal.component_scores or {}
        tp = component.get("tp") or component.get("tp_price")
        sl = component.get("sl") or component.get("sl_price")
        if not tp or not sl:
            logger.warning(f"[{signal.symbol}] No TP/SL set in component_scores.")
            return

        outcome = None
        if signal.signal_type == "buy":
            if current_price >= tp:
                outcome = "tp_hit"
            elif current_price <= sl:
                outcome = "sl_hit"
        elif signal.signal_type == "sell":
            if current_price <= tp:
                outcome = "tp_hit"
            elif current_price >= sl:
                outcome = "sl_hit"

        if outcome:
            signal.is_active = False
            signal.closed_at = datetime.utcnow()
            db.commit()
            logger.info(f"Signal [{signal.symbol}] outcome: {outcome} at {current_price}.")
            await learn_from_outcome(db, signal, outcome)
    except Exception as e:
        logger.error(f"[{signal.symbol}] feedback check error: {e}", exc_info=True)

async def run_guardian_engine():
    """
    Guardian job: Runs check_signal_outcome async over all active signals.
    """
    logger.info("🛡️ Guardian job running: monitoring active signals for outcomes...")
    db = SessionLocal()
    try:
        active_signals = db.query(ActiveSignal).filter(ActiveSignal.is_active == True).all()
        tasks = [check_signal_outcome(db, sig) for sig in active_signals]
        if tasks:
            await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Guardian engine error: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_guardian_engine())
    
