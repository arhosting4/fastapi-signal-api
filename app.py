# app.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI
from dotenv import load_dotenv
import os
import requests
from src.agents.core_controller import generate_final_signal

# Load environment variables from .env
load_dotenv()

# Setup FastAPI app
app = FastAPI()

# Environment configs
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.get("/")
def home():
    return {"message": "✅ Pro Killer AI - ScalpMasterAI API running"}

@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    """
    God-level signal API endpoint.
    """
    decoded_symbol = symbol.replace("-", "/")  # XAU-USD → XAU/USD

    # Fetch recent candles
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "❌ Market data fetch failed", "details": data}

    candles = data["values"]
    result = generate_final_signal(decoded_symbol, candles)

    # Send to Telegram if no errors
    try:
        message = (
            f"📡 *{result['signal']}* Signal for *{decoded_symbol}* ⚡️\n\n"
            f"🧠 *Pattern:* {result['pattern']}\n"
            f"📊 *Risk:* {result['risk']}\n"
            f"📰 *News:* {result['news']}\n"
            f"🔍 *Reason:* {result['reason']}\n"
            f"🎯 *Confidence:* {result['confidence']}%\n"
            f"🏅 *Tier:* {result['tier']}"
        )
        send_telegram_message(message)
    except Exception as e:
        print("⚠️ Telegram send failed:", e)

    return result

def send_telegram_message(message: str):
    """
    Send message to configured Telegram channel.
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=payload)
        print("📤 Telegram status:", response.status_code, response.text)
    except Exception as e:
        print("⚠️ Telegram API error:", e)
