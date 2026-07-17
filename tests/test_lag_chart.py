"""
Test updateLagChart function — validates sorting, best-lag detection,
chart rendering paths, simulation overlay, and table generation.
Static analysis — runs without browser.
"""
import re
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_function(js, func_name):
    """Extract function body by matching braces."""
    pattern = rf'function {func_name}\(.*?\)\s*\{{'
    match = re.search(pattern, js)
    if not match:
        return None
    start = match.start()
    # Count braces from the opening {
    brace_start = match.end() - 1  # position of opening {
    depth = 0
    i = brace_start
    while i < len(js):
        if js[i] == '{':
            depth += 1
        elif js[i] == '}':
            depth -= 1
            if depth == 0:
                return js[start:i+1]
        i += 1
    return None


def test_updateLagChart_exists():
    """updateLagChart function must exist."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    assert 'function updateLagChart(' in js, "updateLagChart function not found"
    print("PASS: updateLagChart function exists")


def test_null_guard():
    """Return early when lagData is null/empty."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    # Must have early return guard for null/empty
    assert '!lagData' in body or 'lagData.length === 0' in body, (
        "Missing null/empty guard for lagData"
    )
    assert 'return' in body.split('\n')[0] or 'return' in body[:200], (
        "Early return must be near function start"
    )
    print("PASS: Null/empty guard present")


def test_sorts_by_lag():
    """Lag data must be sorted by lag days (ascending)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    # Should sort by a.lag - b.lag (ascending)
    assert "a.lag - b.lag" in body or "a.lag - b.lag" in body.replace(' ', ''), (
        "Lag data must be sorted by a.lag - b.lag"
    )
    print("PASS: Lag data sorted by lag days ascending")


def test_best_lag_by_r():
    """Best lag must be determined by max r value."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    # Should find best by comparing r values — the reduce compares b.r > a.r
    body_nospace = body.replace(' ', '')
    assert 'b.r>a.r' in body_nospace or 'b.r>a.r' in body, (
        "Best lag must be selected by max r value (b.r > a.r ? b : a)"
    )
    print("PASS: Best lag selected by max r")


def test_best_lag_dom_updates():
    """Best lag info must update #best-lag-title and #best-lag-desc."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert '#best-lag-title' in body, "Missing #best-lag-title DOM update"
    assert '#best-lag-desc' in body, "Missing #best-lag-desc DOM update"
    assert 'best.lag' in body, "Best lag value must be used in output text"
    print("PASS: Best lag DOM elements updated")


def test_correlation_strength_labels():
    """Correlation strength must use Chinese labels (强/中等/弱)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert '强' in body, "Missing '强' correlation label"
    assert '中等' in body, "Missing '中等' correlation label"
    assert '弱' in body, "Missing '弱' correlation label"
    # Check threshold patterns in the body (with spaces intact)
    assert 'best.r >= 0.5' in body, "Threshold 0.5 for 强 missing"
    assert 'best.r >= 0.2' in body, "Threshold 0.2 for 中等 missing"
    print("PASS: Correlation strength labels (强/中等/弱) present")


def test_dynamic_y_axis():
    """Y-axis must auto-range to include negative values."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert 'yMin' in body, "Missing yMin calculation"
    assert 'yMax' in body, "Missing yMax calculation"
    assert 'Math.min' in body, "Must use Math.min for y-axis range"
    assert 'Math.max' in body, "Must use Math.max for y-axis range"
    assert '- 0.1' in body or '-0.1' in body, "yMin should extend below data min"
    print("PASS: Dynamic y-axis with negative value support")


def test_lagCorrChart_rendered():
    """#lagCorrChart canvas must be targeted for line chart."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert '#lagCorrChart' in body, "Missing #lagCorrChart canvas reference"
    assert 'lagCorrChart' in body, "Missing lagCorrChart variable"
    assert 'destroy()' in body, "Chart must be destroyed before recreation"
    print("PASS: lagCorrChart line chart rendered")


def test_lagChart_bar_rendered():
    """#lagChart canvas must be targeted for bar chart."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert '#lagChart' in body, "Missing #lagChart canvas reference"
    assert "type: 'bar'" in body, (
        "Secondary chart must be type: 'bar'"
    )
    print("PASS: lagChart bar chart rendered")


def test_best_lag_bar_highlighted():
    """Best lag bar must have distinct color (#6ee7b7)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert '#6ee7b7' in body, "Best lag bar must be green (#6ee7b7)"
    assert '#d1d5db' in body, "Non-best bars must be gray (#d1d5db)"
    print("PASS: Best lag bar highlighted green, others gray")


def test_simulation_overlay():
    """Simulation mode must overlay original lag data as dashed line."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert 'simulationMode' in body, "Must check simulationMode"
    assert '_original' in body, "Must access globalData._original"
    assert 'origLagMap' in body, "Must build original lag map for overlay"
    print("PASS: Simulation overlay logic present")


def test_lag_table_rendered():
    """Lag detail table (#lag-table-body) must be populated."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert '#lag-table-body' in body, "Missing #lag-table-body reference"
    assert 'd.r.toFixed(2)' in body or 'd.r.toFixed' in body, (
        "r values must be formatted to 2 decimals"
    )
    print("PASS: Lag detail table populated")


def test_table_strength_badges():
    """Table must include strength badges (strong/moderate/weak/none)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    for strength in ['strong', 'moderate', 'weak', 'none']:
        assert strength in body, f"Strength '{strength}' not found in table logic"
    assert 'badge-green' in body, "Missing badge-green for strong correlation"
    assert 'badge-gold' in body, "Missing badge-gold for moderate correlation"
    assert 'badge-gray' in body, "Missing badge-gray for weak/none correlation"
    print("PASS: Table strength badges complete")


def test_table_header_dynamic():
    """Table header must be dynamically rebuilt for simulation columns."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert "thead.innerHTML" in body, "Table header must be rebuilt dynamically"
    assert '皮尔逊 r' in body, "Header must include '皮尔逊 r' column"
    assert '滞后天数' in body, "Header must include '滞后天数' column"
    print("PASS: Table header rebuilt dynamically")


def test_lag_insight_element():
    """#lag-insight element must be populated with best lag summary."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert '#lag-insight' in body, "Missing #lag-insight element update"
    assert 'best.lag' in body, "Must reference best.lag in insight text"
    print("PASS: lag-insight element populated")


def test_all_three_chart_areas():
    """All three chart areas must be targeted: lagCorrChart, lagChart, lag-insight."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    targets = ['#lagCorrChart', '#lagChart', '#lag-insight']
    for t in targets:
        assert t in body, f"Missing chart target: {t}"
    print("PASS: All three chart areas targeted")


def test_best_lag_strong_tag_in_table():
    """Best lag row in table must have <strong> tag."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    body = extract_function(js, 'updateLagChart')
    assert body, "Could not extract updateLagChart body"

    assert '<strong>' in body, "Best lag row must use <strong> tag"
    assert "d.lag === best.lag" in body, (
        "Must compare d.lag === best.lag for row highlighting"
    )
    print("PASS: Best lag row uses <strong> tag")


if __name__ == '__main__':
    print("=" * 60)
    print("updateLagChart Function Test Suite")
    print("=" * 60)
    tests = [
        test_updateLagChart_exists,
        test_null_guard,
        test_sorts_by_lag,
        test_best_lag_by_r,
        test_best_lag_dom_updates,
        test_correlation_strength_labels,
        test_dynamic_y_axis,
        test_lagCorrChart_rendered,
        test_lagChart_bar_rendered,
        test_best_lag_bar_highlighted,
        test_simulation_overlay,
        test_lag_table_rendered,
        test_table_strength_badges,
        test_table_header_dynamic,
        test_lag_insight_element,
        test_all_three_chart_areas,
        test_best_lag_strong_tag_in_table,
    ]
    import sys
    passed = 0
    failures = []
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            failures.append((t.__name__, str(e)))
            print(f"FAIL: {t.__name__} -> {e}", flush=True)
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{len(tests)} passed", flush=True)
    if failures:
        print(f"\nFailures ({len(failures)}):", flush=True)
        for name, msg in failures:
            print(f"  - {name}: {msg}", flush=True)
        sys.exit(1)
    print("ALL TESTS PASSED!")
