# app.py

from fastapi import FastAPI
from dotenv import load_dotenv
import os
import requests
from agents.core_controller import generate_final_signal

# Load environment variables
load_dotenv()

# FastAPI instance
app = FastAPI()

# Environment variables
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.get("/")
def home():
    return {"message": "🚀 Pro Killer AI - God-Level API is Live"}

@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    """
    Main signal API endpoint. Fetches candles, processes AI logic, sends Telegram message.
    """
    decoded_symbol = symbol.replace("-", "/")  # XAU-USD => XAU/USD
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"

    try:
        response = requests.get(url)
        data = response.json()

        if "values" not in data:
            return {"error": "❌ Market data fetch failed", "details": data}

        candles = data["values"]
        result = generate_final_signal(decoded_symbol, candles)

        # Format Telegram message
        message = f"""
📡 *{result['signal'].upper()}* signal for *{decoded_symbol}*

🧠 *Pattern:* {result['pattern']}
⚠️ *Risk:* {result['risk']}
📰 *News:* {result['news']}
🧠 *Reason:* {result['reason']}
🎯 *Confidence:* {result['confidence']}%
🏅 *Tier:* {result['tier']}
"""

        send_telegram_message(message)

        return result

    except Exception as e:
        return {"error": "⚠️ API error", "details": str(e)}

def send_telegram_message(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload)
        print("✅ Telegram:", response.status_code, response.text)
    except Exception as e:
        print("⚠️ Telegram Send Error:", str(e))
