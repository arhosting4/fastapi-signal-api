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

# Load API keys from .env
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.get("/")
def home():
    return {"message": "🚀 Pro Killer AI - ScalpMaster API is live and operational."}

@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    """
    Main API endpoint for generating god-level signals.
    """

    decoded_symbol = symbol.replace("-", "/")  # Convert XAU-USD → XAU/USD

    # Step 1: Fetch 1min OHLC data (last 5 candles)
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "❌ Market data fetch failed", "details": data}

    candles = data["values"]

    # Step 2: Run core AI signal engine
    result = generate_final_signal(decoded_symbol, candles)

    # Step 3: Send to Telegram
    try:
        message = (
            f"📡 *{result['signal'].upper()}* Signal for *{decoded_symbol}* ⚡️\n\n"
            f"🧠 *Pattern:* {result['pattern']}\n"
            f"📊 *Risk:* {result['risk']}\n"
            f"📰 *News:* {result['news']}\n"
            f"🔍 *Reason:* {result['reason']}\n"
            f"🎯 *Confidence:* {result['confidence']}%\n"
            f"🏅 *Tier:* {result['tier']}"
        )
        send_telegram_message(message)
    except Exception as e:
        print("⚠️ Telegram Error:", str(e))

    return result

def send_telegram_message(message: str):
    """
    Sends signal message to Telegram using secure token/chat from .env.
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload)
        print("✅ Telegram sent:", response.status_code)
    except Exception as e:
        print("⚠️ Telegram API failure:", str(e))
