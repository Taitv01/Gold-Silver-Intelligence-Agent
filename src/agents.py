"""
Gold-Silver-Intelligence Agents Module
Supports: Z.AI GLM (primary via OpenAI SDK), Gemini (fallback)
Includes: Rate limit handling with retry logic
"""
import os
import time
import asyncio
import requests
from openai import OpenAI
import agentscope
from agentscope.agent import ReActAgent
from agentscope.message import Msg
from agentscope.model import GeminiChatModel
from agentscope.formatter import GeminiChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from src.config import SERPER_API_KEY, GEMINI_API_KEY, ZAI_API_KEY


# === Rate Limit Configuration ===
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 30


def search_news(query: str, num_results: int = 10) -> list:
    """
    Search for news using Serper API with retry logic.
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
        "tbs": "qdr:d"
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code in [429, 503]:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY_SECONDS
                    print(f"[WARN] Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[ERROR] Rate limit exceeded after {MAX_RETRIES} attempts")
                    return []
            
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
            if attempt < MAX_RETRIES - 1:
                print(f"[WARN] Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print(f"[ERROR] Serper API request failed after {MAX_RETRIES} attempts: {e}")
                return []
    
    return []


# === Z.AI GLM via OpenAI SDK ===

def get_zai_client():
    """
    Get Z.AI client using OpenAI SDK with base_url.
    """
    if not ZAI_API_KEY:
        raise ValueError("ZAI_API_KEY not configured")
    
    client = OpenAI(
        api_key=ZAI_API_KEY,
        base_url="https://api.z.ai/api/paas/v4/"  # Z.AI endpoint
    )
    return client


def call_zai_glm(messages: list, system_prompt: str = "") -> str:
    """
    Call Z.AI GLM API using OpenAI SDK.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        system_prompt: System prompt for the model
        
    Returns:
        Response text from the model
    """
    client = get_zai_client()
    
    # Build messages with system prompt
    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(messages)
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"[DEBUG] Calling Z.AI GLM API via OpenAI SDK...")
            
            response = client.chat.completions.create(
                model="glm-4.7",
                messages=api_messages,
                temperature=0.7,
            )
            
            content = response.choices[0].message.content
            print(f"[DEBUG] Z.AI response received successfully")
            return content
            
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str
            
            if is_rate_limit and attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY_SECONDS * (attempt + 1)
                print(f"[WARN] Z.AI rate limited (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] Z.AI API error: {e}")
                raise e
    
    raise Exception("Z.AI API failed after all retries")


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


def run_analysis_with_zai(query: str = "gold silver price news") -> str:
    """
    Run analysis pipeline using Z.AI GLM API.
    """
    print(f"[INFO] Starting analysis pipeline with query: {query}")

    # Step 1: Search for news
    print("[INFO] Fetching news from Serper API...")
    news_items = search_news(query)

    if not news_items:
        return "❌ Không tìm thấy tin tức nào. Vui lòng thử lại sau."

    # Format news
    news_text = "\n\n".join([
        f"📰 {item['title']}\n"
        f"   Nguồn: {item['source']} | {item['date']}\n"
        f"   {item['snippet']}"
        for item in news_items[:8]
    ])

    print(f"[INFO] Found {len(news_items)} news articles.")

    # Step 2: NewsHunter analyzes news
    print("[INFO] NewsHunter analyzing news (via Z.AI GLM)...")
    hunter_messages = [{"role": "user", "content": f"Phân tích và lọc các tin tức sau:\n\n{news_text}"}]
    hunter_content = call_zai_glm(hunter_messages, NEWS_HUNTER_PROMPT)

    # Step 3: MarketAnalyst provides insights
    print("[INFO] MarketAnalyst generating report (via Z.AI GLM)...")
    analyst_messages = [{"role": "user", "content": f"Dựa trên các tin tức đã lọc sau đây, hãy phân tích xu hướng giá Vàng/Bạc:\n\n{hunter_content}"}]
    analyst_content = call_zai_glm(analyst_messages, MARKET_ANALYST_PROMPT)

    # Combine reports
    final_report = f"🤖 *Powered by Z.AI GLM-4.7*\n\n{hunter_content}\n\n---\n\n{analyst_content}"

    print("[INFO] Analysis pipeline completed.")
    return final_report


async def run_analysis_with_gemini(query: str = "gold silver price news") -> str:
    """
    Run analysis pipeline using Gemini via AgentScope.
    """
    print(f"[INFO] Starting analysis pipeline with query: {query}")

    # Step 1: Search for news
    print("[INFO] Fetching news from Serper API...")
    news_items = search_news(query)

    if not news_items:
        return "❌ Không tìm thấy tin tức nào. Vui lòng thử lại sau."

    # Format news
    news_text = "\n\n".join([
        f"📰 {item['title']}\n"
        f"   Nguồn: {item['source']} | {item['date']}\n"
        f"   {item['snippet']}"
        for item in news_items[:8]
    ])

    print(f"[INFO] Found {len(news_items)} news articles.")

    # Initialize AgentScope and use Gemini
    print("[INFO] Initializing AgentScope with Gemini...")
    agentscope.init(project="GoldSilverIntelligence", name="analysis")
    
    model = GeminiChatModel(
        model_name="gemini-2.0-flash",
        api_key=GEMINI_API_KEY,
    )
    formatter = GeminiChatFormatter()
    
    # Create agents
    news_hunter = ReActAgent(
        name="NewsHunter",
        sys_prompt=NEWS_HUNTER_PROMPT,
        model=model,
        memory=InMemoryMemory(),
        formatter=formatter,
        toolkit=Toolkit(),
    )
    
    market_analyst = ReActAgent(
        name="MarketAnalyst",
        sys_prompt=MARKET_ANALYST_PROMPT,
        model=model,
        memory=InMemoryMemory(),
        formatter=formatter,
        toolkit=Toolkit(),
    )
    
    # Run agents
    hunter_input = Msg(name="user", content=f"Phân tích và lọc các tin tức sau:\n\n{news_text}", role="user")
    hunter_response = await news_hunter(hunter_input)
    hunter_content = hunter_response.get_text_content() if hasattr(hunter_response, 'get_text_content') else str(hunter_response.content)
    
    analyst_input = Msg(name="NewsHunter", content=f"Dựa trên các tin tức đã lọc sau đây, hãy phân tích xu hướng giá Vàng/Bạc:\n\n{hunter_content}", role="user")
    analyst_response = await market_analyst(analyst_input)
    analyst_content = analyst_response.get_text_content() if hasattr(analyst_response, 'get_text_content') else str(analyst_response.content)
    
    final_report = f"🤖 *Powered by Gemini*\n\n{hunter_content}\n\n---\n\n{analyst_content}"
    print("[INFO] Analysis pipeline completed.")
    return final_report


def run_analysis_pipeline(query: str = "gold silver price news") -> str:
    """
    Run the full analysis pipeline with fallback.
    Priority: Z.AI GLM -> Gemini
    """
    # Try Z.AI GLM first
    if ZAI_API_KEY:
        try:
            print("[INFO] Using Z.AI GLM API (Priority 1) via OpenAI SDK...")
            return run_analysis_with_zai(query)
        except Exception as e:
            print(f"[WARN] Z.AI GLM failed: {e}")
    
    # Fallback to Gemini
    if GEMINI_API_KEY:
        try:
            print("[INFO] Using Gemini API (Fallback)...")
            return asyncio.run(run_analysis_with_gemini(query))
        except Exception as e:
            print(f"[WARN] Gemini failed: {e}")
    
    return "❌ Không có LLM API khả dụng. Vui lòng kiểm tra ZAI_API_KEY hoặc GEMINI_API_KEY."
