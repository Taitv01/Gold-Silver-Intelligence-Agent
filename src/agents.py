"""
Gold-Silver-Intelligence Agents Module
Defines NewsHunter and MarketAnalyst agents using AgentScope.
"""
import requests
import agentscope
from agentscope.agents import DialogAgent
from agentscope.message import Msg

from src.config import MODEL_CONFIG, SERPER_API_KEY


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


def initialize_agents():
    """
    Initialize AgentScope and create agents.

    Returns:
        Tuple of (news_hunter, market_analyst) agents
    """
    if not MODEL_CONFIG:
        raise ValueError("No LLM API key configured. Check .env file.")

    # Initialize AgentScope
    agentscope.init(model_configs=[MODEL_CONFIG])

    # Create NewsHunter Agent
    news_hunter = DialogAgent(
        name="NewsHunter",
        sys_prompt=NEWS_HUNTER_PROMPT,
        model_config_name=MODEL_CONFIG["config_name"],
    )

    # Create MarketAnalyst Agent
    market_analyst = DialogAgent(
        name="MarketAnalyst",
        sys_prompt=MARKET_ANALYST_PROMPT,
        model_config_name=MODEL_CONFIG["config_name"],
    )

    return news_hunter, market_analyst


def run_analysis_pipeline(query: str = "gold silver price news") -> str:
    """
    Run the full analysis pipeline.

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
        for item in news_items[:8]  # Limit to 8 articles
    ])

    print(f"[INFO] Found {len(news_items)} news articles.")

    # Step 2: Initialize agents
    print("[INFO] Initializing agents...")
    news_hunter, market_analyst = initialize_agents()

    # Step 3: NewsHunter filters important news
    print("[INFO] NewsHunter analyzing news...")
    hunter_input = Msg(
        name="user",
        content=f"Phân tích và lọc các tin tức sau:\n\n{news_text}",
        role="user"
    )
    hunter_response = news_hunter(hunter_input)

    # Step 4: MarketAnalyst provides insights
    print("[INFO] MarketAnalyst generating report...")
    analyst_input = Msg(
        name="NewsHunter",
        content=f"Dựa trên các tin tức đã lọc sau đây, hãy phân tích xu hướng giá Vàng/Bạc:\n\n{hunter_response.content}",
        role="user"
    )
    analyst_response = market_analyst(analyst_input)

    # Combine reports
    final_report = f"{hunter_response.content}\n\n---\n\n{analyst_response.content}"

    print("[INFO] Analysis pipeline completed.")
    return final_report
