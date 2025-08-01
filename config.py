# filename: config.py
# ==============================================================================
# مرکزی کنفیگریشن فائل برائے ScalpMaster AI (ڈائنامک روسٹر ورژن)
# ==============================================================================

# 📌 API Settings
API_CONFIG = {
    "PRIMARY_TIMEFRAME": "15min",
    "CANDLE_COUNT": 100,
}

# 🪙 منتخب کرنسی/کموڈیٹی جوڑے (ہفتے کے دن و اختتام پر مختلف)
TRADING_PAIRS = {
    "WEEKDAY_PRIMARY": ["XAU/USD", "EUR/USD", "GBP/USD", "USD/CAD"],
    "WEEKDAY_BACKUP": ["AUD/USD", "NZD/USD", "USD/JPY"],
    "WEEKEND_PRIMARY": ["BTC/USD", "ETH/USD"],
    "WEEKEND_BACKUP": ["SOL/USD", "XRP/USD"],
}

# 🎯 حکمتِ عملی کی سیٹنگز
STRATEGY = {
    "SIGNAL_SCORE_THRESHOLD": 40.0,
    "FINAL_CONFIDENCE_THRESHOLD": 70.0,
    "MIN_RISK_REWARD_RATIO": 1.2,
    "MIN_CONFLUENCE_SCORE": 4,
    "LEVEL_SCORING_WEIGHTS": {
        "pivots": 3,
        "swings": 2,
        "fibonacci": 2,
        "psychological": 1
    }
}

# 📊 تکنیکی تجزیہ کے انڈیکیٹر پیرامیٹرز
TECHNICAL_ANALYSIS = {
    "EMA_SHORT_PERIOD": 10,
    "EMA_LONG_PERIOD": 30,
    "RSI_PERIOD": 14,
    "STOCH_K": 14,
    "STOCH_D": 3,
    "SUPERTREND_ATR": 10,
    "SUPERTREND_FACTOR": 3.0,
}

# 📰 اہم نیوز keywords (symbol-based mapping)
HIGH_IMPACT_KEYWORDS = {
    'USD': ['fed', 'fomc', 'cpi', 'nfp', 'unemployment', 'inflation', 'gdp', 'powell'],
    'EUR': ['ecb', 'inflation', 'gdp', 'unemployment', 'lagarde'],
    'GBP': ['boe', 'inflation', 'gdp', 'unemployment', 'bailey'],
    'JPY': ['boj', 'intervention'],
    'BTC': ['bitcoin', 'etf', 'regulation', 'halving'],
    'ETH': ['ethereum', 'merge', 'staking', 'vitalik'],
}
