class Config:
    SECRET_KEY ="a1r2i3e4l5" 
    SECURITY_PASSWORD_SALT="w1h2i3t4e5"
    # MySQL 접속 설정
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://flask_user:1234@localhost:3306/flask_db?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


# Flask-Security 기본 설정
    SECURITY_REGISTERABLE = True        # 회원가입 ON
    SECURITY_SEND_REGISTER_EMAIL = False # 이메일 인증 비활성화
    SECURITY_PASSWORD_HASH = "bcrypt"
    SECURITY_LOGIN_URL = "/login"
    SECURITY_POST_LOGIN_VIEW = "/auth/redirect"
    SECURITY_POST_LOGOUT_VIEW = "/"