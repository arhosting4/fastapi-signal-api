# filename: config.py

# ==============================================================================
# مرکزی کنفیگریشن فائل برائے ScalpMaster AI (ڈبل انجن ورژن)
# ==============================================================================

# --- API کنفیگریشن ---
API_CONFIG = {
    "PRIMARY_TIMEFRAME": "15min",
    "CANDLE_COUNT": 100,
}

# --- ٹریڈنگ اور نگرانی کے پیرامیٹرز ---
TRADING_PAIRS = {
    # یہ 14 جوڑے ہیں جن کی نگرانی ہمارا "نگران انجن" ہر 2 منٹ بعد کرے گا۔
    # "شکاری انجن" ان ہی جوڑوں میں سے بہترین مواقع تلاش کرے گا۔
    "PAIRS_TO_MONITOR": [
        "XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "USD/CAD", "AUD/USD", 
        "NZD/USD", "USD/CHF", "EUR/JPY", "GBP/JPY", "BTC/USD", "ETH/USD", 
        "SOL/USD", "XRP/USD"
    ],
}

# --- سگنل جنریشن کی حکمت عملی ---
STRATEGY = {
    "SIGNAL_SCORE_THRESHOLD": 40.0,
    "FINAL_CONFIDENCE_THRESHOLD": 70.0,
    "MIN_RISK_REWARD_RATIO": 1.5,
    "MIN_CONFLUENCE_SCORE": 4,
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

# ★★★ نیا کوڈ یہاں سے شروع ہو رہا ہے ★★★
# --- لیول اسکورنگ کے لیے وزن ---
# یہ وزن find_optimal_tp_sl فنکشن میں استعمال ہوں گے تاکہ بہترین TP/SL لیولز کا تعین کیا جا سکے۔
# زیادہ وزن والے لیول زیادہ اہم سمجھے جاتے ہیں۔
LEVEL_SCORING_WEIGHTS = {
    "PIVOT": 4,          # یومیہ پیوٹ پوائنٹس (R1, S1, R2, S2)
    "SWING": 3,          # 15-منٹ کے سوئنگ ہائی/لو
    "FIBONACCI": 2,      # اہم فبوناکی ریٹریسمنٹ لیولز
    "PSYCHOLOGICAL": 1   # نفسیاتی (گول نمبر) لیولز
}
# ★★★ نیا کوڈ یہاں ختم ہو رہا ہے ★★★
