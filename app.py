from fastapi import FastAPI
import requests

from agents.core_controller import generate_final_signal

app = FastAPI()

# ✅ Twelve Data API Key
TWELVE_DATA_API_KEY = "1d3c362a1459423cbc1d24e2a408098b"

# ✅ Telegram Credentials
TELEGRAM_TOKEN = "7010222145:AAHsV2XTAK1F1yTaN0k-TMPoL1S9abl7p2k"
TELEGRAM_CHAT_ID = "@ScalpMasterSignalsAi"

# ✅ Telegram Send Function
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=data)
        if not response.ok:
            print("Telegram send error:", response.text)
    except Exception as e:
        print("Telegram exception:", e)

# ✅ Root Route
@app.get("/")
def home():
    return {"message": "API is running successfully 🚀"}

# ✅ Final Signal Route
@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    decoded_symbol = symbol.replace("-", "/")  # Use "XAU-USD" in browser, converts to "XAU/USD"

    # Get market candles
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "Failed to fetch market data", "details": data}

    candles = data["values"]

    try:
        result = generate_final_signal(decoded_symbol, candles)
    except Exception as e:
        return {"error": "Signal generation failed", "details": str(e)}

    # Telegram Signal Send
    try:
        message = f"*{result['signal'].upper()}* signal for `{decoded_symbol}` ⚡️\n\n" \
                  f"*Risk:* {result['risk']}\n" \
                  f"*News:* {result['news']}\n" \
                  f"*Pattern:* {result['pattern']}\n" \
                  f"*Reason:* {result['reason']}\n" \
                  f"*Confidence:* {result['confidence']}%\n" \
                  f"*Tier:* {result['tier']}"
        send_telegram_message(message)
    except Exception as e:
        print("Telegram error:", e)

    return result
