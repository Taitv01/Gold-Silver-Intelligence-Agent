"""
Gold-Silver-Intelligence Configuration Module
Loads environment variables for API keys and settings.
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


# === LLM API Configuration ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# === Search API ===
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# === Telegram Bot ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# === AgentScope Model Configuration ===
# Defaults to Gemini, fallback to OpenAI
if GEMINI_API_KEY:
    MODEL_CONFIG = {
        "config_name": "gemini",
        "model_type": "gemini_chat",
        "model_name": "gemini-2.0-flash",
        "api_key": GEMINI_API_KEY,
    }
elif OPENAI_API_KEY:
    MODEL_CONFIG = {
        "config_name": "openai",
        "model_type": "openai_chat",
        "model_name": "gpt-4o-mini",
        "api_key": OPENAI_API_KEY,
    }
else:
    MODEL_CONFIG = None
    print("[WARN] No LLM API key found. Set GEMINI_API_KEY or OPENAI_API_KEY.")
