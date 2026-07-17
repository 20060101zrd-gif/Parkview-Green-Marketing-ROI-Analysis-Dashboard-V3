"""
ML Service — IsolationForest anomaly detection + KMeans clustering.
Pure local computation; no external API needed.
"""
import numpy as np
import pandas as pd


def detect_anomalies(df_c, df_s):
    """IsolationForest anomaly detection on monthly sales trend."""
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return {'anomalies': [], 'anomaly_count': 0}

    c = df_c.copy()
    c['month'] = c['create_time'].dt.to_period('M').dt.to_timestamp()
    trend = c.groupby('month').agg(
        issued=('coupon_record_id', 'count'),
        redeemed=('status_code', lambda x: (x == 1).sum()),
    ).reset_index()

    s = df_s.copy()
    s['month'] = s['销售时间'].dt.to_period('M').dt.to_timestamp()
    st = s.groupby('month')['销售额'].sum().reset_index(name='sales')

    merged = pd.merge(trend, st, on='month', how='outer').fillna(0)
    if len(merged) < 3:
        return {'anomalies': [], 'anomaly_count': 0}

    X = merged[['sales']].values
    model = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
    flags = model.fit_predict(X)
    scores = model.score_samples(X)

    mean_val = merged['sales'].mean()
    std_val = merged['sales'].std()
    anomalies = []
    for i, flag in enumerate(flags):
        if flag == -1:
            deviation = (merged.iloc[i]['sales'] - mean_val) / std_val if std_val > 0 else 0
            anomalies.append({
                'time': merged.iloc[i]['month'].strftime('%Y-%m'),
                'value': round(float(merged.iloc[i]['sales']), 2),
                'deviation_sigma': round(deviation, 2),
                'direction': 'high' if deviation > 0 else 'low',
                'score': round(float(scores[i]), 4),
            })

    return {'anomalies': anomalies, 'anomaly_count': len(anomalies)}


def compute_kmeans(cohort_data):
    """KMeans clustering of cohort groups."""
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        return {'clusters': [], 'profiles': {}}

    if len(cohort_data) < 4:
        return {'clusters': [], 'profiles': {}}

    df = pd.DataFrame(cohort_data)
    features = ['avg_coupons', 'redeem_rate', 'atv']
    available = [f for f in features if f in df.columns]
    if len(available) < 2:
        return {'clusters': [], 'profiles': {}}

    X = df[available].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_clusters = min(4, max(2, len(df) // 2))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['cluster'] = kmeans.fit_predict(X_scaled)

    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
    profiles = {}
    for cid in sorted(df['cluster'].unique()):
        subset = df[df['cluster'] == cid]
        profiles[int(cid)] = {
            'size': len(subset),
            'atv_mean': round(float(subset['atv'].mean()), 2),
            'redeem_rate_mean': round(float(subset['redeem_rate'].mean()), 2),
            'avg_coupons_mean': round(float(subset['avg_coupons'].mean()), 2),
            'color': colors[cid % len(colors)],
            'members': subset[['name', 'atv', 'redeem_rate', 'tag']].to_dict('records'),
        }

    return {
        'clusters': df[['name', 'atv', 'redeem_rate', 'avg_coupons', 'cluster', 'tag']].to_dict('records'),
        'profiles': profiles,
    }
