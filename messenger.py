import os
import httpx
from dotenv import load_dotenv
from typing import Dict

# .env فائل سے ماحول کے متغیرات لوڈ کریں
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def format_signal_message(signal_data: Dict) -> str:
    """
    سگنل ڈیٹا کو ایک خوبصورت ٹیلیگرام پیغام میں فارمیٹ کرتا ہے۔
    """
    signal = signal_data.get("signal", "N/A").upper()
    symbol = signal_data.get("symbol", "N/A")
    timeframe = signal_data.get("timeframe", "N/A")
    price = signal_data.get("price", 0.0)
    tp = signal_data.get("tp", 0.0)
    sl = signal_data.get("sl", 0.0)
    reason = signal_data.get("reason", "No specific reason provided.")
    confidence = signal_data.get("confidence", 0.0)
    tier = signal_data.get("tier", "N/A")

    # سگنل کی قسم کے مطابق آئیکن
    icon = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"

    message = (
        f"🚀 **ScalpMaster AI - نیا سگنل!** 🚀\n\n"
        f"**SIGNAL:**  `{signal}` {icon}\n"
        f"**PAIR:**    `{symbol} ({timeframe})`\n"
        f"**PRICE:**   `{price:.5f}`\n"
        f"**TP:**      `{tp:.5f}`\n"
        f"**SL:**      `{sl:.5f}`\n\n"
        f"**REASON:** {reason}\n"
        f"**CONFIDENCE:** {confidence:.2f}% ({tier})"
    )
    return message

async def send_telegram_message(message: str):
    """
    فارمیٹ شدہ پیغام کو ٹیلیگرام پر بھیجتا ہے۔
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram token or chat ID is not set. Skipping message.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown' # تاکہ ہم بولڈ اور دیگر فارمیٹنگ استعمال کر سکیں
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status() # اگر کوئی ایرر ہو تو استثناء پیدا کریں
        print("✅ Telegram message sent successfully!")
    except httpx.HTTPStatusError as e:
        print(f"❌ Failed to send Telegram message. Status: {e.response.status_code}, Response: {e.response.text}")
    except Exception as e:
        print(f"❌ An unexpected error occurred while sending Telegram message: {e}")

                                         
