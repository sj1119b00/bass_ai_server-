from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
import requests
from database import SessionLocal
from models import User

router = APIRouter()

def get_title_by_level(level: int) -> str:
    return {
        1: "입문자",
        2: "초보 앵글러",
        3: "숙련 앵글러",
        4: "포인트 마스터",
        5: "배스헌터 고수"
    }.get(level, "배스 신입")

@router.post("/auth/login")
async def oauth_login(request: Request):
    data = await request.json()
    token = data.get("token")
    provider = data.get("provider")

    if provider not in ["kakao", "naver"]:
        raise HTTPException(status_code=400, detail="지원하지 않는 provider입니다.")

    # ✅ Kakao 처리
    if provider == "kakao":
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("https://kapi.kakao.com/v2/user/me", headers=headers)

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="카카오 인증 실패")

        user_info = response.json()
        oauth_id = str(user_info["id"])
        nickname = user_info["properties"].get("nickname", "")
        profile_image = user_info["properties"].get("profile_image", "")

    # ✅ Naver 처리
    elif provider == "naver":
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("https://openapi.naver.com/v1/nid/me", headers=headers)

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="네이버 인증 실패")

        user_info = response.json()["response"]
        oauth_id = str(user_info["id"])
        nickname = user_info.get("name", "") or user_info.get("nickname", "")
        profile_image = user_info.get("profile_image", "")

    # ✅ DB 저장 또는 조회
    db: Session = SessionLocal()
    user = db.query(User).filter_by(oauth_provider=provider, oauth_id=oauth_id).first()

    if not user:
        user = User(
            oauth_provider=provider,
            oauth_id=oauth_id,
            nickname=nickname,
            profile_image=profile_image
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    user_data = {
        "id": user.id,
        "oauth_provider": user.oauth_provider,
        "oauth_id": user.oauth_id,
        "nickname": user.nickname,
        "level": user.level,
        "exp": user.exp,
        "title": get_title_by_level(user.level)
    }

    db.close()
    return {
        "msg": "로그인 성공",
        "user": user_data
    }
