import pandas as pd


def generate_technical_analysis_score(df: pd.DataFrame) -> float:
    """
    Calculate a simple technical analysis score based on moving averages and RSI.
    """
    if df is None or df.empty:
        return 0.0

    score = 0
    try:
        df["MA20"] = df["close"].rolling(window=20).mean()
        df["MA50"] = df["close"].rolling(window=50).mean()

        if df["MA20"].iloc[-1] > df["MA50"].iloc[-1]:
            score += 1
        elif df["MA20"].iloc[-1] < df["MA50"].iloc[-1]:
            score -= 1

        # RSI Calculation
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()

        rs = avg_gain / avg_loss
        df["RSI"] = 100 - (100 / (1 + rs))

        rsi_latest = df["RSI"].iloc[-1]
        if rsi_latest < 30:
            score += 1
        elif rsi_latest > 70:
            score -= 1

    except Exception as e:
        print(f"[ERROR] TA Score calculation failed: {e}")
        return 0.0

    return round(score, 2)


def calculate_tp_sl(entry_price: float, risk_reward_ratio: float = 2.0, stop_loss_pct: float = 0.02) -> dict:
    """
    Calculate take profit (TP) and stop loss (SL) prices based on entry price and risk/reward.
    """
    stop_loss = round(entry_price * (1 - stop_loss_pct), 2)
    take_profit = round(entry_price + (entry_price - stop_loss) * risk_reward_ratio, 2)
    return {
        "take_profit": take_profit,
        "stop_loss": stop_loss
    }
