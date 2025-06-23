from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests

from strategybot import generate_core_signal
from reasonbot import reason_analysis
from riskguardian import assess_risk
from patternai import detect_pattern
from tierbot import get_tier_label
from sentinel import news_sentiment
from feedback_memory import store_feedback

app = FastAPI()

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telegram config
TELEGRAM_TOKEN = "7010222145:AAFSYuy6fbX3HxLHYbCzAeX479TRf9Cbefc"
TELEGRAM_CHAT_ID = "@ScalpMasterSignalsAi"

# Request model
class CandleData(BaseModel):
    symbol: str
    tf: str
    values: list

# Telegram function
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

# API endpoint
@app.post("/final-signal/{symbol}")
async def final_signal(symbol: str, data: CandleData):
    try:
        closes = data.values
        tf = data.tf

        core_signal = generate_core_signal(symbol, tf, closes)
        if core_signal == "wait":
            return {"status": "no-signal", "error": "Strategy failed or not enough data"}

        reason = reason_analysis(closes)
        risk = assess_risk(closes)
        pattern = detect_pattern(closes)
        news = news_sentiment(symbol)
        tier = get_tier_label(core_signal, risk, news)

        result = {
            "symbol": symbol,
            "signal": core_signal,
            "reason": reason,
            "risk": risk,
            "pattern": pattern,
            "news": news,
            "tier": tier,
            "confidence": 52.25  # static value for now
        }

        # Telegram message
        try:
            message = (
                f"📉 *{result['signal'].upper()}* Signal for {result['symbol']}\n"
                f"🧠 *Pattern:* {result['pattern']}\n"
                f"📊 *Risk:* {result['risk']}\n"
                f"📰 *News:* {result['news']}\n"
                f"🔍 *Reason:* {result['reason']}\n"
                f"🎯 *Confidence:* {result['confidence']}%\n"
                f"🥇 *Tier:* {result['tier']}"
            )
            send_telegram_message(message)
        except Exception as e:
            print("⚠️ Telegram Error:", str(e))

        store_feedback(symbol, result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/")
def read_root():
    return {"status": "API is running"}
