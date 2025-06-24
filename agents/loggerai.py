# src/agents/loggerai.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str):
    """
    Sends a formatted message to the configured Telegram bot/channel.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram config missing.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, data=payload)
        print("✅ Telegram sent:", response.status_code)
    except Exception as e:
        print("❌ Telegram error:", str(e))
