# src/agents/loggerai.py

def log_ai_decision(symbol: str, signal: str, confidence: float, reasoning: str):
    """
    Logs the AI's decision, including signal, confidence, and reasoning.
    This can be expanded to log to a file or database in production.
    """
    print(f"[AI Decision Log] Symbol: {symbol}, Signal: {signal}, "
          f"Confidence: {confidence:.2f}, Reasoning: {reasoning}")
