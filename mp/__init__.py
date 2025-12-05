from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore
from mp.models import db, User, Role
from mp.views.auth import bp as auth_bp
from mp.views.index import bp as index
from mp.views.test import bp as test_bp
from config import Config
from datetime import date

def create_app():
    app = Flask(__name__)
    
    from .views import auth
    app.config.from_object(Config)

    db.init_app(app)

    # Flask-Security 설정
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(app, user_datastore)
    
    # 블루프린트 등록
    app.register_blueprint(auth_bp)
    app.register_blueprint(index)
    app.register_blueprint(test_bp)

    with app.app_context():
        db.create_all()

        # 관리자 role 기본 생성
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = user_datastore.create_role(name='admin')
            db.session.commit()

        # 관리자 계정 기본 생성
        admin_email = "admin@admin.com"
        admin_name = "주인장"
        if not User.query.filter_by(email=admin_email).first():
            user_datastore.create_user(
                name = admin_name,
                email=admin_email,
                password="1234",  # SECURITY_PASSWORD_HASH에 맞게 암호화
                birth=date(1990, 1, 1),   # 🔥 여기에 날짜 넣기
                mobile="01000000000",     # 🔥 mobile도 NOT NULL이라 필요
                roles=[admin_role]
            )
            db.session.commit()

    return app

