# app.py

from fastapi import FastAPI
from dotenv import load_dotenv
import os
import requests
from agents.core_controller import generate_final_signal

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Load secrets
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.get("/")
def read_root():
    return {"message": "🚀 Pro Killer AI ScalpMaster API is Live!"}

@app.get("/final-signal/{symbol}")
def get_final_signal(symbol: str):
    decoded_symbol = symbol.replace("-", "/")  # e.g., XAU-USD -> XAU/USD

    # Fetch OHLC data
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {
            "error": "❌ Failed to fetch market data",
            "details": data
        }

    candles = data["values"]

    # Run god-level signal engine
    final_signal = generate_final_signal(decoded_symbol, candles)
    return final_signal
