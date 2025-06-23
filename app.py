from fastapi import FastAPI
from agents.strategybot import generate_core_signal, fetch_ohlc
import os
import requests

app = FastAPI()

# Telegram credentials from environment
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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


@app.get("/")
def root():
    return {"message": "ScalpMasterAi API is running"}


@app.get("/final-signal/{symbol}")
def get_signal(symbol: str):
    # Simulated dummy data
    tf = "1m"
    data = [2001, 2003, 2005, 2007, 2009, 2011]

    signal = generate_core_signal(symbol, tf, data)
    ohlc = fetch_ohlc(symbol, tf, data)

    if signal in ["buy", "sell"]:
        message = f"*{symbol}* ({tf}) Signal: *{signal.upper()}*\nPrice: `{ohlc['close']}`"
        send_telegram_message(message)
        return {"status": "ok", "signal": signal, "price": ohlc["close"]}
    else:
        return {"status": "no-signal", "error": "Strategy failed or not triggered"}
