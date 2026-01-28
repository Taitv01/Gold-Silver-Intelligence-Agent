"""
Gold-Silver-Intelligence Configuration Module
Loads environment variables for API keys and settings.
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


# === LLM API Configuration ===
ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")  # Z.AI GLM API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# === Search API ===
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# === Telegram Bot ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# === Log configuration status ===
print("=" * 50)
print("[DEBUG] Environment Variables Check:")
print(f"  ZAI_API_KEY length: {len(ZAI_API_KEY) if ZAI_API_KEY else 0}")
print(f"  GEMINI_API_KEY length: {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0}")
print(f"  SERPER_API_KEY length: {len(SERPER_API_KEY) if SERPER_API_KEY else 0}")
print("=" * 50)

print(f"[CONFIG] ZAI_API_KEY (Z.AI GLM): {'Configured ✓' if ZAI_API_KEY else 'NOT SET ❌'}")
print(f"[CONFIG] GEMINI_API_KEY: {'Configured ✓' if GEMINI_API_KEY else 'NOT SET ❌'}")
print(f"[CONFIG] SERPER_API_KEY: {'Configured ✓' if SERPER_API_KEY else 'NOT SET ❌'}")
print(f"[CONFIG] Telegram: {'Configured ✓' if (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) else 'NOT SET ❌'}")

# Priority info
if ZAI_API_KEY:
    print("[CONFIG] LLM Priority: Z.AI GLM (Primary)")
elif GEMINI_API_KEY:
    print("[CONFIG] LLM Priority: Gemini (Primary)")
else:
    print("[CONFIG] ⚠️ WARNING: No LLM API key configured!")
