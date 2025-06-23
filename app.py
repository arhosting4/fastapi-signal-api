from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
from strategybot import generate_final_signal

app = FastAPI()

# CORS setup (optional but useful)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Define input format
class SignalRequest(BaseModel):
    symbol: str
    values: list

# Telegram send function
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

# API route
@app.post("/final-signal/{symbol}")
async def final_signal(symbol: str, request: Request):
    try:
        data = await request.json()
        candles = data["values"]
        result = generate_final_signal(symbol, candles)

        # Safe check to avoid KeyError
        if result.get("signal"):
            try:
                message = f"📉 *{result.get('signal', 'N/A')}* Signal\n" \
                          f"🧠 *Pattern:* {result.get('pattern', 'N/A')}\n" \
                          f"📊 *Risk:* {result.get('risk', 'N/A')}\n" \
                          f"📰 *News:* {result.get('news', 'N/A')}\n" \
                          f"🔎 *Reason:* {result.get('reason', 'N/A')}\n" \
                          f"🎯 *Confidence:* {result.get('confidence', 'N/A')}%\n" \
                          f"🥇 *Tier:* {result.get('tier', 'N/A')}"
                send_telegram_message(message)
            except Exception as e:
                print("⚠️ Telegram Error:", str(e))
        else:
            print("⚠️ No signal generated, skipping Telegram message.")

        return result

    except Exception as e:
        return {"status": "error", "message": str(e)}
