from fastapi import FastAPI
from agents.core_controller import generate_final_signal
from agents.logger import log_signal
import requests
import urllib.parse
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# API key and Telegram configs from environment
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.get("/")
def root():
    return {"message": "API is running successfully 🚀"}

@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    """
    Master AI Fusion Route — returns final decision signal with confidence, reason, risk, pattern, news check.
    URL format: /final-signal/XAU-USD
    """
    decoded_symbol = symbol.replace("-", "/")  # Ensure compatibility with XAU-USD type inputs

    # Fetch OHLC from Twelve Data
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "Market data fetch failed", "details": data}

    candles = data["values"]
    result = generate_final_signal(decoded_symbol, candles)

    # Save to AI log file
    log_signal(decoded_symbol, result, candles)

    # Send to Telegram
    try:
        message = f"🔥 *{result['signal']}* on {decoded_symbol} 🔔\n\n" \
                  f"📊 Pattern: {result['pattern']}\n" \
                  f"⚠️ Risk: {result['risk']}\n" \
                  f"📰 News: {result['news']}\n" \
                  f"🧠 Reason: {result['reason']}\n" \
                  f"🎯 Confidence: {result['confidence']}%\n" \
                  f"🏆 Tier: {result['tier']}"
        send_telegram_message(message)
    except Exception as e:
        print("Telegram error:", e)

    return result

def send_telegram_message(message: str):
    """
    Sends message to the configured Telegram bot/channel.
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload)
        return response.json()
    except Exception as e:
        print("Telegram message error:", e)
        return {"error": str(e)}
