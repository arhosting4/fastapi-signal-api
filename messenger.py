# filename: messenger.py

import os
import logging
import httpx
from typing import Dict, Any

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Individual or group

logger = logging.getLogger(__name__)

async def send_signal_to_telegram(signal_data: Dict[str, Any]):
    """
    سگنل ڈیٹا کو ٹیلیگرام پر بھیجتا ہے۔
    signal_data: SignalData model سے dict (model_dump()) expected
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials set نہیں — message skip کر دیا گیا۔")
        return

    # Format message
    msg = (
        f"📡 New Signal\n"
        f"↪️ {signal_data.get('symbol')} | {signal_data.get('signal_type').upper()} ({signal_data.get('timeframe')})\n"
        f"🎯 Entry: {signal_data.get('entry_price')}\n"
        f"📈 TP: {signal_data.get('tp_price')} | 🛡️ SL: {signal_data.get('sl_price')}\n"
        f"🔢 Confidence: {signal_data.get('confidence')}%\n"
        f"🏅 Tier: {signal_data.get('tier', 'N/A')}\n"
        f"🕒 Time: {signal_data.get('timestamp')}\n"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10)
            if resp.status_code != 200:
                logger.error(f"Telegram send error: {resp.status_code} - {resp.text}")
            else:
                logger.info("📩 سگنل کامیابی سے ٹیلیگرام پر بھیج دیا گیا۔")
    except Exception as e:
        logger.error(f"Telegram message failed: {e}", exc_info=True)
        
