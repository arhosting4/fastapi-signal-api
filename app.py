# app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
from src.agents.strategybot import generate_core_signal  # ✅ Corrected path

app = FastAPI()

# Load secrets from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Enable CORS (optional, useful for frontend testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CandleRequest(BaseModel):
    symbol: str
    timeframe: str
    candles: list

@app.get("/")
def root():
    return {"status": "live"}

@app.post("/final-signal/{symbol}")
def final_signal(symbol: str, req: CandleRequest):
    data = req.dict()
    closes = data["candles"]
    tf = data["timeframe"]
    
    result = {
        "symbol": symbol.upper(),
        "signal": generate_core_signal(symbol, tf, closes),
        "pattern": "Bullish Engulfing",  # static for now
        "risk": "Normal",
        "news": "Clear",
        "reason": "Mixed or neutral signals; no strong alignment",
        "confidence": 52.25,
        "tier": "Tier 5 - Weak"
    }

    # Send Telegram Message
    try:
        message = (
            f"🦾 *{result['signal'].upper()}* Signal\n"
            f"🧠 *Pattern:* {result['pattern']}\n"
            f"📊 *Risk:* {result['risk']}\n"
            f"📰 *News:* {result['news']}\n"
            f"🔍 *Reason:* {result['reason']}\n"
            f"🎯 *Confidence:* {result['confidence']}%\n"
            f"🏅 *Tier:* {result['tier']}"
        )
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
