import random
from sqlalchemy.orm import Session

# --- Corrected Absolute Import ---
from src.database import database_crud as crud

def get_confidence(db: Session, symbol: str, timeframe: str) -> float:
    """
    Estimates the confidence of a signal.
    In a future version, this could use the db session to fetch historical accuracy.
    """
    base_confidence = random.uniform(65.0, 85.0)
    return min(max(base_confidence, 0.0), 100.0)
