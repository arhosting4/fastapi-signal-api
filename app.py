import os
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import time
import json

# Import all agents
from agents.fusion_engine import generate_final_signal
from agents.logger import log_signal # Assuming you have a logger.py in agents

app = FastAPI(
    title="ScalpMaster AI Signal API",
    description="The Most Advanced, Sentient-Level, Self-Learning Forex Signal AI System API.",
    version="1.0.0",
)

# Configure CORS for frontend access
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:5500", # For Live Server VS Code extension
    "https://scalpmasterai.in", # Your domain
    "https://www.scalpmasterai.in", # Your domain with www
    "https://fastapi-signal-api-1.onrender.com", # Your Render URL
    # Add any other origins where your frontend might be hosted
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables for API keys and Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY") # Primary data source
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY") # Secondary data source (if needed)

# --- Helper Functions ---

def send_telegram_message(message: str):
    """Sends a message to the configured Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials not set. Skipping message send.")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
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

async def fetch_real_ohlc_data(symbol: str, interval: str = "1min", outputsize: int = 100) -> list:
    """
    Fetches OHLC data from Twelve Data API.
    Prioritizes Twelve Data.
    """
    if not TWELVE_DATA_API_KEY:
        print("⚠️ TWELVE_DATA_API_KEY is not set. Cannot fetch real data.")
        raise HTTPException(status_code=500, detail="Data API key not configured.")

    # Convert common forex symbols to Twelve Data format (e.g., EUR/USD to EUR/USD)
    # Twelve Data generally accepts EUR/USD or EURUSD. Let's stick to EUR/USD for consistency.
    formatted_symbol = symbol.replace('/', '%2F') # URL encode slash if present

    # Calculate 'from' and 'to' timestamps for the last 'outputsize' minutes
    # Finnhub uses Unix timestamps
    to_timestamp = int(datetime.now().timestamp())
    from_timestamp = int((datetime.now() - timedelta(minutes=outputsize * 2)).timestamp()) # Fetch more to ensure enough data after cleaning

    # --- Try Twelve Data ---
    twelve_data_url = (
        f"https://api.twelvedata.com/time_series?"
        f"symbol={formatted_symbol}&interval={interval}&apikey={TWELVE_DATA_API_KEY}&outputsize={outputsize}"
    )
    print(f"DEBUG: Trying Twelve Data API URL: {twelve_data_url}")

    try:
        response = requests.get(twelve_data_url, headers={"User-Agent": "ScalpMasterAI/1.0"})
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()

        if data.get("status") == "error":
            error_message = data.get("message", "Unknown error from Twelve Data API.")
            print(f"⚠️ Twelve Data API Error for {symbol}: {error_message}")
            # If Twelve Data fails, try Finnhub if key is available
            if FINNHUB_API_KEY:
                print(f"DEBUG: Twelve Data failed, trying Finnhub for {symbol}.")
                return await fetch_finnhub_data(symbol, interval, outputsize)
            else:
                raise HTTPException(status_code=503, detail=f"Twelve Data API Error: {error_message}")
        
        if "values" not in data or not data["values"]:
            print(f"⚠️ No OHLC data found for {symbol} from Twelve Data. Response: {data}")
            # If no data from Twelve Data, try Finnhub if key is available
            if FINNHUB_API_KEY:
                print(f"DEBUG: No data from Twelve Data, trying Finnhub for {symbol}.")
                return await fetch_finnhub_data(symbol, interval, outputsize)
            else:
                raise HTTPException(status_code=404, detail=f"No OHLC data found for {symbol}. Check symbol, API key, or market hours.")

        # Process Twelve Data response
        ohlc_data = []
        for entry in data["values"]:
            # Safely get volume, default to 0.0 if not present or invalid
            volume = float(entry.get("volume", 0.0)) if entry.get("volume") is not None else 0.0
            
            # Safely get datetime, default to current time if not present
            entry_datetime = entry.get("datetime", datetime.now().isoformat())

            ohlc_data.append({
                "open": float(entry["open"]),
                "high": float(entry["high"]),
                "low": float(entry["low"]),
                "close": float(entry["close"]),
                "volume": volume, # Use the safely obtained volume
                "datetime": entry_datetime # Use the safely obtained datetime
            })
        return ohlc_data[::-1] # Reverse to get oldest first

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Network or API connection error with Twelve Data for {symbol}: {e}")
        if FINNHUB_API_KEY:
            print(f"DEBUG: Twelve Data connection failed, trying Finnhub for {symbol}.")
            return await fetch_finnhub_data(symbol, interval, outputsize)
        else:
            raise HTTPException(status_code=503, detail=f"Could not connect to Twelve Data API: {e}")
    except Exception as e:
        print(f"⚠️ An unexpected error occurred while fetching from Twelve Data for {symbol}: {e}")
        if FINNHUB_API_KEY:
            print(f"DEBUG: Twelve Data unexpected error, trying Finnhub for {symbol}.")
            return await fetch_finnhub_data(symbol, interval, outputsize)
        else:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred with Twelve Data: {e}")

async def fetch_finnhub_data(symbol: str, resolution: str = "1", count: int = 100) -> list:
    """
    Fetches OHLC data from Finnhub API.
    'resolution' for Finnhub: 1, 5, 15, 30, 60, D, W, M
    'interval' for Twelve Data: 1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 1day, 1week, 1month
    """
    if not FINNHUB_API_KEY:
        print("⚠️ FINNHUB_API_KEY is not set. Cannot fetch real data from Finnhub.")
        raise HTTPException(status_code=500, detail="Finnhub API key not configured.")

    # Finnhub requires specific symbol formats for forex (e.g., OANDA:EURUSD)
    # For stocks, it's usually just the ticker (e.g., AAPL)
    # Let's assume for now that if it contains '/', it's forex and needs OANDA: prefix
    finnhub_symbol = symbol
    if '/' in symbol:
        finnhub_symbol = f"OANDA:{symbol.replace('/', '')}" # Finnhub uses EURUSD, not EUR/USD for OANDA

    # Convert outputsize to Finnhub's 'count' parameter
    # Finnhub uses 'from' and 'to' timestamps, not 'count' directly for candles
    to_timestamp = int(datetime.now().timestamp())
    from_timestamp = int((datetime.now() - timedelta(minutes=count * 2)).timestamp()) # Fetch more to ensure enough data

    finnhub_url = (
        f"https://finnhub.io/api/v1/forex/candle?" # Use forex endpoint for now
        f"symbol={finnhub_symbol}&resolution={resolution}&from={from_timestamp}&to={to_timestamp}&token={FINNHUB_API_KEY}"
    )
    print(f"DEBUG: Trying Finnhub API URL: {finnhub_url}")

    try:
        response = requests.get(finnhub_url, headers={"User-Agent": "ScalpMasterAI/1.0"})
        response.raise_for_status()
        data = response.json()

        if data.get("s") != "ok":
            error_message = data.get("error", "Unknown error from Finnhub API.")
            print(f"⚠️ Finnhub API Error for {symbol}: {error_message}")
            raise HTTPException(status_code=503, detail=f"Finnhub API Error: {error_message}")
        
        if not data.get("c") or not data.get("o") or not data.get("h") or not data.get("l") or not data.get("v") or not data.get("t"):
            print(f"⚠️ No OHLC data found for {symbol} from Finnhub. Response: {data}")
            raise HTTPException(status_code=404, detail=f"No OHLC data found for {symbol}. Check symbol, API key, or market hours.")

        ohlc_data = []
        for i in range(len(data["c"])):
            ohlc_data.append({
                "open": data["o"][i],
                "high": data["h"][i],
                "low": data["l"][i],
                "close": data["c"][i],
                "volume": data["v"][i],
                "datetime": datetime.fromtimestamp(data["t"][i]).isoformat()
            })
        return ohlc_data

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Network or API connection error with Finnhub for {symbol}: {e}")
        raise HTTPException(status_code=503, detail=f"Could not connect to Finnhub API: {e}")
    except Exception as e:
        print(f"⚠️ An unexpected error occurred while fetching from Finnhub for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred with Finnhub: {e}")


# --- API Endpoints ---

@app.get("/")
async def root():
    """Root endpoint for the ScalpMaster AI API."""
    return {"message": "ScalpMaster AI API is running. Visit /docs for API documentation."}

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

        # Send Telegram message if a clear signal is generated
        if signal_result["status"] == "ok" and signal_result["signal"] in ["buy", "sell"]:
            message = (
                f"📈 ScalpMaster AI Signal Alert 📈\n\n"
                f"Symbol: *{signal_result['symbol'].upper()}*\n"
                f"Signal: *{signal_result['signal'].upper()}*\n"
                f"Confidence: *{signal_result['confidence']:.2f}%*\n"
                f"Tier: *{signal_result['tier']}*\n"
                f"Pattern: *{signal_result['pattern']}*\n"
                f"Reason: _{signal_result['reason']}_\n\n"
                f"Risk: {signal_result['risk']} | News: {signal_result['news']}"
            )
            send_telegram_message(message)
        elif signal_result["status"] == "blocked":
            message = (
                f"🚫 ScalpMaster AI Alert 🚫\n\n"
                f"Symbol: *{signal_result['symbol'].upper()}*\n"
                f"Status: *BLOCKED*\n"
                f"Reason: _{signal_result['error']}_"
            )
            send_telegram_message(message)
        elif signal_result["status"] == "no-signal":
            message = (
                f" neutral ScalpMaster AI Alert neutral \n\n"
                f"Symbol: *{signal_result['symbol'].upper()}*\n"
                f"Status: *NO SIGNAL*\n"
                f"Reason: _{signal_result['reason']}_"
            )
            send_telegram_message(message)


        return signal_result

    except HTTPException as e:
        print(f"Error processing signal for {symbol}: {e.detail}")
        raise e
    except Exception as e:
        print(f"An unexpected error occurred for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")

