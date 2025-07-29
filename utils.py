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
from config import TRADING_PAIRS, API_CONFIG

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے متغیرات ---
PRIORITY_PAIRS_WEEKDAY = TRADING_PAIRS["PRIORITY_PAIRS_WEEKDAY"]
SECONDARY_PAIRS_WEEKDAY = TRADING_PAIRS["SECONDARY_PAIRS_WEEKDAY"]
CRYPTO_PAIRS_WEEKEND = TRADING_PAIRS["CRYPTO_PAIRS_WEEKEND"]
HUNT_LIST_SIZE = TRADING_PAIRS["HUNT_LIST_SIZE"]
PRIMARY_TIMEFRAME = API_CONFIG["PRIMARY_TIMEFRAME"]
CANDLE_COUNT = API_CONFIG["CANDLE_COUNT"]

MARKET_STATE_FILE = "market_state.json"

def get_all_pairs() -> List[str]:
    """
    ہفتے کے دن کی بنیاد پر تمام ممکنہ جوڑوں کی فہرست واپس کرتا ہے۔
    """
    today = datetime.utcnow().weekday()
    if today >= 5: # ہفتہ (5) اور اتوار (6)
        return CRYPTO_PAIRS_WEEKEND
    return PRIORITY_PAIRS_WEEKDAY + SECONDARY_PAIRS_WEEKDAY

def get_priority_pairs() -> List[str]:
    """
    ہفتے کے دن کی بنیاد پر صرف ترجیحی جوڑوں کی فہرست واپس کرتا ہے۔
    """
    today = datetime.utcnow().weekday()
    if today >= 5: # ہفتہ اور اتوار
        return CRYPTO_PAIRS_WEEKEND
    return PRIORITY_PAIRS_WEEKDAY

# ★★★ مکمل طور پر نیا اور درست فنکشن ★★★
def get_pairs_to_hunt(active_symbols: List[str]) -> List[str]:
    """
    ایک ذہین شکار کی فہرست تیار کرتا ہے جو فعال سگنلز کو نظر انداز کرتی ہے
    اور ترجیحات اور مارکیٹ کی حرکت پر مبنی ہوتی ہے۔
    """
    logger.info(f"شکار کی فہرست تیار کی جا رہی ہے۔ فعال سگنلز: {active_symbols}")
    
    # 1. تمام ممکنہ جوڑوں کی فہرست حاصل کریں جو فعال نہیں ہیں
    all_possible_pairs = get_all_pairs()
    available_to_hunt = [p for p in all_possible_pairs if p not in active_symbols]
    
    if not available_to_hunt:
        logger.info("کوئی بھی جوڑا شکار کے لیے دستیاب نہیں کیونکہ سب کے سگنل فعال ہیں۔")
        return []

    # 2. مارکیٹ کی حرکت کی بنیاد پر دستیاب جوڑوں کو ترتیب دیں
    try:
        with open(MARKET_STATE_FILE, 'r') as f:
            market_state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("مارکیٹ اسٹیٹ فائل نہیں ملی، حرکت کی بنیاد پر ترجیح نہیں دی جا سکتی۔")
        market_state = {}

    volatility_map = {}
    for symbol, data in market_state.items():
        if symbol in available_to_hunt and 'current_price' in data and 'previous_price' in data:
            try:
                change_pct = (abs(data['current_price'] - data['previous_price']) / data['previous_price']) * 100
                volatility_map[symbol] = change_pct
            except (TypeError, ZeroDivisionError):
                continue
    
    sorted_by_volatility = sorted(volatility_map.keys(), key=lambda s: volatility_map.get(s, 0), reverse=True)
    
    # 3. حتمی شکار کی فہرست بنائیں (ترجیحات پہلے)
    hunt_list = []
    priority_pairs = get_priority_pairs()
    
    # ترجیحی جوڑوں کو پہلے شامل کریں (اگر دستیاب ہوں)
    for pair in priority_pairs:
        if pair in available_to_hunt:
            hunt_list.append(pair)
            
    # اگر فہرست ابھی بھی چھوٹی ہے، تو حرکت کی بنیاد پر دیگر جوڑوں کو شامل کریں
    for pair in sorted_by_volatility:
        if len(hunt_list) >= HUNT_LIST_SIZE:
            break
        if pair not in hunt_list and pair in available_to_hunt:
            hunt_list.append(pair)
            
    # اگر فہرست اب بھی چھوٹی ہے، تو باقی دستیاب جوڑوں کو شامل کریں
    for pair in available_to_hunt:
        if len(hunt_list) >= HUNT_LIST_SIZE:
            break
        if pair not in hunt_list:
            hunt_list.append(pair)

    final_hunt_list = hunt_list[:HUNT_LIST_SIZE]
    logger.info(f"حتمی اور درست شکار کی فہرست ({len(final_hunt_list)} جوڑے): {final_hunt_list}")
    return final_hunt_list

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """TwelveData API سے OHLC کینڈلز لاتا ہے۔"""
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning(f"[{symbol}] OHLC کے لیے کوئی API کلید دستیاب نہیں۔")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={PRIMARY_TIMEFRAME}&outputsize={CANDLE_COUNT}&apikey={api_key}"
    logger.info(f"[{symbol}] کے لیے Twelve Data API سے ڈیٹا حاصل کیا جا رہا ہے (کلید: {api_key[:8]}...)")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        
        if response.status_code == 429:
            logger.warning(f"API کلید {api_key[:8]}... کی حد ختم ہو گئی۔ اسے طویل مدت کے لیے محدود کیا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key, daily_limit_exceeded=True)
            await asyncio.sleep(1)
            return await fetch_twelve_data_ohlc(symbol)

        response.raise_for_status()
        data = response.json()
        
        if "values" not in data or data.get("status") != "ok":
            logger.warning(f"[{symbol}] کے لیے Twelve Data API نے خرابی واپس کی: {data.get('message', 'نامعلوم')}")
            return None

        validated_data = TwelveDataTimeSeries.model_validate(data)
        logger.info(f"[{symbol}] کے لیے کامیابی سے {len(validated_data.values)} کینڈلز حاصل کی گئیں۔")
        return validated_data.values[::-1]
            
    except Exception as e:
        logger.error(f"[{symbol}] کے لیے OHLC ڈیٹا حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None

async def get_current_prices_from_api(symbols: List[str]) -> Optional[Dict[str, float]]:
    """
    دی گئی علامتوں کی فہرست کے لیے TwelveData API سے تازہ ترین قیمتیں حاصل کرتا ہے۔
    """
    if not symbols:
        return {}

    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning("قیمتیں حاصل کرنے کے لیے کوئی API کلید دستیاب نہیں۔")
        return None

    symbol_str = ",".join(symbols)
    url = f"https://api.twelvedata.com/price?symbol={symbol_str}&apikey={api_key}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)

        if response.status_code == 429:
            logger.warning(f"API کلید {api_key[:8]}... کی حد ختم ہو گئی۔ اسے طویل مدت کے لیے محدود کیا جا رہا ہے۔")
            key_manager.mark_key_as_limited(api_key, daily_limit_exceeded=True)
            await asyncio.sleep(1)
            return await get_current_prices_from_api(symbols)

        response.raise_for_status()
        data = response.json()

        prices = {}
        if "price" in data and isinstance(data['price'], (int, float, str)):
            prices[symbols[0]] = float(data["price"])
        else:
            for symbol, details in data.items():
                if isinstance(details, dict) and "price" in details:
                    prices[symbol] = float(details["price"])
        
        if prices:
            logger.info(f"کامیابی سے {len(prices)} قیمتیں حاصل اور پارس کی گئیں۔")
            return prices
        else:
            logger.warning(f"API سے قیمتیں حاصل ہوئیں لیکن پارس نہیں کی جا سکیں: {data}")
            return None

    except Exception as e:
        logger.error(f"API سے قیمتیں حاصل کرنے میں نامعلوم خرابی: {e}", exc_info=True)
        return None

def update_market_state(live_prices: Dict[str, float]):
    """مارکیٹ کی حالت کو اپ ڈیٹ کرتا ہے تاکہ hunter.py اسے استعمال کر سکے۔"""
    try:
        try:
            with open(MARKET_STATE_FILE, 'r') as f:
                previous_state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            previous_state = {}
        
        current_state = {}
        for symbol, price in live_prices.items():
            current_state[symbol] = {
                "current_price": price,
                "previous_price": previous_state.get(symbol, {}).get("current_price", price)
            }
        
        with open(MARKET_STATE_FILE, 'w') as f:
            json.dump(current_state, f)
        
        logger.info(f"مارکیٹ اسٹیٹ فائل کامیابی سے {len(current_state)} جوڑوں کے لیے اپ ڈیٹ ہو گئی۔")
    except IOError as e:
        logger.error(f"مارکیٹ اسٹیٹ فائل لکھنے میں خرابی: {e}")
        
