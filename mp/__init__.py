# mp/__init__.py 전체 코드
import os
from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore
from mp.models import db, User, Role

from mp.views.auth import bp as auth_bp
from mp.views.index import bp as index
from mp.views.test import bp as test_bp
from mp.views.cctv import bp as traffic_bp
from mp.views.weather import bp as weather_bp
# 경로 주의: 프로젝트 구조에 따라 mp.views.safety_analysis.safety_bp 등으로 정확히 입력
from mp.views.dummy_cctv import bp as dummy_bp, start_fire_thread

from config import Config
from datetime import date

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(app, user_datastore)

    # 블루프린트 등록
    app.register_blueprint(auth_bp)
    app.register_blueprint(index)
    app.register_blueprint(test_bp)
    app.register_blueprint(traffic_bp)
    app.register_blueprint(weather_bp, url_prefix='/api')
    app.register_blueprint(dummy_bp)

    # ------------------------------------------------------------------
    # ⭐ 프린트가 안 찍힌다면 이 부분을 아래처럼 수정해서 강제 실행 확인
    # ------------------------------------------------------------------
    
    # 만약 안 뜬다면 일단 조건문 없이 호출해 보세요
    # if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    start_fire_thread()
    # ------------------------------------------------------------------

    with app.app_context():
        db.create_all()
        # 관리자 생성 로직 생략...

    return app