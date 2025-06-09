from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import numpy as np
import joblib
from sqlalchemy import create_engine
import random

router = APIRouter()

# 입력 데이터 모델
class RecommendRequest(BaseModel):
    latitude: float
    longitude: float
    weather: str
    temperature: Optional[float] = None
    wind: Optional[float] = None
    season: str
    time: str
    max_distance_km: float = 60.0

# 출력 모델 (✅ address 필드 추가)
class RecommendedSpot(BaseModel):
    spot_name: str
    address: str
    latitude: float
    longitude: float
    distance: float
    predicted_score: float
    final_score: float

# 거리 계산 함수
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

# 추천 API
@router.post("/ai/recommend_point", response_model=Optional[RecommendedSpot])
def recommend_point(req: RecommendRequest):
    # DB 연결
    DATABASE_URL = "postgresql://postgres:bassmate1119@localhost:5432/bass_ai_db"
    engine = create_engine(DATABASE_URL)
    
    # ✅ address 포함하도록 수정
    query = """
        SELECT DISTINCT spot_name, latitude, longitude, address
        FROM training_fishing_data
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND address IS NOT NULL
    """
    df = pd.read_sql(query, engine)

    # 거리 계산 및 필터링
    df['distance'] = haversine(req.latitude, req.longitude, df['latitude'], df['longitude'])
    df = df[df['distance'] <= req.max_distance_km].copy()
    if df.empty:
        return None

    # 모델 및 피처 로딩
    model = joblib.load("bass_ai_model_latest.pkl")
    features = joblib.load("bass_ai_model_features.pkl")

    # 입력값 병합
    df['weather'] = req.weather
    df['temperature'] = req.temperature
    df['wind'] = req.wind
    df['time_period'] = req.time
    df['season'] = req.season

    # 모델 입력 피처 처리
    df_model = df[['latitude', 'longitude', 'weather', 'temperature', 'wind', 'time_period', 'season']]
    df_model = pd.get_dummies(df_model)

    # 누락된 피처 채우기
    for col in features:
        if col not in df_model.columns:
            df_model[col] = np.nan
    df_model = df_model[features]

    # 예측 점수 계산
    df['predicted_score'] = model.predict(df_model)
    df['final_score'] = df['predicted_score']  # ✅ 거리 반영 안함

    # 상위 10개 중 무작위 1개 추천
    df_sorted = df.sort_values(by='final_score', ascending=False).head(10)
    selected = df_sorted.sample(n=1).iloc[0]

    return RecommendedSpot(
        spot_name=selected["spot_name"],
        address=selected["address"],  # ✅ KeyError 방지됨
        latitude=selected["latitude"],
        longitude=selected["longitude"],
        distance=float(selected["distance"]),
        predicted_score=float(selected["predicted_score"]),
        final_score=float(selected["final_score"]),
    )
