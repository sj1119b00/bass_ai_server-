from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User

router = APIRouter(prefix="/user")

class NicknameUpdateRequest(BaseModel):
    oauth_provider: str
    oauth_id: str
    new_nickname: str

@router.patch("/update_nickname")  # ✅ 여기 수정됨!
async def update_nickname(data: NicknameUpdateRequest):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter_by(
            oauth_provider=data.oauth_provider,
            oauth_id=data.oauth_id
        ).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.nickname = data.new_nickname
        db.commit()

        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
