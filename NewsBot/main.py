import os
import random
import feedparser
from openai import OpenAI
import requests

# ---------------------------------------------------------------------------
# 1. 중립성 중심 뉴스 RSS 소스 정의
# ---------------------------------------------------------------------------
NEWS_SOURCES = {
    # 한국 (연합뉴스, KBS, YTN, 한국일보)
    "KR": [
        "https://www.yna.co.kr/rss/news.xml",
        "https://www.kbs.co.kr/rss/news_category_all.xml",
        "https://ytn.co.kr/_comm/rss/rss_xml.php?id=0101",
        "https://news.google.com/rss/search?q=site:hankookilbo.com&hl=ko&gl=KR&ceid=KR:ko",
    ],
    # 미국 (AP News, Reuters, NPR)
    "US": [
        "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
        "https://feeds.npr.org/1001/rss.xml",
    ],
    # 기타 국가 (영국 BBC, 독일 DW)
    "OTHERS": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.dw.com/rdf/rss-en-world",
    ],
}


# ---------------------------------------------------------------------------
# 2. 뉴스 수집 함수
# ---------------------------------------------------------------------------
def fetch_articles(url, count=5):
  feed = feedparser.parse(url)
  articles = []
  for entry in feed.entries[:count]:
    articles.append({
        "title": entry.title,
        "link": entry.link,
        "summary": entry.get("summary", ""),
    })
  return articles


def collect_daily_news():
  selected_news = []

  # 한국 뉴스 5개
  kr_pool = []
  for url in NEWS_SOURCES["KR"]:
    kr_pool.extend(fetch_articles(url, 3))
  if kr_pool:
    selected_news.extend(
        random.sample(kr_pool, min(5, len(kr_pool))),
    )

  # 미국 뉴스 3개
  us_pool = []
  for url in NEWS_SOURCES["US"]:
    us_pool.extend(fetch_articles(url, 3))
  if us_pool:
    selected_news.extend(
        random.sample(us_pool, min(3, len(us_pool))),
    )

  # 기타 국가 뉴스 2개
  other_url = random.choice(NEWS_SOURCES["OTHERS"])
  other_pool = fetch_articles(other_url, 3)
  if other_pool:
    selected_news.extend(
        random.sample(other_pool, min(2, len(other_pool))),
    )

  return selected_news[:10]


# ---------------------------------------------------------------------------
# 3. LLM 중립 요약 생성
# ---------------------------------------------------------------------------
def summarize_news(news_list):
  client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

  prompt = f"""
다음은 오늘 수집된 주요 뉴스 10개 목록입니다.
각 기사에 대해 주관적 평가나 감정적 표현을 배제하고, 객관적인 팩트(Fact) 중심으로 2~3줄로 한국어 요약해 주세요.

[출력 형식 예시]
1. [국가 구분] 기사 제목
- 핵심 요약 내용 (2~3줄)
- 출처: 링크 URL

[뉴스 데이터]
{news_list}
"""

  response = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[{"role": "user", "content": prompt}],
      temperature=0.3,  # 일관되고 객관적인 톤 유지를 위해 낮은 온도 설정
  )
  return response.choices[0].message.content


# ---------------------------------------------------------------------------
# 4. 텔레그램 메시지 전송
# ---------------------------------------------------------------------------
def send_telegram_message(message):
  bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
  chat_id = os.getenv("TELEGRAM_CHAT_ID")

  url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

  # 텔레그램 메시지 길이 제한(4096자)을 고려해 분할 전송 처리
  max_length = 4000
  for i in range(0, len(message), max_length):
    payload = {
        "chat_id": chat_id,
        "text": message[i : i + max_length],
        "disable_web_page_preview": True,
    }
    requests.post(url, json=payload)


# ---------------------------------------------------------------------------
# 5. 메인 실행부
# ---------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    news_data = collect_daily_news()
    briefing = summarize_news(news_data)

    header = "📰 **오늘 아침 글로벌 핫토픽 10**\n\n"
    final_message = header + briefing

    send_telegram_message(final_message)
    print("텔레그램 브리핑 발송 완료")
  except Exception as e:
    print(f"오류 발생: {e}")