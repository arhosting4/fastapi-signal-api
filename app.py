# app.py
from fastapi import FastAPI, HTTPException, Query
from agents.fusion_engine import generate_final_signal
from agents.logger import log_signal
import os
import requests
import traceback
import json # Import json for parsing API responses

app = FastAPI()

# Telegram credentials from environment
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# Twelve Data API Key
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

def send_telegram_message(message: str):
    """Sends a message to the configured Telegram chat."""
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
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        print("✅ Telegram response:", response.status_code, response.text)
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Telegram Send Failed: {e}")
    except Exception as e:
        print(f"⚠️ An unexpected error occurred during Telegram send: {e}")


async def fetch_real_ohlc_data(symbol: str) -> list:
    """
    Fetches real OHLCV data from Twelve Data API.
    Returns a list of dictionaries, each representing a candle.
    """
    if not TWELVE_DATA_API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY is not set in environment variables.")

    # Twelve Data API endpoint for time series
    # Using 1min resolution and outputsize=100 for sufficient data for TA-Lib
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&apikey={TWELVE_DATA_API_KEY}&outputsize=100"
        
    print(f"DEBUG: Trying Twelve Data API URL: {url}") # Log the URL being used

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # Check for API errors in the response
        if "status" in data and data["status"] == "error":
            error_message = data.get("message", "Unknown error from Twelve Data API.")
            print(f"⚠️ Twelve Data API Error for {symbol}: {error_message}")
            raise HTTPException(status_code=500, detail=f"Twelve Data API Error: {error_message}")
            
        if "values" not in data or not data["values"]:
            print(f"DEBUG: No 'values' found in Twelve Data response for {symbol}. Response: {data}")
            raise HTTPException(status_code=404, detail=f"No OHLC data found for {symbol}. Check symbol, API key, or market hours.")

        # Twelve Data returns data in reverse chronological order (newest first)
        # We need to reverse it for TA-Lib/pandas_ta which expects oldest first
        ohlc_data = []
        for entry in reversed(data["values"]):
            try:
                ohlc_data.append({
                    "datetime": entry["datetime"],
                    "open": float(entry["open"]),
                    "high": float(entry["high"]),
                    "low": float(entry["low"]),
                    "close": float(entry["close"]),
                    "volume": float(entry.get("volume", 0)) # Use .get() with default for safety
                })
            except ValueError as ve:
                print(f"⚠️ Data conversion error for {symbol} entry {entry}: {ve}")
                continue # Skip this entry if conversion fails
            
        if not ohlc_data:
            raise HTTPException(status_code=404, detail=f"No valid OHLC data could be parsed for {symbol}.")

        return ohlc_data

    except requests.exceptions.Timeout:
        print(f"⚠️ Twelve Data API request timed out for {symbol}.")
        raise HTTPException(status_code=504, detail=f"Twelve Data API request timed out for {symbol}.")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Network or API connection error for {symbol}: {e}")
        raise HTTPException(status_code=503, detail=f"Network or API connection error: {e}")
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON decoding error from Twelve Data for {symbol}: {e}. Response text: {response.text}")
        raise HTTPException(status_code=500, detail=f"Error parsing Twelve Data response: {e}")
    except Exception as e:
        print(f"⚠️ An unexpected error occurred while fetching from Twelve Data for {symbol}: {e}")
        traceback.print_exc() # Print full traceback for unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred with Twelve Data: {e}")


@app.get("/")
def root():
    """Root endpoint for the API."""
    return {"message": "ScalpMasterAi API is running. Visit /docs for API documentation."}


@app.get("/signal")
async def get_signal(symbol: str = Query(..., description="Trading symbol (e.g., AAPL, EUR/USD)")):
    """
    Generates a trading signal for the given symbol using the AI fusion engine.
    """
    print(f"DEBUG: Received symbol: {symbol}")
        
    try:
        # Fetch real OHLC data
        candles = await fetch_real_ohlc_data(symbol)
            
        # Pass candles to the fusion engine
        signal_result = generate_final_signal(symbol, candles)

        # Log the signal
        log_signal(symbol, signal_result, candles)

        # Safely get values for Telegram message, providing defaults if keys are missing
        # This handles cases where signal_result might not have all expected keys
        symbol_upper = signal_result.get('symbol', symbol).upper()
        signal_type = signal_result.get('signal', 'N/A').upper()
        confidence = signal_result.get('confidence', 0.0)
        tier = signal_result.get('tier', 'N/A')
        pattern = signal_result.get('pattern', 'N/A')
        reason = signal_result.get('reason', 'No specific reason provided.')
        risk = signal_result.get('risk', 'N/A')
        news = signal_result.get('news', 'N/A')


        # Send Telegram message based on status
        if signal_result.get("status") == "ok" and signal_type in ["BUY", "SELL"]:
            message = (
                f"📈 ScalpMaster AI Signal Alert 📈\n\n"
                f"Symbol: *{symbol_upper}*\n"
                f"Signal: *{signal_type}*\n"
                f"Confidence: *{confidence:.2f}%*\n"
                f"Tier: *{tier}*\n"
                f"Pattern: *{pattern}*\n"
                f"Reason: _{reason}_\n\n"
                f"Risk: {risk} | News: {news}"
            )
            send_telegram_message(message)
        elif signal_result.get("status") == "blocked":
            message = (
                f"🚫 ScalpMaster AI Alert 🚫\n\n"
                f"Symbol: *{symbol_upper}*\n"
                f"Status: *BLOCKED*\n"
                f"Reason: _{signal_result.get('error', 'Unknown reason.')}_"
            )
            send_telegram_message(message)
        elif signal_result.get("status") == "no-signal":
            message = (
                f" neutral ScalpMaster AI Alert neutral \n\n"
                f"Symbol: *{symbol_upper}*\n"
                f"Status: *NO SIGNAL*\n"
                f"Reason: _{reason}_"
            )
            send_telegram_message(message)


        return signal_result

    except HTTPException as e:
        # Re-raise HTTPException directly as it's already a proper HTTP error
        raise e
    except Exception as e:
        # Catch any other unexpected errors and log them with full traceback
        print(f"CRITICAL ERROR in app.py for {symbol}: {e}")
        traceback.print_exc() # Print full traceback
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")

                    
