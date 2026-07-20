"""
Global integration tests — full pipeline from insight generation to simulation.
Tests: generate_insight format, export report, cache invalidation, no side effects.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from webapp.services.ai_service import (
    generate_insight, _build_template_insight, predict_trend_simulation,
    _LEGACY_ACTION_MAP, DIMENSION_TRANSFORM,
)
from webapp.app import app


# ============================================================
# 1. generate_insight returns structured recommendations
# ============================================================
def test_generate_insight_structured_recs():
    """Local template insight should return dict-format recommendations."""
    kpis = {'roi': 5, 'conversion_rate': 0.5, 'coupon_leverage': 0.01,
            'total_issued': 10000, 'total_sales': 500000, 'aov': 800,
            'member_contribution': 60}
    structure = [{'name': '停车券', 'pct': 85, 'count': 8500},
                 {'name': '体验券', 'pct': 15, 'count': 1500}]
    cohorts = [
        {'level': '菁英会员', 'age_group': '80后', 'redeem_rate': 2.0, 'atv': 800,
         'avg_coupons': 3, 'tag': 'GREEN', 'issued': 500, 'redeemed': 100, 'sales': 400000},
        {'level': '普通会员', 'age_group': '90后', 'redeem_rate': 0.3, 'atv': 150,
         'avg_coupons': 8, 'tag': 'RED', 'issued': 2000, 'redeemed': 30, 'sales': 30000},
    ]
    lag_data = [{'lag': 0, 'r': -0.3}, {'lag': 3, 'r': 0.5}]
    anomalies = {'anomaly_count': 0, 'anomalies': []}

    result = generate_insight(kpis, structure, cohorts, lag_data, anomalies)
    assert 'recommendations' in result
    assert isinstance(result['recommendations'], list)
    assert len(result['recommendations']) > 0
    # Each recommendation should be a dict with expected keys
    for rec in result['recommendations']:
        assert isinstance(rec, dict), f"Expected dict, got {type(rec)}: {rec}"
        assert 'text' in rec or 'action' in rec, f"Missing text/action: {rec}"
        assert 'effect' in rec, f"Missing effect: {rec}"
        assert rec['effect'] in DIMENSION_TRANSFORM, f"Unknown effect: {rec['effect']}"
        assert 'pct' in rec, f"Missing pct: {rec}"


# ============================================================
# 2. Export report handles dict recommendations
# ============================================================
def test_export_report_dict_recs():
    """api_export_report should format dict recommendations correctly."""
    with app.test_client() as client:
        resp = client.post('/api/export-report', json={
            'metrics': {'roi': 15, 'conversion_rate': 0.8, 'total_sales': 1000000,
                        'aov': 500, 'member_contribution': 55, 'coupon_leverage': 0.03,
                        'total_issued': 5000, 'total_redeemed': 200},
            'alerts': [{'severity': 'warning', 'message': '测试告警'}],
            'insight_text': '测试洞察',
            'recommendations': [
                {'text': '削减停车券', 'action': '削减停车券50%', 'effect': 'coupon_volume', 'pct': -50},
                {'text': '提升转化', 'action': '提升转化效率', 'effect': 'sales_efficiency', 'pct': 20},
            ],
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert '削减停车券' in data['content']
        assert '提升转化' in data['content']


# ============================================================
# 3. Export report handles legacy string recommendations
# ============================================================
def test_export_report_legacy_strings():
    """api_export_report should still work with legacy string recommendations."""
    with app.test_client() as client:
        resp = client.post('/api/export-report', json={
            'metrics': {'roi': 10, 'conversion_rate': 0.5, 'total_sales': 500000,
                        'aov': 400, 'member_contribution': 50, 'coupon_leverage': 0.02,
                        'total_issued': 3000, 'total_redeemed': 100},
            'alerts': [],
            'insight_text': 'legacy test',
            'recommendations': ['建议一', '建议二'],
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert '建议一' in data['content']


# ============================================================
# 4. Cache invalidation — different inputs produce different results
# ============================================================
def test_simulation_cache_different_inputs():
    """predict_trend_simulation should produce different results for different inputs."""
    trend1 = {'labels': ['W1'], 'coupon': [100], 'sales': [1000], 'correlation': 0}
    lag1 = [{'lag': 0, 'r': -0.3}]
    trend2 = {'labels': ['W1'], 'coupon': [500], 'sales': [5000], 'correlation': 0}
    lag2 = [{'lag': 0, 'r': 0.5}]

    r1 = predict_trend_simulation(trend1, lag1, ['cut_parking'])
    r2 = predict_trend_simulation(trend2, lag2, ['cut_parking'])
    assert r1['trend']['coupon'][0] != r2['trend']['coupon'][0]


# ============================================================
# 5. No side effects — original data unchanged after simulation
# ============================================================
def test_no_side_effects():
    """predict_trend_simulation should not mutate input data."""
    trend = {'labels': ['W1', 'W2'], 'coupon': [100, 200], 'sales': [1000, 2000], 'correlation': 0}
    lag = [{'lag': 0, 'r': -0.3, 'strength': 'weak'}, {'lag': 3, 'r': 0.5, 'strength': 'moderate'}]
    trend_copy = {'labels': list(trend['labels']), 'coupon': list(trend['coupon']),
                  'sales': list(trend['sales']), 'correlation': trend['correlation']}
    lag_copy = [dict(l) for l in lag]

    predict_trend_simulation(trend, lag, [{'effect': 'coupon_volume', 'pct': -50}])

    assert trend['coupon'] == trend_copy['coupon']
    assert trend['sales'] == trend_copy['sales']
    assert [l['r'] for l in lag] == [l['r'] for l in lag_copy]


# ============================================================
# 6. _build_template_insight edge cases
# ============================================================
def test_build_template_empty_cohorts():
    """Template insight should handle empty cohorts gracefully."""
    result = _build_template_insight(
        {'roi': 20, 'conversion_rate': 1.5, 'coupon_leverage': 0.1},
        [], [], []
    )
    assert 'recommendations' in result
    assert len(result['recommendations']) > 0
    # Default fallback recommendation should be dict format
    assert isinstance(result['recommendations'][0], dict)


if __name__ == '__main__':
    tests = [v for k, v in list(globals().items()) if k.startswith('test_')]
    passed = 0
    for test in tests:
        try:
            test()
            print(f'  PASS {test.__name__}')
            passed += 1
        except Exception as e:
            print(f'  FAIL {test.__name__}: {e}')
    print(f'\n{passed}/{len(tests)} tests passed')
