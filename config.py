# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # .env 파일 불러오기

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")