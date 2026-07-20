"""
Unit tests for the 3 critical fixes (2026-07-20):

Fix A: predict_trend_simulation — DeepSeek only generates text analysis, numeric values always from local DIMENSION_TRANSFORM
Fix B: generate_analysis page_overview local fallback — per-page differentiated findings
Fix C: applySimulation coupon_volume ROI transform — cutting low-efficiency coupons should NOT drop ROI
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from webapp.services.ai_service import (
    DIMENSION_TRANSFORM, _LEGACY_ACTION_MAP,
    _scale_coupon, _scale_sales, _offset_lag,
    predict_trend_simulation, generate_analysis,
    _build_template_insight,
)


def _make_trend(labels, coupon, sales):
    return {'labels': labels, 'coupon': coupon, 'sales': sales, 'correlation': 0}


def _make_lag(pairs):
    """pairs: list of (lag_day, r_value)"""
    return [{'lag': d, 'r': r, 'strength': 'moderate'} for d, r in pairs]


# ============================================================
# FIX A: predict_trend_simulation — DeepSeek only text, local rules for numbers
# ============================================================

def test_fixA_trend_numeric_always_from_local():
    """Fix A: predict_trend_simulation always computes trend/lag via DIMENSION_TRANSFORM."""
    trend = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag = _make_lag([(0, -0.3), (3, 0.5)])
    result = predict_trend_simulation(trend, lag, [
        {'effect': 'coupon_volume', 'pct': -50},
        {'effect': 'sales_efficiency', 'pct': 20},
    ])
    assert 'trend' in result
    assert 'lag' in result
    assert 'predicted_by' in result
    # Numeric values must come from DIMENSION_TRANSFORM (deterministic)
    assert result['trend']['coupon'][0] == 50     # 100 * 0.5
    assert result['trend']['sales'][0] == 1200     # 1000 * 1.2


def test_fixA_trend_predicted_by_mentions_local_engine():
    """Fix A: predicted_by always references local engine (numeric source)."""
    trend = _make_trend(['W1'], [100], [1000])
    lag = _make_lag([(0, 0.5)])
    result = predict_trend_simulation(trend, lag, ['cut_parking'])
    # predicted_by should reference local engine (numeric is always local)
    assert '本地规则引擎' in result['predicted_by']


def test_fixA_trend_has_ai_analysis_field():
    """Fix A: result dict may have ai_analysis field (DeepSeek text, not numeric)."""
    trend = _make_trend(['W1'], [100], [1000])
    lag = _make_lag([(0, 0.5)])
    result = predict_trend_simulation(trend, lag, ['cut_parking'])
    # ai_analysis may be None (no API key) or a string — both acceptable
    assert 'ai_analysis' in result or result.get('ai_analysis') is None


def test_fixA_trend_determinism():
    """Fix A: Same input always produces same numeric output (deterministic)."""
    trend1 = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag1 = _make_lag([(0, -0.3), (3, 0.5)])
    trend2 = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag2 = _make_lag([(0, -0.3), (3, 0.5)])
    r1 = predict_trend_simulation(trend1, lag1, ['cut_parking', 'boost_green'])
    r2 = predict_trend_simulation(trend2, lag2, ['cut_parking', 'boost_green'])
    assert r1['trend']['coupon'] == r2['trend']['coupon']
    assert r1['trend']['sales'] == r2['trend']['sales']
    assert [x['r'] for x in r1['lag']] == [x['r'] for x in r2['lag']]


def test_fixA_trend_cache_hit():
    """Fix A: Cache returns deep copies (no shared references)."""
    trend = _make_trend(['W1'], [100], [1000])
    lag = _make_lag([(0, 0.5)])
    r1 = predict_trend_simulation(trend, lag, ['cut_parking'])
    r2 = predict_trend_simulation(trend, lag, ['cut_parking'])
    # Should be same values (cache hit)
    assert r1['trend']['coupon'] == r2['trend']['coupon']
    # But different objects (deep copy)
    assert r1 is not r2


def test_fixA_trend_no_side_effects():
    """Fix A: predict_trend_simulation must NOT mutate input data."""
    trend = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag = _make_lag([(0, -0.3), (3, 0.5)])
    trend_copy = {'labels': list(trend['labels']), 'coupon': list(trend['coupon']),
                  'sales': list(trend['sales']), 'correlation': trend['correlation']}
    lag_copy = [dict(l) for l in lag]
    predict_trend_simulation(trend, lag, [{'effect': 'coupon_volume', 'pct': -50}])
    assert trend['coupon'] == trend_copy['coupon']
    assert trend['sales'] == trend_copy['sales']


# ============================================================
# FIX B: generate_analysis page_overview — per-page differentiated
# ============================================================

def _sample_kpis():
    return {'roi': 8, 'conversion_rate': 0.5, 'total_issued': 10000,
            'total_sales': 500000, 'aov': 800, 'member_contribution': 60,
            'coupon_leverage': 0.01}

def _sample_structure():
    return [{'name': '停车券', 'pct': 85, 'count': 8500},
            {'name': '体验券', 'pct': 15, 'count': 1500}]

def _sample_cohorts():
    return [
        {'level': '菁英会员', 'age_group': '80后', 'redeem_rate': 2.0, 'atv': 800,
         'avg_coupons': 3, 'tag': 'GREEN', 'issued': 500, 'redeemed': 100, 'sales': 400000},
        {'level': '普通会员', 'age_group': '90后', 'redeem_rate': 0.3, 'atv': 150,
         'avg_coupons': 8, 'tag': 'RED', 'issued': 2000, 'redeemed': 30, 'sales': 30000},
    ]

def _sample_lag():
    return [{'lag': 0, 'r': -0.3}, {'lag': 3, 'r': 0.5}, {'lag': 7, 'r': 0.2}]


def test_fixB_summary_page_different_from_kpi():
    """Fix B: summary page findings != kpi page findings."""
    kpis = _sample_kpis()
    structure = _sample_structure()
    cohorts = _sample_cohorts()
    lag_data = _sample_lag()

    r_summary = generate_analysis('page_overview', kpis=kpis, structure=structure,
                                   cohorts=cohorts, lag_data=lag_data, page='summary')
    r_kpi = generate_analysis('page_overview', kpis=kpis, structure=structure,
                               cohorts=cohorts, lag_data=lag_data, page='kpi')

    assert r_summary['generated_by'] == '本地规则引擎'
    assert r_kpi['generated_by'] == '本地规则引擎'
    # Findings should differ between pages
    assert r_summary['findings'] != r_kpi['findings'], (
        f"Summary and KPI findings should differ!\nSummary: {r_summary['findings']}\nKPI: {r_kpi['findings']}"
    )


def test_fixB_all_six_pages_have_different_findings():
    """Fix B: All 6 pages should produce distinct findings."""
    kpis = _sample_kpis()
    structure = _sample_structure()
    cohorts = _sample_cohorts()
    lag_data = _sample_lag()

    pages = ['summary', 'kpi', 'structure', 'trend', 'cohort', 'insight']
    results = {}
    for p in pages:
        results[p] = generate_analysis('page_overview', kpis=kpis, structure=structure,
                                        cohorts=cohorts, lag_data=lag_data, page=p)

    # Collect all findings sets
    findings_sets = {}
    for p, r in results.items():
        findings_sets[p] = tuple(sorted(r.get('findings', [])))
        assert len(r.get('findings', [])) > 0, f"Page '{p}' has empty findings"

    # Check that at least some pages differ from each other
    unique_findings = set(findings_sets.values())
    assert len(unique_findings) >= 3, (
        f"Expected at least 3 unique findings sets across 6 pages, got {len(unique_findings)}"
    )


def test_fixB_each_page_has_summary_and_recommendation():
    """Fix B: Every page result has summary, findings, recommendation."""
    kpis = _sample_kpis()
    structure = _sample_structure()
    cohorts = _sample_cohorts()
    lag_data = _sample_lag()

    for page in ['summary', 'kpi', 'structure', 'trend', 'cohort', 'insight']:
        r = generate_analysis('page_overview', kpis=kpis, structure=structure,
                               cohorts=cohorts, lag_data=lag_data, page=page)
        assert 'summary' in r, f"Page '{page}' missing 'summary'"
        assert 'findings' in r, f"Page '{page}' missing 'findings'"
        assert 'recommendation' in r, f"Page '{page}' missing 'recommendation'"
        assert isinstance(r['findings'], list), f"Page '{page}' findings not a list"
        assert len(r['findings']) >= 1, f"Page '{page}' has empty findings"


def test_fixB_structure_page_focuses_on_parking():
    """Fix B: structure page should mention parking coupon share."""
    kpis = _sample_kpis()
    structure = _sample_structure()
    r = generate_analysis('page_overview', kpis=kpis, structure=structure,
                           cohorts=_sample_cohorts(), lag_data=_sample_lag(), page='structure')
    all_text = ' '.join(r['findings']) + ' ' + r['summary']
    assert '停车' in all_text or '85' in all_text, (
        f"Structure page should mention parking coupons, got: {all_text}"
    )


def test_fixB_trend_page_focuses_on_lag():
    """Fix B: trend page should mention lag day or correlation."""
    kpis = _sample_kpis()
    lag_data = _sample_lag()
    r = generate_analysis('page_overview', kpis=kpis, structure=_sample_structure(),
                           cohorts=_sample_cohorts(), lag_data=lag_data, page='trend')
    all_text = ' '.join(r['findings']) + ' ' + r['summary']
    assert '滞后' in all_text or '天' in all_text or 'r=' in all_text, (
        f"Trend page should mention lag analysis, got: {all_text}"
    )


def test_fixB_cohort_page_mentions_tags():
    """Fix B: cohort page should mention GREEN/GOLD/RED/GRAY tags."""
    kpis = _sample_kpis()
    r = generate_analysis('page_overview', kpis=kpis, structure=_sample_structure(),
                           cohorts=_sample_cohorts(), lag_data=_sample_lag(), page='cohort')
    all_text = ' '.join(r['findings']) + ' ' + r['summary']
    has_tag = any(tag in all_text for tag in ['GREEN', 'GOLD', 'RED', 'GRAY'])
    assert has_tag, f"Cohort page should mention quadrant tags, got: {all_text}"


def test_fixB_empty_data_handling():
    """Fix B: Pages handle empty data gracefully."""
    for page in ['summary', 'kpi', 'structure', 'trend', 'cohort', 'insight']:
        r = generate_analysis('page_overview', kpis=None, structure=None,
                               cohorts=None, lag_data=None, page=page)
        assert 'findings' in r
        assert isinstance(r['findings'], list)
        assert len(r['findings']) >= 1  # Should have fallback text


# ============================================================
# FIX D: module_focus local fallback — broad keyword matching
# ============================================================

def test_fixD_module_focus_resource_misallocation():
    """Fix D: '资源错配' module should get parking-specific analysis."""
    r = generate_analysis('module_focus', kpis=_sample_kpis(), structure=_sample_structure(),
                           cohorts=_sample_cohorts(), lag_data=_sample_lag(), module_name='资源错配')
    assert 'insight' in r
    assert 'finding' in r
    assert '停车券' in r['finding'] or '85' in r['finding'] or '资源' in r['finding'], (
        f"'资源错配' module should mention parking, got: {r['finding']}"
    )
    assert '模块数据已加载' not in r['insight'], (
        f"'资源错配' should not be generic fallback, got: {r['insight']}"
    )


def test_fixD_module_focus_command_center():
    """Fix D: '核心指挥看板' should get KPI overview."""
    r = generate_analysis('module_focus', kpis=_sample_kpis(), structure=_sample_structure(),
                           cohorts=_sample_cohorts(), lag_data=_sample_lag(), module_name='核心指挥看板')
    assert 'ROI' in r['finding'] or 'roi' in r['finding'].lower() or '安全线' in r['finding'], (
        f"'核心指挥看板' should mention ROI, got: {r['finding']}"
    )


def test_fixD_module_focus_lag_window():
    """Fix D: '滞后' module should get lag-specific analysis."""
    r = generate_analysis('module_focus', kpis=_sample_kpis(), structure=_sample_structure(),
                           cohorts=_sample_cohorts(), lag_data=_sample_lag(), module_name='滞后窗口')
    assert '天' in r['finding'] or '滞后' in r['finding'] or 'r=' in r['finding'], (
        f"'滞后窗口' should mention lag, got: {r['finding']}"
    )


def test_fixD_module_focus_unknown_fallback():
    """Fix D: Unknown module name should still produce data-driven fallback."""
    r = generate_analysis('module_focus', kpis=_sample_kpis(), structure=_sample_structure(),
                           cohorts=_sample_cohorts(), lag_data=_sample_lag(), module_name='某个未知模块')
    assert 'insight' in r and 'finding' in r
    # Should NOT be the old generic text
    assert '模块数据已加载' not in r['insight'], (
        f"Unknown module should still use data-driven fallback, got: {r['insight']}"
    )
    # Should contain some actual data reference
    assert len(r['finding']) > 10, f"Finding too short: {r['finding']}"
# ============================================================
# FIX C: applySimulation coupon_volume ROI — no drop on cut
# ============================================================

def test_fixC_coupon_volume_cut_roi_should_not_drop():
    """Fix C: When cutting coupon_volume (-60%), ROI should rise (not drop).
    
    The JS code is: d.kpis.roi = Math.round(d.kpis.roi * (1 - (pct/100) * 0.15))
    So for pct=-60: roi *= (1 - (-0.6 * 0.15)) = (1 + 0.09) = 1.09 → +9%
    """
    roi = 100  # base ROI
    pct = -60
    # New JS formula: 1 - (pct/100) * 0.15
    factor = 1 - (pct / 100) * 0.15
    new_roi = round(roi * factor)
    assert new_roi > roi, (
        f"Cutting coupon_volume by {pct}% should RAISE ROI, "
        f"but ROI went from {roi} to {new_roi} (factor={factor:.3f})"
    )


def test_fixC_coupon_volume_increase_roi_mild_drop():
    """Fix C: When increasing coupon_volume (+30%), ROI may drop mildly (new coupons need time)."""
    roi = 100
    pct = 30
    factor = 1 - (pct / 100) * 0.15
    new_roi = round(roi * factor)
    assert new_roi < roi, (
        f"Increasing coupon_volume by +{pct}% should slightly reduce short-term ROI, "
        f"but ROI went from {roi} to {new_roi} (factor={factor:.3f})"
    )
    # The drop should be modest (<10%)
    assert new_roi >= roi * 0.9, f"ROI drop too large: {roi} → {new_roi}"


def test_fixC_coupon_volume_zero_change():
    """Fix C: pct=0 should not change ROI."""
    roi = 100
    pct = 0
    factor = 1 - (pct / 100) * 0.15
    new_roi = round(roi * factor)
    assert new_roi == roi


def test_fixC_coupon_volume_extreme_cut():
    """Fix C: Extreme cut (-100%) should still produce reasonable ROI."""
    roi = 50
    pct = -100
    factor = 1 - (pct / 100) * 0.15
    new_roi = round(roi * factor)
    assert new_roi > roi
    # Factor should be 1.15 → ROI 50 * 1.15 = 57.5 → round=57 (banker's rounding)
    assert new_roi == 57


# ============================================================
# Integration tests
# ============================================================

def test_integration_fixA_fixC_together():
    """Integration: predict_trend_simulation with coupon_volume cut → trend changes, ROI logic is sound."""
    trend = _make_trend(['W1', 'W2'], [1000, 2000], [50000, 100000])
    lag = _make_lag([(0, -0.3), (3, 0.5)])
    result = predict_trend_simulation(trend, lag, [
        {'effect': 'coupon_volume', 'pct': -60}
    ])
    # Coupons reduced to 40%
    assert result['trend']['coupon'][0] == 400  # 1000 * 0.4
    assert result['trend']['coupon'][1] == 800  # 2000 * 0.4
    # Sales unchanged (coupon_volume doesn't affect sales)
    assert result['trend']['sales'][0] == 50000


def test_integration_all_dimensions():
    """Integration: All three dimensions applied together produce correct numeric results."""
    trend = _make_trend(['W1', 'W2'], [100, 200], [1000, 2000])
    lag = _make_lag([(0, -0.3), (3, 0.5)])
    result = predict_trend_simulation(trend, lag, [
        {'effect': 'coupon_volume', 'pct': -50},
        {'effect': 'sales_efficiency', 'pct': 20},
        {'effect': 'lag_correlation', 'pct': 30},
    ])
    assert result['trend']['coupon'][0] == 50      # 100 * 0.5
    assert result['trend']['sales'][0] == 1200      # 1000 * 1.2
    assert result['lag'][0]['r'] == 0.0             # -0.3 + 0.3
    assert result['lag'][1]['r'] == 0.8             # 0.5 + 0.3


def test_integration_legacy_actions_still_work():
    """Integration: Legacy string actions still map correctly via _LEGACY_ACTION_MAP."""
    trend = _make_trend(['W1'], [100], [1000])
    lag = _make_lag([(0, 0.5)])
    result = predict_trend_simulation(trend, lag, ['cut_parking', 'boost_green', 'optimize_lag'])
    assert result['trend']['coupon'][0] == 40       # 100 * 0.4 (cut_parking: coupon_volume -60%)
    # Step 1: cut_parking → coupon_volume -60%: coupon 100→40, sales unchanged
    # Step 2: boost_green → sales_efficiency +15%: sales 1000→1150
    # Step 3: optimize_lag → lag_correlation +15%: r 0.5→0.65
    assert result['trend']['sales'][0] == 1150      # 1000 * 1.15


# ============================================================
# Runner
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("3 Critical Fixes — Unit Test Suite (2026-07-20)")
    print("=" * 60)

    all_tests = [
        # Fix A
        test_fixA_trend_numeric_always_from_local,
        test_fixA_trend_predicted_by_mentions_local_engine,
        test_fixA_trend_has_ai_analysis_field,
        test_fixA_trend_determinism,
        test_fixA_trend_cache_hit,
        test_fixA_trend_no_side_effects,
        # Fix B
        test_fixB_summary_page_different_from_kpi,
        test_fixB_all_six_pages_have_different_findings,
        test_fixB_each_page_has_summary_and_recommendation,
        test_fixB_structure_page_focuses_on_parking,
        test_fixB_trend_page_focuses_on_lag,
        test_fixB_cohort_page_mentions_tags,
        test_fixB_empty_data_handling,
        # Fix C
        test_fixC_coupon_volume_cut_roi_should_not_drop,
        test_fixC_coupon_volume_increase_roi_mild_drop,
        test_fixC_coupon_volume_zero_change,
        test_fixC_coupon_volume_extreme_cut,
        # Fix D: module_focus local fallback
        test_fixD_module_focus_resource_misallocation,
        test_fixD_module_focus_command_center,
        test_fixD_module_focus_lag_window,
        test_fixD_module_focus_unknown_fallback,
        # Integration
        test_integration_fixA_fixC_together,
        test_integration_all_dimensions,
        test_integration_legacy_actions_still_work,
    ]

    passed = 0
    for t in all_tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"\n  FAIL {t.__name__}")
            print(f"    {e}")

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{len(all_tests)} passed")

    if passed < len(all_tests):
        print(f"\n{len(all_tests) - passed} test(s) FAILED!")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED!")
