# filename: config.py

import os
from typing import List, Dict, Set
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# .env فائل کو لوڈ کریں تاکہ pydantic_settings اسے پڑھ سکے
load_dotenv()

class APISettings(BaseSettings):
    """
    بیرونی APIs اور بنیادی ایپلیکیشن کی سیٹنگز۔
    یہ .env فائل سے اقدار لوڈ کرے گی۔
    """
    # ماڈل کنفیگریشن: .env فائل کا نام اور کیس کی عدم حساسیت
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # ڈیٹا بیس کنکشن
    DATABASE_URL: str = "sqlite:///./signals.db"

    # Twelve Data API کیز (کوما سے الگ شدہ)
    TWELVE_DATA_API_KEYS: str
    
    # MarketAux API کی
    MARKETAUX_API_KEY: str

    # ٹیلیگرام بوٹ کی تفصیلات
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str

    # لاگنگ کی سطح
    LOG_LEVEL: str = "INFO"

    @property
    def twelve_data_keys_list(self) -> List[str]:
        """کوما سے الگ کی گئی API کیز کی سٹرنگ کو ایک فہرست میں تبدیل کرتا ہے۔"""
        if not self.TWELVE_DATA_API_KEYS:
            return []
        return [key.strip() for key in self.TWELVE_DATA_API_KEYS.split(',') if key.strip()]

class StrategySettings(BaseSettings):
    """
    ٹریڈنگ کی حکمت عملی اور تکنیکی تجزیے کے لیے پیرامیٹرز۔
    یہ اقدار ہارڈ کوڈڈ ہیں کیونکہ یہ حکمت عملی کا بنیادی حصہ ہیں،
    لیکن انہیں .env سے بھی اوور رائڈ کیا جا سکتا ہے۔
    """
    model_config = SettingsConfigDict(extra='ignore')

    # سگنل بنانے کے لیے کم از کم اسکور
    SIGNAL_SCORE_THRESHOLD: float = 40.0
    # حتمی سگنل جاری کرنے کے لیے کم از کم اعتماد
    FINAL_CONFIDENCE_THRESHOLD: float = 70.0
    # کم از کم رسک/ریوارڈ کا تناسب
    MIN_RISK_REWARD_RATIO: float = 1.2
    # کنفلونس اسکور کی کم از کم حد
    MIN_CONFLUENCE_SCORE: int = 4

class TradingSettings(BaseSettings):
    """
    ٹریڈنگ کے جوڑوں اور ٹائم فریم کے لیے سیٹنگز۔
    """
    PRIMARY_TIMEFRAME: str = "15min"
    CANDLE_COUNT: int = 100
    
    WEEKDAY_PRIMARY: List[str] = ["XAU/USD", "EUR/USD", "GBP/USD", "USD/CAD"]
    WEEKDAY_BACKUP: List[str] = ["AUD/USD", "NZD/USD", "USD/JPY"]
    WEEKEND_PRIMARY: List[str] = ["BTC/USD", "ETH/USD"]
    WEEKEND_BACKUP: List[str] = ["SOL/USD", "XRP/USD"]

class TechnicalAnalysisSettings(BaseSettings):
    """
    تکنیکی انڈیکیٹرز کے لیے پیرامیٹرز۔
    """
    EMA_SHORT_PERIOD: int = 10
    EMA_LONG_PERIOD: int = 30
    RSI_PERIOD: int = 14
    STOCH_K: int = 14
    STOCH_D: int = 3
    SUPERTREND_ATR: int = 10
    SUPERTREND_FACTOR: float = 3.0

class NewsSettings(BaseSettings):
    """
    خبروں کے تجزیے کے لیے مطلوبہ الفاظ۔
    """
    HIGH_IMPACT_KEYWORDS: Dict[str, List[str]] = {
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

# تمام سیٹنگز کو ایک جگہ پر قابلِ رسائی بنانے کے لیے سنگلٹن آبجیکٹس
api_settings = APISettings()
strategy_settings = StrategySettings()
trading_settings = TradingSettings()
tech_settings = TechnicalAnalysisSettings()
news_settings = NewsSettings()

# ایک .env.example فائل بھی بنائی جانی چاہیے تاکہ صارف کو معلوم ہو کہ کون سے متغیرات سیٹ کرنے ہیں:
# DATABASE_URL="postgresql://user:password@host:port/database"
# TWELVE_DATA_API_KEYS="key1,key2,key3,key4,key5,key6,key7,key8,key9"
# MARKETAUX_API_KEY="your_marketaux_key"
# TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
# TELEGRAM_CHAT_ID="your_telegram_chat_id"
# LOG_LEVEL="INFO"
