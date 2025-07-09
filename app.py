# app.py
from fastapi import FastAPI, HTTPException
import os
import requests
import json
from datetime import datetime, timedelta
import random

# Import your AI agents
from agents.fusion_engine import generate_final_signal
from agents.logger import log_signal

app = FastAPI(
    title="ScalpMasterSignalsAi API",
    description="The Most Advanced, Sentient-Level, Self-Learning Forex Signal AI System",
    version="1.0.0",
)

# Telegram credentials from environment
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Twelve Data API Key (from environment variables)
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

# This print is for debugging purposes to confirm API key loading
print(f"DEBUG: Value of TWELVE_DATA_API_KEY from os.getenv(): {TWELVE_DATA_API_KEY}")

def send_telegram_message(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials not set. Skipping message send.")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload)
        response.raise_for_status() # Raise an exception for HTTP errors
        print(f"✅ Telegram response: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Telegram Send Failed: {e}")
    except Exception as e:
        print(f"⚠️ An unexpected error occurred during Telegram send: {e}")

# Helper function for dummy data (for local testing without API key)
def _generate_dummy_candles(outputsize: int) -> list:
    dummy_candles = []
    base_price = 100.0
    for i in range(outputsize):
        # Simulate some price movement
        close_price = base_price + (i * 0.1) + (random.uniform(-0.5, 0.5))
        open_price = close_price + random.uniform(-0.2, 0.2)
        high_price = max(open_price, close_price) + random.uniform(0, 0.3)
        low_price = min(open_price, close_price) - random.uniform(0, 0.3)

        dummy_candles.append({
            "datetime": (datetime.now() - timedelta(minutes=outputsize - 1 - i)).isoformat(),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": 1000 + i * 10
        })
    return dummy_candles # Already oldest first

# fetch_real_ohlc_data to use Twelve Data API
def fetch_real_ohlc_data(symbol: str, interval: str = "1min", outputsize: int = 50) -> list:
    """
    Fetches OHLC data for a given symbol from Twelve Data API.

    Parameters:
        symbol (str): The trading pair symbol (e.g., "AAPL", "EUR/USD").
        interval (str): The interval of the candles (e.g., "1min", "5min", "15min", "1h", "1day").
        outputsize (int): The number of data points to retrieve.

    Returns:
        list: A list of OHLC candle dictionaries, ordered from oldest to newest.
              Returns an empty list if data fetching fails or API key is missing.
    """
    if not TWELVE_DATA_API_KEY:
        print("⚠️ TWELVE_DATA_API_KEY is not set. Cannot fetch real data. Using dummy data.")
        return _generate_dummy_candles(outputsize)

    # --- Twelve Data Symbol Formatting ---
    # Twelve Data expects symbols like "AAPL" for stocks, "EUR/USD" or "FX:EURUSD" for forex.
    # We will try to send the symbol as is, and if it fails, try a common forex format.
    formatted_symbol = symbol.upper()
    
    # List of symbols to try in order
    symbols_to_try = [formatted_symbol]
    if '/' in formatted_symbol: # If it's a forex pair like EUR/USD
        symbols_to_try.append(formatted_symbol.replace('/', '')) # EURUSD
        symbols_to_try.append(f"FX:{formatted_symbol.replace('/', '')}") # FX:EURUSD
    
    # Add common stock symbols if it's not a forex pair
    if not any(s in formatted_symbol for s in ['/', ':']): # Simple check if it's likely a stock
        symbols_to_try.append(formatted_symbol) # Just the symbol
    
    final_data = None
    for s_to_try in symbols_to_try:
        url = f"https://api.twelvedata.com/time_series?symbol={s_to_try}&interval={interval}&apikey={TWELVE_DATA_API_KEY}&outputsize={outputsize}"
        print(f"DEBUG: Trying Twelve Data API URL: {url}") # Debug print for each attempt

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()

            if "values" in data and isinstance(data["values"], list):
                final_data = data
                break # Found data, exit loop
            elif "code" in data and data["code"] == 400:
                print(f"⚠️ Twelve Data API Error for {s_to_try}: {data.get('message', 'Unknown error')}")
                # Continue to next symbol to try
            elif "status" in data and data["status"] == "error":
                print(f"⚠️ Twelve Data API Error for {s_to_try}: {data.get('message', 'Unknown error')}")
                # Continue to next symbol to try
            else:
                print(f"⚠️ Unexpected response from Twelve Data API for {s_to_try}: {data}")
                # Continue to next symbol to try
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching data from Twelve Data for {s_to_try}: {e}")
            # Continue to next symbol to try
        except (ValueError, TypeError, KeyError) as e:
            print(f"⚠️ Data parsing error from Twelve Data for {s_to_try}: {e}. Raw data: {data}")
            # Continue to next symbol to try
        except Exception as e:
            print(f"⚠️ An unexpected error occurred during data fetch for {s_to_try}: {e}")
            # Continue to next symbol to try

    if not final_data:
        print(f"⚠️ Failed to fetch data for {symbol} after trying all formats.")
        return []

    processed_candles = []
    for candle_data in reversed(final_data["values"]): # Twelve Data returns newest first
        processed_candles.append({
            "datetime": candle_data["datetime"],
            "open": float(candle_data["open"]),
            "high": float(candle_data["high"]),
            "low": float(candle_data["low"]),
            "close": float(candle_data["close"]),
            "volume": float(candle_data.get("volume", 0))
        })
    return processed_candles


@app.get("/")
def root():
    return {"message": "ScalpMasterAi API is running. Visit /docs for API documentation."}

@app.get("/signal")
async def get_signal(symbol: str): # symbol is now a query parameter
    """
    Generates a trading signal for the given symbol using the AI fusion engine.
    Example: /signal?symbol=AAPL or /signal?symbol=EUR/USD
    """
    print(f"DEBUG: Received symbol: {symbol}") # Debug print to confirm received symbol
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required.")

    # Symbol is processed inside fetch_real_ohlc_data for Twelve Data specific formatting
    processed_symbol_for_log = symbol.upper() # Keep this for consistent logging

    # Fetch real OHLC data
    candles = fetch_real_ohlc_data(symbol, interval="1min", outputsize=50) # Pass original symbol

    if not candles:
        raise HTTPException(status_code=404, detail=f"No OHLC data found for {symbol}. Check symbol, API key, or market hours.")

    # Generate final signal using the fusion engine
    signal_result = generate_final_signal(processed_symbol_for_log, candles)

    # Log the signal result
    log_signal(processed_symbol_for_log, signal_result, candles)

    # Send Telegram message if a valid signal is generated
    if signal_result.get("status") == "ok" and signal_result.get("signal") in ["buy", "sell"]:
        signal_type = signal_result["signal"].upper()
        confidence = signal_result.get("confidence", "N/A")
        tier = signal_result.get("tier", "N/A")
        reason = signal_result.get("reason", "No specific reason.")
        
        # Get the latest close price from the fetched candles
        latest_close_price = candles[-1].get("close", "N/A")

        message = (
            f"📈 *ScalpMaster AI Signal Alert* 📉\n\n"
            f"📊 *Symbol:* `{processed_symbol_for_log}`\n"
            f"🚀 *Signal:* `{signal_type}`\n"
            f"💰 *Current Price:* `{latest_close_price}`\n"
            f"⭐ *Confidence:* `{confidence}%`\n"
            f"🏆 *Tier:* `{tier}`\n"
            f"💡 *Reason:* _{reason}_\n\n"
            f"🔗 [View on ScalpMasterSignalsAi.in](https://ScalpMasterSignalsAi.in)" # Placeholder URL
        )
        send_telegram_message(message)
    elif signal_result.get("status") == "blocked":
        message = (
            f"🚫 *ScalpMaster AI Blocked Signal* 🚫\n\n"
            f"📊 *Symbol:* `{processed_symbol_for_log}`\n"
            f"⚠️ *Reason:* `{signal_result.get('error', 'Market conditions not favorable.')}`\n\n"
            f"Consider reviewing market conditions."
        )
        send_telegram_message(message)

    return signal_result

# You can add more endpoints here for admin control, insight center, etc.
# For example, an endpoint to get signal logs
@app.get("/logs/{symbol}")
def get_signal_logs(symbol: str):
    """
    Retrieves signal logs for a specific symbol.
    """
    log_file_path = os.path.join("logs", f"{symbol.replace('/', '_')}_log.jsonl")
    if not os.path.exists(log_file_path):
        raise HTTPException(status_code=404, detail=f"No logs found for {symbol}")

    logs = []
    try:
        with open(log_file_path, "r") as f:
            for line in f:
                logs.append(json.loads(line))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {e}")
    
    return logs
                                                                          
