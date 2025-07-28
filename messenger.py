# filename: messenger.py

import os
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_alert(signal_data: Dict[str, Any]):
    """ایک نئے سگنل کے لیے فارمیٹ شدہ ٹیلیگرام الرٹ بھیجتا ہے۔"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("ٹیلیگرام بوٹ ٹوکن یا چیٹ آئی ڈی سیٹ نہیں ہے۔ الرٹ نہیں بھیجا جا رہا۔")
        return

    # ★★★ ذہین کلیدی نام کا انتخاب ★★★
    # یہ چیک کرے گا کہ آیا 'signal' موجود ہے، اگر نہیں تو 'signal_type' استعمال کرے گا۔
    signal = (signal_data.get('signal') or signal_data.get('signal_type', 'N/A')).upper()
    symbol = signal_data.get('symbol', 'N/A')
    
    # یہ قیمت، ٹی پی، اور ایس ایل کے لیے دونوں ممکنہ ناموں کو چیک کرے گا۔
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
    params = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=params)
            response.raise_for_status()
        logger.info(f"{symbol} کے لیے نیا ٹیلیگرام سگنل الرٹ کامیابی سے بھیجا گیا۔")
    except Exception as e:
        logger.error(f"نیا ٹیلیگرام الرٹ بھیجنے میں ناکام: {e}", exc_info=True)

async def send_signal_update_alert(updated_signal: Dict[str, Any]):
    """ایک اپ ڈیٹ شدہ سگنل کے لیے فارمیٹ شدہ ٹیلیگرام الرٹ بھیجتا ہے۔"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    symbol = updated_signal.get('symbol', 'N/A')
    confidence = updated_signal.get('confidence', 0.0)
    reason = updated_signal.get('reason', 'کوئی وجہ فراہم نہیں کی گئی۔')
    signal_type = (updated_signal.get('signal') or updated_signal.get('signal_type', 'N/A')).upper()

    icon = "📈"
    message = (
        f"{icon} *ScalpMaster AI سگنل اپ ڈیٹ* {icon}\n\n"
        f"*{signal_type} {symbol}* سگنل کی تصدیق ہو گئی ہے!\n\n"
        f"🔥 *نیا اعتماد:* {confidence:.2f}%\n\n"
        f"📝 *تازہ ترین AI وجہ:* _{reason}_"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=params)
            response.raise_for_status()
        logger.info(f"{symbol} کے لیے ٹیلیگرام سگنل اپ ڈیٹ الرٹ کامیابی سے بھیجا گیا۔")
    except Exception as e:
        logger.error(f"ٹیلیگرام سگنل اپ ڈیٹ الرٹ بھیجنے میں ناکام: {e}", exc_info=True)
        
