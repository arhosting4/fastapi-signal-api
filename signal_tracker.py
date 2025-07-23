import logging
from typing import List, Dict, Any
from src.database.models import LiveSignal
from src.database.models import SessionLocal

logger = logging.getLogger(__name__)

def get_all_signals() -> List[Dict[str, Any]]:
    """
    Fetch all currently active trade signals from the LiveSignal table.
    """
    try:
        db = SessionLocal()
        signals = db.query(LiveSignal).filter(LiveSignal.active == True).all()
        return [signal.to_dict() for signal in signals] if signals else []
    except Exception as e:
        logger.error(f"Error retrieving live signals: {e}")
        return []
    finally:
        db.close()
