# filename: config.py
# ==============================================================================
# مرکزی کنفیگریشن فائل برائے ScalpMaster AI (ڈائنامک روسٹر ورژن)
# ==============================================================================
API_CONFIG = {
    "PRIMARY_TIMEFRAME": "15min",
    "CANDLE_COUNT": 100,
}
TRADING_PAIRS = {
    "WEEKDAY_PRIMARY": ["XAU/USD", "EUR/USD", "GBP/USD", "USD/CAD"],
    "WEEKDAY_BACKUP": ["AUD/USD", "NZD/USD", "USD/JPY"],
    "WEEKEND_PRIMARY": ["BTC/USD", "ETH/USD"],
    "WEEKEND_BACKUP": ["SOL/USD", "XRP/USD"],
}
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
TECHNICAL_ANALYSIS = {
    "EMA_SHORT_PERIOD": 10,
    "EMA_LONG_PERIOD": 30,
    "RSI_PERIOD": 14,
    "STOCH_K": 14,
    "STOCH_D": 3,
    "SUPERTREND_ATR": 10,
    "SUPERTREND_FACTOR": 3.0,
}
HIGH_IMPACT_KEYWORDS = {
    'USD': ['fed', 'fomc', 'cpi', 'nfp', 'unemployment', 'inflation', 'gdp', 'powell'],
    'EUR': ['ecb', 'inflation', 'gdp', 'unemployment', 'lagarde'],
    'GBP': ['boe', 'inflation', 'gdp', 'unemployment', 'bailey'],
    'JPY': ['boj', 'intervention'],
    'CAD': ['boc'],
    'AUD': ['rba'],
    'NZD': ['rbnz'],
    'XAU': ['war', 'crisis', 'geopolitical', 'fed', 'inflation'],
    'BTC': ['sec', 'regulation', 'etf', 'crypto ban', 'halving']
}
