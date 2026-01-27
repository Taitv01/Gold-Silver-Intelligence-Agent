"""
Gold-Silver-Intelligence Agents Module
Rewritten for AgentScope 1.0+ API (async-based).
Supports: Gemini, ZhipuAI (GLM), OpenAI as fallback.
"""
import os
import asyncio
import requests
import agentscope
from agentscope.agent import ReActAgent
from agentscope.message import Msg
from agentscope.model import GeminiChatModel, OpenAIChatModel, ZhipuAIChatModel
from agentscope.formatter import GeminiChatFormatter, OpenAIChatFormatter, ZhipuAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from src.config import SERPER_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, GLM_API_KEY


def search_news(query: str, num_results: int = 10) -> list:
    """
    Search for news using Serper API.

    Args:
        query: Search query string
        num_results: Number of results to return

    Returns:
        List of news articles with title, link, snippet
    """
    if not SERPER_API_KEY:
        print("[ERROR] SERPER_API_KEY not configured.")
        return []

    url = "https://google.serper.dev/news"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "num": num_results,
        "tbs": "qdr:d"  # Last 24 hours
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        news = []
        for item in data.get("news", []):
            news.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", ""),
                "date": item.get("date", "")
            })
        return news

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Serper API request failed: {e}")
        return []


# === Agent System Prompts ===

NEWS_HUNTER_PROMPT = """Bạn là NewsHunter - chuyên gia thu thập và lọc tin tức thị trường Vàng/Bạc.

NHIỆM VỤ:
1. Phân tích các tin tức được cung cấp
2. Lọc ra các tin quan trọng liên quan đến:
   - Chính sách lãi suất Fed/FOMC
   - Chiến tranh, xung đột địa chính trị
   - Chỉ số DXY (USD Index)
   - Lạm phát, CPI, việc làm Mỹ
   - Chính sách tiền tệ các ngân hàng trung ương lớn

OUTPUT FORMAT:
📰 **TIN TỨC QUAN TRỌNG**

1. [Tiêu đề tin 1]
   - Nguồn: [source]
   - Tóm tắt: [2-3 câu tóm tắt]

2. [Tiêu đề tin 2]
   ...

Nếu không có tin quan trọng, trả về: "Không có tin đáng chú ý trong 24h qua."
"""

MARKET_ANALYST_PROMPT = """Bạn là MarketAnalyst - chuyên gia phân tích tác động tin tức lên giá Vàng/Bạc.

NHIỆM VỤ:
Dựa trên tin tức được cung cấp, phân tích xu hướng giá Vàng/Bạc.

PHƯƠNG PHÁP PHÂN TÍCH:
- Fed hawkish (tăng lãi suất) → Bearish cho Vàng/Bạc
- Fed dovish (giữ/giảm lãi suất) → Bullish cho Vàng/Bạc
- DXY tăng → Bearish cho Vàng/Bạc
- DXY giảm → Bullish cho Vàng/Bạc
- Bất ổn địa chính trị → Bullish (safe haven)
- Lạm phát cao → Bullish (hedge)

OUTPUT FORMAT:
📊 **PHÂN TÍCH THỊ TRƯỜNG VÀNG/BẠC**

🔹 **Xu hướng Vàng (XAU/USD):** [BULLISH/BEARISH/NEUTRAL]
🔹 **Xu hướng Bạc (XAG/USD):** [BULLISH/BEARISH/NEUTRAL]

**Lý do:**
[Giải thích ngắn gọn 3-5 điểm chính]

**Khuyến nghị:**
[Gợi ý hành động: Mua/Bán/Quan sát]

⚠️ *Đây là phân tích tham khảo, không phải tư vấn đầu tư.*
"""


def get_model_and_formatter():
    """
    Get the appropriate model and formatter based on available API keys.
    Priority: Gemini -> GLM (ZhipuAI) -> OpenAI
    """
    # Priority 1: Gemini
    if GEMINI_API_KEY:
        print("[INFO] Using Gemini API (gemini-2.0-flash)")
        model = GeminiChatModel(
            model_name="gemini-2.0-flash",
            api_key=GEMINI_API_KEY,
        )
        formatter = GeminiChatFormatter()
        return model, formatter
    
    # Priority 2: ZhipuAI (GLM)
    if GLM_API_KEY:
        print("[INFO] Using ZhipuAI GLM API (glm-4-flash)")
        model = ZhipuAIChatModel(
            model_name="glm-4-flash",
            api_key=GLM_API_KEY,
        )
        formatter = ZhipuAIChatFormatter()
        return model, formatter
    
    # Priority 3: OpenAI
    if OPENAI_API_KEY:
        print("[INFO] Using OpenAI API (gpt-4o-mini)")
        model = OpenAIChatModel(
            model_name="gpt-4o-mini",
            api_key=OPENAI_API_KEY,
        )
        formatter = OpenAIChatFormatter()
        return model, formatter
    
    raise ValueError("No LLM API key configured. Set GEMINI_API_KEY, GLM_API_KEY, or OPENAI_API_KEY.")


def get_model_and_formatter_with_fallback():
    """
    Try to get model with automatic fallback if primary fails.
    Tries: Gemini -> GLM -> OpenAI
    """
    errors = []
    
    # Try Gemini first
    if GEMINI_API_KEY:
        try:
            print("[INFO] Trying Gemini API...")
            model = GeminiChatModel(
                model_name="gemini-2.0-flash",
                api_key=GEMINI_API_KEY,
            )
            formatter = GeminiChatFormatter()
            return model, formatter, "Gemini"
        except Exception as e:
            errors.append(f"Gemini: {e}")
            print(f"[WARN] Gemini failed: {e}")
    
    # Fallback to GLM
    if GLM_API_KEY:
        try:
            print("[INFO] Trying ZhipuAI GLM API...")
            model = ZhipuAIChatModel(
                model_name="glm-4-flash",
                api_key=GLM_API_KEY,
            )
            formatter = ZhipuAIChatFormatter()
            return model, formatter, "GLM"
        except Exception as e:
            errors.append(f"GLM: {e}")
            print(f"[WARN] GLM failed: {e}")
    
    # Fallback to OpenAI
    if OPENAI_API_KEY:
        try:
            print("[INFO] Trying OpenAI API...")
            model = OpenAIChatModel(
                model_name="gpt-4o-mini",
                api_key=OPENAI_API_KEY,
            )
            formatter = OpenAIChatFormatter()
            return model, formatter, "OpenAI"
        except Exception as e:
            errors.append(f"OpenAI: {e}")
            print(f"[WARN] OpenAI failed: {e}")
    
    raise ValueError(f"All LLM APIs failed. Errors: {errors}")


async def run_analysis_async(query: str = "gold silver price news") -> str:
    """
    Run the full analysis pipeline (async version).

    Args:
        query: Search query for news

    Returns:
        Final analysis report as string
    """
    print(f"[INFO] Starting analysis pipeline with query: {query}")

    # Step 1: Search for news
    print("[INFO] Fetching news from Serper API...")
    news_items = search_news(query)

    if not news_items:
        return "❌ Không tìm thấy tin tức nào. Vui lòng thử lại sau."

    # Format news for agent
    news_text = "\n\n".join([
