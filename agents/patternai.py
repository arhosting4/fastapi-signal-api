# agents/patternai.py

def detect_pattern(candles: list) -> str:
    """
    Very basic pattern recognition (placeholder).
    Add more logic later for advanced patterns.
    """
    try:
        if len(candles) < 3:
            return "no-pattern"

        last = float(candles[0]['close'])
        mid = float(candles[1]['close'])
        first = float(candles[2]['close'])

        if last > mid > first:
            return "up-trend"
        elif last < mid < first:
            return "down-trend"
        else:
            return "sideways"
    except Exception:
        return "error"
