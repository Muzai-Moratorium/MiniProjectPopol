# mp/__init__.py 전체 코드
import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore
from flask_apscheduler import APScheduler
from mp.models import db, User, Role

from mp.views.auth import bp as auth_bp
from mp.views.index import bp as index
from mp.views.test import bp as test_bp
from mp.views.cctv import bp as traffic_bp
from mp.views.weather import bp as weather_bp
# 경로 주의: 프로젝트 구조에 따라 mp.views.safety_analysis.safety_bp 등으로 정확히 입력
from mp.views.dummy_cctv import bp as dummy_bp, start_fire_thread
from mp.views.traffic_predict import bp as traffic_predict_bp
from mp.views.shoulder_parking import bp as shoulder_bp
from mp.views.traffic_cone import bp as traffic_cone_bp
from mp.views.traffic_cone import bp as traffic_cone_bp, start_cone_thread
from mp.views.wrong_way import bp as wrong_way_bp
from mp.views.traffic_mgmt import bp as traffic_mgmt_bp, sync_traffic_to_db

from config import Config
from datetime import date

# 전역 변수로 스케줄러 객체 생성
scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    # 2. 스케줄러 설정 및 시작
    scheduler.init_app(app)
    scheduler.start()

    @app.context_processor
    def inject_kakao_key():
        return dict(kakao_app_key=os.environ.get('KAKAO_APP_KEY'))

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(app, user_datastore)

    # 블루프린트 등록
    app.register_blueprint(auth_bp)
    app.register_blueprint(index)
    app.register_blueprint(test_bp)
    app.register_blueprint(traffic_bp)
    app.register_blueprint(weather_bp, url_prefix='/api')
    app.register_blueprint(dummy_bp)
    app.register_blueprint(traffic_predict_bp)
    app.register_blueprint(shoulder_bp)
    app.register_blueprint(traffic_cone_bp)
    app.register_blueprint(wrong_way_bp)
    app.register_blueprint(traffic_mgmt_bp)

    # 3. 10분 간격 자동 작업 등록 (함수 내부에서 @scheduler.task 정의)
    @scheduler.task('interval', id='traffic_sync_job', minutes=10)
    def scheduled_task():
        with app.app_context():
            print("--- [Scheduler] 실시간 교통 데이터 수집 중 ---")
            sync_traffic_to_db()

    # 스레드 시작
    start_fire_thread()
    start_cone_thread()

    with app.app_context():
        db.create_all()
        sync_traffic_to_db()

    return app