from fastapi import FastAPI, File, Form, UploadFile, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import os
import json
import requests

from database import Base, engine, SessionLocal, create_tables
from models import Catch, User, TrainingFishingData
from routers.ai import recommend
from routers import user 
from auth.auth import router as auth_router
from config import KAKAO_API_KEY

# ✅ 테이블 생성
create_tables()

# ✅ FastAPI 인스턴스 생성
app = FastAPI()

app.include_router(user.router)

# ✅ CORS 허용 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 이미지 저장 폴더 생성
os.makedirs("images", exist_ok=True)

# ✅ 정적 파일 제공
app.mount("/images", StaticFiles(directory="images"), name="images")

# ✅ DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ 루트 테스트용
@app.get("/")
def read_root():
    return {"message": "BassMate API 동작 중!"}

# ✅ 로그인 유무 확인 (SharedPreferences 값으로 체크)
@app.post("/auth/verify")
async def verify_user(request: Request):
    data = await request.json()
    oauth_provider = data.get("oauth_provider")
    oauth_id = data.get("oauth_id")

    print(f"verify 요청: provider={oauth_provider}, id={oauth_id}")

    db: Session = SessionLocal()
    user = db.query(User).filter_by(oauth_provider=oauth_provider, oauth_id=oauth_id).first()

    if user:
        user_data = {
            "id": user.id,
            "nickname": user.nickname,
            "level": user.level,
            "exp": user.exp,
            "title": get_title_by_level(user.level)
        }
        db.close()
        return JSONResponse(
            content=json.loads(json.dumps({
                "valid": True,
                "user": user_data
            }, ensure_ascii=False))
        )
    else:
        db.close()
        return JSONResponse(
            content=json.loads(json.dumps({"valid": False}, ensure_ascii=False))
        )

# ✅ 로그인 시 레벨 타이틀 계산 함수
def get_title_by_level(level: int) -> str:
    return {
        1: "입문자",
        2: "차분 에이널러",
        3: "숙련 에이널러",
        4: "포인트 마스터",
        5: "배스헬터 고수"
    }.get(level, "배스 신입")

# ✅ 문자열 바람 → 숫자 변환 함수
def map_wind_str_to_float(wind_str: str) -> float:
    mapping = {
        "약함": 1.0,
        "보통": 3.0,
        "강함": 6.0
    }
    return mapping.get(wind_str.strip(), 3.0)

# ✅ 회원가입 or 로그인 API
@app.post("/register_or_login")
def register_or_login(
    oauth_provider: str = Form(...),
    oauth_id: str = Form(...),
    nickname: str = Form(""),
    profile_image: str = Form(""),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter_by(oauth_provider=oauth_provider, oauth_id=oauth_id).first()
    if user:
        return {"msg": "로그인 성공", "user_id": user.id}
    else:
        new_user = User(
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            nickname=nickname,
            profile_image=profile_image
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"msg": "회원가입 완료", "user_id": new_user.id}

# ✅ 조과 업로드 API (Catch + TrainingFishingData 저장)
@app.post("/upload_catch")
async def upload_catch(
    photo: UploadFile = File(...),
    user_id: int = Form(...),
    spot_name: str = Form(...),
    address: str = Form(...),
    rig: str = Form(...),
    temperature: float = Form(...),
    wind: str = Form(...),
    weather: str = Form(...),
    time_period: str = Form(...),
    timestamp: str = Form(...)
):
    # ✅ 이미지 저장
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}"
    image_path = os.path.join("images", filename)
    with open(image_path, "wb") as f:
        f.write(await photo.read())

    # ✅ 주소 → 위도/경도 변환
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    kakao_res = requests.get(
        "https://dapi.kakao.com/v2/local/search/address.json",
        headers=headers,
        params={"query": address}
    )
    kakao_json = kakao_res.json()
    if not kakao_json["documents"]:
        raise HTTPException(status_code=400, detail="주소를 위경도로 변환할 수 없습니다.")
    lat = float(kakao_json["documents"][0]["y"])
    lon = float(kakao_json["documents"][0]["x"])

    # ✅ DB 저장
    db = SessionLocal()

    # 1) Catch 저장
    catch = Catch(
        user_id=user_id,
        spot_name=spot_name,
        rig=rig,
        temp=temperature,
        condition=weather,
        timestamp=datetime.fromisoformat(timestamp),
        address=address,
        filename=filename
    )
    db.add(catch)

    # 2) TrainingFishingData 저장
    training_data = TrainingFishingData(
        spot_name=spot_name,
        address=address,
        latitude=lat,
        longitude=lon,
        weather=weather,
        time_period=time_period,
        bait_type=rig,
        temperature=str(temperature),
        wind=str(map_wind_str_to_float(wind)),  # ✅ 여기만 수정!
        result=1,
        blog_url=f"app_upload_{filename}",
        posted_at=datetime.fromisoformat(timestamp)
    )
    db.add(training_data)

    db.commit()
    db.close()

    return {"status": "success", "filename": filename}

# ✅ 조과 목록 조회 API
@app.get("/catches")
def get_catches():
    db = SessionLocal()
    catches = db.query(Catch).filter(
        Catch.spot_name.isnot(None),
        Catch.spot_name != "",
        Catch.address.isnot(None),
        Catch.address != "",
        Catch.filename.isnot(None),
        Catch.filename != ""
    ).all()
    db.close()

    result = []
    for row in catches:
        result.append({
            "spot_name": row.spot_name,
            "rig": row.rig,
            "address": row.address,
            "image_url": f"/images/{row.filename}"
        })

    return {"catches": result}

# ✅ 추천 API 연결
app.include_router(recommend.router)

# ✅ OAuth 로그인 API 연결
app.include_router(auth_router)
