from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore
from mp.models import db, User, Role

from mp.views.auth import bp as auth_bp
from mp.views.index import bp as index
from mp.views.test import bp as test_bp
from mp.views.cctv import bp as traffic_bp
from config import Config
from datetime import date




# ===========================
# 🔥 Flask Application Factory
# ===========================
def create_app():
    app = Flask(__name__)

    # 설정 불러오기
    app.config.from_object(Config)

    # DB 초기화
    db.init_app(app)

    # Flask-Security 초기화
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(app, user_datastore)

    # Blueprint 등록
    app.register_blueprint(auth_bp)
    app.register_blueprint(index)
    app.register_blueprint(test_bp)
    app.register_blueprint(traffic_bp)

    # DB 생성 및 기본 데이터 등록
    with app.app_context():
        db.create_all()

        # 관리자 role 생성
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = user_datastore.create_role(name='admin')
            db.session.commit()

        # 관리자 계정 생성
        admin_email = "admin@admin.com"
        admin_name = "주인장"

        if not User.query.filter_by(email=admin_email).first():
            user_datastore.create_user(
                name=admin_name,
                email=admin_email,
                password="1234",
                birth=date(1990, 1, 1),
                mobile="01000000000",
                roles=[admin_role]
            )
            db.session.commit()

    return app
