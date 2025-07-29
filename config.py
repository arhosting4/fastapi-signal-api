# filename: config.py

# ==============================================================================
# مرکزی کنفیگریشن فائل برائے ScalpMaster AI
# تمام اہم پیرامیٹرز یہاں مرکزی حیثیت رکھتے ہیں۔
# ==============================================================================

# --- API کنفیگریشن ---
API_CONFIG = {
    "PRIMARY_TIMEFRAME": "15min",
    "CANDLE_COUNT": 100,
}

# --- ٹریڈنگ پیرامیٹرز ---
TRADING_PAIRS = {
    "PRIORITY_PAIRS_WEEKDAY": ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"],
    "SECONDARY_PAIRS_WEEKDAY": [
        "AUD/USD", "USD/JPY", "USD/CAD", "NZD/USD", "USD/CHF", 
        "EUR/JPY", "GBP/JPY", "ETH/USD"
    ],
    "CRYPTO_PAIRS_WEEKEND": ["BTC/USD", "ETH/USD", "SOL/USD"],
    "HUNT_LIST_SIZE": 4,
}

# --- سگنل جنریشن کی حکمت عملی ---
STRATEGY = {
    "SIGNAL_SCORE_THRESHOLD": 40.0,
    "FINAL_CONFIDENCE_THRESHOLD": 70.0,
    "MIN_RISK_REWARD_RATIO": 1.5,
}

# --- سگنل کی حد بندی ---
SIGNAL_LIMITS = {
    "MAX_FOREX_SIGNALS": 4,
    "MAX_CRYPTO_SIGNALS": 2,
}

# --- فیڈ بیک چیکر ---
FEEDBACK_CHECKER = {
    "MAX_PAIRS_PER_CALL": 8,
}

# --- تکنیکی تجزیہ کے پیرامیٹرز ---
TECHNICAL_ANALYSIS = {
    "EMA_SHORT_PERIOD": 10,
    "EMA_LONG_PERIOD": 30,
    "RSI_PERIOD": 14,
    "STOCH_K": 14,
    "STOCH_D": 3,
    "SUPERTREND_ATR": 10,
    "SUPERTREND_FACTOR": 3.0,
}

# --- خبروں کے لیے مطلوبہ الفاظ ---
HIGH_IMPACT_KEYWORDS = {
    'USD': ['fed', 'fomc', 'cpi', 'nfp', 'unemployment', 'inflation', 'gdp', 'powell'],
    'EUR': ['ecb', 'inflation', 'gdp', 'unemployment', 'lagarde'],
    'GBP': ['boe', 'inflation', 'gdp', 'unemployment', 'bailey'],
    'XAU': ['war', 'crisis', 'geopolitical', 'fed', 'inflation'],
    'BTC': ['sec', 'regulation', 'etf', 'crypto ban', 'halving']
}
