"""
Frontend dynamic button tests — static JS analysis.
Tests: parameter passing correctness, helper function existence, backward compatibility.
These are static analysis tests that validate the JS code patterns exist,
NOT runtime tests (which would require a browser).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _read_js():
    """Read the dashboard.js file content."""
    js_path = os.path.join(os.path.dirname(__file__), '..',
                           'webapp', 'static', 'js', 'dashboard.js')
    with open(js_path, 'r', encoding='utf-8') as f:
        return f.read()


JS_CONTENT = _read_js()


# ============================================================
# 1. renderActionableRecs function exists
# ============================================================
def test_render_actionable_recs_exists():
    assert 'function renderActionableRecs(' in JS_CONTENT, \
        'renderActionableRecs function not found in dashboard.js'


# ============================================================
# 2. renderActionableRecs handles dict format
# ============================================================
def test_render_actionable_recs_handles_dict():
    """renderActionableRecs should check typeof r === 'object' for dict handling."""
    assert "typeof r === 'object'" in JS_CONTENT, \
        'renderActionableRecs should handle dict recommendations'


# ============================================================
# 2b. renderActionableRecs uses original button style
# ============================================================
def test_render_actionable_recs_original_button_style():
    """renderActionableRecs should use original btn btn-primary btn-sm button style with '采纳建议' text."""
    assert 'btn btn-primary btn-sm' in JS_CONTENT, \
        'renderActionableRecs should keep original btn btn-primary btn-sm class'
    assert '采纳建议' in JS_CONTENT, \
        'renderActionableRecs should use "采纳建议" button text'


# ============================================================
# 3. fetchSimulationTrend sends structured actions
# ============================================================
def test_fetch_simulation_trend_structured():
    """fetchSimulationTrend should send {effect, pct} objects."""
    assert "effect: p.action" in JS_CONTENT or "effect:p.action" in JS_CONTENT, \
        'fetchSimulationTrend should send effect field'
    assert "pct: p.pct" in JS_CONTENT or "pct:p.pct" in JS_CONTENT, \
        'fetchSimulationTrend should send pct field'


# ============================================================
# 4. applySimulation has new dimension branches
# ============================================================
def test_apply_simulation_coupon_volume():
    assert "coupon_volume" in JS_CONTENT, \
        'applySimulation should handle coupon_volume'


def test_apply_simulation_sales_efficiency():
    assert "sales_efficiency" in JS_CONTENT, \
        'applySimulation should handle sales_efficiency'


def test_apply_simulation_lag_correlation():
    assert "lag_correlation" in JS_CONTENT, \
        'applySimulation should handle lag_correlation'


# ============================================================
# 5. Backward compatibility — legacy actions still present
# ============================================================
def test_legacy_cut_parking_still_exists():
    assert "cut_parking" in JS_CONTENT, \
        'Legacy cut_parking action should still be supported'


def test_legacy_boost_green_still_exists():
    assert "boost_green" in JS_CONTENT, \
        'Legacy boost_green action should still be supported'


def test_legacy_melt_red_still_exists():
    assert "melt_red" in JS_CONTENT, \
        'Legacy melt_red action should still be supported'


def test_legacy_optimize_lag_still_exists():
    assert "optimize_lag" in JS_CONTENT, \
        'Legacy optimize_lag action should still be supported'


# ============================================================
# 6. updateAIInsight uses renderActionableRecs
# ============================================================
def test_update_ai_insight_uses_render():
    assert 'renderActionableRecs(' in JS_CONTENT, \
        'updateAIInsight should call renderActionableRecs'


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
