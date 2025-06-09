from fastapi import FastAPI, File, Form, UploadFile, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import os
import json

from database import Base, engine, SessionLocal, create_tables
from models import Catch, User
from routers.ai import recommend
from routers import user 
from auth.auth import router as auth_router

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

# ✅ 로그인 시 레벨 타이클 계산 함수
def get_title_by_level(level: int) -> str:
    return {
        1: "입문자",
        2: "차분 에이널러",
        3: "숙련 에이널러",
        4: "포인트 마스터",
        5: "배스헬터 고수"
    }.get(level, "배스 신입")

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

# ✅ 조과 업로드 API
@app.post("/upload_catch")
async def upload_catch(
    photo: UploadFile = File(...),
    address: str = Form(...),
    timestamp: str = Form(...),
    temp: float = Form(...),
    condition: str = Form(...),
    rig: str = Form(...),
    spot_name: str = Form(...)
):
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}"
    image_path = os.path.join("images", filename)

    with open(image_path, "wb") as f:
        f.write(await photo.read())

    db = SessionLocal()
    catch = Catch(
        spot_name=spot_name,
        address=address,
        rig=rig,
        temp=temp,
        condition=condition,
        timestamp=datetime.fromisoformat(timestamp),
        filename=filename
    )
    db.add(catch)
    db.commit()
    db.close()

    return {"status": "success", "filename": filename}

# ✅ 조과 목록 조회 API
@app.get("/catches")
def get_catches():
    db = SessionLocal()
    catches = db.query(Catch).all()
    db.close()

    result = []
    for row in catches:
        result.append({
            "spot_name": row.spot_name,
            "address": row.address,
            "rig": row.rig,
            "temp": row.temp,
            "condition": row.condition,
            "timestamp": row.timestamp.isoformat(),
            "filename": row.filename,
            "image_url": f"/images/{row.filename}"
        })

    return {"catches": result}

# ✅ 추천 API 연결
app.include_router(recommend.router)

# ✅ OAuth 로그인 API 연결
app.include_router(auth_router)
