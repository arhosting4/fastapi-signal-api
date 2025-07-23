from typing import Dict, Any, Optional
# --- Corrected Absolute Import ---
import trainerai 
from database_config import SessionLocal

def fuse_signals(core_signal: Dict, patterns: Dict, risk: Dict) -> Optional[Dict[str, Any]]:
    """
    Fuses signals from various AI modules into a single, confident signal.
    """
    if not core_signal or core_signal['signal'] == 'hold':
        return None

    confidence = 0.0
    reasons = []

    # Base confidence from core signal
    confidence += core_signal.get('confidence', 0)
    reasons.append(core_signal.get('reason', 'Core signal triggered'))

    # Adjust based on patterns
    if patterns and patterns['pattern_name'] != 'No Pattern':
        confidence += patterns.get('score', 0)
        reasons.append(f"Pattern: {patterns['pattern_name']}")

    # Adjust based on risk
    if risk:
        if risk['status'] == 'High':
            confidence *= 0.7 # Reduce confidence by 30% in high-risk
            reasons.append("High market risk detected")
        elif risk['status'] == 'Moderate':
            confidence *= 0.9 # Reduce confidence by 10% in moderate-risk
            reasons.append("Moderate market risk")

    # Use trainerai to get a final confidence score based on historical data (placeholder)
    db_session = SessionLocal()
    try:
        # This call can be made more sophisticated
        historical_confidence = trainerai.get_confidence(db_session, "XAU/USD", "15min")
        # Average the calculated confidence with historical confidence
        confidence = (confidence + historical_confidence) / 2
    finally:
        db_session.close()

    final_signal = {
        "signal": core_signal['signal'],
        "confidence": min(confidence, 100.0), # Cap confidence at 100
        "reason": ". ".join(reasons)
    }
    
    return final_signal
