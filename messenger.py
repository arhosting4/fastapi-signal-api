# filename: messenger.py

import os
import httpx

# یہ ماحول کے متغیرات (environment variables) سے آپ کی ٹیلیگرام کی معلومات حاصل کرے گا
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(signal_data: dict):
    """
    ایک نئے سگنل کی اطلاع ٹیلیگرام پر بھیجتا ہے۔
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("--- MESSENGER: Telegram credentials not set. Skipping message. ---")
        return

    # پیغام کو فارمیٹ کرنا
    signal = signal_data.get('signal', 'N/A').upper()
    symbol = signal_data.get('symbol', 'N/A')
    price = signal_data.get('price', 0)
    confidence = signal_data.get('confidence', 0)
    tier = signal_data.get('tier', 'N/A')
    tp = signal_data.get('tp', 0)
    sl = signal_data.get('sl', 0)
    reason = signal_data.get('reason', 'No reason provided.')

    # سگنل کی قسم کے مطابق ایموجی
    emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"

    message = (
        f"{emoji} *New Signal Alert* {emoji}\n\n"
        f"*{signal} {symbol}*\n"
        f"--------------------------------------\n"
        f"🔹 *Entry Price:* `{price:.5f}`\n"
        f"🔹 *Confidence:* `{confidence:.2f}%`\n"
        f"🔹 *Tier:* `{tier}`\n"
        f"--------------------------------------\n"
        f"📈 *Take Profit (TP):* `{tp:.5f}`\n"
        f"🛑 *Stop Loss (SL):* `{sl:.5f}`\n"
        f"--------------------------------------\n"
        f"📝 *Reason:* _{reason}_"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=params)
            response.raise_for_status() # اگر کوئی خرابی ہو تو ایرر دے
        print(f"--- MESSENGER: Successfully sent message to Telegram for {symbol}. ---")
    except httpx.HTTPStatusError as e:
        print(f"--- MESSENGER ERROR: Failed to send message. Status: {e.response.status_code}, Response: {e.response.text} ---")
    except Exception as e:
        print(f"--- MESSENGER CRITICAL ERROR: An unexpected error occurred: {e} ---")

