from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
import json
import openai

# 🔐 환경변수 불러오기
load_dotenv(dotenv_path="chatgpt.env")

# ✅ OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

router = APIRouter()

# 요청 형식
class RecommendRequest(BaseModel):
    latitude: float
    longitude: float
    weather: str
    temperature: float
    season: str
    time: str

# 응답 형식
class Recommendation(BaseModel):
    name: str
    adress: str
    message: str

class RecommendResponse(BaseModel):
    recommendations: List[Recommendation]

@router.post("/ai/recommend_point", response_model=RecommendResponse)
async def recommend_point(req: RecommendRequest):
    prompt = f"""
    사용자의 위치와 환경 정보는 다음과 같아:
    - 날씨: {req.weather}
    - 기온: {req.temperature}도
    - 계절: {req.season}
    - 시간대: {req.time}
    - 위도/경도: {req.latitude}, {req.longitude}

    위 정보를 기반으로, 직선거리 60km 이내 배스낚시 포인트 중 최신 조황이 있는 곳으로 2곳을 추천해줘.
    각 포인트는 JSON 형식으로 name(포인트 이름), adress(주소), message 필드를 포함하고,
    거리나 숫자는 말하지 말고, 추천하는 말투로 설명해줘.

    예시:
    [
      {{
        "name": "고삼저수지",
        "adress": "경기도 안성시 고삼면 월향리",
        "message": "오늘같이 흐린 봄날엔 고삼저수지처럼 수심이 깊고 구조물이 많은 곳이 좋아요. 다운샷 리그에 3인치 웜을 써서 바닥층을 천천히 탐색해보세요."
      }}
    ]
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 배스 낚시 포인트 추천 전문가야."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9
        )
        content = response.choices[0].message["content"]
        recommendations = json.loads(content)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=500,
            content={"error": "GPT 응답이 JSON 형식이 아님", "raw": content}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

    return RecommendResponse(
        recommendations=[
            Recommendation(name=rec["name"], adress=rec["adress"], message=rec["message"])
            for rec in recommendations
        ]
    )
