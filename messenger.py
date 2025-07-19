import os
import httpx
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def format_signal_message(signal_data: Dict[str, Any]) -> str:
    try:
        signal = signal_data.get("signal", "N/A").upper()
        symbol = signal_data.get("symbol", "N/A")
        timeframe = signal_data.get("timeframe", "N/A")
        price = float(signal_data.get("price", 0.0))
        tp = float(signal_data.get("tp", 0.0))
        sl = float(signal_data.get("sl", 0.0))
        reason = signal_data.get("reason", "No specific reason provided.")
        confidence = float(signal_data.get("confidence", 0.0))
        tier = signal_data.get("tier", "N/A")
        icon = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
        message = (
            f"🚀 *ScalpMaster AI - نیا سگنل!* 🚀\n\n"
            f"*SIGNAL:*  `{signal}` {icon}\n"
            f"*PAIR:*    `{symbol} ({timeframe})`\n"
            f"*PRICE:*   `{price:.5f}`\n"
            f"*TP:*      `{tp:.5f}`\n"
            f"*SL:*      `{sl:.5f}`\n\n"
            f"*REASON:* {reason}\n"
            f"*CONFIDENCE:* {confidence:.2f}% ({tier})"
        )
        return message
    except Exception as e:
        print(f"ERROR formatting Telegram message: {e}")
        return f"Error processing signal data: {signal_data}"

async def send_telegram_message(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram token or chat ID is not set. Skipping message.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to send Telegram message. Status: {response.status_code}, Response: {response.text}")
        else:
            print("✅ Telegram message sent successfully!")
    except httpx.RequestError as e:
        print(f"❌ HTTP Request Error sending Telegram message: {e}")
    except Exception as e:
        print(f"❌ Unexpected error sending Telegram message: {e}")
        
