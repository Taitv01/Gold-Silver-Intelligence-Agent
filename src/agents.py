"""
Gold-Silver-Intelligence Agents Module
Multi-provider LLM support: Gemini (primary) + Perplexity (fallback).
Includes: Serper news search, rate limit handling, retry logic.
"""
import time
import requests
from google import genai
from google.genai import types
from openai import OpenAI

from src.config import SERPER_API_KEY, GEMINI_API_KEY, PERPLEXITY_API_KEY


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
            seen_titles = set()
            seen_links = set()

            for item in data.get("news", []):
                title = item.get("title", "")
                link = item.get("link", "")

                normalized_title = title.lower().strip()

                if normalized_title in seen_titles or link in seen_links:
                    print(f"[INFO] Skipping duplicate news: {title[:50]}...")
                    continue

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


def search_twitter(query: str, num_results: int = 5) -> list:
    """
    Search for Twitter/X.com posts using Serper API with retry logic.

    Args:
        query: Search query string
        num_results: Number of results to return

    Returns:
        List of Twitter posts with title, link, snippet
    """
    if not SERPER_API_KEY:
        print("[ERROR] SERPER_API_KEY not configured.")
        return []

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    twitter_query = f"{query} (site:x.com OR site:twitter.com)"
    payload = {
        "q": twitter_query,
        "num": num_results,
        "tbs": "qdr:d"
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)

            if response.status_code in RATE_LIMIT_CODES:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY_SECONDS * (attempt + 1)
                    print(f"[WARN] Twitter search rate limited (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[ERROR] Twitter search rate limit exceeded after {MAX_RETRIES} attempts")
                    return []

            response.raise_for_status()
            data = response.json()

            tweets = []
            seen_links = set()

            for item in data.get("organic", []):
                link = item.get("link", "")

                if "x.com" not in link and "twitter.com" not in link:
                    continue

                if link in seen_links:
                    continue

                seen_links.add(link)
                tweets.append({
                    "title": item.get("title", ""),
                    "link": link,
                    "snippet": item.get("snippet", ""),
                    "source": "X/Twitter",
                    "date": item.get("date", "Gần đây")
                })

            print(f"[INFO] Found {len(tweets)} tweets from X/Twitter")
            return tweets

        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"[WARN] Twitter search failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print(f"[ERROR] Twitter search failed after {MAX_RETRIES} attempts: {e}")
                return []

    return []


def search_all_sources(query: str, num_news: int = 8, num_tweets: int = 5) -> list:
    """
    Search for news from all sources: News + Twitter/X.com

    Args:
        query: Search query string
        num_news: Number of news articles to fetch
        num_tweets: Number of tweets to fetch

    Returns:
        Combined list of news and tweets, deduplicated
    """
    print("[INFO] Fetching news from Serper API...")
    news = search_news(query, num_news)

    print("[INFO] Fetching posts from X/Twitter...")
    tweets = search_twitter(query, num_tweets)

    all_items = news + tweets
    print(f"[INFO] Total: {len(news)} news + {len(tweets)} tweets = {len(all_items)} items")

    return all_items


# === Agent System Prompts ===

NEWS_HUNTER_PROMPT = """Bạn là NewsHunter - chuyên gia thu thập và lọc tin tức thị trường Vàng/Bạc.

NGUỒN TIN: Bạn sẽ nhận được tin tức từ nhiều nguồn:
- Tin tức từ các trang báo chính thống
- Bài đăng từ X/Twitter (có thể từ các chuyên gia, nhà phân tích)

NHIỆM VỤ:
1. Phân tích các tin tức và bài đăng được cung cấp
2. Lọc ra các tin quan trọng liên quan đến:
   - Chính sách lãi suất Fed/FOMC
   - Chiến tranh, xung đột địa chính trị
   - Chỉ số DXY (USD Index)
   - Lạm phát, CPI, việc làm Mỹ
   - Chính sách tiền tệ các ngân hàng trung ương lớn
   - Ý kiến từ các chuyên gia nổi tiếng trên X/Twitter

OUTPUT FORMAT:
📰 **TIN TỨC QUAN TRỌNG**

1. [Tiêu đề tin 1]
   - Nguồn: [source] (đánh dấu 🐦 nếu từ X/Twitter)
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


def _call_gemini(prompt: str, system_instruction: str = "") -> str:
    """
    Call Google Gemini API with retry logic.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    config = types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=2048,
    )
    if system_instruction:
        config.system_instruction = system_instruction

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config,
            )
            return response.text

        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str

            if is_rate_limit and attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY_SECONDS * (attempt + 1) * 2
                print(f"[WARN] Gemini rate limited (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise


def _call_perplexity(prompt: str, system_instruction: str = "") -> str:
    """
    Call Perplexity API (OpenAI-compatible) with retry logic.
    """
    client = OpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai"
    )

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="sonar",
                messages=messages,
                max_tokens=2048,
                temperature=0.7,
            )
            return response.choices[0].message.content

        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "rate" in error_str or "quota" in error_str

            if is_rate_limit and attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY_SECONDS * (attempt + 1) * 2
                print(f"[WARN] Perplexity rate limited (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise


def call_llm(prompt: str, system_instruction: str = "") -> tuple:
    """
    Call LLM with automatic fallback: Gemini -> Perplexity.

    Args:
        prompt: User prompt to send
        system_instruction: System instruction for the model

    Returns:
        Tuple of (response_text, provider_name)
    """
    errors = []

    # Priority 1: Gemini
    if GEMINI_API_KEY:
        try:
            print("[INFO] Calling Gemini API...")
            result = _call_gemini(prompt, system_instruction)
            return result, "Gemini"
        except Exception as e:
            errors.append(f"Gemini: {e}")
            print(f"[WARN] Gemini failed: {e}")

    # Priority 2: Perplexity (fallback)
    if PERPLEXITY_API_KEY:
        try:
            print("[INFO] Falling back to Perplexity API...")
            result = _call_perplexity(prompt, system_instruction)
            return result, "Perplexity"
        except Exception as e:
            errors.append(f"Perplexity: {e}")
            print(f"[WARN] Perplexity failed: {e}")

    raise ValueError(
        f"All LLM providers failed. "
        f"Configure GEMINI_API_KEY or PERPLEXITY_API_KEY in .env\n"
        f"Errors: {errors}"
    )


def run_analysis_pipeline(query: str = "gold silver price news") -> str:
    """
    Run the full analysis pipeline with multi-provider LLM support.
    Priority: Gemini -> Perplexity (auto-fallback).

    Args:
        query: Search query for news

    Returns:
        Final analysis report as string
    """
    print(f"[INFO] Starting analysis pipeline with query: {query}")

    # Step 1: Search for news from all sources
    news_items = search_all_sources(query, num_news=8, num_tweets=5)

    if not news_items:
        return "❌ Không tìm thấy tin tức nào. Vui lòng thử lại sau."

    # Format news for agent
    news_text = "\n\n".join([
        f"📰 {item['title']}\n"
        f"   Nguồn: {item['source']} | {item['date']}\n"
        f"   {item['snippet']}"
        for item in news_items[:12]
    ])

    print(f"[INFO] Found {len(news_items)} items total.")

    # Step 2: NewsHunter filters important news
    print("[INFO] NewsHunter analyzing news...")
    hunter_content, provider1 = call_llm(
        prompt=f"Phân tích và lọc các tin tức sau:\n\n{news_text}",
        system_instruction=NEWS_HUNTER_PROMPT,
    )

    # Step 3: MarketAnalyst provides insights
    print("[INFO] MarketAnalyst generating report...")
    analyst_content, provider2 = call_llm(
        prompt=f"Dựa trên các tin tức đã lọc sau đây, hãy phân tích xu hướng giá Vàng/Bạc:\n\n{hunter_content}",
        system_instruction=MARKET_ANALYST_PROMPT,
    )

    # Determine provider display
    if provider1 == provider2:
        provider_label = provider1
    else:
        provider_label = f"{provider1} + {provider2}"

    # Combine reports
    final_report = f"🤖 *Powered by {provider_label}*\n\n{hunter_content}\n\n---\n\n{analyst_content}"

    print(f"[INFO] Analysis pipeline completed. (Provider: {provider_label})")
    return final_report
