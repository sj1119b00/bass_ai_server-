from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os
import csv

app = FastAPI()

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 이미지/데이터 폴더 생성
os.makedirs("images", exist_ok=True)
os.makedirs("data", exist_ok=True)

# CSV 경로
csv_path = "data/uploads.csv"

# CSV 초기 헤더 생성 (위경도 제거됨)
if not os.path.exists(csv_path):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "address", "timestamp", "temp", "condition", "rig", "spot_name"])

# 이미지 접근 가능하게 설정
app.mount("/images", StaticFiles(directory="images"), name="images")

# 루트 확인용
@app.get("/")
def read_root():
    return {"message": "배포 성공! 🎉"}

# ✅ 업로드 API (위도/경도 제거됨)
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
    # 이미지 저장
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}"
    image_path = os.path.join("images", filename)

    with open(image_path, "wb") as f:
        f.write(await photo.read())

    # CSV 저장
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([filename, address, timestamp, temp, condition, rig, spot_name])

    return {"status": "success", "filename": filename}

# ✅ 조과 목록 조회
@app.get("/catches")
def get_catches():
    if not os.path.exists(csv_path):
        return JSONResponse(content={"catches": []})

    catches = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["image_url"] = f"https://bass-ai-api.onrender.com/images/{row['filename']}"
            catches.append(row)

    return {"catches": catches}
@app.get("/debug_csv")
def debug_csv():
    if not os.path.exists(csv_path):
        return {"exists": False, "message": "CSV 파일 없음"}

    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"exists": True, "content": content}