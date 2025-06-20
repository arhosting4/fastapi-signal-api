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
def home():
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

    return {
        "pair": pair,
        "signal": core,
        "pattern": pattern,
        "reason": reason,
        "confidence": confidence,
        "tier": tier
    }

@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    decoded_symbol = urllib.parse.unquote(symbol)

    # Fetch real market data from Twelve Data
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "Failed to fetch market data", "details": data}

    candles = data["values"]
    result = generate_final_signal(decoded_symbol)

    message = f"**{result['signal']}** {decoded_symbol.upper()} ⚡️\n\n" \
              f"Risk: {result['risk']}\n" \
              f"News: {result['news']}\n" \
              f"Pattern: {result['pattern']}\n" \
              f"Reason: {result['reason']}\n" \
              f"Confidence: {result['confidence']}%\n"

    send_telegram_message(message)

    return {
        "pair": decoded_symbol,
        "signal": result["signal"],
        "pattern": result["pattern"],
        "risk": result["risk"],
        "news": result["news"],
        "reason": result["reason"],
        "confidence": result["confidence"]
    }
