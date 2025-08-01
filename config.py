# filename: config.py

import logging
from typing import List, Optional

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# لاگنگ کی ترتیب
logger = logging.getLogger(__name__)

class AppSettings(BaseSettings):
    """ایپلیکیشن کی عمومی سیٹنگز۔"""
    PROJECT_NAME: str = "ScalpMaster AI"
    VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"

class APISettings(BaseSettings):
    """
    بیرونی API کیز اور حساس معلومات کے لیے سیٹنگز۔
    یہ pydantic-settings کا استعمال کرتے ہوئے .env فائل یا ماحولیاتی متغیرات سے لوڈ ہوتی ہیں۔
    """
    # ماڈل کو بتائیں کہ .env فائل کو بھی دیکھنا ہے
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # ڈیٹا بیس کا URL
    DATABASE_URL: PostgresDsn

    # ★★★ حل: تمام مطلوبہ فیلڈز کے لیے ایک خالی ڈیفالٹ ویلیو فراہم کریں ★★★
    # اس سے ایپلیکیشن کریش نہیں ہوگی اگر متغیر سیٹ نہ ہو۔
    TWELVE_DATA_API_KEYS: str = Field(default="")
    MARKETAUX_API_KEY: str = Field(default="")
    TELEGRAM_BOT_TOKEN: str = Field(default="")
    TELEGRAM_CHAT_ID: str = Field(default="")

    # یہ ایک پراپرٹی ہے جو API کیز کی سٹرنگ کو ایک فہرست میں تبدیل کرتی ہے
    @property
    def twelve_data_keys_list(self) -> List[str]:
        if not self.TWELVE_DATA_API_KEYS:
            logger.warning("TWELVE_DATA_API_KEYS ماحولیاتی متغیر سیٹ نہیں ہے یا خالی ہے۔")
            return []
        return [key.strip() for key in self.TWELVE_DATA_API_KEYS.split(',') if key.strip()]

class TradingSettings(BaseSettings):
    """ٹریڈنگ جوڑوں کے لیے سیٹنگز۔"""
    WEEKDAY_PRIMARY: List[str] = ["XAU/USD", "EUR/USD", "GBP/USD", "USD/CAD"]
    WEEKDAY_BACKUP: List[str] = ["AUD/USD", "NZD/USD", "USD/JPY"]
    WEEKEND_PRIMARY: List[str] = ["BTC/USD", "ETH/USD"]
    WEEKEND_BACKUP: List[str] = ["SOL/USD", "XRP/USD"]

class StrategySettings(BaseSettings):
    """ٹریڈنگ کی حکمت عملی کے لیے پیرامیٹرز۔"""
    SIGNAL_SCORE_THRESHOLD: float = 40.0
    FINAL_CONFIDENCE_THRESHOLD: float = 70.0
    MIN_RISK_REWARD_RATIO: float = 1.2
    MIN_CONFLUENCE_SCORE: int = 4

# --- سیٹنگز کے نمونے بنانا ---
# یہ نمونے پوری ایپلیکیشن میں استعمال ہوں گے

app_settings = AppSettings()
api_settings = APISettings()
trading_settings = TradingSettings()
strategy_settings = StrategySettings()

# ایپلیکیشن شروع ہونے پر ایک بار چیک کریں
if not api_settings.twelve_data_keys_list:
    logger.critical("کوئی Twelve Data API کلید فراہم نہیں کی گئی۔ شکاری اور نگران انجن کام نہیں کریں گے۔")
if not api_settings.MARKETAUX_API_KEY:
    logger.warning("MARKETAUX_API_KEY فراہم نہیں کیا گیا۔ خبروں کا ماڈیول کام نہیں کرے گا۔")
if not api_settings.TELEGRAM_BOT_TOKEN or not api_settings.TELEGRAM_CHAT_ID:
    logger.warning("ٹیلیگرام کی سیٹنگز فراہم نہیں کی گئیں۔ الرٹس نہیں بھیجے جائیں گے۔")

# LOG_LEVEL="INFO"
