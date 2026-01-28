"""
Gold-Silver-Intelligence Configuration Module
Loads environment variables for API keys and settings.
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


# === LLM API Configuration ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")  # Groq (FREE, Priority 1)
ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")    # Z.AI GLM (Fallback 1)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # Gemini (Fallback 2)

# === Search API ===
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# === Telegram Bot ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# === Log configuration status ===
print("=" * 50)
print("[DEBUG] Environment Variables Check:")
print(f"  GROQ_API_KEY length: {len(GROQ_API_KEY) if GROQ_API_KEY else 0}")
print(f"  ZAI_API_KEY length: {len(ZAI_API_KEY) if ZAI_API_KEY else 0}")
print(f"  GEMINI_API_KEY length: {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0}")
print(f"  SERPER_API_KEY length: {len(SERPER_API_KEY) if SERPER_API_KEY else 0}")
print("=" * 50)

print(f"[CONFIG] GROQ_API_KEY (Llama 3.3 70B): {'Configured ✓' if GROQ_API_KEY else 'NOT SET ❌'}")
print(f"[CONFIG] ZAI_API_KEY (Z.AI GLM): {'Configured ✓' if ZAI_API_KEY else 'NOT SET'}")
print(f"[CONFIG] GEMINI_API_KEY: {'Configured ✓' if GEMINI_API_KEY else 'NOT SET'}")
print(f"[CONFIG] SERPER_API_KEY: {'Configured ✓' if SERPER_API_KEY else 'NOT SET ❌'}")
print(f"[CONFIG] Telegram: {'Configured ✓' if (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) else 'NOT SET ❌'}")

# Priority info
if GROQ_API_KEY:
    print("[CONFIG] LLM Priority: Groq (FREE - Llama 3.3 70B)")
elif ZAI_API_KEY:
    print("[CONFIG] LLM Priority: Z.AI GLM")
elif GEMINI_API_KEY:
    print("[CONFIG] LLM Priority: Gemini")
else:
    print("[CONFIG] ⚠️ WARNING: No LLM API key configured!")
