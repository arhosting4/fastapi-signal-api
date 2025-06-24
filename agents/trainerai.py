# src/agents/trainerai.py

def log_signal_feedback(symbol: str, signal: str, success: bool):
    """
    Logs the outcome of a signal. In a real system, this could feed an AI trainer.
    """
    feedback = "✔️ SUCCESS" if success else "❌ FAIL"
    print(f"[FEEDBACK] Signal for {symbol.upper()} = {signal.upper()} ➜ {feedback}")
