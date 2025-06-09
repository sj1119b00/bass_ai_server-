from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
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

@router.post("/auth/verify")
async def verify_user(request: Request):
    data = await request.json()
    oauth_provider = data.get("oauth_provider")
    oauth_id = data.get("oauth_id")

    print(f"verify 요청: provider={oauth_provider}, id={oauth_id}")

    with SessionLocal() as db:
        user = db.query(User).filter_by(oauth_provider=oauth_provider, oauth_id=oauth_id).first()

        if user:
            user_data = {
                "id": user.id,
                "nickname": user.nickname,
                "level": user.level,
                "exp": user.exp,
                "title": get_title_by_level(user.level)
            }
            return JSONResponse(content={"valid": True, "user": user_data}, media_type="application/json; charset=utf-8"   )
        else:
            return JSONResponse(content={"valid": False}, status_code=401)
