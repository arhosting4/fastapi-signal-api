import os
import sys
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Fix path for agents import
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
if AGENTS_DIR not in sys.path:
    sys.path.append(AGENTS_DIR)

# Import AI logic
from core_controller import generate_final_signal

# Load environment variables
load_dotenv()
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# FastAPI setup
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For public access. Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "✅ ScalpMasterAi God-Level AI API is Running!"}

@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    try:
        decoded_symbol = symbol.replace("-", "/")

        # Fetch last 5 candles
        url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
        response = requests.get(url)
        data = response.json()

        if "values" not in data:
            return {"error": "❌ Market data fetch failed", "details": data}

        candles = data["values"]

        # AI signal logic
        result = generate_final_signal(decoded_symbol, candles)

        # Telegram message
        message = (
            f"📡 *{result['signal']}* Signal for *{decoded_symbol}*\n\n"
            f"🧠 *Pattern:* {result['pattern']}\n"
            f"📊 *Risk:* {result['risk']}\n"
            f"📰 *News:* {result['news']}\n"
            f"🔍 *Reason:* {result['reason']}\n"
            f"🎯 *Confidence:* {result['confidence']}%\n"
            f"🏅 *Tier:* {result['tier']}"
        )
        send_telegram_message(message)

        return result

    except Exception as e:
        return {"error": f"⚠️ Exception in signal generation: {str(e)}"}


def send_telegram_message(message: str):
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
        print("⚠️ Telegram send failed:", str(e))
