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
GLM_API_KEY = os.getenv("GLM_API_KEY", "")  # ZhipuAI GLM API

# === Search API ===
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# === Telegram Bot ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# === Log available API keys ===
available_apis = []
if GEMINI_API_KEY:
    available_apis.append("Gemini")
if GLM_API_KEY:
    available_apis.append("ZhipuAI (GLM)")
if OPENAI_API_KEY:
    available_apis.append("OpenAI")

if available_apis:
    print(f"[CONFIG] Available LLM APIs: {', '.join(available_apis)}")
else:
    print("[CONFIG] WARNING: No LLM API key configured!")
