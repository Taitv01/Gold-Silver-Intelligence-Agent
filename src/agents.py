"""
Gold-Silver-Intelligence Agents Module
Supports: Groq (primary), Z.AI GLM (fallback 1), Gemini (fallback 2)
Includes: Rate limit handling with retry logic
"""
import os
import time
import asyncio
import requests
from openai import OpenAI

from src.config import SERPER_API_KEY, GEMINI_API_KEY, ZAI_API_KEY, GROQ_API_KEY


# === Rate Limit Configuration ===
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 10


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


# === LLM Clients ===

def get_groq_client():
    """Get Groq client using OpenAI SDK."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured")
    
    return OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )


def get_zai_client():
    """Get Z.AI client using OpenAI SDK."""
    if not ZAI_API_KEY:
        raise ValueError("ZAI_API_KEY not configured")
    
    return OpenAI(
        api_key=ZAI_API_KEY,
        base_url="https://api.z.ai/api/paas/v4/"
    )


def call_llm(messages: list, system_prompt: str = "", provider: str = "groq") -> str:
    """
    Call LLM API using OpenAI SDK.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        system_prompt: System prompt for the model
        provider: "groq" or "zai"
        
    Returns:
        Response text from the model
    """
    # Get client based on provider
    if provider == "groq":
        client = get_groq_client()
        model = "llama-3.3-70b-versatile"  # Groq's best free model
    else:
        client = get_zai_client()
        model = "glm-4.7"
    
    # Build messages with system prompt
    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(messages)
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"[DEBUG] Calling {provider.upper()} API ({model})...")
            
            response = client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=0.7,
                max_tokens=2048,
            )
            
            content = response.choices[0].message.content
            print(f"[DEBUG] {provider.upper()} response received successfully")
            return content
            
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str
            
            if is_rate_limit and attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY_SECONDS * (attempt + 1)
                print(f"[WARN] {provider.upper()} rate limited (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] {provider.upper()} API error: {e}")
                raise e
    
    raise Exception(f"{provider.upper()} API failed after all retries")


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


def run_analysis_with_llm(query: str, provider: str) -> str:
    """
    Run analysis pipeline with specified LLM provider.
    """
    provider_name = "Groq Llama-3.3-70B" if provider == "groq" else "Z.AI GLM-4.7"
    print(f"[INFO] Starting analysis pipeline with {provider_name}")
    print(f"[INFO] Query: {query}")

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
    print(f"[INFO] NewsHunter analyzing news (via {provider_name})...")
    hunter_messages = [{"role": "user", "content": f"Phân tích và lọc các tin tức sau:\n\n{news_text}"}]
    hunter_content = call_llm(hunter_messages, NEWS_HUNTER_PROMPT, provider)

    # Step 3: MarketAnalyst provides insights
    print(f"[INFO] MarketAnalyst generating report (via {provider_name})...")
    analyst_messages = [{"role": "user", "content": f"Dựa trên các tin tức đã lọc sau đây, hãy phân tích xu hướng giá Vàng/Bạc:\n\n{hunter_content}"}]
    analyst_content = call_llm(analyst_messages, MARKET_ANALYST_PROMPT, provider)

    # Combine reports
    final_report = f"🤖 *Powered by {provider_name}*\n\n{hunter_content}\n\n---\n\n{analyst_content}"

    print("[INFO] Analysis pipeline completed.")
    return final_report


def run_analysis_pipeline(query: str = "gold silver price news Fed interest rate") -> str:
    """
    Run the full analysis pipeline with fallback.
    Priority: Groq -> Z.AI GLM -> Gemini
    """
    # Try Groq first (best free option)
    if GROQ_API_KEY:
        try:
            print("[INFO] Using Groq API (Priority 1) - FREE with generous limits...")
            return run_analysis_with_llm(query, "groq")
        except Exception as e:
            print(f"[WARN] Groq failed: {e}")
    
    # Fallback to Z.AI GLM
    if ZAI_API_KEY:
        try:
            print("[INFO] Using Z.AI GLM API (Fallback 1)...")
            return run_analysis_with_llm(query, "zai")
        except Exception as e:
            print(f"[WARN] Z.AI GLM failed: {e}")
    
    # Fallback to Gemini (if implemented)
    if GEMINI_API_KEY:
        print("[INFO] Gemini fallback not implemented in simplified version")
    
    return "❌ Không có LLM API khả dụng. Vui lòng kiểm tra GROQ_API_KEY, ZAI_API_KEY hoặc GEMINI_API_KEY."
