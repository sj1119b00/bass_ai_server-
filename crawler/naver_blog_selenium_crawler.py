import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re
import json
from time import sleep
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from config import OPENAI_API_KEY, KAKAO_API_KEY
from openai import OpenAI

client = OpenAI(api_key=OPENAI_API_KEY)

# DB 설정
DATABASE_URL = "postgresql://postgres:bassmate1119@localhost:5432/bass_ai_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# 테이블 모델
class FishingCatch(Base):
    __tablename__ = "fishing_catches"
    id = Column(Integer, primary_key=True)
    spot_name = Column(String)
    blog_title = Column(String)
    blog_url = Column(String, unique=True)
    summary = Column(Text)
    posted_at = Column(DateTime)
    weather = Column(String)
    time_period = Column(String)
    bait_type = Column(String)
    temperature = Column(String)
    wind = Column(String)
    result = Column(Integer)

# GPT 정제
def gpt_extract_fishing_info(content: str) -> dict:
    prompt = f"""
너는 낚시 조행기에서 핵심 정보를 추출해서 **정확히 아래 JSON 형식만** 출력해야 해.
아래 형식에서 누락된 값은 `null`로 채워. 절대 형식 바꾸지 마.
그 외 설명, 주석, 텍스트 없이 **오직 JSON만** 출력해.

다음은 JSON 형식이다:
{{
  "date": "YYYY-MM-DD",
  "spot_name": "포인트 이름",
  "weather": "날씨 요약",
  "time_period": "낚시 시간대",
  "bait_type": "사용 채비",
  "temperature": "기온 또는 수온",
  "wind": "바람 정보",
  "result": 0 또는 1
}}

다음은 낚시 조행기 본문이다:
\"\"\"{content[:1500]}\"\"\"
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 낚시 데이터를 정제하는 어시스턴트야."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        text = response.choices[0].message.content.strip()
        print("💬 GPT 원본 응답:", text)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(match.group()) if match else {}
    except Exception as e:
        print(f"GPT 실패: {e}")
        return {}

def extract_field(parsed, *keys):
    for key in keys:
        if key in parsed:
            return parsed[key]
    return None

# ✅ 다지역 키워드 기반 크롤링 함수
def crawl_blog_posts_by_region(keywords, max_pages=3):
    db = SessionLocal()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    for keyword in keywords:
        print(f"\n🗺️ [지역 키워드: {keyword}] 시작\n")
        for page in range(1, max_pages + 1):
            print(f"📄 {page}페이지 크롤링 중...")
            start = (page - 1) * 10 + 1
            url = f"https://search.naver.com/search.naver?where=view&query={keyword}&sm=tab_pge&start={start}"
            driver.get(url)
            sleep(2)

            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="blog.naver.com"]')
            for link in links:
                blog_title = link.text.strip()
                blog_url = link.get_attribute("href")

                if not blog_url or "MyBlog" in blog_url:
                    continue
                if db.query(FishingCatch).filter_by(blog_url=blog_url).first():
                    continue

                try:
                    driver.execute_script("window.open('');")
                    driver.switch_to.window(driver.window_handles[1])
                    driver.get(blog_url)
                    sleep(2)

                    iframes = driver.find_elements(By.CSS_SELECTOR, "iframe#mainFrame")
                    if iframes:
                        driver.switch_to.frame(iframes[0])

                    html = driver.page_source
                    soup = BeautifulSoup(html, 'html.parser')
                    content_div = (
                        soup.find("div", {"class": "se-main-container"}) or
                        soup.find("div", {"class": "post-view"}) or
                        soup.find("div", {"id": "post-view"}) or
                        soup.find("div", {"class": "post_ct"}) or
                        soup.find("div", {"id": "contentArea"})
                    )
                    content_text = content_div.get_text(separator="\n") if content_div else ""
                    driver.switch_to.default_content()

                    if not content_text.strip():
                        raise Exception("본문 없음")

                    parsed = gpt_extract_fishing_info(content_text)
                    spot_name = extract_field(parsed, "spot_name")
                    if not spot_name:
                        continue

                    db.add(FishingCatch(
                        spot_name=spot_name,
                        blog_title=blog_title,
                        blog_url=blog_url,
                        summary=content_text[:300],
                        posted_at=datetime.today(),
                        weather=str(extract_field(parsed, "weather")),
                        time_period=str(extract_field(parsed, "time_period")),
                        bait_type=str(extract_field(parsed, "bait_type")),
                        temperature=str(extract_field(parsed, "temperature")),
                        wind=str(extract_field(parsed, "wind")),
                        result=int(extract_field(parsed, "result") or 0)
                    ))
                    print(f"✅ 저장됨: {spot_name}")

                except Exception as e:
                    print(f"❌ 블로그 처리 실패: {e}")
                finally:
                    try:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                    except Exception:
                        break

            db.commit()
    db.close()
    driver.quit()
    print("🎉 전체 지역 크롤링 완료!")

if __name__ == "__main__":
    region_keywords = [
        "경기도 배스낚시", "강원도 배스낚시", "충청도 배스낚시",
        "전라도 배스낚시", "경상도 배스낚시", "제주도 배스낚시"
    ]
    crawl_blog_posts_by_region(region_keywords, max_pages=10)
