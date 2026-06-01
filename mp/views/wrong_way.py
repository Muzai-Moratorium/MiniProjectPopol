from flask import Blueprint, render_template, Response, request, jsonify
import cv2
import numpy as np
import time
import os
import threading
import random

# Blueprint 객체 생성
bp = Blueprint(
    "wrong_way",
    __name__,
    url_prefix="/wrong_way",
    template_folder="templates",
    static_folder="static"
)

# ------------------------------------------------------------
# 1. 설정 및 초기화
# ------------------------------------------------------------
VIDEO_PATH = "mp/static/videos/wrongway.mp4" 
MODEL_PATH = "yolo11n.pt"
VEHICLE_CLASSES = [2, 3, 5, 7]

# 글로벌 상태 관리
IS_RUNNING = False
IS_DETECTED = False
latest_frame = None
background_thread = None

# 학습 관련 변수
is_trained = False
init_counter = 0
INIT_FRAMES = 45 
lane_direction_map = {}
violation_history = {} # 오탐지 방지용 ID별 위반 카운트

model = None

# ------------------------------------------------------------
# 2. 백그라운드 분석 로직
# ------------------------------------------------------------
def process_wrong_way_background(video_source):
    global IS_RUNNING, IS_DETECTED, latest_frame, is_trained, init_counter, lane_direction_map, violation_history
    
    cap = cv2.VideoCapture(video_source)
    is_trained = True
    init_counter = INIT_FRAMES
    
    print(f"[INFO] 역주행 감지 스레드 시작: {video_source}")

    try:
        while IS_RUNNING and cap.isOpened():
            success, frame = cap.read()
            if not success:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # 무한 반복
                continue
            
            # 가짜 역주행 토글 이벤트 (가끔 활성화)
            if random.random() < 0.02:
                IS_DETECTED = not IS_DETECTED
            
            annotated_frame = frame.copy()
            if IS_DETECTED:
                # 역주행 가짜 UI 표시
                cv2.rectangle(annotated_frame, (100, 100), (300, 300), (0, 0, 255), 3)
                cv2.putText(annotated_frame, "WRONG WAY! ID:DUMMY", (100, 90), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.rectangle(annotated_frame, (100, 100), (300, 300), (0, 255, 0), 1)

            latest_frame = annotated_frame
            time.sleep(0.03) # 프레임 지연

    finally:
        cap.release()
        IS_RUNNING = False
        print("[INFO] 역주행 감지 스레드 종료")

# ------------------------------------------------------------
# 3. 라우트 정의
# ------------------------------------------------------------
def generate_frames():
    global latest_frame
    while IS_RUNNING:
        if latest_frame is not None:
            ret, buffer = cv2.imencode('.jpg', latest_frame)
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + 
                       buffer.tobytes() + b'\r\n')
        time.sleep(0.03)

@bp.route('/')
def index():
    return render_template('wrong_way.html')

@bp.route('/toggle_wrong_way', methods=['POST'])
def toggle_wrong_way():
    global IS_RUNNING, background_thread
    IS_RUNNING = not IS_RUNNING
    
    if IS_RUNNING:
        if background_thread is None or not background_thread.is_alive():
            background_thread = threading.Thread(
                target=process_wrong_way_background, 
                args=(VIDEO_PATH,),
                daemon=True
            )
            background_thread.start()
    
    return jsonify({'status': 'ON' if IS_RUNNING else 'OFF'})

@bp.route('/check_status')
def check_status():
    return jsonify({
        'is_running': IS_RUNNING,
        'is_detected': IS_DETECTED,
        'is_trained': is_trained
    })

@bp.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')