class Config:
    SECRET_KEY = "a1r2i3e4l5"
    SECURITY_PASSWORD_SALT = "w1h2i3t4e5"
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:1234@localhost:3306/flask_db?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False



    # Flask-Security 설정
    SECURITY_REGISTERABLE = False
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_PASSWORD_HASH = "bcrypt"
    SECURITY_LOGIN_URL = "/login"
    SECURITY_POST_LOGIN_VIEW = "None"
    SECURITY_POST_LOGOUT_VIEW = "/"
    SECURITY_RECOVERABLE = True
