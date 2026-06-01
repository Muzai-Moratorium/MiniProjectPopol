# mp/views/traffic_cone.py
import os, cv2, time, threading, random
from flask import Blueprint, render_template, Response, jsonify

bp = Blueprint("traffic_cone", __name__, url_prefix="/traffic_cone")

DUMMY_DIR = os.path.join(os.getcwd(), "mp", "static", "videos")
CONE_VIDEO = "cone_test3.mp4"
cone_model = None

# 상태 관리 변수
cone_config = {
    "is_running": False,
    "cone_detected": False,
    "active_video": ""
}

def run_cone_detection():
    global cone_config
    print("[CONE] 스레드 시작됨") 
    
    while True:
        if not cone_config["is_running"]:
            cone_config["cone_detected"] = False
            cone_config["active_video"] = ""
            time.sleep(1)
            continue

        print("[CONE] 감지 시작...")
        
        video_path = os.path.join(DUMMY_DIR, CONE_VIDEO)
        if not os.path.exists(video_path):
            print(f"[CONE] ⚠️ {CONE_VIDEO} 파일 없음!")
            time.sleep(2)
            continue

        print(f"[CONE] 선택된 비디오: {CONE_VIDEO}") 
        
        cap = cv2.VideoCapture(video_path)
        
        while cap.isOpened() and cone_config["is_running"]:
            success, frame = cap.read()
            if not success:
                # 영상 끝나면 break (종료)
                print(f"[CONE] {CONE_VIDEO} 읽기 실패 또는 종료") 
                break

            # YOLO 분석 생략 (더미 감지: 15% 확률로 임의의 교통콘 감지 플래그 설정)
            detected = random.random() < 0.15
            
            cone_config["cone_detected"] = detected
            cone_config["active_video"] = CONE_VIDEO if detected else ""
            
            time.sleep(0.5)
        
        cap.release()
        print(f"[CONE] {CONE_VIDEO} 종료")
        # while True 루프로 돌아가서 다시 시작

# 서버 시작 시 스레드 자동 실행
def start_cone_thread():
    thread = threading.Thread(target=run_cone_detection, daemon=True)
    thread.start()
    print("[CONE] 백그라운드 스레드 등록 완료") 

# --- API 엔드포인트 ---

@bp.route('/toggle_coneload', methods=['POST'])
def toggle_coneload():
    """ConeLoad 버튼 클릭 시 호출"""
    cone_config["is_running"] = not cone_config["is_running"]
    status = "ON" if cone_config["is_running"] else "OFF"
    print(f"[CONE] 버튼 토글: {status}") 
    return jsonify({"status": status})

@bp.route('/check_cone')
def check_status():
    """프론트엔드에서 주기적으로 감지 여부 확인"""
    return jsonify(cone_config)

@bp.route('/video_feed/<filename>')
def video_feed(filename):
    video_path = os.path.join(DUMMY_DIR, filename)
    print(f"[CONE] 스트림 요청: {filename}") 
    
    def generate():
        cap = cv2.VideoCapture(video_path)
        while cap.isOpened():
            if not cone_config["is_running"]:
                break
                
            ret, frame = cap.read()
            if not ret:
                break

            # YOLO 분석 없이 영상을 그대로 인코딩해서 보냄
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.03)
                
        cap.release()
        print(f"[CONE] 스트림 종료: {filename}") 
        
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')