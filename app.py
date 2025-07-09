# app.py
from fastapi import FastAPI, HTTPException
import os
import requests
import json
from datetime import datetime, timedelta
import random
import time # For Finnhub rate limiting

# Import your AI agents
from agents.fusion_engine import generate_final_signal
from agents.logger import log_signal

# NEW: Finnhub client
import finnhub

app = FastAPI(
    title="ScalpMasterSignalsAi API",
    description="The Most Advanced, Sentient-Level, Self-Learning Forex Signal AI System",
    version="1.0.0",
)

# Telegram credentials from environment
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# NEW: Finnhub API Key (from environment variables)
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# Initialize Finnhub client
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

# This print is for debugging purposes to confirm API key loading
print(f"DEBUG: Value of FINNHUB_API_KEY from os.getenv(): {FINNHUB_API_KEY}")

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

# NEW: fetch_real_ohlc_data to use Finnhub API
def fetch_real_ohlc_data(symbol: str, interval: str = "1", outputsize: int = 50) -> list:
    """
    Fetches OHLC data for a given symbol from Finnhub API.

    Parameters:
        symbol (str): The trading pair symbol (e.g., "AAPL", "OANDA:EURUSD").
        interval (str): The interval of the candles (e.g., "1", "5", "15", "60").
                        Finnhub uses seconds for resolution (1, 5, 15, 30, 60, D, W, M).
        outputsize (int): The number of data points to retrieve.

    Returns:
        list: A list of OHLC candle dictionaries, ordered from oldest to newest.
              Returns an empty list if data fetching fails or API key is missing.
    """
    if not FINNHUB_API_KEY:
        print("⚠️ FINNHUB_API_KEY is not set. Cannot fetch real data. Using dummy data.")
        return _generate_dummy_candles(outputsize)

    # Convert interval to Finnhub resolution (seconds)
    # Finnhub resolution: 1, 5, 15, 30, 60, D, W, M
    resolution = interval
    if interval == "1min": resolution = "1"
    elif interval == "5min": resolution = "5"
    elif interval == "15min": resolution = "15"
    elif interval == "60min": resolution = "60"
    elif interval == "D": resolution = "D"
    elif interval == "W": resolution = "W"
    elif interval == "M": resolution = "M"

    # Get current timestamp and timestamp for 'outputsize' minutes ago
    to_timestamp = int(time.time())
    from_timestamp = int(to_timestamp - (outputsize * int(resolution) * 60)) # Approx for minutes

    # Finnhub expects forex symbols like "OANDA:EURUSD" or "FX_IDC:EURUSD"
    # For stocks, it's just "AAPL"
    finnhub_symbol = symbol.upper()
    if '/' in symbol: # Convert EUR/USD to OANDA:EURUSD
        finnhub_symbol = f"OANDA:{symbol.replace('/', '')}"

    print(f"DEBUG: Fetching Finnhub data for symbol: {finnhub_symbol}, resolution: {resolution}, from: {from_timestamp}, to: {to_timestamp}")

    try:
        # Finnhub API call
        # Note: Finnhub's free tier has a rate limit of 30 calls/sec and 500 calls/month for some endpoints.
        # Candle data might be limited to 60 calls/min.
        data = finnhub_client.stock_candles(finnhub_symbol, resolution, from_timestamp, to_timestamp)

        if data and data.get('s') == 'ok':
            candles_data = []
            # Finnhub returns 'c' (close), 'h' (high), 'l' (low), 'o' (open), 't' (timestamp), 'v' (volume)
            # Data is usually oldest first, which is what we need.
            for i in range(len(data['t'])):
                candles_data.append({
                    "datetime": datetime.fromtimestamp(data['t'][i]).isoformat(),
                    "open": data['o'][i],
                    "high": data['h'][i],
                    "low": data['l'][i],
                    "close": data['c'][i],
                    "volume": data['v'][i]
                })
            return candles_data
        elif data and data.get('s') == 'no_data':
            print(f"⚠️ Finnhub API: No data found for {finnhub_symbol} with resolution {resolution}.")
            return []
        else:
            print(f"⚠️ Unexpected response from Finnhub API for {finnhub_symbol}: {data}")
            return []
    except finnhub.FinnhubAPIException as e:
        print(f"⚠️ Finnhub API Error for {finnhub_symbol}: {e}")
        return []
    except Exception as e:
        print(f"⚠️ An unexpected error occurred during Finnhub data fetch for {finnhub_symbol}: {e}")
        return []


@app.get("/")
def root():
    return {"message": "ScalpMasterAi API is running. Visit /docs for API documentation."}

# UPDATED: Changed from path parameter to query parameter for better symbol handling
@app.get("/signal")
async def get_signal(symbol: str): # symbol is now a query parameter
    """
    Generates a trading signal for the given symbol using the AI fusion engine.
    Example: /signal?symbol=AAPL or /signal?symbol=EUR/USD
    """
    print(f"DEBUG: Received symbol: {symbol}") # Debug print to confirm received symbol
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required.")

    # Symbol is processed inside fetch_real_ohlc_data for Finnhub specific formatting
    processed_symbol_for_log = symbol.upper() # Keep this for consistent logging

    # Fetch real OHLC data
    # Finnhub resolution is '1' for 1-minute, '5' for 5-minute etc.
    candles = fetch_real_ohlc_data(symbol, interval="1", outputsize=50) # Pass original symbol

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
