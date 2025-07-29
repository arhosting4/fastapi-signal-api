# filename: config.py

# ==============================================================================
# مرکزی کنفیگریشن فائل (Central Configuration File)
# اس فائل میں پروجیکٹ کی تمام اہم سیٹنگز اور پیرامیٹرز موجود ہیں۔
# ==============================================================================

# --- سگنل ہنٹنگ اور رسک مینجمنٹ ---
HUNTING_SETTINGS = {
    "MAX_FOREX_SIGNALS": 4,  # ایک وقت میں زیادہ سے زیادہ فعال فاریکس سگنلز
    "MAX_CRYPTO_SIGNALS": 2, # ایک وقت میں زیادہ سے زیادہ فعال کرپٹو سگنلز
    "FINAL_CONFIDENCE_THRESHOLD": 70.0, # سگنل بنانے کے لیے کم از کم اعتماد کا اسکور
    "MIN_RISK_REWARD_RATIO": 1.5, # کم از کم قابل قبول رسک/ریوارڈ تناسب
}

# --- تکنیکی تجزیہ کے پیرامیٹرز (StrategyBot) ---
TECHNICAL_ANALYSIS = {
    "EMA_SHORT_PERIOD": 10,
    "EMA_LONG_PERIOD": 30,
    "RSI_PERIOD": 14,
    "STOCH_K": 14,
    "STOCH_D": 3,
    "SUPERTREND_ATR": 10,
    "SUPERTREND_FACTOR": 3.0,
    "SIGNAL_SCORE_THRESHOLD": 40.0, # بنیادی سگنل (buy/sell) پیدا کرنے کے لیے تکنیکی اسکور کی حد
}

# --- ٹریڈنگ جوڑوں کی فہرستیں (utils.py) ---
TRADING_PAIRS = {
    "PRIORITY_PAIRS_WEEKDAY": ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"],
    "SECONDARY_PAIRS_WEEKDAY": [
        "AUD/USD", "USD/JPY", "USD/CAD", "NZD/USD", "USD/CHF",
        "EUR/JPY", "GBP/JPY", "ETH/USD"
    ],
    "CRYPTO_PAIRS_WEEKEND": ["BTC/USD", "ETH/USD", "SOL/USD"],
    "HUNT_LIST_SIZE": 4, # شکار کی فہرست میں کتنے جوڑے ہونے چاہئیں
}

# --- API اور ڈیٹا سورس کی کنفیگریشن ---
API_CONFIG = {
    "PRIMARY_TIMEFRAME": "15min",
    "CANDLE_COUNT": 100,
}

# --- فیڈ بیک چیکر کی کنفیگریشن ---
FEEDBACK_CHECKER = {
    "MAX_PAIRS_PER_CALL": 8, # ایک وقت میں کتنے جوڑوں کی قیمتیں چیک کرنی ہیں
}

