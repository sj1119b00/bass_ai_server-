import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import csv
import re
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Base, FishingCatch, TrainingFishingData
from config import KAKAO_API_KEY
from tqdm import tqdm
from datetime import datetime

DATABASE_URL = "postgresql://postgres:bassmate1119@localhost:5432/bass_ai_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# ✅ 날씨 코드 → 설명 변환
weather_map = {
    0: "맑음", 1: "대체로 맑음", 2: "부분 흐림", 3: "흐림",
    45: "안개", 48: "서리 안개", 51: "약한 이슬비", 53: "중간 이슬비", 55: "강한 이슬비",
    61: "약한 비", 63: "중간 비", 65: "강한 비", 71: "약한 눈", 73: "중간 눈", 75: "강한 눈",
    80: "소나기", 81: "강한 소나기", 82: "매우 강한 소나기"
}

# ✅ 시간대 표준화 함수
def normalize_time_period(text: str) -> str:
    if not text or text.strip().lower() in ["none", "정보 없음"]:
        return None

    text = text.strip().lower()

    # 먼저 시간 범위 표현에서 숫자 추출: "5:20 - 6:00", "19 ~ 23시"
    time_range = re.findall(r"(\d{1,2})[:시]", text)
    if time_range:
        hour = int(time_range[0])
        if 0 <= hour < 6:
            return "새벽"
        elif 6 <= hour < 11:
            return "아침"
        elif 11 <= hour < 14:
            return "오전"
        elif 14 <= hour < 19:
            return "오후"
        else:
            return "야간"

    # 키워드 기반 우선 인식
    if "새벽" in text or "동트" in text or "일출" in text or "이른" in text:
        return "새벽"
    if "아침" in text:
        return "아침"
    if "오전" in text:
        return "오전"
    if "오후" in text:
        return "오후"
    if "야간" in text or "밤" in text or "늦은" in text:
        return "야간"

    # 복수 키워드 있을 경우 → 가장 앞에 있는 키워드 기준
    for keyword in ["새벽", "아침", "오전", "오후", "야간"]:
        if keyword in text:
            return keyword

    return None


# ✅ 날씨 API
def get_weather_info(lat, lon, date_str):
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={date_str}&end_date={date_str}"
        f"&daily=temperature_2m_mean,windspeed_10m_max,weathercode"
        f"&timezone=Asia%2FSeoul"
    )
    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            if "daily" in data and data["daily"]["temperature_2m_mean"]:
                return {
                    "temperature": data["daily"]["temperature_2m_mean"][0],
                    "wind": data["daily"]["windspeed_10m_max"][0],
                    "weather": weather_map.get(data["daily"]["weathercode"][0], "기타")
                }
            else:
                print(f"❗날씨 데이터 없음: lat={lat}, lon={lon}, date={date_str}")
        else:
            print(f"❌ 날씨 API 실패: status={res.status_code}, lat={lat}, lon={lon}, date={date_str}")
    except Exception as e:
        print(f"❌ 날씨 API 예외: {e}")
    return None

# ✅ 좌표 찾기 (spot_name → 위경도)
def get_coords_by_kakao(query):
    url = f"https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": query}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        documents = response.json().get("documents", [])
        if documents:
            first = documents[0]
            return first["address_name"], float(first["y"]), float(first["x"])
    return None, None, None

# ✅ 데이터 전송 + 날씨 보완 + 기존 데이터 업데이트
def transfer_data():
    db = SessionLocal()
    catches = db.query(FishingCatch).all()
    fail_logs = []

    for row in tqdm(catches):
        if not row.spot_name or not row.posted_at:
            continue

        address, lat, lon = get_coords_by_kakao(row.spot_name)
        if not lat or not lon:
            continue

        # ✅ 시간대 정형화
        standard_time_period = normalize_time_period(row.time_period)

        # 날씨 기본값
        weather = row.weather
        temperature = row.temperature
        wind = row.wind

        # 누락되었을 경우 → 날씨 API 호출
        if not weather or not temperature or not wind:
            date_str = row.posted_at.strftime("%Y-%m-%d")
            weather_data = get_weather_info(lat, lon, date_str)
            if weather_data:
                weather = weather_data["weather"]
                temperature = weather_data["temperature"]
                wind = weather_data["wind"]
            else:
                fail_logs.append({
                    "spot_name": row.spot_name,
                    "latitude": lat,
                    "longitude": lon,
                    "date": date_str,
                    "blog_url": row.blog_url
                })
                continue  # 날씨 실패 시 이 row는 스킵

        # 이미 존재하는 데이터가 있으면 업데이트
        existing = db.query(TrainingFishingData).filter_by(blog_url=row.blog_url).first()
        if existing:
            updated = False
            if not existing.weather and weather:
                existing.weather = weather
                updated = True
            if not existing.temperature and temperature:
                existing.temperature = temperature
                updated = True
            if not existing.wind and wind:
                existing.wind = wind
                updated = True
            if not existing.time_period and standard_time_period:
                existing.time_period = standard_time_period
                updated = True
            if updated:
                db.add(existing)
            continue  # 중복은 insert 안 함

        # 새로 insert
        refined = TrainingFishingData(
            spot_name=row.spot_name,
            address=address,
            latitude=lat,
            longitude=lon,
            weather=weather,
            time_period=standard_time_period,
            bait_type=row.bait_type,
            temperature=temperature,
            wind=wind,
            result=row.result,
            blog_url=row.blog_url,
            posted_at=row.posted_at
        )
        db.add(refined)

    db.commit()
    db.close()

    # 실패 로그 저장
    if fail_logs:
        with open("weather_api_failures.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["spot_name", "latitude", "longitude", "date", "blog_url"])
            writer.writeheader()
            writer.writerows(fail_logs)
        print(f"⚠️ 날씨 API 실패 {len(fail_logs)}건 → weather_api_failures.csv에 저장됨")

    print("🎯 정제된 데이터 이관 + 시간 정형화 + 날씨 보완 완료!")

if __name__ == "__main__":
    transfer_data()
