import os
import httpx
from dotenv import load_dotenv
from typing import Dict, Any

# .env فائل سے ماحول کے متغیرات لوڈ کریں
# یہ لائن یقینی بناتی ہے کہ اگر .env فائل موجود ہے تو وہ لوڈ ہو
load_dotenv()

# ماحول کے متغیرات کو محفوظ طریقے سے حاصل کریں
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def format_signal_message(signal_data: Dict[str, Any]) -> str:
    """
    سگنل ڈیٹا کو ایک خوبصورت ٹیلیگرام پیغام میں فارمیٹ کرتا ہے۔
    """
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

        # سگنل کی قسم کے مطابق آئیکن
        icon = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"

        # پیغام کی تشکیل
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
        # اگر فارمیٹنگ میں کوئی مسئلہ ہو تو ایک سادہ پیغام واپس کریں
        return f"Error processing signal data: {signal_data}"


async def send_telegram_message(message: str):
    """
    فارمیٹ شدہ پیغام کو ٹیلیگرام پر بھیجتا ہے۔
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram token or chat ID is not set in environment variables. Skipping message.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown' # تاکہ ہم بولڈ (* *) اور کوڈ (` `) فارمیٹنگ استعمال کر سکیں
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            
            # اگر ٹیلیگرام سے کوئی ایرر آئے تو اسے لاگ کریں
            if response.status_code != 200:
                print(f"❌ Failed to send Telegram message. Status: {response.status_code}, Response: {response.text}")
            else:
                print("✅ Telegram message sent successfully!")

    except httpx.RequestError as e:
        print(f"❌ HTTP Request Error while sending Telegram message: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred while sending Telegram message: {e}")

