# app.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os

from src.agents.strategybot import generate_core_signal

app = FastAPI()

# ✅ Telegram details from env or fallback
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "your-real-token-here")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your-real-chat-id")

class CandleData(BaseModel):
    symbol: str
    tf: str
    closes: list

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

@app.post("/final-signal/{symbol}")
async def get_final_signal(symbol: str, data: CandleData):
    try:
        result = generate_core_signal(symbol, data.tf, data.closes)

        if result == "wait":
            return {"status": "no-signal", "error": "Strategy failed or not enough data."}

        message = (
            f"📡 *{result.upper()}* signal for *{symbol.upper()}* on timeframe *{data.tf}*.\n"
            f"🔍 Data: {data.closes[-3:]}"
        )
        send_telegram_message(message)

        return {"status": "signal", "signal": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
