import requests
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

def fetch_current_price_twelve_data(symbol: str, key_manager) -> Optional[float]:
    """Fetch current price from Twelve Data API"""
    try:
        if not key_manager:
            print("--- No key manager available ---")
            return None
        
        api_key = key_manager.get_next_key()
        if not api_key:
            print("--- No API key available ---")
            return None
        
        url = "https://api.twelvedata.com/price"
        params = {
            "symbol": symbol,
            "apikey": api_key
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if "price" in data:
                price = float(data["price"])
                print(f"--- Fetched price for {symbol}: {price} ---")
                return price
            else:
                print(f"--- No price data for {symbol}: {data} ---")
                return None
        
        elif response.status_code == 429:
            print(f"--- Rate limit hit for {symbol}, marking key as failed ---")
            key_manager.mark_key_failed(api_key)
            time.sleep(2)
            return None
        
        else:
            print(f"--- Error fetching price for {symbol}: HTTP {response.status_code} ---")
            return None
        
    except Exception as e:
        print(f"--- ERROR in fetch_current_price_twelve_data: {e} ---")
        return None

def fetch_historical_data_twelve_data(symbol: str, timeframe: str, key_manager, days: int = 30) -> Optional[List[Dict[str, Any]]]:
    """Fetch historical data from Twelve Data API"""
    try:
        if not key_manager:
            print("--- No key manager available ---")
            return None
        
        api_key = key_manager.get_next_key()
        if not api_key:
            print("--- No API key available ---")
            return None
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "apikey": api_key
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if "values" in data and data["values"]:
                historical_data = []
                for item in data["values"]:
                    candle = {
                        "datetime": item.get("datetime", ""),
                        "open": float(item.get("open", 0)),
                        "high": float(item.get("high", 0)),
                        "low": float(item.get("low", 0)),
                        "close": float(item.get("close", 0)),
                        "volume": float(item.get("volume", 0))
                    }
                    historical_data.append(candle)
                
                # Reverse to get chronological order (oldest first)
                historical_data.reverse()
                print(f"--- Fetched {len(historical_data)} candles for {symbol} {timeframe} ---")
                return historical_data
            
            else:
                print(f"--- No historical data for {symbol}: {data} ---")
                return None
        
        elif response.status_code == 429:
            print(f"--- Rate limit hit for {symbol}, marking key as failed ---")
            key_manager.mark_key_failed(api_key)
            time.sleep(2)
            return None
        
        else:
            print(f"--- Error fetching historical data for {symbol}: HTTP {response.status_code} ---")
            return None
        
    except Exception as e:
        print(f"--- ERROR in fetch_historical_data_twelve_data: {e} ---")
        return None

def validate_symbol_format(symbol: str) -> bool:
    """Validate if symbol format is supported"""
    try:
        valid_symbols = [
            "XAUUSD", "EURUSD", "GBPUSD", "USDJPY", 
            "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"
        ]
        
        return symbol.upper() in valid_symbols
        
    except Exception as e:
        print(f"--- ERROR in validate_symbol_format: {e} ---")
        return False

def format_price_for_symbol(price: float, symbol: str) -> float:
    """Format price according to symbol precision"""
    try:
        if symbol.upper() == "XAUUSD":
            return round(price, 2)
        elif symbol.upper() in ["USDJPY"]:
            return round(price, 3)
        else:
            return round(price, 5)
        
    except Exception as e:
        print(f"--- ERROR in format_price_for_symbol: {e} ---")
        return price

def calculate_pip_value(symbol: str, price_change: float) -> float:
    """Calculate pip value for the given symbol"""
    try:
        if symbol.upper() == "XAUUSD":
            return price_change  # Gold is measured in dollars
        elif symbol.upper() in ["USDJPY"]:
            return price_change * 100  # JPY pairs
        else:
            return price_change * 10000  # Standard forex pairs
        
    except Exception as e:
        print(f"--- ERROR in calculate_pip_value: {e} ---")
        return price_change

def get_market_hours_status() -> Dict[str, str]:
    """Check if markets are open"""
    try:
        current_time = datetime.utcnow()
        current_hour = current_time.hour
        current_weekday = current_time.weekday()  # 0 = Monday, 6 = Sunday
        
        # Weekend check
        if current_weekday >= 5:  # Saturday or Sunday
            return {"status": "closed", "reason": "Weekend"}
        
        # Monday opening check (markets open at 22:00 UTC Sunday)
        if current_weekday == 0 and current_hour < 22:
            return {"status": "closed", "reason": "Monday opening"}
        
        # Friday closing check (markets close at 22:00 UTC Friday)
        if current_weekday == 4 and current_hour >= 22:
            return {"status": "closed", "reason": "Friday closing"}
        
        return {"status": "open", "reason": "Market hours"}
        
    except Exception as e:
        print(f"--- ERROR in get_market_hours_status: {e} ---")
        return {"status": "unknown", "reason": "Error checking market hours"}

def test_api_connection(key_manager) -> Dict[str, Any]:
    """Test API connection with a simple request"""
    try:
        if not key_manager:
            return {"status": "error", "message": "No key manager"}
        
        test_result = fetch_current_price_twelve_data("EURUSD", key_manager)
        
        if test_result:
            return {"status": "success", "price": test_result}
        else:
            return {"status": "error", "message": "Failed to fetch test price"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
