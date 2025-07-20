import os
import httpx

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_alert(signal_data: dict):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    signal = signal_data.get('signal', 'N/A').upper()
    symbol = signal_data.get('symbol', 'N/A')
    price = signal_data.get('price', 0.0)
    tp = signal_data.get('tp', 0.0)
    sl = signal_data.get('sl', 0.0)
    reason = signal_data.get('reason', 'No reason provided.')

    icon = "🟢" if signal == "BUY" else "🔴"
    message = (
        f"{icon} *ScalpMaster AI Signal* {icon}\n\n"
        f"*Action:* {signal} {symbol}\n"
        f"*Entry Price:* `{price:.5f}`\n"
        f"*Take Profit:* `{tp:.5f}`\n"
        f"*Stop Loss:* `{sl:.5f}`\n\n"
        f"*AI Reason:* _{reason}_"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=params)
    except Exception:
        pass
        
