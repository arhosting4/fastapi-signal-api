from fastapi import FastAPI
from agents.strategybot import generate_core_signal, fetch_fake_ohlc
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
import requests

from fastapi import FastAPI
import requests
import urllib.parse

app = FastAPI()

# Twelve Data API Key
TWELVE_DATA_API_KEY = "1d3c362a1459423cbc1d24e2a408098b"

@app.get("/")
def home():
    return {"message": "API is running"}

@app.get("/price/{symbol:path}")  # Use :path to allow slashes like XAU/USD
def get_price(symbol: str):
    decoded_symbol = urllib.parse.unquote(symbol)
    url = f"https://api.twelvedata.com/price?symbol={decoded_symbol}&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    return response.json()


TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YourChannelOrUserID"

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

@app.get("/")
def root():
    return {"message": "API is running"}

@app.get("/ohlc/{pair}/{tf}")
def get_ohlc(pair: str, tf: str):
    candles = [fetch_fake_ohlc(pair, tf) for _ in range(10)]
    closes = [c["close"] for c in candles]
    return {"closes": closes}

@app.get("/signal/{pair}/{tf}")
def generate_signal(pair: str, tf: str):
    core = generate_core_signal(pair, tf)
    pattern = detect_patterns(pair, tf)

    if not core or not pattern:
        return {"status": "no-signal", "reason": "Core or pattern failed"}
    
    if check_risk(pair, tf):
        return {"status": "blocked", "reason": "High market risk"}

    if check_news(pair):
        return {"status": "blocked", "reason": "Red news event"}

    reason = generate_reason(core, pattern)
    confidence = get_confidence(pair, tf, core, pattern)
    tier = "Tier 1" if confidence > 80 else "Tier 2"

    message = f"**{core['signal']}** {pair.upper()} ({tf})\nConfidence: {confidence}%\nReason: {reason}\nTier: {tier}"
    send_telegram_message(message)

    return {
        "pair": pair,
        "tf": tf,
        "signal": core["signal"],
        "confidence": confidence,
        "reason": reason,
        "tier": tier
    }
