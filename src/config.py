"""
Gold-Silver-Intelligence Configuration Module
Loads environment variables for API keys and settings.
Supports: Gemini (primary) + Perplexity (fallback)
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


# === LLM API Configuration ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# === Search API ===
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# === Telegram Bot ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# === Log Configuration Status ===
available_llm = []
if GEMINI_API_KEY:
    available_llm.append("Gemini [Priority 1]")
if PERPLEXITY_API_KEY:
    available_llm.append("Perplexity [Priority 2]")

if available_llm:
    print(f"[CONFIG] LLM APIs: {', '.join(available_llm)}")
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
