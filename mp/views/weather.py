from flask import Flask, request, jsonify, Blueprint  # ty:ignore[unresolved-import]
import os
from datetime import datetime, timedelta
from geopy.distance import geodesic
import requests
import pandas as pd

bp = Blueprint("weather", __name__)

# 엑셀 파일 로드
location_data = pd.read_excel('mp/static/nxny.xlsx')[['격자 X', '격자 Y', '경도(초/100)', '위도(초/100)']]

# --- 기상청 base_time 보정 ---
def get_base_time():
    now = datetime.now()
    if now.minute < 30:
        now -= timedelta(hours=1)
    base_date = now.strftime("%Y%m%d")
    base_time = now.strftime("%H") + "30"
    return base_date, base_time

# --- 가장 가까운 격자 찾기 ---
def find_nearest_grid_coordinates(latitude, longitude):
    min_distance = float('inf')
    nearest_nx = None
    nearest_ny = None

    for _, row in location_data.iterrows():
        grid_point = (row['위도(초/100)'], row['경도(초/100)'])
        distance = geodesic((latitude, longitude), grid_point).meters
        if distance < min_distance:
            min_distance = distance
            nearest_nx = row['격자 X']
            nearest_ny = row['격자 Y']

    return nearest_nx, nearest_ny

# --- API 요청 ---
@bp.route('/weather', methods=['GET'])
def get_weather():
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')

    if not latitude or not longitude:
        return jsonify({"error": "Both latitude and longitude parameters are required"}), 400

    latitude = float(latitude)
    longitude = float(longitude)

    nx, ny = find_nearest_grid_coordinates(latitude, longitude)
    base_date, base_time = get_base_time()

    service_key = os.environ.get("WEATHER_SERVICE_KEY")

    api_url = (
        f"https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
        f"?serviceKey={service_key}"
        f"&pageNo=1&numOfRows=1000&dataType=JSON"
        f"&base_date={base_date}&base_time={base_time}&nx={int(nx)}&ny={int(ny)}"
    )

    try:
        response = requests.get(api_url, timeout=10)
        # 상태 코드 확인
        if response.status_code != 200:
            return jsonify({"error": f"HTTP {response.status_code}", "text": response.text}), 500

        data = response.json()
        items = data["response"]["body"]["items"]["item"]

        # 단순화된 JSON
        parsed = {}
        for i in items:
            category = i["category"]
            value = i["obsrValue"]
            if category == "T1H": parsed["temp"] = float(value)
            if category == "REH": parsed["humidity"] = float(value)
            if category == "RN1": parsed["rain"] = float(value)
            if category == "WSD": parsed["wind"] = float(value)
            if category == "PTY": parsed["rainType"] = int(value)
            if category == "SKY": parsed["sky"] = int(value)

        return jsonify(parsed)

    except Exception as e:
        return jsonify({"error": str(e)}), 500



#출처: https: // marketerbong.tistory.com / 100[마켓플레이어, 마케터봉: 티스토리]