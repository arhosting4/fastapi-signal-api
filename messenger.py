# filename: messenger.py
import os
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ماحول سے راز لوڈ کریں
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_alert(signal_data: Dict[str, Any]):
    """
    ماحولیاتی متغیرات سے بوٹ ٹوکن اور چیٹ آئی ڈی کا استعمال کرکے ایک فارمیٹ شدہ ٹیلیگرام الرٹ بھیجتا ہے۔
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("ٹیلیگرام بوٹ ٹوکن یا چیٹ آئی ڈی سیٹ نہیں ہے۔ الرٹ نہیں بھیجا جا رہا۔")
        return

    # سگنل ڈیٹا سے اقدار نکالیں
    signal = signal_data.get('signal', 'N/A').upper()
    symbol = signal_data.get('symbol', 'N/A')
    price = signal_data.get('price', 0.0)
    tp = signal_data.get('tp', 0.0)
    sl = signal_data.get('sl', 0.0)
    confidence = signal_data.get('confidence', 0.0)
    tier = signal_data.get('tier', 'N/A')
    reason = signal_data.get('reason', 'کوئی وجہ فراہم نہیں کی گئی۔')

    icon = "🟢" if signal == "BUY" else "🔴"
    message = (
        f"{icon} *ScalpMaster AI سگنل* {icon}\n\n"
        f"*{signal} {symbol}*\n\n"
        f"🔹 *انٹری قیمت:* `{price:.5f}`\n"
        f"🔸 *ٹیک پرافٹ:* `{tp:.5f}`\n"
        f"🔸 *اسٹاپ لاس:* `{sl:.5f}`\n\n"
        f"📈 *اعتماد:* {confidence:.2f}%\n"
        f"🎖️ *درجہ:* {tier}\n\n"
        f"📝 *AI وجہ:* _{reason}_"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=params)
            response.raise_for_status() # HTTP غلطیوں کے لیے استثناء اٹھائیں
        logger.info(f"{symbol} کے لیے ٹیلیگرام سگنل الرٹ کامیابی سے بھیجا گیا۔")
    except httpx.HTTPStatusError as e:
        logger.error(f"ٹیلیگرام الرٹ بھیجنے میں ناکام: HTTP {e.response.status_code} - {e.response.text}", exc_info=True)
    except Exception as e:
        logger.error(f"ٹیلیگرام الرٹ بھیجنے میں ناکام: {e}", exc_info=True)
        
