# filename: config.py

# ==============================================================================
# مرکزی کنفیگریشن فائل برائے ScalpMaster AI (ڈائنامک روسٹر ورژن)
# ==============================================================================

# --- API کنفیگریشن ---
API_CONFIG = {
    "PRIMARY_TIMEFRAME": "15min",
    "CANDLE_COUNT": 100,
}

# --- ٹریڈنگ اور نگرانی کے پیرامیٹرز (متحرک روسٹر) ---
TRADING_PAIRS = {
    # بنیادی جوڑے جنہیں ہمیشہ ترجیح دی جائے گی
    "WEEKDAY_PRIMARY": ["XAU/USD", "EUR/USD", "GBP/USD", "USD/CAD"],
    # بیک اپ جوڑے جو بنیادی جوڑوں کے مصروف ہونے پر استعمال ہوں گے
    "WEEKDAY_BACKUP": ["AUD/USD", "NZD/USD", "USD/JPY"],
    
    # ہفتے کے آخر کے لیے بنیادی کرپٹو جوڑے
    "WEEKEND_PRIMARY": ["BTC/USD", "ETH/USD"],
    # ہفتے کے آخر کے لیے بیک اپ کرپٹو جوڑے
    "WEEKEND_BACKUP": ["SOL/USD", "XRP/USD"],
}

# --- سگنل جنریشن کی حکمت عملی ---
STRATEGY = {
    "SIGNAL_SCORE_THRESHOLD": 40.0,
    "FINAL_CONFIDENCE_THRESHOLD": 70.0,
    "MIN_RISK_REWARD_RATIO": 1.5,
    "MIN_CONFLUENCE_SCORE": 4,
    "CONFLUENCE_WEIGHTS": {
        "pivots": 3,
        "swings": 2,
        "fibonacci": 2,
        "psychological": 1
    }
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
    'JPY': ['boj', 'intervention'],
    'CAD': ['boc'],
    'AUD': ['rba'],
    'NZD': ['rbnz'],
    'XAU': ['war', 'crisis', 'geopolitical', 'fed', 'inflation'],
    'BTC': ['sec', 'regulation', 'etf', 'crypto ban', 'halving']
}
