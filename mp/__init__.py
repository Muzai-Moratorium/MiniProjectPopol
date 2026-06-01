# mp/__init__.py 전체 코드
import os

from dotenv import load_dotenv

load_dotenv()
from datetime import date

from flask import Flask
from flask_apscheduler import APScheduler
from flask_security import Security, SQLAlchemyUserDatastore

from config import Config
from mp.models import Role, User, db
from mp.views.auth import bp as auth_bp
from mp.views.cctv import bp as traffic_bp

# 경로 주의: 프로젝트 구조에 따라 mp.views.safety_analysis.safety_bp 등으로 정확히 입력
from mp.views.dummy_cctv import bp as dummy_bp
from mp.views.index import bp as index
from mp.views.massage import bp as massage_bp
from mp.views.shoulder_parking import bp as shoulder_bp
from mp.views.test import bp as test_bp
from mp.views.traffic_cone import bp as traffic_cone_bp
from mp.views.traffic_mgmt import bp as traffic_mgmt_bp
from mp.views.traffic_mgmt import sync_traffic_to_db
from mp.views.traffic_predict import bp as traffic_predict_bp
from mp.views.traffic_scenario import bp as traffic_scenario_bp
from mp.views.weather import bp as weather_bp
from mp.views.wrong_way import bp as wrong_way_bp


def create_app():
    import logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # 폴링 로그 spam 방지
    
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    @app.context_processor
    def inject_kakao_key():
        return dict(kakao_app_key=os.environ.get("KAKAO_APP_KEY"))

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(app, user_datastore)

    # 블루프린트 등록
    app.register_blueprint(auth_bp)
    app.register_blueprint(index)
    app.register_blueprint(test_bp)
    app.register_blueprint(traffic_bp)
    app.register_blueprint(weather_bp, url_prefix="/api")
    app.register_blueprint(dummy_bp)
    app.register_blueprint(traffic_predict_bp)
    app.register_blueprint(shoulder_bp)
    app.register_blueprint(traffic_cone_bp)
    app.register_blueprint(wrong_way_bp)  # ⭐ 역주행 감지 블루프린트 등록
    app.register_blueprint(traffic_mgmt_bp)  # 교통관리 블루프린트 등록
    app.register_blueprint(traffic_scenario_bp)
    app.register_blueprint(massage_bp)
    # ------------------------------------------------------------------
    # ⭐ 프린트가 안 찍힌다면 이 부분을 아래처럼 수정해서 강제 실행 확인
    # ------------------------------------------------------------------

    # 만약 안 뜬다면 일단 조건문 없이 호출해 보세요
    # if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    # start_fire_thread()
    # start_cone_thread()      # 교통콘 감지 스레드
    # ------------------------------------------------------------------

    with app.app_context():
        db.create_all()

        # 관리자 생성 로직
        admin_role = user_datastore.find_role("admin")
        if not admin_role:
            admin_role = user_datastore.create_role(
                name="admin", description="Administrator"
            )

        admin_user = user_datastore.find_user(email="admin@test.com")
        if admin_user:
            user_datastore.delete_user(admin_user)
            db.session.commit()
            admin_user = None
            
        if not admin_user:
            from datetime import date
            user_datastore.create_user(
                email="admin@test.com",
                password="admin1234",  # Flask-Security가 내부적으로 해싱하므로 평문 전달
                name="관리자",
                birth=date(1990, 1, 1),
                mobile="010-1234-5678",
                roles=[admin_role]
            )
        db.session.commit()

        # ⭐ 서버 시작 시 교통 데이터 동기화 (Location 테이블에 데이터 적재)
        try:
            sync_traffic_to_db()
            print("[Traffic] 초기 데이터 동기화 완료!")
        except Exception as e:
            print(f"[Traffic Warning] 초기 동기화 실패: {e}")

    return app
