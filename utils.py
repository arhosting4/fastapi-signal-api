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
from config import TRADING_PAIRS, API_CONFIG # ★★★ مرکزی کنفیگریشن امپورٹ کریں ★★★

logger = logging.getLogger(__name__)

MARKET_STATE_FILE = "market_state.json"

def get_all_pairs() -> List[str]:
    """
    ہفتے کے دن کی بنیاد پر تمام ممکنہ جوڑوں کی فہرست واپس کرتا ہے۔
    """
    today = datetime.utcnow().weekday()
    if today >= 5: # ہفتہ (5) اور اتوار (6)
        return TRADING_PAIRS["CRYPTO_PAIRS_WEEKEND"]
    return TRADING_PAIRS["PRIORITY_PAIRS_WEEKDAY"] + TRADING_PAIRS["SECONDARY_PAIRS_WEEKDAY"]

def get_priority_pairs() -> List[str]:
    """
    ہفتے کے دن کی بنیاد پر صرف ترجیحی جوڑوں کی فہرست واپس کرتا ہے۔
    """
    today = datetime.utcnow().weekday()
    if today >= 5: # ہفتہ اور اتوار
        return TRADING_PAIRS["CRYPTO_PAIRS_WEEKEND"]
    return TRADING_PAIRS["PRIORITY_PAIRS_WEEKDAY"]

def get_pairs_to_hunt(active_symbols: List[str]) -> List[str]:
    """
    ایک ذہین شکار کی فہرست تیار کرتا ہے جو ترجیحات اور مارکیٹ کی حرکت پر مبنی ہوتی ہے۔
    """
    logger.info(f"شکار کی فہرست تیار کی جا رہی ہے۔ فعال سگنلز: {active_symbols}")
    
    try:
        with open(MARKET_STATE_FILE, 'r') as f:
            market_state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning("مارکیٹ اسٹیٹ فائل نہیں ملی، حرکت کی بنیاد پر ترجیح نہیں دی جا سکتی۔")
        market_state = {}

    volatility_map = {}
    for symbol, data in market_state.items():
        if 'current_price' in data and 'previous_price' in data:
            try:
                change_pct = (abs(data['current_price'] - data['previous_price']) / data['previous_price']) * 100
                volatility_map[symbol] = change_pct
            except (TypeError, ZeroDivisionError):
                continue
    
    sorted_by_volatility = sorted(volatility_map.keys(), key=lambda s: volatility_map.get(s, 0), reverse=True)
    
    hunt_list = []
    
    priority_pairs = get_priority_pairs()
    for pair in priority_pairs:
        if pair not in active_symbols:
            hunt_list.append(pair)
    
    logger.info(f"ترجیحی جوڑوں کو شامل کرنے کے بعد شکار کی فہرست: {hunt_list}")
    
    hunt_list_size = TRADING_PAIRS["HUNT_LIST_SIZE"]

    if len(hunt_list) < hunt_list_size:
        secondary_pairs = TRADING_PAIRS["SECONDARY_PAIRS_WEEKDAY"] if datetime.utcnow().weekday() < 5 else []
        for pair in sorted_by_volatility:
            if len(hunt_list) >= hunt_list_size: break
            if pair in secondary_pairs and pair not in hunt_list and pair not in active_symbols:
                hunt_list.append(pair)
    
    logger.info(f"حرکت والے جوڑوں کو شامل کرنے کے بعد شکار کی فہرست: {hunt_list}")

    if len(hunt_list) < hunt_list_size:
        all_secondary_pairs = TRADING_PAIRS["SECONDARY_PAIRS_WEEKDAY"] if datetime.utcnow().weekday() < 5 else []
        for pair in all_secondary_pairs:
            if len(hunt_list) >= hunt_list_size: break
            if pair not in hunt_list and pair not in active_symbols:
                hunt_list.append(pair)

    final_hunt_list = hunt_list[:hunt_list_size]
    logger.info(f"حتمی شکار کی فہرست ({len(final_hunt_list)} جوڑے): {final_hunt_list}")
    return final_hunt_list

async def fetch_twelve_data_ohlc(symbol: str) -> Optional[List[Candle]]:
    """TwelveData API سے OHLC کینڈلز لاتا ہے۔"""
    api_key = key_manager.get_api_key()
    if not api_key:
        logger.warning(f"[{symbol}] OHLC کے لیے کوئی API کلید دستیاب نہیں۔")
        return None
    
    # ★★★ کنفیگریشن فائل سے پیرامیٹرز استعمال کریں ★★★
    timeframe = API_CONFIG["PRIMARY_TIMEFRAME"]
    candle_count = API_CONFIG["CANDLE_COUNT"]
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={timeframe}&outputsize={candle_count}&apikey={api_key}"
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
        
