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
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# === Search API ===
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# === Telegram Bot ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# === Log available API keys ===
available_apis = []
if PERPLEXITY_API_KEY:
    available_apis.append("Perplexity [Priority 1]")
if GEMINI_API_KEY:
    available_apis.append("Gemini [Priority 2]")
if GLM_API_KEY:
    available_apis.append("ZhipuAI (GLM) [Priority 3]")
if OPENAI_API_KEY:
    available_apis.append("OpenAI [Priority 4]")

if available_apis:
    print(f"[CONFIG] Available LLM APIs: {', '.join(available_apis)}")
else:
    print("[CONFIG] WARNING: No LLM API key configured!")

if SERPER_API_KEY:
    print("[CONFIG] Serper API: Configured ✓")
else:
    print("[CONFIG] WARNING: SERPER_API_KEY not configured!")

if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    print("[CONFIG] Telegram: Configured ✓")
else:
    print("[CONFIG] WARNING: Telegram not fully configured!")
