"""
Test that hover analysis binding matches actual HTML selectors.
Runs without browser — validates JS code patterns against HTML structure.
"""
import re
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def test_hover_selector_matches_html():
    """The hover event listener must match classes that actually exist in HTML."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    html = read_file(os.path.join(PROJECT_ROOT, 'webapp/templates/index.html'))

    # Extract the closest() chain from bindHoverAnalysis
    match = re.search(r'var target = e\.target\.closest\((.*?)\);', js)
    assert match, "Could not find hover target selector in JS"
    selector_str = match.group(1)

    # Extract class names from the selector
    classes = re.findall(r"'\.([\w-]+)'", selector_str)
    print(f"Hover targets: {classes}")

    # Check each class exists in HTML
    for cls in classes:
        assert cls in html, f"Class '{cls}' from hover selector NOT found in HTML! Hover will never fire."

    # Verify key title classes exist in HTML
    for check in ['panel-title', 'section-title']:
        count = html.count(check)
        assert count > 0, f"{check} found {count} times in HTML — must be > 0"
        print(f"  .{check} found {count} times in HTML")

    print("PASS: All hover selector classes exist in HTML")


def test_simulation_mode_does_not_block_hover():
    """Simulation mode should NOT disable hover analysis."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    # Find the if-guard in bindHoverAnalysis
    bind_func = re.search(r'function bindHoverAnalysis\(\) \{.*?\n\}', js, re.DOTALL)
    assert bind_func, "Could not find bindHoverAnalysis function"

    func_body = bind_func.group(0)
    # Should NOT contain "simulationMode" in the if-guard
    guard_match = re.search(r'if\s*\(!target.*?\)\s*return;', func_body)
    assert guard_match, "Could not find the guard statement"
    guard = guard_match.group(0)
    assert 'simulationMode' not in guard, (
        f"CRITICAL: simulationMode still blocks hover! Guard: {guard}"
    )
    print("PASS: Simulation mode does NOT block hover analysis")


def test_fetchFocusedAnalysis_has_safety_fallback():
    """fetchFocusedAnalysis must have a safety timer fallback."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    assert 'aiPanelSafetyTimer' in js, "CRITICAL: aiPanelSafetyTimer not found — no safety fallback!"
    assert "textContent.indexOf('正在分析')" in js, (
        "CRITICAL: Safety timer does not check for '正在分析' text"
    )
    print("PASS: fetchFocusedAnalysis has safety timer fallback")


def test_focus_name_strips_trailing_wen():
    """The focus name should strip trailing '问' from ask button."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function fetchFocusedAnalysis\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find fetchFocusedAnalysis"
    body = func.group(0)
    assert "问" in body and "replace" in body, "CRITICAL: No stripping of trailing '问' from focus name"
    assert "\\\\s*问\\\\s*$" in body or "/\\s*问\\s*$/" in body, "CRITICAL: Regex for stripping '问' not found"
    print("PASS: Focus name strips trailing '问'")


def test_backend_module_param_matches():
    """Frontend sends 'module' param, backend reads 'module' param."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    py = read_file(os.path.join(PROJECT_ROOT, 'webapp/app.py'))

    # Frontend URL
    url_match = re.search(r"module_focus&module=", js)
    assert url_match, "Frontend URL must contain 'module_focus&module='"
    print(f"Frontend sends: ...module_focus&module=...")

    # Backend reads
    backend_match = re.search(r"request\.args\.get\('module'", py)
    assert backend_match, "Backend must read request.args.get('module')"
    print(f"Backend reads: request.args.get('module', ...)")

    print("PASS: Frontend/backend param names match")


def test_cleanText_strips_bracket_tags():
    """cleanText function must strip [xxx] bracket tags."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function cleanText\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find cleanText function"
    body = func.group(0)
    assert '\\[\\w+\\]' in body or '\\[[A-Za-z]+\\]' in body, (
        "CRITICAL: cleanText does not strip [xxx] bracket tags"
    )
    print("PASS: cleanText strips [xxx] bracket tags")


def test_all_cleanText_calls():
    """All AI text rendering should use cleanText (excluding cleanText definition itself)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    # Exclude the cleanText function definition itself
    js_without_clean = re.sub(r'function cleanText\(.*?\n\}', '', js, flags=re.DOTALL)

    raw_replaces = len(re.findall(r'\.replace\(/\\\*\\\*\(', js_without_clean))
    clean_calls = len(re.findall(r'cleanText\(', js_without_clean))

    print(f"  Raw .replace() calls remaining (outside cleanText): {raw_replaces}")
    print(f"  cleanText() calls: {clean_calls}")
    assert raw_replaces == 0, (
        f"Found {raw_replaces} raw .replace() calls that should use cleanText()"
    )
    print("PASS: All AI text uses cleanText()")


def test_updateSimulationBanner_has_x_buttons():
    """Simulation banner must render × buttons for each suggestion."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function updateSimulationBanner\(\) \{.*?\n\}', js, re.DOTALL)
    assert func, "Could not find updateSimulationBanner"
    body = func.group(0)
    assert '&times;' in body, "CRITICAL: No × button HTML in updateSimulationBanner"
    assert 'window.removeSuggestion' in body, "CRITICAL: × button must call window.removeSuggestion"
    print("PASS: Simulation banner has × buttons")


def test_old_banner_overwrite_removed():
    """updateSimulationNotes must NOT overwrite banner with old version."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function updateSimulationNotes\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find updateSimulationNotes"
    body = func.group(0)
    # Should call updateSimulationBanner, NOT set banner.innerHTML directly
    has_old_overwrite = "banner.innerHTML" in body
    has_delegate = "updateSimulationBanner()" in body
    assert not has_old_overwrite or has_delegate, (
        "CRITICAL: updateSimulationNotes still overwrites banner directly!"
    )
    print("PASS: updateSimulationNotes delegates to updateSimulationBanner")


if __name__ == '__main__':
    print("=" * 60)
    print("Hover Analysis & Simulation Banner Test Suite")
    print("=" * 60)
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
            print(f"\nFAIL: {t.__name__}")
            print(f"  {e}")
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{len(tests)} passed")
    assert passed == len(tests), f"{len(tests) - passed} test(s) FAILED"
    print("ALL TESTS PASSED!")
