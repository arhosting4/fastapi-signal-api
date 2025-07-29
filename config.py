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

# --- سگنل جنریشن کی حکمت عملی (اپ ڈیٹ شدہ) ---
STRATEGY = {
    # --- بنیادی سگنل فلٹر ---
    "SIGNAL_SCORE_THRESHOLD": 50.0,  # تکنیکی اسکور کی حد کو 40 سے بڑھا کر 50 کر دیا گیا
    "FINAL_CONFIDENCE_THRESHOLD": 75.0, # اعتماد کی حد کو 70 سے بڑھا کر 75 کر دیا گیا

    # --- "A-Grade" ٹریڈ کے لیے سخت قوانین ---
    "MIN_RISK_REWARD_RATIO": 2.5,  # رسک/ریوارڈ تناسب کو 2.0 سے بڑھا کر 2.5 کر دیا گیا
    "MIN_CONFLUENCE_SCORE": 7,     # ★★★ نیا قانون: TP/SL لیول کا کم از کم کنفلونس اسکور 7 ہونا چاہیے
    "REQUIRE_PATTERN_CONFIRMATION": True, # ★★★ نیا قانون: ٹریڈ کے لیے ایک موافق کینڈل اسٹک پیٹرن لازمی ہے
}

# --- فیڈ بیک چیکر ---
FEEDBACK_CHECKER = {
    "MAX_PAIRS_PER_CALL": 7,
    "PRIORITY_SYMBOLS": ["XAU/USD", "BTC/USD", "ETH/USD", "GBP/JPY"]
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
