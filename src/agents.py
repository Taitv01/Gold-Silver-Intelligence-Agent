"""
Gold-Silver-Intelligence Agents Module
Rewritten for AgentScope 1.0+ API (async-based).
Supports: Gemini (primary), OpenAI-compatible APIs (fallback)
Includes: Rate limit handling with retry logic
"""
import os
import time
import asyncio
import requests
import agentscope
from agentscope.agent import ReActAgent
from agentscope.message import Msg
from agentscope.model import GeminiChatModel, OpenAIChatModel
from agentscope.formatter import GeminiChatFormatter, OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from src.config import SERPER_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, GLM_API_KEY, PERPLEXITY_API_KEY


# === Rate Limit Configuration ===
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
RATE_LIMIT_CODES = [429, 503]


def search_news(query: str, num_results: int = 10) -> list:
    """
    Search for news using Serper API with retry logic.

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

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            # Handle rate limiting
            if response.status_code in RATE_LIMIT_CODES:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY_SECONDS * (attempt + 1)
                    print(f"[WARN] Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[ERROR] Rate limit exceeded after {MAX_RETRIES} attempts")
                    return []
            
            response.raise_for_status()
            data = response.json()

            news = []
            seen_titles = set()  # Theo dõi tiêu đề đã xem
            seen_links = set()   # Theo dõi liên kết đã xem
            
            for item in data.get("news", []):
                title = item.get("title", "")
                link = item.get("link", "")
                
                # Chuẩn hóa tiêu đề để so sánh (chữ thường, xóa khoảng trắng thừa)
                normalized_title = title.lower().strip()
                
                # Bỏ qua nếu tiêu đề hoặc liên kết đã tồn tại
                if normalized_title in seen_titles or link in seen_links:
                    print(f"[INFO] Skipping duplicate news: {title[:50]}...")
                    continue
                
                # Thêm vào tập hợp đã xem
                seen_titles.add(normalized_title)
                seen_links.add(link)
                
                news.append({
                    "title": title,
                    "link": link,
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


def get_model_and_formatter_with_fallback():
    """
    Try to get model with automatic fallback if primary fails.
    Priority: Gemini -> Perplexity -> GLM (ZhipuAI) -> OpenAI
    
    Note: Change priority order based on which API keys you have available.
    """
    errors = []
    
    # Priority 1: Try Gemini first
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
    
    # Priority 2: Fallback to Perplexity (OpenAI-compatible)
    if PERPLEXITY_API_KEY:
        try:
            print("[INFO] Trying Perplexity API...")
            model = OpenAIChatModel(
                model_name="llama-3.1-sonar-small-128k-online",
                api_key=PERPLEXITY_API_KEY,
                base_url="https://api.perplexity.ai",
            )
            formatter = OpenAIChatFormatter()
            return model, formatter, "Perplexity"
        except Exception as e:
            errors.append(f"Perplexity: {e}")
            print(f"[WARN] Perplexity failed: {e}")

    # Priority 3: Fallback to GLM (ZhipuAI - uses OpenAI-compatible API)
    if GLM_API_KEY:
        try:
            print("[INFO] Trying ZhipuAI GLM API (OpenAI-compatible)...")
            model = OpenAIChatModel(
                model_name="glm-4-flash",
                api_key=GLM_API_KEY,
                base_url="https://open.bigmodel.cn/api/paas/v4/",
            )
            formatter = OpenAIChatFormatter()
            return model, formatter, "GLM"
        except Exception as e:
            errors.append(f"GLM: {e}")
            print(f"[WARN] GLM failed: {e}")
    
    # Priority 3: Fallback to OpenAI
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


async def call_agent_with_retry(agent, input_msg, agent_name: str, max_retries: int = MAX_RETRIES):
    """
    Call an agent with retry logic for rate limit handling.
    
    Args:
        agent: The agent to call
        input_msg: Input message
        agent_name: Name of the agent (for logging)
        max_retries: Maximum number of retries
        
    Returns:
        Agent response content as string
    """
    for attempt in range(max_retries):
        try:
            response = await agent(input_msg)
            content = response.get_text_content() if hasattr(response, 'get_text_content') else str(response.content)
            return content
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str
            
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = RETRY_DELAY_SECONDS * (attempt + 1) * 2  # Exponential backoff
                print(f"[WARN] {agent_name} rate limited (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise e
    
    raise Exception(f"{agent_name} failed after {max_retries} attempts")


async def run_analysis_async(query: str = "gold silver price news") -> str:
    """
    Run the full analysis pipeline (async version) with rate limit handling.

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
        f"📰 {item['title']}\n"
        f"   Nguồn: {item['source']} | {item['date']}\n"
        f"   {item['snippet']}"
        for item in news_items[:8]
    ])

    print(f"[INFO] Found {len(news_items)} news articles.")

    # Step 2: Initialize AgentScope
    print("[INFO] Initializing AgentScope...")
    agentscope.init(project="GoldSilverIntelligence", name="analysis")

    # Step 3: Get model and formatter with fallback support
    model, formatter, provider = get_model_and_formatter_with_fallback()
    print(f"[INFO] Using {provider} as LLM provider")

    # Step 4: Create NewsHunter Agent
    print("[INFO] Creating NewsHunter agent...")
    news_hunter = ReActAgent(
        name="NewsHunter",
        sys_prompt=NEWS_HUNTER_PROMPT,
        model=model,
        memory=InMemoryMemory(),
        formatter=formatter,
        toolkit=Toolkit(),
    )

    # Step 5: Create MarketAnalyst Agent
    print("[INFO] Creating MarketAnalyst agent...")
    market_analyst = ReActAgent(
        name="MarketAnalyst",
        sys_prompt=MARKET_ANALYST_PROMPT,
        model=model,
        memory=InMemoryMemory(),
        formatter=formatter,
        toolkit=Toolkit(),
    )

    # Step 6: NewsHunter filters important news (with retry)
    print("[INFO] NewsHunter analyzing news...")
    hunter_input = Msg(
        name="user",
        content=f"Phân tích và lọc các tin tức sau:\n\n{news_text}",
        role="user"
    )
    hunter_content = await call_agent_with_retry(news_hunter, hunter_input, "NewsHunter")

    # Step 7: MarketAnalyst provides insights (with retry)
    print("[INFO] MarketAnalyst generating report...")
    analyst_input = Msg(
        name="NewsHunter",
        content=f"Dựa trên các tin tức đã lọc sau đây, hãy phân tích xu hướng giá Vàng/Bạc:\n\n{hunter_content}",
        role="user"
    )
    analyst_content = await call_agent_with_retry(market_analyst, analyst_input, "MarketAnalyst")

    # Combine reports
    final_report = f"🤖 *Powered by {provider}*\n\n{hunter_content}\n\n---\n\n{analyst_content}"

    print("[INFO] Analysis pipeline completed.")
    return final_report


def run_analysis_pipeline(query: str = "gold silver price news") -> str:
    """
    Run the full analysis pipeline (sync wrapper).
    
    Args:
        query: Search query for news

    Returns:
        Final analysis report as string
    """
    return asyncio.run(run_analysis_async(query))
