from fastapi import FastAPI
import requests
import urllib.parse

from agents.core_controller import generate_final_signal

app = FastAPI()

TWELVE_DATA_API_KEY = "1d3c362a1459423cbc1d24e2a408098b"

@app.get("/")
def home():
    return {"message": "API is running successfully 🚀"}

@app.get("/final-signal/{symbol}")
def final_signal(symbol: str):
    decoded_symbol = symbol.replace("-", "/")  # use XAU-USD format in URL

    # Fetch latest 5 candles
    url = f"https://api.twelvedata.com/time_series?symbol={decoded_symbol}&interval=1min&outputsize=5&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        return {"error": "Failed to fetch market data", "details": data}

    candles = data["values"]
    result = generate_final_signal(decoded_symbol, candles)

    # Optional: Telegram
    try:
        message = f"**{result['signal']}** {decoded_symbol} ⚡️\n\n" \
                  f"Risk: {result['risk']}\n" \
                  f"News: {result['news']}\n" \
                  f"Pattern: {result['pattern']}\n" \
                  f"Reason: {result['reason']}\n" \
                  f"Confidence: {result['confidence']}%\n" \
                  f"Tier: {result['tier']}"
        # send_telegram_message(message)  # Uncomment if function exists
    except Exception as e:
        print("Telegram Error:", e)

    return result
