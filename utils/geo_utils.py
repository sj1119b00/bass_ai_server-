import requests
from config import KAKAO_API_KEY

def get_lat_lng_from_address(address: str):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": address}

    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            documents = res.json().get("documents", [])
            if documents:
                x = float(documents[0]["x"])  # 경도
                y = float(documents[0]["y"])  # 위도
                return y, x
    except Exception as e:
        print(f"❌ 주소 → 좌표 변환 실패: {e}")
    return None, None
