from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# 본인 PostgreSQL 연결 정보 맞게 수정!
DATABASE_URL = "postgresql://postgres:bassmate1119@localhost:5432/bass_ai_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)
