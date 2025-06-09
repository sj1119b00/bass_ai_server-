# train_model.py (정규화된 점수 기반 회귀 모델)

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from xgboost import XGBRegressor
import joblib

# ✅ PostgreSQL 연결
DATABASE_URL = "postgresql://postgres:bassmate1119@localhost:5432/bass_ai_db"
engine = create_engine(DATABASE_URL)

# ✅ 학습 데이터 로딩
query = """
SELECT latitude, longitude, weather, temperature, wind, time_period,
       created_at AS posted_at, result
FROM training_fishing_data
WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND result IS NOT NULL
"""
df = pd.read_sql(query, engine)

# ✅ 날짜 파생 컬럼
df['posted_at'] = pd.to_datetime(df['posted_at'])
df['month'] = df['posted_at'].dt.month
df['hour'] = df['posted_at'].dt.hour
df['season'] = df['month'].map({
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "fall", 10: "fall", 11: "fall"
})

# ✅ 수치형 변환 + 결측치 처리
df['temperature'] = pd.to_numeric(df['temperature'], errors='coerce')
df['wind'] = pd.to_numeric(df['wind'], errors='coerce')
df['temperature'].fillna(df['temperature'].mean(), inplace=True)
df['wind'].fillna(df['wind'].mean(), inplace=True)

# ✅ 점수 변환: result → 별점 기반 점수로 (0 → 0.5, 1 → 3.0)
df['score'] = df['result'].map({0: 0.5, 1: 3.0})

# ✅ One-hot 인코딩
df = pd.get_dummies(df, columns=["weather", "time_period", "season"])

# ✅ 입력(X), 정답(y)
X = df.drop(columns=["posted_at", "month", "result", "score"])
y = df["score"]

# ✅ 스케일링 적용
scaler = StandardScaler()
numerical_cols = ["latitude", "longitude", "temperature", "wind", "hour"]
X[numerical_cols] = scaler.fit_transform(X[numerical_cols])

# ✅ 데이터 분할
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ✅ XGBoost 회귀 모델 구성
model = XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    missing=np.nan
)
model.fit(X_train, y_train)

# ✅ 모델 평가
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("\n✅ 모델 학습 완료")
print(f"📊 평균제곱오차 (MSE): {mse:.4f}")
print(f"📈 결정계수 (R2 score): {r2:.4f}")

# ✅ 모델 저장
joblib.dump(model, "bass_ai_model_latest.pkl")
joblib.dump(scaler, "bass_ai_scaler.pkl")
joblib.dump(X.columns.tolist(), "bass_ai_model_features.pkl")

print("💾 모델 및 피처 정보 저장 완료!")
