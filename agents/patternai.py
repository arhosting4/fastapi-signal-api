# agents/patternai.py

def detect_candle_pattern(candles: list) -> str:
    """
    Detect basic candlestick patterns using the last 3 candles.
    """
    if len(candles) < 3:
        return "none"

    try:
        c1 = float(candles[-3]['close'])
        o1 = float(candles[-3]['open'])
        c2 = float(candles[-2]['close'])
        o2 = float(candles[-2]['open'])
        c3 = float(candles[-1]['close'])
        o3 = float(candles[-1]['open'])

        # Bullish Three White Soldiers
        if c1 > o1 and c2 > o2 and c3 > o3 and c3 > c2 > c1:
            return "three_white_soldiers"

        # Bearish Three Black Crows
        elif c1 < o1 and c2 < o2 and c3 < o3 and c3 < c2 < c1:
            return "three_black_crows"

        # Doji
        elif abs(o3 - c3) < 0.0001:
            return "doji"

        # Bullish Engulfing
        elif o2 > c2 and c3 > o3 and c3 > o2 and o3 < c2:
            return "bullish_engulfing"

        # Bearish Engulfing
        elif o2 < c2 and c3 < o3 and c3 < o2 and o3 > c2:
            return "bearish_engulfing"

        else:
            return "none"
    except Exception as e:
        print("Pattern detection error:", e)
        return "error"
