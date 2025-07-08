# app.py
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import os
import requests
import json # For logging
from datetime import datetime, timedelta # For logging and dummy data

# Import your AI agents
from agents.fusion_engine import generate_final_signal
from agents.logger import log_signal

# Load environment variables from .env file (for local development)
load_dotenv()

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

# UPDATED: fetch_real_ohlc_data to use Twelve Data API
def fetch_real_ohlc_data(symbol: str, interval: str = "1min", outputsize: int = 50) -> list:
    """
    Fetches OHLC data for a given symbol from Twelve Data API.

    Parameters:
        symbol (str): The trading pair symbol (e.g., "EUR/USD", "XAU/USD").
        interval (str): The interval of the candles (e.g., "1min", "5min", "1h").
        outputsize (int): The number of data points to retrieve.

    Returns:
        list: A list of OHLC candle dictionaries, ordered from oldest to newest.
              Returns an empty list if data fetching fails or API key is missing.
    """
    if not TWELVE_DATA_API_KEY:
        print("⚠️ TWELVE_DATA_API_KEY is not set. Cannot fetch real data.")
        # Fallback to dummy data for local testing if API key is missing
        # In production, you might want to raise an error or handle differently
        return _generate_dummy_candles(outputsize)

    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVE_DATA_API_KEY}&outputsize={outputsize}"
    
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()

        if "values" in data:
            # Twelve Data returns newest first, so we need to reverse for our logic (oldest first)
            # Also, ensure numerical values are converted to float/int if needed by agents
            processed_candles = []
            for candle in reversed(data["values"]): # Reverse to get oldest first
                processed_candles.append({
                    "datetime": candle.get("datetime"),
                    "open": float(candle.get("open")),
                    "high": float(candle.get("high")),
                    "low": float(candle.get("low")),
                    "close": float(candle.get("close")),
                    "volume": float(candle.get("volume", 0)) # Volume might be missing for some symbols
                })
            return processed_candles
        elif "message" in data:
            print(f"⚠️ Twelve Data API Error for {symbol}: {data['message']}")
            return []
        else:
            print(f"⚠️ Unexpected response from Twelve Data API for {symbol}: {data}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error fetching data from Twelve Data for {symbol}: {e}")
        return []
    except ValueError as e: # Catch errors during float conversion
        print(f"⚠️ Data conversion error from Twelve Data for {symbol}: {e}")
        return []
    except Exception as e:
        print(f"⚠️ An unexpected error occurred during data fetch for {symbol}: {e}")
        return []

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

# Add random import for dummy data
import random


# app.py (only the relevant part for get_signal endpoint)

@app.get("/signal/{symbol}")
async def get_signal(symbol: str):
    """
    Generates a trading signal for the given symbol using the AI fusion engine.
    """
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required.")

    # Convert symbol to uppercase for consistency with API requirements
    processed_symbol = symbol.upper()

    # Fetch real OHLC data
    # Pass the processed_symbol to the data fetcher
    candles = fetch_real_ohlc_data(processed_symbol, interval="1min", outputsize=50)

    if not candles:
        # Provide more specific detail for 404
        raise HTTPException(status_code=404, detail=f"No OHLC data found for {processed_symbol}. Check symbol, API key, or market hours.")

    # Generate final signal using the fusion engine
    signal_result = generate_final_signal(processed_symbol, candles) # Pass processed_symbol

    # Log the signal result
    log_signal(processed_symbol, signal_result, candles) # Pass processed_symbol

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
            f"📊 *Symbol:* `{processed_symbol}`\n" # Use processed_symbol here
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
            f"📊 *Symbol:* `{processed_symbol}`\n" # Use processed_symbol here
            f"⚠️ *Reason:* `{signal_result.get('error', 'Market conditions not favorable.')}`\n\n"
            f"Consider reviewing market conditions."
        )
        send_telegram_message(message)

    return signal_result

# ... rest of app.py


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
