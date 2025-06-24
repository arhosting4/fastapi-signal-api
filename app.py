# app.py

from fastapi import FastAPI
from dotenv import load_dotenv
import os
import requests
from agents.core_controller import generate_final_signal

# Load environment variables
load_dotenv()

# FastAPI app instance
app = FastAPI()

# Load keys from environment
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


@app.get("/")
def home():
    return {"message": "✅ Pro Killer AI - ScalpMasterAi API is running!"}


@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    """
    Final endpoint to fetch signal, process AI logic, and send Telegram update.
    """
    decoded_symbol = symbol.replace("-", "/")  # XAU-USD → XAU/USD

    # Fetch 5 candles
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "❌ Failed to fetch market data", "details": data}

    candles = data["values"]

    # Get AI decision
    result = generate_final_signal(decoded_symbol, candles)

    # Format message
    try:
        message = f"📡 *{result['signal'].upper()}* Signal for *{decoded_symbol}* ⚡️\n\n" \
                  f"🧠 *Pattern:* {result['pattern']}\n" \
                  f"📊 *Risk:* {result['risk']}\n" \
                  f"📰 *News:* {result['reason']}\n" \
                  f"🎯 *Confidence:* {result['confidence']}%\n" \
                  f"🏅 *Tier:* {result['tier']}"
        send_telegram_message(message)
    except Exception as e:
        print("⚠️ Telegram Send Error:", str(e))

    return result


def send_telegram_message(message: str):
    """
    Sends message to Telegram channel.
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload)
        print("✅ Telegram response:", response.status_code, response.text)
    except Exception as e:
        print("⚠️ Telegram API error:", str(e))
