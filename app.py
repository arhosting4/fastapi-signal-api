from fastapi import FastAPI
import requests
import urllib.parse

from agents.strategybot import generate_core_signal, fetch_fake_ohlc
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
from agents.core_controller import generate_final_signal

app = FastAPI()

TWELVE_DATA_API_KEY = "1d3c362a1459423cbc1d24e2a408098b"
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YourChannelOrUserID"

# Root endpoint
@app.get("/")
def home():
    return {"message": "API is running"}

# Real market price fetch for chart or signal use
@app.get("/price/{symbol}")
def get_price(symbol: str):
    decoded_symbol = urllib.parse.unquote(symbol)
    url = f"https://api.twelvedata.com/price?symbol={decoded_symbol}&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    return response.json()

# Final AI signal output with full fusion logic
@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    decoded_symbol = urllib.parse.unquote(symbol)
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "Failed to fetch market data", "details": data}

    candles = data["values"]
    result = generate_final_signal(decoded_symbol, candles)

    message = f"**{result['signal']}** {decoded_symbol.upper()} ⚡️\n\n" \
              f"Risk: {result['risk']}\n" \
              f"News: {result['news']}\n" \
              f"Pattern: {result['pattern']}\n" \
              f"Reason: {result['reason']}\n" \
              f"Confidence: {result['confidence']}%\n"

    send_telegram_message(message)

    return result

# Telegram alert function
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram Error:", e)
