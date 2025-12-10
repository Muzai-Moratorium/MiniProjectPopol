# traffic_analysis/traffic_bp.py

from flask import Blueprint, render_template, Response, request
import urllib.request
import urllib.error
import json
import pandas as pd
import cv2
import numpy as np
import time
from collections import deque
import sys

# Blueprint 객체 생성
bp = Blueprint(
    "traffic",
    __name__,
    url_prefix="/traffic",
    template_folder="templates",
    static_folder="static"
)
# ----------------------------------------------------------------------
# 1. 설정 및 상수 정의 (원본 유지 및 MIN_Y 수정)
# ----------------------------------------------------------------------
key = "88e0c489ff14491a8642560c3eaebac5"

# 🌐 API 검색 범위 (안성 지역 포함을 위해 MIN_Y 확장)
MIN_X = 126.5 
MAX_X = 127.6 
MIN_Y = 36.8  # 37.0 -> 36.8로 확장 (안성IC 등 남부 지역 포함)
MAX_Y = 37.8  

# CCTV 필터링 키워드 (사용자 지정 목록)
TARGET_CCTV_FILTERS = [
    "[경부선] 서초", "[경부선] 원지동", "[경부선] 양재", "[경부선] 상적교",
    "[경부선] 달래내2", "[경부선] 금현동", "[경부선] 달래내1", "[경부선] 금토분기점1",
    "[경부선] 금토분기점2", "[경부선] 판교분기점", "[경부선] 판교3", "[경부선] 판교2",
    "[경부선] 판교1", "[경부선] 삼평터널(서울)", "[경부선] 백현", "[경부선] 서울영업소",
    "[경부선] 서울영업소-광장", "[경부선] 금곡교", "[경부선] 죽전휴계소", "[경부선] 죽전",
    "[경부선] 신갈분기점_경부", "[경부선] 신갈분기점2", "[경부선] 수원", "[경부선] 공세육교",
    "[경부선] 기흥휴계소", "[경부선] 기흥", "[경부선] 기흥동탄", "[경부선] 경부동탄터널(입구방음터널)",
    "[경부선] 경부동탄터널(부산1)", "[경부선] 경부동탄터널(부산2)", "[경부선] 경부동탄터널(부산3)",
    "[경부선] 경부동탄터널(부산4)", "[경부선] 경부동탄터널(부산5)", "[경부선] 경부동탄터널(출구방음터널)",
    "[경부선] 경부동탄터널(출구)", "[경부선] 동탄분기점", "[경부선] 동탄JC(동탄)", "[경부선] 부산동",
    "[경부선] 오산", "[경부선] 원동", "[경부선] 남사육교", "[경부선] 외동천교", "[경부선] 진위천교",
    "[경부선] 남사졸음쉼터", "[경부선] 남사정류장", "[경부선] 산하", "[경부선] 안성휴계소2",
    "[경부선] 안성휴게소(서울)", "[경부선] 원곡", "[경부선] 안성분기점1", "[경부선] 안성분기점2",
    "[경부선] 안성휴계소(부산)", "[경부선] 공도", "[경부선] 원곡졸음쉼터", "[경부선] 안성"
]

url_cctv_api = (
    f'https://openapi.its.go.kr:9443/cctvInfo?apiKey={key}&type=ex&cctvType=1'
    f'&minX={MIN_X}&maxX={MAX_X}&minY={MIN_Y}&maxY={MAX_Y}&getType=json'
)

# --- [설정] 분석 기준 ---
ROI_Y_RATIO = 0.35              
PERSPECTIVE_WEIGHT_MAX = 10.0    
HISTORY_LENGTH = 100             
OCCUPANCY_EMPTY_LIMIT = 0.003   
SPEED_CONGESTION = 1.0          
SPEED_SLOW = 2.0                

# --- 전역 변수 ---
CCTV_URL_DICT = {}
FILTERED_NAMES = []
IS_INITIALIZED = False

# ----------------------------------------------------------------------
# 2. 헬퍼 함수
# ----------------------------------------------------------------------

def get_status_text_and_color(avg_speed, avg_occupancy):
    """최종 상태 반환"""
    if avg_occupancy < OCCUPANCY_EMPTY_LIMIT:
        return "차량 없음 (No Traffic)", (192, 192, 192) # Gray
    if avg_speed < SPEED_CONGESTION:
        return "정체 (Congested)", (0, 0, 255) # Red (BGR)
    if avg_speed < SPEED_SLOW:
        return "서행 (Slow)", (0, 255, 255) # Yellow (BGR)
    return "원활 (Clear)", (0, 255, 0) # Green (BGR)

def draw_text_with_outline(img, text, pos, font_scale, color, thickness):
    """배경 없이 글씨를 잘 보이게 하기 위해 외곽선(검정)을 먼저 그리고 색깔 글씨를 씀"""
    x, y = pos
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness, cv2.LINE_AA)

def initialize_cctv_data():
    """CCTV 목록을 API에서 가져와 필터링 및 전역 변수에 저장"""
    global CCTV_URL_DICT, FILTERED_NAMES, IS_INITIALIZED
    if IS_INITIALIZED:
        return

    print("🌐 CCTV 목록을 가져오는 중...")
    try:
        response = urllib.request.urlopen(url_cctv_api)
        json_str = response.read().decode('utf-8')
        data_list = json.loads(json_str).get("response", {}).get("data", [])
        
        if not data_list:
            print("[Error] CCTV 데이터를 찾지 못했습니다.")
            return

        cctv_play = pd.json_normalize(data_list, sep=',')
        CCTV_URL_DICT = cctv_play.set_index('cctvname')['cctvurl'].to_dict()
        
        # 필터링 (TARGET_CCTV_FILTERS 순서대로 정렬)
        filtered_names = []
        for filter_condition in TARGET_CCTV_FILTERS:
            # 완전 일치하는 이름 찾기
            if filter_condition in CCTV_URL_DICT and filter_condition not in filtered_names:
                 filtered_names.append(filter_condition)
            
            # 부분 일치하는 이름 찾기 (혹시 모를 상황 대비)
            for cctv_name in CCTV_URL_DICT.keys():
                if cctv_name not in filtered_names and filter_condition in cctv_name:
                    filtered_names.append(cctv_name)

        FILTERED_NAMES = filtered_names
        IS_INITIALIZED = True
        print(f"✨ CCTV 목록 초기화 완료 ({len(FILTERED_NAMES)}개)")

    except Exception as e:
        print(f"[Error] CCTV 초기화 실패: {e}")

# ----------------------------------------------------------------------
# 3. 비디오 프레임 제너레이터 (핵심 분석 로직)
# ----------------------------------------------------------------------
def generate_frames(cctv_url):
    """비디오 캡처 및 실시간 분석을 수행하고 JPEG 프레임을 Yield"""
    
    capture = cv2.VideoCapture(cctv_url) 
    if not capture.isOpened():
        print(f"[Error] 스트림 연결 실패: {cctv_url}")
        return

    # 변수 초기화
    prev_frame_gray = None
    
    # 히스토리 버퍼
    history_down = deque(maxlen=HISTORY_LENGTH) 
    history_up = deque(maxlen=HISTORY_LENGTH)   
    
    # 배경 차분 객체 (점유율 계산용)
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=40, detectShadows=False)

    # LK 파라미터 (광학 흐름 추정용)
    feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7) 
    lk_params = dict(winSize=(15, 15), maxLevel=2, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)) 
    
    weight_map = None
    
    # FPS 조절을 위한 시간 변수
    start_time = time.time()
    
    try:
        while capture.isOpened():
            run, frame = capture.read()
            if not run:
                print("스트림 종료 또는 읽기 실패. 재시도 중...")
                time.sleep(1)
                capture = cv2.VideoCapture(cctv_url)
                continue
            
            # --- 2. 전처리 ---
            frame_blur = cv2.GaussianBlur(frame, (5, 5), 0)
            current_gray_full = cv2.cvtColor(frame_blur, cv2.COLOR_BGR2GRAY)
            annotated_frame = frame.copy()
            
            H, W = current_gray_full.shape
            roi_y_start = int(H * ROI_Y_RATIO)
            roi_h = H - roi_y_start

            # --- 가중치 맵 생성 (최초 1회) ---
            if weight_map is None or weight_map.shape[0] != roi_h:
                weights = np.linspace(PERSPECTIVE_WEIGHT_MAX, 1.0, roi_h).reshape(-1, 1)
                weight_map = weights.astype(np.float32)

            if prev_frame_gray is not None:
                # --- 3. 영상 안정화 및 ROI 처리 ---
                # 웹 환경에서는 안정화 로직을 제거하거나 간소화하여 성능 저하 및 끊김 방지
                stabilized_gray = current_gray_full # 안정화 생략

                roi_gray = stabilized_gray[roi_y_start:, :]
                roi_prev_gray = prev_frame_gray[roi_y_start:, :]
                
                # --- 4. 점유율 (Occupancy) - 배경 차분 ---
                fg_mask = bg_subtractor.apply(roi_gray, learningRate=0.005) # 학습률 낮춤
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
                
                total_pixels = fg_mask.size
                occupancy_rate = np.count_nonzero(fg_mask) / total_pixels

                # --- 5. 광학 흐름 및 가중치 적용 ---
                flow = cv2.calcOpticalFlowFarneback(roi_prev_gray, roi_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                flow_y = flow[..., 1] 
                weighted_flow_y = flow_y * weight_map

                # --- 6. 방향 분리 및 속도 계산 ---
                
                mask_down = (weighted_flow_y > 0.3) 
                speed_down = np.median(weighted_flow_y[mask_down]) if np.sum(mask_down) > 10 else 0.0
                    
                mask_up = (weighted_flow_y < -0.3)
                speed_up = np.median(np.abs(weighted_flow_y[mask_up])) if np.sum(mask_up) > 10 else 0.0

                # --- 7. 데이터 누적 및 상태 판단 ---
                history_down.append((speed_down, occupancy_rate))
                history_up.append((speed_up, occupancy_rate))

                if len(history_down) > 10:
                    avg_speed_down = np.mean([s for s, o in history_down])
                    avg_occ_down   = np.mean([o for s, o in history_down])
                    
                    avg_speed_up   = np.mean([s for s, o in history_up])
                    avg_occ_up     = np.mean([o for s, o in history_up])

                    status_down, color_down = get_status_text_and_color(avg_speed_down, avg_occ_down)
                    status_up, color_up     = get_status_text_and_color(avg_speed_up, avg_occ_up)
                    
                    # 시각화
                    cv2.line(annotated_frame, (0, roi_y_start), (W, roi_y_start), (0, 255, 255), 1)
                    
                    draw_text_with_outline(annotated_frame, f"방향 1: {status_down}", (20, 50), 0.8, color_down, 2)
                    draw_text_with_outline(annotated_frame, f"W.Spd:{avg_speed_down:.1f} | 점유율:{avg_occ_down*100:.1f}%", (20, 80), 0.6, (220, 220, 220), 1)

                    draw_text_with_outline(annotated_frame, f"방향 2: {status_up}", (20, 120), 0.8, color_up, 2)
                    draw_text_with_outline(annotated_frame, f"W.Spd:{avg_speed_up:.1f} | 점유율:{avg_occ_up*100:.1f}%", (20, 150), 0.6, (220, 220, 220), 1)
                    
                else:
                    draw_text_with_outline(annotated_frame, f"데이터 수집 중... ({len(history_down)}/{HISTORY_LENGTH})", (20, 50), 1, (255,255,255), 2)

                prev_frame_gray = current_gray_full.copy()

            else:
                draw_text_with_outline(annotated_frame, "초기화 중...", (20, 50), 1, (255,255,255), 2)
                prev_frame_gray = current_gray_full.copy()

            # --- 8. 스트리밍 전송 ---
            ret, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # 프레임 속도 조절 (대략 1초에 15~30프레임)
            time.sleep(0.03)

    finally:
        if capture:
            capture.release()


# ----------------------------------------------------------------------
# 4. Blueprint 라우트 정의
# ----------------------------------------------------------------------


@bp.route('/', methods=['GET', 'POST'])  # '/cctv' -> '/' 변경
def index():
    initialize_cctv_data()

    target_name = request.form.get('cctv_name') if request.method == 'POST' else None
    if not target_name and FILTERED_NAMES:
        target_name = FILTERED_NAMES[0]

    target_url = CCTV_URL_DICT.get(target_name)

    return render_template('traffic.html',
                           cctv_names=FILTERED_NAMES,
                           target_name=target_name,
                           target_url=target_url)


@bp.route('/video_feed/<path:cctv_url>')
def video_feed(cctv_url):
    decoded_url = urllib.parse.unquote(cctv_url)
    return Response(generate_frames(decoded_url),
                    mimetype='multipart/x-mixed-replace; boundary=frame')