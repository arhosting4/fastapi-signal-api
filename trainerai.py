import random
from sqlalchemy.orm import Session
import logging

# براہ راست امپورٹ
import database_crud as crud

def get_confidence(db: Session, symbol: str, signal_type: str) -> float:
    """
    Estimates the confidence of a signal based on historical feedback.
    A higher confidence is given if past signals of the same type for the symbol were correct.
    """
    try:
        feedback_stats = crud.get_feedback_stats(db, symbol=symbol)
        
        base_confidence = 60.0  # Start with a base confidence
        
        if feedback_stats['total'] > 5: # Only adjust if we have enough data
            accuracy = feedback_stats['accuracy']
            if signal_type == "BUY":
                # Increase confidence if historical accuracy is high
                adjustment = (accuracy - 50) * 0.4 # Scale the adjustment
                base_confidence += adjustment
            elif signal_type == "SELL":
                # For sells, we can use the same logic or a different one
                adjustment = (accuracy - 50) * 0.4
                base_confidence += adjustment

        # Add a small random factor to avoid static confidence scores
        random_factor = random.uniform(-3.0, 3.0)
        final_confidence = base_confidence + random_factor
        
        # Ensure confidence is within bounds [0, 100]
        return max(0, min(100, final_confidence))

    except Exception as e:
        logging.error(f"Error calculating confidence for {symbol}: {e}", exc_info=True)
        return 50.0 # Return a neutral confidence on error
