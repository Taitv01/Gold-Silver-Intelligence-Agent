"""
Gold-Silver-Intelligence Telegram Bot Module
Sends alerts and reports via Telegram Bot API.
"""
import time
import requests
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


TELEGRAM_MAX_LENGTH = 4096
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3


def _split_message(message: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list:
    """
    Split a long message into chunks that fit Telegram's limit.
    Splits at line boundaries to preserve formatting.
    """
    if len(message) <= max_length:
        return [message]

    chunks = []
    while message:
        if len(message) <= max_length:
            chunks.append(message)
            break

        split_pos = message.rfind("\n", 0, max_length)
        if split_pos == -1:
            split_pos = max_length

        chunks.append(message[:split_pos])
        message = message[split_pos:].lstrip("\n")

    return chunks


def send_alert(message: str, parse_mode: str = "Markdown") -> bool:
    """
    Send a message to Telegram chat. Automatically splits long messages.

    Args:
        message: The message text to send
        parse_mode: Message format ('Markdown' or 'HTML')

    Returns:
        True if all parts sent successfully, False otherwise
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ERROR] Telegram credentials not configured.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = _split_message(message)
    all_sent = True

    for i, chunk in enumerate(chunks):
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": parse_mode,
        }

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(url, json=payload, timeout=10)

                if response.status_code == 429:
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY_SECONDS * (attempt + 1)
                        print(f"[WARN] Telegram rate limited, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"[ERROR] Telegram rate limit exceeded after {MAX_RETRIES} attempts")
                        all_sent = False
                        break

                response.raise_for_status()
                if len(chunks) > 1:
                    print(f"[OK] Telegram message part {i + 1}/{len(chunks)} sent.")
                else:
                    print("[OK] Telegram message sent.")
                break

            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"[WARN] Telegram send failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    print(f"[ERROR] Failed to send Telegram message: {e}")
                    all_sent = False

    return all_sent


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
