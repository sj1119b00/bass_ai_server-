from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import csv

app = FastAPI()

# Flutter 앱에서 접속 허용 (CORS 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 저장 폴더 만들기
os.makedirs("images", exist_ok=True)
os.makedirs("data", exist_ok=True)

# CSV 파일 경로
csv_path = "data/uploads.csv"

# CSV 파일이 없으면 헤더 생성
if not os.path.exists(csv_path):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "lat", "lon", "address", "timestamp", "temp", "condition", "rig", "spot_name"])

# ✅ 루트 경로 응답 추가 (Render에서 확인용!)
@app.get("/")
def read_root():
    return {"message": "배포 성공! 🎉"}

# API 정의
@app.post("/upload_catch")
async def upload_catch(
    photo: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form(...),
    timestamp: str = Form(...),
    temp: float = Form(...),
    condition: str = Form(...),
    rig: str = Form(...),
    spot_name: str = Form(...)
):
    # 이미지 저장
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}"
    image_path = os.path.join("images", filename)

    with open(image_path, "wb") as f:
        f.write(await photo.read())

    # CSV에 정보 저장
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([filename, latitude, longitude, address, timestamp, temp, condition, rig, spot_name])

    return {"status": "success", "filename": filename}
