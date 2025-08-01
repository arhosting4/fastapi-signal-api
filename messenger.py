import os
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# 🔐 ٹیلیگرام سیٹنگز ماحولیاتی متغیرات سے لی جا رہی ہیں
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==============================================================================
# 📤 سگنل الرٹ ٹیلیگرام پر بھیجیں
# ==============================================================================
async def send_telegram_alert(signal_data: Dict[str, Any]):
    """ایک نئے سگنل کے لیے فارمیٹ شدہ ٹیلیگرام الرٹ بھیجتا ہے۔"""

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️ ٹیلیگرام بوٹ ٹوکن یا چیٹ آئی ڈی سیٹ نہیں ہے۔ الرٹ نہیں بھیجا جا رہا۔")
        return

    try:
        signal = (signal_data.get('signal') or signal_data.get('signal_type', 'N/A')).upper()
        symbol = signal_data.get('symbol', 'N/A')
        price = signal_data.get('price') or signal_data.get('entry_price', 0.0)
        tp = signal_data.get('tp') or signal_data.get('tp_price', 0.0)
        sl = signal_data.get('sl') or signal_data.get('sl_price', 0.0)
        confidence = signal_data.get('confidence', 0.0)
        tier = signal_data.get('tier', 'N/A')
        reason = signal_data.get('reason', 'کوئی وجہ فراہم نہیں کی گئی۔')

        icon = "🟢" if signal == "BUY" else "🔴"

        message = (
            f"{icon} *ScalpMaster AI نیا سگنل* {icon}\n\n"
            f"*{signal} {symbol}*\n\n"
            f"🔹 *انٹری قیمت:* `{price:.5f}`\n"
            f"🔸 *ٹیک پرافٹ:* `{tp:.5f}`\n"
            f"🔸 *اسٹاپ لاس:* `{sl:.5f}`\n\n"
            f"📈 *اعتماد:* {confidence:.2f}%\n"
            f"🎖️ *درجہ:* {tier}\n\n"
            f"📝 *AI وجہ:* _{reason}_"
        )

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)

    except Exception as e:
        logger.error(f"❌ ٹیلیگرام الرٹ بھیجنے میں خرابی: {e}", exc_info=True)

# ==============================================================================
# 🆕 سگنل اپڈیٹ الرٹ (مثلاً price breach یا confirmation)
# ==============================================================================
def send_signal_update_alert(update_data: Dict[str, Any]):
    """اگر کوئی سگنل اپڈیٹ ہو (جیسے confirmation یا breach) تو الرٹ بھیجتا ہے۔"""
    logger.info(f"🔔 سگنل اپڈیٹ: {update_data.get('symbol', 'N/A')} - {update_data.get('status', 'N/A')}")
