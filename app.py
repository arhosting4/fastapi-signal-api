# src/app.py

from fastapi import FastAPI
from agents.core_controller import generate_final_signal
import os
import requests

app = FastAPI()

@app.get("/")
def index():
    return {"message": "ScalpMasterAi API is running"}

@app.get("/final-signal/{symbol}")
def get_final_signal(symbol: str):
    # Example mock data, replace with real OHLC fetch logic if needed
    sample_data = [2000, 2005, 2010, 2012, 2011, 2015]
    tf = "1m"
    
    result = generate_final_signal(symbol, tf, sample_data)

    # Telegram Notification
    if result["status"] == "ok":
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if token and chat_id:
            message = f"**{symbol} ({tf}) Signal:** `{result['signal'].upper()}`\nPrice: {result['price']}"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            requests.post(url, data=payload)

    return result
