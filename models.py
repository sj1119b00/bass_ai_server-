from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    oauth_provider = Column(String, nullable=False)  # ex: kakao, naver
    oauth_id = Column(String, unique=True, nullable=False)
    nickname = Column(String, default="")
    profile_image = Column(String, default="")
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserPoint(Base):
    __tablename__ = "user_points"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(String)  # ex: "조과 업로드", "광고 시청", "GPT 사용"
    amount = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserLevel(Base):
    __tablename__ = "user_levels"
    level = Column(Integer, primary_key=True)
    required_exp = Column(Integer)  # 해당 레벨에 필요한 누적 경험치

class UserBadge(Base):
    __tablename__ = "user_badges"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    badge_name = Column(String)
    is_equipped = Column(Boolean, default=False)  # 착용 중 여부

class Catch(Base):
    __tablename__ = "catches"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_path = Column(String)
    bait = Column(String)
    address = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommunityPost(Base):
    __tablename__ = "community_posts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    image_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class RecommendationLog(Base):
    __tablename__ = "recommendation_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    location = Column(String)
    bait = Column(String)
    used_gpt = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class FishingCatch(Base):
    __tablename__ = "fishing_catches"
    id = Column(Integer, primary_key=True)
    spot_name = Column(String)              # 포인트 이름
    blog_title = Column(String)             # 블로그 제목
    blog_url = Column(String, unique=True)  # 블로그 링크
    summary = Column(Text)                  # 요약 내용
    posted_at = Column(DateTime)            # 글 작성일
    weather = Column(String)                # 날씨
    time_period = Column(String)            # 시간대
    bait_type = Column(String)              # 채비
    temperature = Column(String)            # 수온
    wind = Column(String)                   # 바람세기
    result = Column(Integer)                # 조과 여부
    created_at = Column(DateTime, default=datetime.utcnow)

class FishingSpot(Base):
    __tablename__ = "fishing_spots"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)         # 포인트 이름 (고삼지, 청평호 등)
    type = Column(String)                      # '댐', '저수지', '천', '기타'
    found_in_title = Column(String)            # 포인트를 발견한 블로그 제목
    blog_url = Column(String)                  # 해당 블로그 URL
    created_at = Column(DateTime, default=datetime.utcnow)

class TrainingFishingData(Base):
    __tablename__ = "training_fishing_data"
    id = Column(Integer, primary_key=True)
    spot_name = Column(String)                  # 포인트 이름
    address = Column(String)                    # 주소 (문자열)
    latitude = Column(Float)                    # 위도
    longitude = Column(Float)                   # 경도
    weather = Column(String)
    time_period = Column(String)
    bait_type = Column(String)
    temperature = Column(String)
    wind = Column(String)
    result = Column(Integer)
    blog_url = Column(String)
    posted_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)