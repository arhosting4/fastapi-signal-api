import random
from sqlalchemy.orm import Session

# --- Corrected Absolute Import ---
# This tells Python to look inside the 'src' folder, then the 'database' subfolder,
# and find the 'database_crud' module.
from src.database import database_crud as crud

def get_confidence(db: Session, symbol: str, timeframe: str) -> float:
    """
    Estimates the confidence of a signal, incorporating feedback from the database.
    This is a simplified model.
    """
    # Base confidence is a random value to simulate AI variability
    base_confidence = random.uniform(65.0, 85.0)
    
    try:
        # Fetch feedback stats to adjust confidence
        # This part is commented out as get_feedback_stats_from_db is not in the final crud
        # In a future version, you could implement this.
        # feedback_stats = crud.get_feedback_stats_from_db(db, symbol=symbol)
        # if feedback_stats and feedback_stats['total'] > 10:
        #     accuracy = feedback_stats['accuracy']
        #     # Adjust confidence based on historical accuracy
        #     if accuracy > 0.7:
        #         base_confidence += 5.0
        #     elif accuracy < 0.4:
        #         base_confidence -= 10.0
        pass # Placeholder for future logic
    except Exception as e:
        # Log the error if logging is configured in this file
        # For now, we pass silently to not crash the signal generation
        pass

    return min(max(base_confidence, 0.0), 100.0) # Ensure confidence is between 0 and 100
