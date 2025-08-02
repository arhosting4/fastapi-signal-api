# filename: config.py

# --- API/Engine settings ---
API_CONFIG = {
    "PRIMARY_TIMEFRAME": "15min",         # Main chart timeframe for all OHLC/data fetch
    "CANDLE_COUNT": 100                   # Number of complete candles to analyze (excluding incomplete live bar)
}

# --- Trading Pairs Lists ---
TRADING_PAIRS = {
    "WEEKDAY_PRIMARY": [
        "BTC/USD", "ETH/USD", "EUR/USD", "GOLD/USD"
        # اپنی ضرورت کے مطابق مزید جوڑیاں شامل کریں
    ],
    "WEEKDAY_BACKUP": [
        "ADA/USD", "DOGE/USD"
        # اگر primary دن میں پوری نہ جگہ تو یہاں سے backup لے
    ],
    "WEEKEND_PRIMARY": [
        "BTC/USD", "ETH/USD"
    ],
    "WEEKEND_BACKUP": [
        "LTC/USD"
    ]
}

# --- Risk/Volatility Thresholds (riskguardian.py) ---
RISK_PARAMS = {
    "ATR_LENGTH": 14,            # ATR lookback length
    "AVG_CLOSE_LENGTH": 20,      # For averaging close
    "VOL_HIGH": 0.005,           # High volatility threshold (% of avg close)
    "VOL_MODERATE": 0.002,       # Moderate volatility threshold
    "ATR_MULT_HIGH": 1.5,
    "ATR_MULT_MODERATE": 1.8,
    "ATR_MULT_NORMAL": 2.0
}

# --- Technical Analysis Parameters (strategybot.py etc) ---
TECHNICAL_ANALYSIS = {
    "EMA_SHORT_PERIOD": 12,
    "EMA_LONG_PERIOD": 26,
    "RSI_PERIOD": 14,
    "STOCH_K": 14,
    "STOCH_D": 3,
    "SUPERTREND_ATR": 10,
    "SUPERTREND_FACTOR": 3
}

# --- News Impact Keywords Grouped By Currency (sentinel.py) ---
HIGH_IMPACT_KEYWORDS = {
    "USD": ["fed", "interest rate", "inflation", "nfp", "cpi", "fomc", "unemployment", "powell"],
    "EUR": ["ecb", "germany", "inflation", "gdp", "draghi"],
    "GBP": ["boe", "bank of england", "uk inflation"],
    "JPY": ["boj", "bank of japan", "yen", "inflation"],
    "XAU": ["gold", "precious metals", "commodity"],
    "BTC": ["bitcoin", "crypto ban", "etf"],
    # مزید symbols/currencies add کرنے کے لیے یہی فارمیٹ برقرار رکھیں
}
