# src/agents/strategybot.py

def apply_strategy_layers(symbol: str, candles: list) -> dict:
    """
    Apply technical and AI-based strategies to extract signals.
    """
    try:
        last_close = float(candles[-1]['close'])
        prev_close = float(candles[-2]['close'])

        signal = "buy" if last_close > prev_close else "sell"
        confidence = round(abs(last_close - prev_close) / last_close, 4)

        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "strategy_used": "Simple Momentum"
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "signal": "error",
            "confidence": 0.0,
            "strategy_used": "error",
            "error": str(e)
        }
