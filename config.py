# filename: config.py
"""
مرکزی کنفیگریشن فائل
تمام اہم پیرامیٹرز اور سیٹنگز یہاں محفوظ ہیں
"""

# Signal Hunting Configuration
PRIMARY_TIMEFRAME = "15min"
CANDLE_COUNT = 100
AVAILABLE_PAIRS_WEEKDAY = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
AVAILABLE_PAIRS_WEEKEND = ["BTC/USD"]

# Fusion Engine & Confidence Thresholds
SCOUTING_THRESHOLD = 45.0
CONFLUENCE_BONUS = 15.0
FINAL_CONFIDENCE_THRESHOLD = 60.0
MAX_ACTIVE_SIGNALS = 5

# Feedback Checker Configuration
EXPIRY_MINUTES = 15

# Risk Guardian Configuration
ATR_LENGTH = 14
ATR_MULTIPLIER_HIGH_RISK = 1.5
ATR_MULTIPLIER_MODERATE_RISK = 1.8
ATR_MULTIPLIER_NORMAL_RISK = 2.0

# StrategyBot Configuration
SMA_SHORT_PERIOD = 10
SMA_LONG_PERIOD = 30
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BBANDS_PERIOD = 20
STOCH_K = 14
STOCH_D = 3

# Scheduler Intervals
HUNT_JOB_MINUTES = 5
CHECK_JOB_MINUTES = 1
NEWS_JOB_HOURS = 4

# News Analysis
HIGH_IMPACT_KEYWORDS = ['rate', 'inflation', 'cpi', 'fed', 'ecb', 'boj', 'unemployment', 'war', 'crisis', 'nfp']
