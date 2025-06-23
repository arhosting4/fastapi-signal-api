from fastapi import FastAPI
from dotenv import load_dotenv
import os
import requests
from agents.core_controller import generate_final_signal

# Load environment variables from .env file or Render secrets
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Environment variables
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.get("/")
def home():
    return {"message": "🚀 Pro Killer AI - ScalpMasterAi API is running successfully"}

@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    decoded_symbol = symbol.replace("-", "/")  # e.g., XAU-USD -> XAU/USD

    # Fetch OHLC data from Twelve Data
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "❌ Failed to fetch market data", "details": data}

    candles = data["values"]
    result = generate_final_signal(decoded_symbol, candles)

    # Prepare and send Telegram message
    try:
        message = f"📡 *{result['signal']}* Signal for *{decoded_symbol}* ⚡️\n\n" \
                  f"🧠 *Pattern:* {result['pattern']}\n" \
                  f"📊 *Risk:* {result['risk']}\n" \
                  f"📰 *News:* {result['news']}\n" \
                  f"🔍 *Reason:* {result['reason']}\n" \
                  f"🎯 *Confidence:* {result['confidence']}%\n" \
                  f"🏅 *Tier:* {result['tier']}"
        send_telegram_message(message)
    except Exception as e:
        print("⚠️ Telegram Error:", str(e))

    return result

def send_telegram_message(message: str):
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
        print("⚠️ Telegram Send Failed:", str(e))
