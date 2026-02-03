"""
Gold-Silver-Intelligence Telegram Bot Module
Sends alerts and reports via Telegram Bot API.
"""
import requests
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_alert(message: str, parse_mode: str = "Markdown") -> bool:
    """
    Send a message to Telegram chat.

    Args:
        message: The message text to send
        parse_mode: Message format ('Markdown' or 'HTML')

    Returns:
        True if successful, False otherwise
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ERROR] Telegram credentials not configured.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("[OK] Telegram message sent.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to send Telegram message: {e}")
        return False


def send_report(title: str, content: str) -> bool:
    """
    Send a formatted report to Telegram.

    Args:
        title: Report title
        content: Report body

    Returns:
        True if successful, False otherwise
    """
    message = f"📊 *{title}*\n\n{content}"
    return send_alert(message)
