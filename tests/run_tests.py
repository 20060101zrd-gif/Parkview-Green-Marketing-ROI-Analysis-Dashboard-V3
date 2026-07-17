import sys
sys.path.insert(0, '.')
from tests.test_hover_analysis import *

tests = [
    test_hover_selector_matches_html,
    test_simulation_mode_does_not_block_hover,
    test_fetchFocusedAnalysis_has_safety_fallback,
    test_focus_name_strips_trailing_wen,
    test_backend_module_param_matches,
    test_cleanText_strips_bracket_tags,
    test_all_cleanText_calls,
    test_updateSimulationBanner_has_x_buttons,
    test_old_banner_overwrite_removed,
]
passed = 0
for t in tests:
    try:
        t()
        passed += 1
    except AssertionError as e:
        print(f"FAIL: {t.__name__} -> {e}")
print(f"\n{passed}/{len(tests)} passed")
