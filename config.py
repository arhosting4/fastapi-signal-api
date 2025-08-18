import logging
from typing import List, Dict

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class AppSettings(BaseSettings):
    PROJECT_NAME: str = "ScalpMaster AI"
    VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"

class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    
    DATABASE_URL: PostgresDsn
    TWELVE_DATA_API_KEYS: str = Field(default="")
    MARKETAUX_API_KEY: str = Field(default="")
    TELEGRAM_BOT_TOKEN: str = Field(default="")
    TELEGRAM_CHAT_ID: str = Field(default="")
    
    # ★★★ نئی سیٹنگ ★★★
    POLYGON_API_KEY: str = Field(default="")
    
    PRIMARY_TIMEFRAME: str = "15min"
    CANDLE_COUNT: int = 100

    @property
    def twelve_data_keys_list(self) -> List[str]:
        if not self.TWELVE_DATA_API_KEYS:
            logger.warning("TWELVE_DATA_API_KEYS ماحولیاتی متغیر سیٹ نہیں ہے یا خالی ہے۔")
            return []
        return [key.strip() for key in self.TWELVE_DATA_API_KEYS.split(',') if key.strip()]

# ... (باقی تمام کلاسز جیسے TradingSettings, StrategySettings, وغیرہ ویسی ہی رہیں گی) ...

class TradingSettings(BaseSettings):
    WEEKDAY_PRIMARY: List[str] = ["XAU/USD", "EUR/USD", "GBP/USD", "USD/CAD"]
    WEEKDAY_BACKUP: List[str] = ["AUD/USD", "NZD/USD", "USD/JPY"]
    WEEKEND_PRIMARY: List[str] = ["BTC/USD", "ETH/USD"]
    WEEKEND_BACKUP: List[str] = ["SOL/USD", "XRP/USD"]

class StrategySettings(BaseSettings):
    SIGNAL_SCORE_THRESHOLD: float = 40.0
    FINAL_CONFIDENCE_THRESHOLD: float = 70.0
    MIN_RISK_REWARD_RATIO: float = 1.2
    MIN_CONFLUENCE_SCORE: int = 4

class TechnicalAnalysisSettings(BaseSettings):
    EMA_SHORT_PERIOD: int = 10
    EMA_LONG_PERIOD: int = 30
    RSI_PERIOD: int = 14
    STOCH_K: int = 14
    STOCH_D: int = 3
    SUPERTREND_ATR: int = 10
    SUPERTREND_FACTOR: float = 3.0
    BBANDS_PERIOD: int = 20
    BBANDS_STD_DEV: int = 2
    BBANDS_SQUEEZE_THRESHOLD: float = 0.8

class NewsSettings(BaseSettings):
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

app_settings = AppSettings()
api_settings = APISettings()
trading_settings = TradingSettings()
strategy_settings = StrategySettings()
tech_settings = TechnicalAnalysisSettings()
news_settings = NewsSettings()

# --- اہم سیٹنگز کی موجودگی کی جانچ ---
if not api_settings.POLYGON_API_KEY:
    logger.warning("POLYGON_API_KEY فراہم نہیں کیا گیا۔ حجم کا قابل اعتماد ڈیٹا حاصل نہیں کیا جائے گا۔")
# ... (باقی جانچیں ویسی ہی رہیں گی) ...
