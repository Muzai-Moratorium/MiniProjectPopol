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
import os
from dotenv import load_dotenv
import sys
import urllib.parse # URL 디코딩을 위해 명시적으로 import

# ======================= ★ YOLO11 모델 불러오기 ★ ======================
try:
    from ultralytics import YOLO
    # 필요하다면 tracker 설정을 위해 'bytetrack.yaml' 등을 사용할 수도 있습니다.
    yolo_model = YOLO("yolo11s.pt")
    print("✅ YOLO11 모델 로드 완료")
except Exception as e:
    print("⚠ YOLO 로드 실패:", e)
    yolo_model = None
# ==========================================================================

bp = Blueprint(
    "traffic",
    __name__,
    url_prefix="/traffic",
    template_folder="templates",
    static_folder="static"
)

# ----------------------------------------------------------------------
# 1. 설정 및 상수 정의
# ----------------------------------------------------------------------
key = os.getenv("API_KEY", "YOUR_DEFAULT_KEY_OR_EXIT_IF_REQUIRED") 
# 만약 API 키가 필수라면, key가 None일 경우 여기서 프로그램을 종료하거나 예외를 발생시켜야 합니다.
if key == "YOUR_DEFAULT_KEY_OR_EXIT_IF_REQUIRED":
    print("❌ 경고: API_KEY 환경 변수가 로드되지 않았습니다. 기본값이 사용되거나 로직이 실패할 수 있습니다.")

MIN_X = 126.5 
MAX_X = 127.6 
MIN_Y = 36.8  
MAX_Y = 37.8  

TARGET_CCTV_FILTERS = [
    "[경부선] 서초", "[경부선] 원지동", "[경부선] 양재", "[경부선] 상적교",
    "[경부선] 달래내2", "[경부선] 금현동", "[경부선] 달래내1", "[경부선] 금토분기점1",
    "[경부선] 금토분기점2", "[경부선] 판교분기점", "[경부선] 판교3", "[경부선] 판교2",
    "[경부선] 판교1", "[경부선] 삼평터널(서울)", "[경부선] 백현", "[경부선] 서울영업소",
    "[경부선] 서울영업소-광장", "[경부선] 금곡교", "[경부선] 죽전휴계소", "[경부선] 죽전",
    "[경부선] 신갈분기점_경부", "[경부선] 신갈분기점2", "[경부선] 수원", "[경부선] 공세육교",
    "[경부선] 기흥휴계소", "[경부선] 기흥", "[경부선] 기흥동탄",
    "[경부선] 경부동탄터널(입구방음터널)", "[경부선] 경부동탄터널(부산1)", "[경부선] 경부동탄터널(부산2)",
    "[경부선] 경부동탄터널(부산3)", "[경부선] 경부동탄터널(부산4)", "[경부선] 경부동탄터널(부산5)",
    "[경부선] 경부동탄터널(출구방음터널)", "[경부선] 경부동탄터널(출구)", "[경부선] 동탄분기점",
    "[경부선] 동탄JC(동탄)", "[경부선] 부산동", "[경부선] 오산", "[경부선] 원동",
    "[경부선] 남사육교", "[경부선] 외동천교", "[경부선] 진위천교", "[경부선] 남사졸음쉼터",
    "[경부선] 남사정류장", "[경부선] 산하", "[경부선] 안성휴계소2",
    "[경부선] 안성휴게소(서울)", "[경부선] 원곡", "[경부선] 안성분기점1",
    "[경부선] 안성분기점2", "[경부선] 안성휴계소(부산)", "[경부선] 공도",
    "[경부선] 원곡졸음쉼터", "[경부선] 안성"
]

url_cctv_api = (
    f'https://openapi.its.go.kr:9443/cctvInfo?apiKey={key}&type=ex&cctvType=1'
    f'&minX={MIN_X}&maxX={MAX_X}&minY={MIN_Y}&maxY={MAX_Y}&getType=json'
)

# --- [추가] 카메라 안정화 및 일시정지 상수 ---
CAMERA_MOVE_THRESHOLD = 20.0    # 20px 이상 움직이면 카메라 이동으로 간주
PAUSE_DURATION = 3.0            # 이동 감지 시 3초간 분석 중단 (이동 시간 고려)

ROI_Y_RATIO = 0.35
PERSPECTIVE_WEIGHT_MAX = 10.0
HISTORY_LENGTH = 100
OCCUPANCY_EMPTY_LIMIT = 0.005 
SPEED_CONGESTION = 1.0
SPEED_SLOW = 2.0

CCTV_URL_DICT = {}
FILTERED_NAMES = []
IS_INITIALIZED = False

bbox_smooth = {}  
ALPHA = 0.6       

# ----------------------------------------------------------------------
# 2. 상태 텍스트 함수 (변동 없음)
# ----------------------------------------------------------------------
def get_status_text_and_color(avg_speed, avg_occupancy):
    # 1. 점유율이 매우 낮음 -> 차가 없음 (가장 먼저 판단)
    if avg_occupancy < OCCUPANCY_EMPTY_LIMIT:
        return "No Traffic", (192, 192, 192)
    # 2. 정체
    if avg_speed < SPEED_CONGESTION:
        return "Congested", (0, 0, 255)
    # 3. 서행
    if avg_speed < SPEED_SLOW:
        return "Slow", (0, 255, 255)
    # 4. 원활
    return "Clear", (0, 255, 0)

def draw_text_with_outline(img, text, pos, font_scale, color, thickness):
    x, y = pos
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                font_scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                font_scale, color, thickness, cv2.LINE_AA)

# ----------------------------------------------------------------------
# 3. CCTV API 초기화 (변동 없음)
# ----------------------------------------------------------------------
def initialize_cctv_data():
    global CCTV_URL_DICT, FILTERED_NAMES, IS_INITIALIZED
    if IS_INITIALIZED:
        return

    try:
        response = urllib.request.urlopen(url_cctv_api)
        json_str = response.read().decode('utf-8')
        data_list = json.loads(json_str).get("response", {}).get("data", [])

        cctv_play = pd.json_normalize(data_list, sep=',')
        CCTV_URL_DICT = cctv_play.set_index('cctvname')['cctvurl'].to_dict()

        filtered = []
        for f in TARGET_CCTV_FILTERS:
            if f in CCTV_URL_DICT:
                filtered.append(f)
            # URL 이름이 필터 이름을 포함하는 경우 추가
            for name in CCTV_URL_DICT.keys():
                if f in name and name not in filtered:
                    filtered.append(name)
                    CCTV_URL_DICT[f] = CCTV_URL_DICT.pop(name)
                    break 

        FILTERED_NAMES = filtered
        IS_INITIALIZED = True
        print("✨ CCTV 목록 초기화 완료")

    except Exception as e:
        print("[Error] CCTV 초기화 실패:", e)

# ----------------------------------------------------------------------
# 4. 비디오 분석 + YOLO (카메라 안정화 및 일시정지 로직 추가)
# ----------------------------------------------------------------------
def generate_frames(cctv_url):
    capture = cv2.VideoCapture(cctv_url)
    if not capture.isOpened():
        print("[Error] 스트림 열기 실패:", cctv_url)
        return

    prev_frame_gray = None
    history_down = deque(maxlen=HISTORY_LENGTH)
    history_up = deque(maxlen=HISTORY_LENGTH)

    # 배경 차분 객체 초기화
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(
        history=500, varThreshold=40, detectShadows=False
    )

    weight_map = None
    frame_count = 0  
    latest_detections = [] 
    
    # ⭐ [추가] 카메라 안정화 및 일시 정지 변수 ⭐
    is_paused = False
    pause_end_time = 0.0
    
    # LK 파라미터 정의 (OpenCV 단독 코드에서 가져옴)
    feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7) 
    lk_params = dict(winSize=(15, 15), maxLevel=2, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)) 

    try:
        while capture.isOpened():
            # 1. 일시 정지 상태 체크 및 해제
            if is_paused:
                if time.time() > pause_end_time:
                    # 일시 정지 해제 및 모든 분석 상태 초기화
                    is_paused = False
                    prev_frame_gray = None
                    history_down.clear()
                    history_up.clear()
                    # 배경 차분 객체 재초기화 (누적된 마스크 정보 삭제)
                    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=40, detectShadows=False)
                    print(f"[{cctv_url}] 분석 재개 및 초기화 완료.")
                else:
                    # 일시 정지 중에는 프레임만 읽어와서 경고 표시
                    ok, frame = capture.read()
                    if not ok: break
                    annotated_frame = frame.copy()
                    draw_text_with_outline(annotated_frame, "PAUSED (Camera Moving)", (20, 50), 1, (0, 0, 255), 2)
                    
                    # 프레임 인코딩 및 반환
                    ret, buffer = cv2.imencode('.webp', annotated_frame, [int(cv2.IMWRITE_WEBP_QUALITY), 80])
                    if not ret: continue
                    yield (b'--frame\r\n' b'Content-Type: image/webp\r\n\r\n' + buffer.tobytes() + b'\r\n')
                    continue # 다음 루프로 이동 (분석 로직 건너뛰기)
            
            # 2. 프레임 읽기 (일반 루프)
            ok, frame = capture.read()
            if not ok:
                capture = cv2.VideoCapture(cctv_url)
                continue

            annotated_frame = frame.copy()
            H, W = frame.shape[:2]

            # =================== ★ YOLO DETECTION (변동 없음) ★ =========================
            if yolo_model is not None:
                # ... (YOLO 및 Smoothing 로직 유지) ...
                if frame_count % 2 == 0:
                    results = yolo_model.track(frame, persist=True, verbose=False)
                    current_detections = []

                    for box in results[0].boxes:
                        cls = int(box.cls[0])
                        if cls not in [2, 3, 5, 7]: continue

                        track_id = int(box.id[0]) if box.id is not None else -1
                        x1, y1, x2, y2 = map(int, box.xyxy[0])

                        if track_id != -1:
                            if track_id in bbox_smooth:
                                prev = bbox_smooth[track_id]
                                smoothed = [
                                    int(prev[0] * (1 - ALPHA) + x1 * ALPHA),
                                    int(prev[1] * (1 - ALPHA) + y1 * ALPHA),
                                    int(prev[2] * (1 - ALPHA) + x2 * ALPHA),
                                    int(prev[3] * (1 - ALPHA) + y2 * ALPHA)
                                ]
                                bbox_smooth[track_id] = smoothed
                                x1, y1, x2, y2 = smoothed
                            else:
                                bbox_smooth[track_id] = [x1, y1, x2, y2]
                        
                        label_text = f"{results[0].names[cls]} {track_id}" if track_id != -1 else results[0].names[cls]
                        current_detections.append({'coords': (x1, y1, x2, y2), 'label': label_text})
                    
                    latest_detections = current_detections

                for det in latest_detections:
                    gx1, gy1, gx2, gy2 = det['coords']
                    cv2.rectangle(annotated_frame, (gx1, gy1), (gx2, gy2), (0, 255, 0), 2)
                    cv2.putText(
                        annotated_frame, det['label'], (gx1, gy1 - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA,
                    )
            
            frame_count += 1
            # ==============================================================================

            # 3. 전처리 및 안정화 로직 (LK Flow)
            frame_blur = cv2.GaussianBlur(frame, (5, 5), 0)
            current_gray_full = cv2.cvtColor(frame_blur, cv2.COLOR_BGR2GRAY)
            
            stabilized_gray = current_gray_full # 기본값
            
            if prev_frame_gray is not None:
                # --- 카메라 이동 감지 및 안정화 ---
                p0 = cv2.goodFeaturesToTrack(prev_frame_gray, mask=None, **feature_params)
                m = None
                
                if p0 is not None and len(p0) > 20:
                    p1, st, err = cv2.calcOpticalFlowPyrLK(prev_frame_gray, current_gray_full, p0, None, **lk_params)
                    if p1 is not None and st is not None:
                        good_new = p1[st==1]
                        good_old = p0[st==1]
                        if len(good_new) > 5:
                            m, _ = cv2.estimateAffine2D(good_old, good_new)

                if m is not None:
                    # 3-1. 이동 감지 (카메라 P/T/Z)
                    move_mag = np.sqrt(m[0, 2]**2 + m[1, 2]**2)
                    if move_mag > CAMERA_MOVE_THRESHOLD:
                        is_paused = True
                        pause_end_time = time.time() + PAUSE_DURATION
                        print(f"[{cctv_url}] 카메라 이동 ({move_mag:.1f}px). {PAUSE_DURATION}초 일시정지.")
                        
                        # 일시 정지 직후에는 현재 프레임을 마지막으로 보내고 루프 재시작
                        draw_text_with_outline(annotated_frame, f"Detected Move ({move_mag:.1f}px). Pausing...", (20, 50), 1, (0, 0, 255), 2)
                        ret, buffer = cv2.imencode('.webp', annotated_frame, [int(cv2.IMWRITE_WEBP_QUALITY), 80])
                        yield (b'--frame\r\n' b'Content-Type: image/webp\r\n\r\n' + buffer.tobytes() + b'\r\n')
                        continue

                    # 3-2. 프레임 안정화
                    stabilized_frame = cv2.warpAffine(frame_blur, m, (W, H))
                    stabilized_gray = cv2.cvtColor(stabilized_frame, cv2.COLOR_BGR2GRAY)
                # (m is None인 경우 stabilized_gray는 current_gray_full 유지)


                # =================== 기존 광학 흐름(Optical Flow) 로직 (방향별 점유율 계산) ===================
                roi_y_start = int(H * ROI_Y_RATIO)
                roi_h = H - roi_y_start

                if weight_map is None:
                    weights = np.linspace(PERSPECTIVE_WEIGHT_MAX, 1.0, roi_h).reshape(-1, 1)
                    weight_map = weights.astype(np.float32)

                roi_gray = stabilized_gray[roi_y_start:, :]
                roi_prev = prev_frame_gray[roi_y_start:, :]

                # 1. 배경 차분 마스크 획득 (움직이는 모든 물체)
                fg_mask = bg_subtractor.apply(roi_gray, learningRate=0.005)
                fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN,
                                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
                fg_mask_binary = (fg_mask > 0).astype(np.uint8) 

                # 2. 광학 흐름 계산 및 가중치 적용
                flow = cv2.calcOpticalFlowFarneback(
                    roi_prev, roi_gray, None,
                    0.5, 3, 15, 3, 5, 1.2, 0
                )
                flow_y = flow[..., 1]
                weighted_flow = flow_y * weight_map

                # 3. 방향 분리
                mask_down_bool = (weighted_flow > 0.3)
                mask_up_bool = (weighted_flow < -0.3)
                mask_down_uint8 = mask_down_bool.astype(np.uint8)
                mask_up_uint8 = mask_up_bool.astype(np.uint8)

                # 속도 계산
                speed_down = np.median(weighted_flow[mask_down_bool]) if np.sum(mask_down_bool) > 10 else 0.0
                speed_up = np.median(np.abs(weighted_flow[mask_up_bool])) if np.sum(mask_up_bool) > 10 else 0.0

                # 4. 방향별 점유율 계산
                total_pixels = fg_mask.size
                if total_pixels > 0:
                    occ_down_mask_combined = cv2.bitwise_and(fg_mask_binary, fg_mask_binary, mask=mask_down_uint8)
                    occupancy_rate_down = np.count_nonzero(occ_down_mask_combined) / total_pixels

                    occ_up_mask_combined = cv2.bitwise_and(fg_mask_binary, fg_mask_binary, mask=mask_up_uint8)
                    occupancy_rate_up = np.count_nonzero(occ_up_mask_combined) / total_pixels
                else:
                    occupancy_rate_down = 0.0
                    occupancy_rate_up = 0.0

                # 5. 데이터 누적
                history_down.append((speed_down, occupancy_rate_down))
                history_up.append((speed_up, occupancy_rate_up))

                if len(history_down) > 10:
                    # 6. 평균 및 상태 판단
                    avg_speed_down = np.mean([s for s, o in history_down])
                    avg_occ_down   = np.mean([o for s, o in history_down]) 

                    avg_speed_up   = np.mean([s for s, o in history_up])
                    avg_occ_up     = np.mean([o for s, o in history_up])   

                    status_down, color_down = get_status_text_and_color(avg_speed_down, avg_occ_down)
                    status_up, color_up     = get_status_text_and_color(avg_speed_up, avg_occ_up)

                    # 7. 시각화
                    cv2.line(annotated_frame, (0, roi_y_start), (W, roi_y_start), (0, 255, 255), 1)

                    draw_text_with_outline(annotated_frame, f"UP : {status_up}", (20, 50), 0.8, color_up, 2)
                    draw_text_with_outline(annotated_frame,
                                           f"W.Spd:{avg_speed_up:.1f} | OCC:{avg_occ_up*100:.1f}%", 
                                           (20, 80), 0.6, (220,220,220), 1)

                    draw_text_with_outline(annotated_frame, f"DOWN : {status_down}", (20, 120), 0.8, color_down, 2)
                    draw_text_with_outline(annotated_frame,
                                           f"W.Spd:{avg_speed_down:.1f} | OCC:{avg_occ_down*100:.1f}%", 
                                           (20, 150), 0.6, (220,220,220), 1)
                else:
                    draw_text_with_outline(annotated_frame, f"Collecting Data... ({len(history_down)}/{HISTORY_LENGTH})", (20, 50), 1, (255,255,255), 2)


            prev_frame_gray = stabilized_gray.copy()
            # ==========================================================================

            ret, buffer = cv2.imencode('.webp', annotated_frame, [int(cv2.IMWRITE_WEBP_QUALITY), 80])
            if not ret:
                continue

            yield (b'--frame\r\n'
                    b'Content-Type: image/webp\r\n\r\n' +
                    buffer.tobytes() + b'\r\n')

    finally:
        capture.release()

# ----------------------------------------------------------------------
# 5. 라우트 (변동 없음)
# ----------------------------------------------------------------------
@bp.route('/cctv', methods=['GET', 'POST'])
def index():
    initialize_cctv_data()
    target_name = request.form.get('cctv_name') if request.method == 'POST' else None

    if not target_name and FILTERED_NAMES:
        target_name = FILTERED_NAMES[0]

    target_url = CCTV_URL_DICT.get(target_name)

    return render_template(
        'traffic.html',
        cctv_names=FILTERED_NAMES,
        target_name=target_name,
        target_url=target_url
    )

@bp.route('/video_feed/<path:cctv_url>')
def video_feed(cctv_url):
    decoded = urllib.parse.unquote(cctv_url)
    return Response(
        generate_frames(decoded),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )