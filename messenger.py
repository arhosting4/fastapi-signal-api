import os
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, before_sleep_log
from typing import Dict, Any

# --- Configuration ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
RETRY_LOG = logging.getLogger(__name__)

# --- Initial Check ---
if not BOT_TOKEN or not CHAT_ID:
    logging.warning("Telegram BOT_TOKEN or CHAT_ID not found in environment variables. Telegram alerts are disabled.")

def format_signal_message(signal_data: Dict[str, Any]) -> str:
    """Formats the signal data into a human-readable message using MarkdownV2."""
    signal_type = signal_data.get('signal', 'N/A').upper()
    symbol = signal_data.get('symbol', 'N/A').replace('/', r'\/') # Escape for MarkdownV2
    timeframe = signal_data.get('timeframe', 'N/A')
    
    icon = "🟢" if signal_type == "BUY" else "🔴"
    
    # Ensure prices are formatted correctly
    entry_price = f"{signal_data.get('entry_price', 0.0):.5f}"
    tp_price = f"{signal_data.get('tp_price', 0.0):.5f}"
    sl_price = f"{signal_data.get('sl_price', 0.0):.5f}"
    
    confidence = f"{signal_data.get('confidence', 0.0):.2f}%"
    reason = signal_data.get('reason', 'No specific reason provided').replace('.', r'\.') # Escape dots

    message = (
        f"{icon} *New AI Signal: {signal_type}*\n\n"
        f"*Symbol:* `{symbol} ({timeframe})`\n"
        f"*Entry:* `{entry_price}`\n"
        f"*Take Profit:* `{tp_price}`\n"
        f"*Stop Loss:* `{sl_price}`\n\n"
        f"*Confidence:* `{confidence}`\n"
        f"*Reason:* _{reason}_"
    )
    return message

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    before_sleep=before_sleep_log(RETRY_LOG, logging.WARNING)
)
async def send_telegram_alert(signal_data: Dict[str, Any]):
    """Sends a formatted message to a Telegram chat with retry logic."""
    if not BOT_TOKEN or not CHAT_ID:
        return

    message = format_signal_message(signal_data)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'MarkdownV2'
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        logging.info(f"Successfully sent Telegram alert for symbol {signal_data.get('symbol')}.")
    except httpx.HTTPStatusError as e:
        logging.error(f"Failed to send Telegram alert. Status: {e.response.status_code}, Response: {e.response.text}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred while sending Telegram alert: {e}")
        raise
        
