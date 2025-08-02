# filename: messenger.py

import logging
from typing import Dict, Any

import httpx

# مقامی امپورٹس
from config import api_settings

logger = logging.getLogger(__name__)

# --- کنفیگریشن سے مستقل اقدار ---
TELEGRAM_BOT_TOKEN = api_settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = api_settings.TELEGRAM_CHAT_ID

def _normalize_signal_data(signal_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    مختلف ذرائع سے آنے والے سگنل ڈیٹا کو ایک معیاری ساخت میں تبدیل کرتا ہے۔
    اس سے کوڈ کی تکرار کم ہوتی ہے۔
    """
    return {
        "symbol": signal_data.get('symbol', 'N/A'),
        "signal_type": (signal_data.get('signal') or signal_data.get('signal_type', 'N/A')).upper(),
        "entry_price": signal_data.get('price') or signal_data.get('entry_price', 0.0),
        "tp_price": signal_data.get('tp') or signal_data.get('tp_price', 0.0),
        "sl_price": signal_data.get('sl') or signal_data.get('sl_price', 0.0),
        "confidence": signal_data.get('confidence', 0.0),
        "tier": signal_data.get('tier', 'N/A'),
        "reason": signal_data.get('reason', 'کوئی وجہ فراہم نہیں کی گئی۔'),
    }

async def _send_message(message: str, symbol: str, alert_type: str):
    """
    ٹیلیگرام API کو ایک پیغام بھیجنے کے لیے مرکزی فنکشن۔
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("ٹیلیگرام بوٹ ٹوکن یا چیٹ آئی ڈی سیٹ نہیں ہے۔ الرٹ نہیں بھیجا جا رہا۔")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=params)
            response.raise_for_status()
        logger.info(f"'{symbol}' کے لیے ٹیلیگرام {alert_type} الرٹ کامیابی سے بھیجا گیا۔")
    except httpx.HTTPStatusError as e:
        logger.error(f"ٹیلیگرام API سے خرابی ({e.response.status_code}): {e.response.text}")
    except Exception as e:
        logger.error(f"ٹیلیگرام {alert_type} الرٹ بھیجنے میں ناکام: {e}", exc_info=True)

async def send_telegram_alert(signal_data: Dict[str, Any]):
    """ایک نئے سگنل کے لیے فارمیٹ شدہ ٹیلیگرام الرٹ بھیجتا ہے۔"""
    norm_data = _normalize_signal_data(signal_data)
    
    icon = "🟢" if norm_data['signal_type'] == "BUY" else "🔴"
    message = (
        f"{icon} *ScalpMaster AI نیا سگنل* {icon}\n\n"
        f"*{norm_data['signal_type']} {norm_data['symbol']}*\n\n"
        f"🔹 *انٹری قیمت:* `{norm_data['entry_price']:.5f}`\n"
        f"🔸 *ٹیک پرافٹ:* `{norm_data['tp_price']:.5f}`\n"
        f"🔸 *اسٹاپ لاس:* `{norm_data['sl_price']:.5f}`\n\n"
        f"📈 *اعتماد:* {norm_data['confidence']:.2f}%\n"
        f"🎖️ *درجہ:* {norm_data['tier']}\n\n"
        f"📝 *AI وجہ:* _{norm_data['reason']}_"
    )
    
    await _send_message(message, norm_data['symbol'], "نیا سگنل")

async def send_signal_update_alert(updated_signal: Dict[str, Any]):
    """ایک اپ ڈیٹ شدہ سگنل کے لیے فارمیٹ شدہ ٹیلیگرام الرٹ بھیجتا ہے۔"""
    norm_data = _normalize_signal_data(updated_signal)

    icon = "📈"
    message = (
        f"{icon} *ScalpMaster AI سگنل اپ ڈیٹ* {icon}\n\n"
        f"*{norm_data['signal_type']} {norm_data['symbol']}* سگنل کی تصدیق ہو گئی ہے!\n\n"
        f"🔥 *نیا اعتماد:* {norm_data['confidence']:.2f}%\n\n"
        f"📝 *تازہ ترین AI وجہ:* _{norm_data['reason']}_"
    )
    
    await _send_message(message, norm_data['symbol'], "سگنل اپ ڈیٹ")
    
