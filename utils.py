# filename: utils.py

import os
import httpx
import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from key_manager import key_manager
from schemas import TwelveDataTimeSeries, Candle

logger = logging.getLogger(__name__)

# ==============================================================================
# ★★★ نیا اسٹریٹجک پیئر مینجمنٹ سسٹم ★★★
# ==============================================================================

# بنیادی جوڑے جنہیں ہمیشہ ترجیح دی جائے گی
PRIORITY_PAIRS_WEEKDAY = ["XAU/USD", "EUR/USD", "GBP/USD", "BTC/USD"]
# دیگر جوڑے جو بیک اپ کے طور پر کام کریں گے
SECONDARY_PAIRS_WEEKDAY = [
    "AUD/USD", "USD/JPY", "USD/CAD", "NZD/USD", "USD/CHF", 
    "EUR/JPY", "GBP/JPY", "ETH/USD"
]
# ہفتے کے آخر کے لیے جوڑے
CRYPTO_PAIRS_WEEKEND = ["BTC/USD", "ETH/USD", "SOL/USD"]

# مارکیٹ کی حالت کو پڑھنے کے لیے فائل کا نام
MARKET_STATE_FILE = "market_state.json"
# شکار کی فہرست میں کتنے جوڑے ہونے چاہئیں
HUNT_LIST_SIZE = 4 

def get_all_pairs() -> List[str]:
    """
    ہفتے کے دن کی بنیاد پر تمام ممکنہ جوڑوں کی فہرست واپس کرتا ہے۔
    """
    today = datetime.utcnow().weekday()
    if today >= 5: # ہفتہ (5) اور اتوار (6)
        return CRYPTO_PAIRS_WEEKEND
    return PRIORITY_PAIRS_WEEKDAY + SECONDARY_PAIRS_WEEKDAY

# ==============================================================================
# ★★★ نیا، ذہین، اور حتمی "شکار کے لیے جوڑے حاصل کرنے والا" فنکشن ★★★
# ==============================================================================
def get_pairs_to_hunt(active_symbols: List[str]) -> List[str]:
    """
    ایک ذہین شکار کی فہرست تیار کرتا ہے جو ترجیحات اور مارکیٹ کی حرکت پر مبنی ہوتی ہے۔
    """
    logger.info(f"شکار کی فہرست تیار کی جا رہی ہے۔ فعال سگنلز: {active_symbols}")
    
    # 1. مارکیٹ کی حالت کو کیش فائل سے پڑھیں
    try:
        with open(MARKET_STATE_FILE, 'r') as f:
            market_state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("مارکیٹ اسٹیٹ فائل نہیں ملی یا خالی ہے۔ حرکت کی بنیاد پر ترجیح نہیں دی جا سکتی۔")
        market_state = {}

    # 2. ہر جوڑے کی حرکت (volatility) کا حساب لگائیں
    volatility_map = {}
    for symbol, data in market_state.items():
        if 'current_price' in data and 'previous_price' in data:
            try:
                # قیمت میں فیصد تبدیلی
                change_pct = (abs(data['current_price'] - data['previous_price']) / data['previous_price']) * 100
                volatility_map[symbol] = change_pct
            except (TypeError, ZeroDivisionError):
                continue
    
    # حرکت کی بنیاد پر جوڑوں کو ترتیب دیں (سب سے زیادہ حرکت والے پہلے)
    sorted_by_volatility = sorted(volatility_map.keys(), key=lambda s: volatility_map.get(s, 0), reverse=True)
    
    # 3. شکار کی فہرست تیار کریں
    hunt_list = []
    
    # سطح 1: ترجیحی جوڑوں کو چیک کریں جو فارغ ہیں
    today = datetime.utcnow().weekday()
    priority_pairs = PRIORITY_PAIRS_WEEKDAY if today < 5 else CRYPTO_PAIRS_WEEKEND
    
    for pair in priority_pairs:
        if pair not in active_symbols:
            hunt_list.append(pair)
    
    logger.info(f"ترجیحی جوڑوں کو شامل کرنے کے بعد شکار کی فہرست: {hunt_list}")

    # سطح 2: اگر فہرست میں جگہ ہے، تو سب سے زیادہ حرکت والے ثانوی جوڑوں کو شامل کریں
    if len(hunt_list) < HUNT_LIST_SIZE:
        for pair in sorted_by_volatility:
            if len(hunt_list) >= HUNT_LIST_SIZE: break
            # اس بات کو یقینی بنائیں کہ یہ جوڑا پہلے سے فہرست میں یا فعال سگنلز میں نہیں ہے
            if pair not in hunt_list and pair not in active_symbols and pair in get_all_pairs():
                hunt_list.append(pair)
    
    logger.info(f"حرکت والے جوڑوں کو شامل کرنے کے بعد شکار کی فہرست: {hunt_list}")

    # سطح 3: اگر فہرست اب بھی خالی ہے، تو باقی تمام فارغ جوڑوں میں سے شامل کریں
    if len(hunt_list) < HUNT_LIST_SIZE:
        all_available_pairs = get_all_pairs()
        for pair in all_available_pairs:
            if len(hunt_list) >= HUNT_LIST_SIZE: break
            if pair not in hunt_list and pair not in active_symbols:
                hunt_list.append(pair)

    final_hunt_list = hunt_list[:HUNT_LIST_SIZE]
    logger.info(f"حتمی شکار کی فہرست ({len(final_hunt_list)} جوڑے): {final_hunt_list}")
    return final_hunt_list


# ... (باقی تمام فنکشنز جیسے fetch_twelve_data_ohlc اور get_current_prices_from_api ویسے ہی رہیں گے) ...

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    # ... (کوئی تبدیلی نہیں) ...
    pass

async def get_current_prices_from_api(symbols: List[str]) -> Optional[Dict[str, float]]:
    # ... (کوئی تبدیلی نہیں) ...
    pass
    
