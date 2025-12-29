from flask import Flask, Blueprint, request, jsonify, render_template
import pandas as pd
import numpy as np
from datetime import time, timedelta

# ----------------------------
# Flask 앱 & Blueprint 설정
# ----------------------------
app = Flask(__name__)

bp = Blueprint(
    'traffic_scenario',
    __name__,
    url_prefix='/traffic_scenario'
)


# ----------------------------
# 페이지 렌더링
# ----------------------------
@bp.route('/', endpoint='scenario_page')
def scenario_page():
    """기본 시나리오 페이지"""
    return render_template('traffic_scenario.html')


@bp.route('/testpage', endpoint='test_page')
def test_page():
    """테스트 페이지"""
    return render_template('test2.html', title="테스트페이지")


# ----------------------------
# 더미 예측 데이터 생성
# ----------------------------
def make_dummy_prediction(start, end):
    rng = pd.date_range(start, end, freq='H')
    return pd.DataFrame({
        'datetime': rng,
        'pred': np.random.randint(20, 140, len(rng))
    })


def congestion_level(v):
    if v < 30:
        return "원활"
    elif v < 60:
        return "보통"
    elif v < 90:
        return "혼잡"
    else:
        return "매우 혼잡"


# ----------------------------
# Helper: 시간대별 그룹 생성
# ----------------------------
def time_bins(df, start_hour, end_hour, step_minutes=30):
    """시간 구간별로 나누기, step_minutes 단위"""
    bins = []
    current = pd.Timestamp(df['datetime'].dt.date.min()) + pd.Timedelta(hours=start_hour)
    end_time = pd.Timestamp(df['datetime'].dt.date.min()) + pd.Timedelta(hours=end_hour)

    while current < end_time:
        next_time = current + pd.Timedelta(minutes=step_minutes)
        bins.append((current.time(), next_time.time()))
        current = next_time
    return bins


def group_extremes(df, bins, mode='min'):
    """각 시간대별 최소/최대값 추출"""
    results = []
    for start, end in bins:
        group = df[(df['datetime'].dt.time >= start) & (df['datetime'].dt.time < end)]
        if not group.empty:
            if mode == 'min':
                val = group['pred'].min()
            else:
                val = group['pred'].max()
            rows = group[group['pred'] == val]
            for _, row in rows.iterrows():
                results.append({
                    'time': row['datetime'].strftime('%H:%M'),
                    'traffic_value': float(row['pred']),
                    'congestion_level': congestion_level(row['pred'])
                })
    return results


# ----------------------------
# API: 출근 시간 여러 구간 최소값
# ----------------------------
@bp.route('/best-commute-times', methods=['POST'])
def best_commute_times():
    data = request.get_json()
    df = make_dummy_prediction(data['start_date'], data['end_date'])
    df['datetime'] = pd.to_datetime(df['datetime'])

    bins = time_bins(df, 7, 9, step_minutes=30)
    result = group_extremes(df, bins, mode='min')
    return jsonify(result)


# ----------------------------
# API: 퇴근 시간 여러 구간 최대값
# ----------------------------
@bp.route('/worst-offwork-times', methods=['POST'])
def worst_offwork_times():
    data = request.get_json()
    df = make_dummy_prediction(data['start_date'], data['end_date'])
    df['datetime'] = pd.to_datetime(df['datetime'])

    bins = time_bins(df, 17, 19, step_minutes=30)
    result = group_extremes(df, bins, mode='max')
    return jsonify(result)


# ----------------------------
# API: 전체 이상치 (시간대별)
# ----------------------------
@bp.route('/anomaly-times', methods=['POST'])
def anomaly_times():
    data = request.get_json()
    df = make_dummy_prediction(data['start_date'], data['end_date'])
    df['datetime'] = pd.to_datetime(df['datetime'])

    mean = df['pred'].mean()
    std = df['pred'].std()
    anomaly = df[df['pred'] > mean + 2 * std]

    bins = time_bins(anomaly, 0, 24, step_minutes=60)
    result = group_extremes(anomaly, bins, mode='max')
    return jsonify(result)


# ----------------------------
# Flask 앱에 Blueprint 등록
# ----------------------------
app.register_blueprint(bp)

# ----------------------------
# 앱 실행
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
