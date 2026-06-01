from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
import uuid
import pandas as pd
import numpy as np
import warnings
import random
import math

warnings.filterwarnings("ignore")

db = SQLAlchemy()

# User와 Role 관계 = Many-to-Many
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    name = db.Column(db.String(20), nullable=False)
    birth = db.Column(db.Date, nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    roles = db.relationship('Role', secondary=user_roles, backref='users')


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cctv_name = db.Column(db.String(255), unique=True, nullable=False)
    lng = db.Column(db.String(50), nullable=False)  # 충분한 길이를 확보합니다.
    lat = db.Column(db.String(50), nullable=False)


class TrafficStatus(db.Model):
    __tablename__ = 'traffic_status'
    id = db.Column(db.Integer, primary_key=True)
    # Location 테이블의 id를 참조하는 Foreign Key (1:N 관계의 N쪽)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    # 분석 시점 (어떤 시점의 데이터인지 기록)
    timestamp = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    # 상행선 (서울 방향) 상태: 원활, 서행, 정체, N/A
    status_upstream = db.Column(db.String(50), nullable=False)
    # 하행선 (부산 방향) 상태: 원활, 서행, 정체, N/A
    status_downstream = db.Column(db.String(50), nullable=False)

    location = db.relationship(
        'Location',
        backref=db.backref('statuses', lazy='dynamic', order_by=timestamp.desc())
    )


# ============================================================
# 교통량 예측 모델 (독립된 클래스)
# ============================================================
class TrafficPredictor:
    """교통량 예측 모델"""

    def __init__(self, config):
        self.config = config
        self.model = None
        self.features = None
        self.section = None
        self.history = None

    def load_data(self, df, section):
        """특정 구간 데이터 로드"""
        self.section = section

        df['ds'] = pd.to_datetime(df['일시'])
        df['y'] = df['교통량']

        df_sec = (
            df[df['구간'] == section]
            .sort_values('ds')
            .reset_index(drop=True)
        )

        return df_sec

    def engineer_features(self, df_sec):
        """Feature Engineering"""
        df_sec = df_sec.copy()

        df_sec['요일'] = df_sec['ds'].dt.dayofweek
        df_sec['시간'] = df_sec['ds'].dt.hour
        df_sec['일'] = df_sec['ds'].dt.day
        df_sec['월'] = df_sec['ds'].dt.month
        df_sec['주'] = df_sec['ds'].dt.isocalendar().week.astype(int)

        for l in self.config.LAG_LIST:
            df_sec[f'lag_{l}'] = df_sec['y'].shift(l)

        df_sec['roll_24'] = df_sec['y'].rolling(24).mean()
        df_sec['roll_168'] = df_sec['y'].rolling(168).mean()

        self.features = (
                [f'lag_{l}' for l in self.config.LAG_LIST] +
                ['roll_24', 'roll_168', '요일', '시간', '일', '월', '주']
        )

        df_sec = df_sec.dropna().reset_index(drop=True)
        return df_sec

    def train(self, df_sec):
        """모델 학습 (더미화)"""
        self.history = df_sec.set_index('ds')['y'].copy()
        
        # 가짜 평가지표 반환
        metrics = {
            'mae': round(random.uniform(5.0, 15.0), 2),
            'mape': round(random.uniform(3.0, 8.0), 2),
            'r2': round(random.uniform(0.80, 0.95), 4),
            'train_size': len(df_sec) - 200,
            'valid_size': 200
        }
        return metrics

    def predict_future(self, start_date, end_date):
        """미래 예측 (더미화)"""
        future_dates = pd.date_range(start=start_date, end=end_date, freq='H')
        preds = []

        # 과거 데이터의 마지막 평균값을 기준으로 기준점 탐색
        base_value = float(self.history.iloc[-24:].mean()) if self.history is not None and len(self.history) >= 24 else 100.0

        for t in future_dates:
            # 시간대(hour) 및 주말 여부에 따른 간단한 예측값 모델링 (사인 함수 활용)
            hour_factor = math.sin((t.hour - 6) / 24.0 * 2 * math.pi)  # 출퇴근 시간대 반영하는 곡선
            day_factor = 0.7 if t.dayofweek >= 5 else 1.0  # 주말은 교통량 감소
            
            noise = random.uniform(-10, 10)
            y_hat = base_value * day_factor * (1.0 + 0.3 * hour_factor) + noise
            y_hat = max(0, float(y_hat))

            preds.append(y_hat)

        return pd.DataFrame({
            'ds': future_dates,
            'pred': preds
        })