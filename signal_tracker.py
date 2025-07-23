import requests
from datetime import datetime
from src.database.models import SessionLocal
from database_crud import save_live_signal


def fetch_crypto_signal():
    url = "https://api.binance.com/api/v3/ticker/price"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        # Example: Pick top 5 USDT pairs
        usdt_pairs = [d for d in data if "USDT" in d["symbol"]][:5]
        signal_time = datetime.utcnow()

        db = SessionLocal()
        for pair in usdt_pairs:
            signal_data = {
                "symbol": pair["symbol"],
                "price": float(pair["price"]),
                "source": "Binance API",
                "created_at": signal_time,
            }
            save_live_signal(db, signal_data)

        db.close()
        print("✅ Live signals saved successfully.")
    else:
        print(f"❌ Failed to fetch signals, status code: {response.status_code}")
