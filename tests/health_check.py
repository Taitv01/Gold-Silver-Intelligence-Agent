"""
Gold-Silver Intelligence Agent - Health Check Script
Validates all API connections before running main analysis.
"""
import os
import sys
import requests

# Add project root to path
sys.path.insert(0, ".")

from src.config import (
    GEMINI_API_KEY, 
    OPENAI_API_KEY, 
    GLM_API_KEY,
    SERPER_API_KEY, 
    TELEGRAM_BOT_TOKEN, 
    TELEGRAM_CHAT_ID
)


def check_serper_api() -> bool:
    """Test Serper API connection."""
    print("\n🔍 Checking Serper API...")
    
    if not SERPER_API_KEY:
        print("   ❌ SERPER_API_KEY not configured")
        return False
    
    try:
        url = "https://google.serper.dev/news"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {"q": "gold price", "num": 1}
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        news_count = len(data.get("news", []))
        print(f"   ✅ Serper API OK - Found {news_count} news article(s)")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Serper API failed: {e}")
        return False


def check_telegram_bot() -> bool:
    """Test Telegram Bot connection."""
    print("\n📱 Checking Telegram Bot...")
    
    if not TELEGRAM_BOT_TOKEN:
        print("   ❌ TELEGRAM_BOT_TOKEN not configured")
        return False
    
    if not TELEGRAM_CHAT_ID:
        print("   ❌ TELEGRAM_CHAT_ID not configured")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get("ok"):
            bot_name = data["result"].get("username", "Unknown")
            print(f"   ✅ Telegram Bot OK - @{bot_name}")
            return True
        else:
            print(f"   ❌ Telegram Bot error: {data}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Telegram API failed: {e}")
        return False


def check_llm_apis() -> dict:
    """Check which LLM APIs are configured."""
    print("\n🤖 Checking LLM APIs...")
    
    results = {
        "gemini": False,
        "glm": False,
        "openai": False,
        "any_available": False
    }
    
    if GLM_API_KEY:
        print("   ✅ GLM_API_KEY configured (ZhipuAI)")
        results["glm"] = True
        results["any_available"] = True
    else:
        print("   ⚠️  GLM_API_KEY not configured")
    
    if GEMINI_API_KEY:
        print("   ✅ GEMINI_API_KEY configured")
        results["gemini"] = True
        results["any_available"] = True
    else:
        print("   ⚠️  GEMINI_API_KEY not configured")
    
    if OPENAI_API_KEY:
        print("   ✅ OPENAI_API_KEY configured")
        results["openai"] = True
        results["any_available"] = True
    else:
        print("   ⚠️  OPENAI_API_KEY not configured")
    
    if not results["any_available"]:
        print("   ❌ No LLM API keys configured!")
    
    return results


def run_health_check() -> bool:
    """Run all health checks and return overall status."""
    print("=" * 50)
    print("🏥 Gold-Silver Intelligence Agent - Health Check")
    print("=" * 50)
    
    all_passed = True
    
    # Check Serper API
    if not check_serper_api():
        all_passed = False
    
    # Check Telegram
    if not check_telegram_bot():
        all_passed = False
    
    # Check LLM APIs
    llm_status = check_llm_apis()
    if not llm_status["any_available"]:
        all_passed = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ Health Check PASSED - All systems operational")
    else:
        print("⚠️  Health Check COMPLETED with warnings")
    print("=" * 50)
    
    return all_passed


if __name__ == "__main__":
    success = run_health_check()
    sys.exit(0 if success else 1)
