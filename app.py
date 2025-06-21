from fastapi import FastAPI
import requests
import os
from dotenv import load_dotenv
from agents.core_controller import generate_final_signal

# Load environment variables
load_dotenv()

app = FastAPI()

# Load API keys from .env
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


@app.get("/")
def home():
    return {"message": "API is running successfully 🚀"}


@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    decoded_symbol = symbol.replace("-", "/")  # Example: XAU-USD to XAU/USD

    # Fetch latest market data from TwelveData
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "Failed to fetch market data", "details": data}

    candles = data["values"]
    result = generate_final_signal(decoded_symbol, candles)

    # Build Telegram message
    message = (
        f"📡 **{result['signal']}** — `{decoded_symbol}`\n"
        f"Risk: {result['risk']}\n"
        f"News: {result['news']}\n"
        f"Pattern: {result['pattern']}\n"
        f"Reason: {result['reason']}\n"
        f"Confidence: {result['confidence']}%\n"
        f"Tier: {result['tier']}"
    )

    # Send to Telegram
    try:
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        telegram_response = requests.post(telegram_url, data=payload)
        telegram_response.raise_for_status()
    except Exception as e:
        print("Telegram Error:", str(e))

    return result
