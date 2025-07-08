# app.py
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import os
import requests
import json # For logging
from datetime import datetime, timedelta # For logging and dummy data

# Import your AI agents - REMOVED 'src.' prefix
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

# Twelve Data API Key (if you plan to use it for real data)
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

# Dummy OHLC data fetcher for testing
# In a real scenario, this would fetch data from an external API like Twelve Data
def fetch_real_ohlc_data(symbol: str, interval: str = "1min", outputsize: int = 50) -> list:
    """
    Fetches OHLC data for a given symbol.
    This is a placeholder. You would integrate with Twelve Data or another provider here.
    """
    dummy_candles = []
    for i in range(outputsize):
        close_price = 1000 + i * 2 + (i % 5) * 0.5 # Simulate some price movement
        dummy_candles.append({
            "datetime": (datetime.now() - timedelta(minutes=outputsize - 1 - i)).isoformat(),
            "open": str(close_price - 1),
            "high": str(close_price + 1),
            "low": str(close_price - 0.5),
            "close": str(close_price),
            "volume": str(1000 + i * 10)
        })
    return dummy_candles[::-1] # Return in ascending order of time (oldest first)


@app.get("/")
def root():
    return {"message": "ScalpMasterAi API is running. Visit /docs for API documentation."}

@app.get("/signal/{symbol}")
async def get_signal(symbol: str):
    """
    Generates a trading signal for the given symbol using the AI fusion engine.
    """
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required.")

    # Fetch real OHLC data (or use dummy for now)
    candles = fetch_real_ohlc_data(symbol, interval="1min", outputsize=50)

    if not candles:
        raise HTTPException(status_code=404, detail=f"No OHLC data found for {symbol}")

    # Generate final signal using the fusion engine
    signal_result = generate_final_signal(symbol, candles)

    # Log the signal result
    log_signal(symbol, signal_result, candles)

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
            f"📊 *Symbol:* `{symbol.upper()}`\n"
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
            f"📊 *Symbol:* `{symbol.upper()}`\n"
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
    
