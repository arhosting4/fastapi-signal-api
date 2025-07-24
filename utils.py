import os
import time
import logging
import httpx
from typing import List, Optional, Dict
from tenacity import retry, stop_after_attempt, wait_fixed, before_sleep_log

logging.basicConfig(level=logging.INFO, format=\'%(asctime)s - %(levelname)s - %(message)s\')
RETRY_LOG = logging.getLogger(__name__)

async def fetch_twelve_data_ohlc(symbol: str, timeframe: str, output_size: int = 100) -> Optional[Dict]:
    logging.warning(f"Using mocked data for {symbol}-{timeframe}. Please provide TWELVE_DATA_API_KEYS for real data.")
    # Mock OHLC data for testing purposes
    return {
        \'close\': [1.0, 1.0001, 1.0002, 1.0003, 1.0004, 1.0005, 1.0006, 1.0007, 1.0008, 1.0009],
        \'open\': [1.0, 1.0001, 1.0002, 1.0003, 1.0004, 1.0005, 1.0006, 1.0007, 1.0008, 1.0009],
        \'high\': [1.001, 1.0011, 1.0012, 1.0013, 1.0014, 1.0015, 1.0016, 1.0017, 1.0018, 1.0019],
        \'low\': [0.999, 0.9991, 0.9992, 0.9993, 0.9994, 0.9995, 0.9996, 0.9997, 0.9998, 0.9999],
        \'volume\': [100, 110, 120, 130, 140, 150, 160, 170, 180, 190],
        \'ATR\': [0.0005, 0.0005, 0.0005, 0.0005, 0.0005, 0.0005, 0.0005, 0.0005, 0.0005, 0.0005]
    }

def get_available_pairs() -> List[str]:
    """Returns a list of trading pairs to be processed."""
    # This can be expanded to read from a config file or database
    return ["EUR/USD", "XAU/USD", "GBP/USD", "BTC/USD"]
    

def get_current_price_twelve_data(symbol: str) -> Optional[Dict]:
    logging.warning(f"Using mocked current price data for {symbol}. Please provide TWELVE_DATA_API_KEYS for real data.")
    # Mock current price data for testing purposes
    return {"price": 1.0005}

