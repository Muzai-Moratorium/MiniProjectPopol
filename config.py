import os

class Config:
    SECRET_KEY ="a1r2i3e4l5" 
    SECURITY_PASSWORD_SALT="w1h2i3t4e5"
    # 데이터베이스 접속 설정 (.env에 DATABASE_URL이 없으면 기본적으로 SQLite 사용)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///flask_db.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


# Flask-Security 기본 설정
    SECURITY_REGISTERABLE = False       # 회원가입 off 커스텀 회원가입 이용
    SECURITY_SEND_REGISTER_EMAIL = False # 이메일 인증 비활성화
    SECURITY_PASSWORD_HASH = "bcrypt"
    SECURITY_LOGIN_URL = "/login"
    SECURITY_POST_LOGIN_VIEW = "/auth/redirect"
    SECURITY_POST_LOGOUT_VIEW = "/"
    SECURITY_RECOVERABLE = True


    DATA_PATH = 'data/traffic_data.csv'

    XGBOOST_PARAMS = {
        'n_estimators': 800,
        'learning_rate': 0.03,
        'max_depth': 8,
        'subsample': 0.9,
        'colsample_bytree': 0.9,
        'random_state': 42,
        'tree_method': 'hist'
    }
    LAG_LIST = [1, 24, 48, 72, 168]
    TRAIN_END = "2025-09-30 23:00:00"
    VALID_END = "2025-11-30 23:00:00"