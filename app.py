# app.py

from fastapi import FastAPI
from dotenv import load_dotenv
import os
import requests
from agents.core_controller import generate_final_signal

# Load .env file
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Load secrets from environment
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.get("/")
def home():
    return {"message": "🚀 Pro Killer AI - God Level Signal API is live!"}

@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    """
    Main endpoint: fetch market data, run all AI agents, send Telegram signal.
    """
    decoded_symbol = symbol.replace("-", "/")  # e.g. XAU-USD → XAU/USD

    # Fetch market candles
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "❌ Market data fetch failed", "details": data}

    candles = data["values"]
    result = generate_final_signal(decoded_symbol, candles)

    if result.get("validated"):
        send_telegram_message(result)

    return result


def send_telegram_message(result: dict):
    """
    Sends formatted signal to the Telegram channel.
    """
    try:
        message = (
            f"📡 *{result['final_signal']}* Signal for *{result['symbol']}* ⚡️\n\n"
            f"🧠 *Pattern:* {result['pattern']}\n"
            f"📊 *Risk:* {result['risk']}\n"
            f"📰 *News:* {result['news']}\n"
            f"🔍 *Reason:* {result['reason']}\n"
            f"🎯 *Confidence:* {result['confidence']}%\n"
            f"🏅 *Tier:* {result['tier']}"
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload)
        print("✅ Telegram Response:", response.status_code, response.text)

    except Exception as e:
        print("⚠️ Telegram Send Error:", str(e))
