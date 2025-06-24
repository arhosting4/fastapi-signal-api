# src/agents/sentinel.py

def filter_noise_and_score(symbol: str, candles: list) -> float:
    """
    Applies a basic filter to evaluate confidence based on candle consistency.
    Returns a float between 0 and 1.
    """
    try:
        closes = [float(c["close"]) for c in candles]
        if len(closes) < 4:
            return 0.0

        diffs = [abs(closes[i] - closes[i - 1]) for i in range(1, len(closes))]
        avg_diff = sum(diffs) / len(diffs)

        if avg_diff == 0:
            return 0.0

        movement_strength = abs(closes[-1] - closes[0]) / avg_diff

        # Normalize to a confidence level (example logic)
        if movement_strength >= 3:
            return 0.03  # 3%
        elif movement_strength >= 2:
            return 0.02
        elif movement_strength >= 1.5:
            return 0.015
        elif movement_strength >= 1:
            return 0.01
        else:
            return 0.005
    except Exception:
        return 0.0
