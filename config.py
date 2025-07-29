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

# --- ٹریڈنگ پیرامیٹرز (★★★ اپ ڈیٹ شدہ ★★★) ---
# اب ہم صرف 14 منتخب جوڑوں پر توجہ مرکوز کریں گے۔
TRADING_PAIRS = {
    "PRIMARY_PAIRS": [
        "XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "USD/CAD", 
        "AUD/USD", "NZD/USD", "USD/CHF", "EUR/JPY", "GBP/JPY"
    ],
    "CRYPTO_PAIRS": ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD"],
}

# --- سگنل جنریشن کی حکمت عملی (★★★ اپ ڈیٹ شدہ ★★★) ---
STRATEGY = {
    "SIGNAL_SCORE_THRESHOLD": 40.0,
    "FINAL_CONFIDENCE_THRESHOLD": 70.0,
    "MIN_RISK_REWARD_RATIO": 1.5,
    # نیا پیرامیٹر: کم از کم اتنی فیصد حرکت پر گہرا تجزیہ کیا جائے گا۔
    # اس سے ہم غیر ضروری API کالز سے بچیں گے۔
    "MIN_CHANGE_PERCENT_FOR_ANALYSIS": 0.10, # مثال: 0.10%
}

# --- فیڈ بیک چیکر ---
FEEDBACK_CHECKER = {
    # ایک کال میں زیادہ سے زیادہ 7 جوڑے بھیجے جا سکتے ہیں (TwelveData کی حد)
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
