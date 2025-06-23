# app.py

from fastapi import FastAPI
from dotenv import load_dotenv
import os
import requests
from agents.core_controller import generate_final_signal

# Load .env variables
load_dotenv()

# FastAPI app
app = FastAPI()

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

@app.get("/")
def home():
    return {"message": "✅ Pro Killer AI - God-Level Signal API Running"}

@app.get("/final-signal/{symbol}")
def get_final_signal(symbol: str):
    """
    Final AI signal with multi-agent fusion and Telegram messaging.
    """
    decoded_symbol = symbol.replace("-", "/")
    tf = "1min"  # fixed timeframe

    # Fetch market candles
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval={tf}&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        return {"error": "❌ API Fetch Error", "details": str(e)}

    if "values" not in data:
        return {"error": "❌ Invalid data from API", "details": data}

    candles = [float(c["close"]) for c in reversed(data["values"])]

    # AI Signal
    result = generate_final_signal(decoded_symbol, tf, candles)

    if result.get("status") != "ok":
        return {"error": "AI Error", "details": result}

    # Compose message
    message = (
        f"🚀 *{result['signal'].upper()}* signal for *{result['symbol']}* ({tf})\n\n"
        f"🧠 Reason: {result['reason']}\n"
        f"💰 Price: {result['price']}"
    )

    # Send Telegram message
    send_telegram_message(message)

    return result


def send_telegram_message(message: str):
    """
    Send signal to Telegram channel securely.
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload)
        print("✅ Telegram:", response.status_code)
    except Exception as e:
        print("⚠️ Telegram Error:", e)
