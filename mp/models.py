from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
import uuid

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
    name = db.Column(db.String(20),nullable=False)
    birth = db.Column(db.Date, nullable = False)
    mobile = db.Column(db.String(20),unique=True,nullable=False)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    roles = db.relationship('Role', secondary=user_roles, backref='users')

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cctv_name = db.Column(db.String(255), unique=True, nullable=False)
    lng = db.Column(db.String(50), nullable=False) # 충분한 길이를 확보합니다.
    lat = db.Column(db.String(50), nullable=False)
    
class TrafficStatus(db.Model):
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