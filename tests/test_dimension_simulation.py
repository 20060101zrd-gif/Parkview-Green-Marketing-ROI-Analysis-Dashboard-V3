"""
Unit tests for symmetric dimension architecture — trend simulation transforms.
Tests: each dimension positive/negative, multi-dimension combinations,
determinism, data-following, backward compatibility, boundary conditions.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from webapp.services.ai_service import (
    DIMENSION_TRANSFORM, _LEGACY_ACTION_MAP,
    _scale_coupon, _scale_sales, _offset_lag,
    predict_trend_simulation,
)


def _make_trend(labels, coupon, sales):
    return {'labels': labels, 'coupon': coupon, 'sales': sales, 'correlation': 0}


def _make_lag(pairs):
    """pairs: list of (lag_day, r_value)"""
    return [{'lag': d, 'r': r, 'strength': 'moderate'} for d, r in pairs]


# ============================================================
# 1. coupon_volume — positive pct (enhance)
# ============================================================
def test_coupon_volume_positive():
    trend = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag = _make_lag([(0, -0.3), (3, 0.5)])
    result_trend, result_lag = _scale_coupon(trend, lag, 50)  # +50%
    assert result_trend['coupon'][0] == 150   # 100 * 1.5
    assert result_trend['coupon'][1] == 300   # 200 * 1.5
    assert result_trend['sales'][0] == 1000   # unchanged
    assert result_lag[0]['r'] == -0.3         # unchanged


# ============================================================
# 2. coupon_volume — negative pct (reduce)
# ============================================================
def test_coupon_volume_negative():
    trend = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag = _make_lag([(0, -0.3)])
    result_trend, _ = _scale_coupon(trend, lag, -60)  # -60%
    assert result_trend['coupon'][0] == 40    # 100 * 0.4
    assert result_trend['coupon'][1] == 80    # 200 * 0.4


# ============================================================
# 3. coupon_volume — zero floor (no negative coupons)
# ============================================================
def test_coupon_volume_zero_floor():
    trend = _make_trend(['W1'], [5], [500])
    lag = []
    result_trend, _ = _scale_coupon(trend, lag, -200)  # would be negative
    assert result_trend['coupon'][0] == 0


# ============================================================
# 4. sales_efficiency — positive pct
# ============================================================
def test_sales_efficiency_positive():
    trend = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag = _make_lag([(0, -0.3)])
    result_trend, _ = _scale_sales(trend, lag, 30)  # +30%
    assert result_trend['sales'][0] == 1300   # 1000 * 1.3
    assert result_trend['sales'][1] == 2600   # 2000 * 1.3
    assert result_trend['coupon'][0] == 100   # unchanged


# ============================================================
# 5. sales_efficiency — negative pct
# ============================================================
def test_sales_efficiency_negative():
    trend = _make_trend(['W1'], [100], [1000])
    lag = []
    result_trend, _ = _scale_sales(trend, lag, -20)  # -20%
    assert result_trend['sales'][0] == 800    # 1000 * 0.8


# ============================================================
# 6. sales_efficiency — positive floor (min 1)
# ============================================================
def test_sales_efficiency_min_one():
    trend = _make_trend(['W1'], [100], [10])
    lag = []
    result_trend, _ = _scale_sales(trend, lag, -200)  # would go negative
    assert result_trend['sales'][0] == 1


# ============================================================
# 7. lag_correlation — positive pct (enhance correlation)
# ============================================================
def test_lag_correlation_positive():
    trend = _make_trend(['W1'], [100], [1000])
    lag = _make_lag([(0, -0.3), (3, 0.5)])
    result_trend, result_lag = _offset_lag(trend, lag, 30)  # +0.30
    assert result_lag[0]['r'] == 0.0    # -0.3 + 0.3
    assert result_lag[1]['r'] == 0.8    # 0.5 + 0.3
    assert result_trend['coupon'][0] == 100  # unchanged


# ============================================================
# 8. lag_correlation — negative pct (weaken correlation)
# ============================================================
def test_lag_correlation_negative():
    trend = _make_trend(['W1'], [100], [1000])
    lag = _make_lag([(0, 0.6), (3, 0.8)])
    result_trend, result_lag = _offset_lag(trend, lag, -40)  # -0.40
    assert result_lag[0]['r'] == 0.2    # 0.6 - 0.4
    assert result_lag[1]['r'] == 0.4    # 0.8 - 0.4


# ============================================================
# 9. lag_correlation — clamp to [-1, 1]
# ============================================================
def test_lag_correlation_clamp():
    trend = _make_trend(['W1'], [100], [1000])
    lag = _make_lag([(0, 0.9), (3, -0.9)])
    _, result_lag = _offset_lag(trend, lag, 50)   # +0.50 -> would exceed 1
    assert result_lag[0]['r'] == 1.0
    _, result_lag2 = _offset_lag(trend, _make_lag([(0, 0.9)]), -200)  # would go below -1
    assert result_lag2[0]['r'] == -1.0


# ============================================================
# 10. Multi-dimension combination
# ============================================================
def test_multi_dimension_combination():
    trend = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag = _make_lag([(0, -0.3), (3, 0.5)])
    # Apply coupon_volume (-50%) then sales_efficiency (+20%) then lag_correlation (+15%)
    trend, lag = _scale_coupon(trend, lag, -50)
    trend, lag = _scale_sales(trend, lag, 20)
    trend, lag = _offset_lag(trend, lag, 15)
    assert trend['coupon'][0] == 50     # 100 * 0.5
    assert trend['sales'][0] == 1200    # 1000 * 1.2 (coupon transform doesn't affect sales)
    assert lag[0]['r'] == -0.15         # -0.3 + 0.15
    assert lag[1]['r'] == 0.65          # 0.5 + 0.15


# ============================================================
# 11. Determinism — same input, same output
# ============================================================
def test_determinism():
    trend1 = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag1 = _make_lag([(0, -0.3), (3, 0.5)])
    trend2 = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag2 = _make_lag([(0, -0.3), (3, 0.5)])
    t1, l1 = _scale_coupon(trend1, lag1, 30)
    t2, l2 = _scale_coupon(trend2, lag2, 30)
    assert t1['coupon'] == t2['coupon']
    assert t1['sales'] == t2['sales']
    assert [x['r'] for x in l1] == [x['r'] for x in l2]


# ============================================================
# 12. Data-following — different data, proportional results
# ============================================================
def test_data_following():
    trend_a = _make_trend(['W1'], [100], [1000])
    trend_b = _make_trend(['W1'], [500], [5000])
    lag = []
    ta, _ = _scale_sales(trend_a, lag, 50)
    tb, _ = _scale_sales(trend_b, lag, 50)
    assert ta['sales'][0] == 1500   # 1000 * 1.5
    assert tb['sales'][0] == 7500   # 5000 * 1.5


# ============================================================
# 13. Backward compatibility — legacy string actions
# ============================================================
def test_legacy_action_map():
    assert _LEGACY_ACTION_MAP['cut_parking'] == ('coupon_volume', -60)
    assert _LEGACY_ACTION_MAP['boost_green'] == ('sales_efficiency', 15)
    assert _LEGACY_ACTION_MAP['melt_red'] == ('coupon_volume', -80)
    assert _LEGACY_ACTION_MAP['optimize_lag'] == ('lag_correlation', 15)


def test_predict_trend_with_legacy_string():
    """predict_trend_simulation should handle legacy string actions."""
    trend = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag = _make_lag([(0, -0.3), (3, 0.5)])
    result = predict_trend_simulation(trend, lag, ['cut_parking'])
    assert 'trend' in result
    assert 'lag' in result
    assert result['predicted_by'] == '本地规则引擎'
    # coupon reduced by 60%
    assert result['trend']['coupon'][0] == 40


def test_predict_trend_with_new_dict():
    """predict_trend_simulation should handle new dict-format actions."""
    trend = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag = _make_lag([(0, -0.3), (3, 0.5)])
    result = predict_trend_simulation(trend, lag, [
        {'effect': 'coupon_volume', 'pct': -50},
        {'effect': 'sales_efficiency', 'pct': 20},
    ])
    assert result['predicted_by'] == '本地规则引擎'
    assert result['trend']['coupon'][0] == 50     # 100 * 0.5
    assert result['trend']['sales'][0] == 1200    # 1000 * 1.2


# ============================================================
# 14. DIMENSION_TRANSFORM completeness
# ============================================================
def test_dimension_transform_keys():
    assert 'coupon_volume' in DIMENSION_TRANSFORM
    assert 'sales_efficiency' in DIMENSION_TRANSFORM
    assert 'lag_correlation' in DIMENSION_TRANSFORM
    assert callable(DIMENSION_TRANSFORM['coupon_volume'])
    assert callable(DIMENSION_TRANSFORM['sales_efficiency'])
    assert callable(DIMENSION_TRANSFORM['lag_correlation'])


# ============================================================
# 15. Edge case — empty trend/lag
# ============================================================
def test_empty_data():
    empty_trend = {'labels': [], 'coupon': [], 'sales': [], 'correlation': 0}
    empty_lag = []
    t, l = _scale_coupon(empty_trend, empty_lag, 50)
    assert t['coupon'] == []
    assert t['sales'] == []
    assert l == []
    t2, l2 = _offset_lag(empty_trend, empty_lag, 30)
    assert l2 == []


if __name__ == '__main__':
    # Run all tests
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
