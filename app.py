from fastapi import FastAPI
from agents.strategybot import generate_core_signal, fetch_fake_ohlc
from agents.patternai import detect_patterns
from agents.riskguardian import check_risk
from agents.sentinel import check_news
from agents.reasonbot import generate_reason
from agents.trainerai import get_confidence
from agents.core_controller import fuse_signals, generate_final_signal

import requests
import urllib.parse

app = FastAPI()

# Replace this with your actual working TwelveData API key
TWELVE_DATA_API_KEY = "1d3c362a1459423cbc1d24e2a408098b"

@app.get("/")
def home():
    return {"message": "API is running successfully 🚀"}

# God-level signal endpoint: uses live OHLC and fusion AI
@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    decoded_symbol = symbol.replace("-", "/")  # e.g., XAU-USD becomes XAU/USD

    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "Failed to fetch market data", "details": data}

    candles = data["values"]
    fused = fuse_signals(candles, decoded_symbol)

    # Optional Telegram Message
    try:
        message = f"**{fused['signal']}** {decoded_symbol} ⚡️\n\n" \
                  f"Risk: {fused['risk']}\n" \
                  f"News: {fused['news']}\n" \
                  f"Pattern: {fused['pattern']}\n" \
                  f"Reason: {fused['reason']}\n" \
                  f"Confidence: {fused['confidence']}%\n" \
                  f"Tier: {fused['tier']}"

        send_telegram_message(message)
    except Exception as e:
        print("Telegram error:", e)

    return fused


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

    return {
        "pair": pair,
        "tf": tf,
        "signal": core["signal"],
        "confidence": confidence,
        "reason": reason,
        "tier": tier
    }


# Optional: Telegram Bot Credentials
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YourChannelOrUserID"

def send_telegram_message(message):
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN" or TELEGRAM_CHAT_ID == "YourChannelOrUserID":
        return  # Skip if token not configured

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
