"""
Unit tests for the 5 critical fixes applied 2024-07-16.

Fix 1: AI panel initial text "AI正在分析中..." (not "鼠标滑取模块进行分析")
Fix 2: KPI card CSS — no duplicate .kpi-card-value blocks causing style conflicts
Fix 3: Alert card green checkmark — uses .alert-icon class selector (not bare 'span')
Fix 4: Local mode insight page — shows proper message (not "加载中...")
Fix 5: Ask "问" buttons — hidden via injected <style> rule in local mode (not just one-time DOM scan)
"""
import re
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)


def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# ============================================================
# FIX 1: AI panel initial text
# ============================================================
def test_fix1_ai_panel_initial_text():
    """Fix 1: AI panel shows 'AI正在分析中...' not '鼠标滑取模块进行分析'."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    assert 'AI正在分析中...' in js, (
        "Fix 1 FAILED: 'AI正在分析中...' not found in dashboard.js"
    )
    assert '鼠标滑取模块进行分析' not in js, (
        "Fix 1 FAILED: Old text '鼠标滑取模块进行分析' still present"
    )
    print("PASS: Fix 1 — AI panel initial text is 'AI正在分析中...'")


# ============================================================
# FIX 2: KPI card CSS — no duplicate blocks
# ============================================================
def test_fix2_css_no_duplicate_kpi_card_value():
    """Fix 2: Only ONE .kpi-card-value block in CSS (no duplicates causing conflicts)."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))

    # Count .kpi-card-value { blocks (not .kpi-card-value .val etc)
    # Match the opening brace of .kpi-card-value selector
    blocks = re.findall(r'\.kpi-card-value\s*\{', css)
    count = len(blocks)
    assert count == 1, (
        f"Fix 2 FAILED: Found {count} .kpi-card-value {{ blocks (expected exactly 1). "
        f"Duplicates cause style conflicts."
    )
    print(f"PASS: Fix 2 — Only {count} .kpi-card-value {{ block in CSS")


def test_fix2_css_no_duplicate_kpi_card_sub():
    """Fix 2: Only ONE .kpi-card-sub block in CSS."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))

    blocks = re.findall(r'\.kpi-card-sub\s*\{', css)
    count = len(blocks)
    assert count == 1, (
        f"Fix 2 FAILED: Found {count} .kpi-card-sub {{ blocks (expected exactly 1)"
    )
    print(f"PASS: Fix 2 — Only {count} .kpi-card-sub {{ block in CSS")


def test_fix2_css_no_duplicate_kpi_card_ai_note():
    """Fix 2: Only ONE .kpi-card-ai-note block in CSS."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))

    blocks = re.findall(r'\.kpi-card-ai-note\s*\{', css)
    count = len(blocks)
    assert count == 1, (
        f"Fix 2 FAILED: Found {count} .kpi-card-ai-note {{ blocks (expected exactly 1)"
    )
    print(f"PASS: Fix 2 — Only {count} .kpi-card-ai-note {{ block in CSS")


def test_fix2_css_no_duplicate_color_bars():
    """Fix 2: No genuinely conflicting color bar rules (border-top vs --card-accent are OK)."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))

    # The original conflict was that border-top:3px was defined in TWO places with different colors.
    # Now: line ~192 sets border-top, line ~274 sets CSS variables (--card-accent).
    # These serve different purposes and don't conflict.
    # Key check: no duplicate "border-top" in kpi-card color blocks
    border_top_blocks = re.findall(r'\.kpi-card\.\w+\s*\{[^}]*border-top', css)
    for color in ['green', 'blue', 'purple', 'gold']:
        matching = [b for b in border_top_blocks if f'.kpi-card.{color}' in b]
        assert len(matching) <= 1, (
            f"Fix 2 FAILED: Found {len(matching)} border-top definitions for .kpi-card.{color}"
        )
    print("PASS: Fix 2 — No conflicting border-top rules across color bars")


def test_fix2_kpi_card_value_has_overflow_hidden():
    """Fix 2: .kpi-card-value must have overflow:hidden and min-width:0 for anti-overflow."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))

    # Find the .kpi-card-value block content
    match = re.search(r'\.kpi-card-value\s*\{([^}]+)\}', css)
    assert match, "Could not find .kpi-card-value block"
    block_body = match.group(1)

    assert 'overflow' in block_body and 'hidden' in block_body, (
        "Fix 2 FAILED: .kpi-card-value missing 'overflow: hidden'"
    )
    assert 'min-width' in block_body and ': 0' in block_body.split('min-width')[1][:10], (
        "Fix 2 FAILED: .kpi-card-value missing 'min-width: 0'"
    )
    print("PASS: Fix 2 — .kpi-card-value has overflow:hidden and min-width:0")


def test_fix2_css_no_gap_zero_override():
    """Fix 2: The removed duplicate block had gap:0 — must NOT be present."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))

    # After the first .kpi-card-value, there should be no gap:0 !important
    first_pos = css.index('.kpi-card-value')
    # Find all .kpi-card-value positions
    all_positions = [m.start() for m in re.finditer(r'\.kpi-card-value\s*\{', css)]
    assert len(all_positions) == 1, (
        f"Fix 2 FAILED: Still {len(all_positions)} .kpi-card-value blocks"
    )
    # In the single block, gap should be 4px, not 0
    block_match = re.search(r'\.kpi-card-value\s*\{([^}]+)\}', css)
    block_body = block_match.group(1)
    assert 'gap: 0' not in block_body, (
        "Fix 2 FAILED: .kpi-card-value still has gap:0"
    )
    print("PASS: Fix 2 — No gap:0 override in .kpi-card-value")


# ============================================================
# FIX 3: Alert card green checkmark — .alert-icon selector
# ============================================================
def test_fix3_html_has_alert_icon_class():
    """Fix 3: HTML alert cards use class='alert-icon' on icon span (not bare span)."""
    html = read_file(os.path.join(PROJECT_ROOT, 'webapp/templates/index.html'))

    alert_icon_count = html.count('class="alert-icon"')
    assert alert_icon_count >= 2, (
        f"Fix 3 FAILED: Found {alert_icon_count} .alert-icon elements in HTML "
        f"(expected >= 2 for alert-structure and alert-structure-struct)"
    )
    print(f"PASS: Fix 3 — {alert_icon_count} .alert-icon elements in HTML")


def test_fix3_js_uses_alert_icon_selector():
    """Fix 3: JS uses '.alert-icon' selector, not bare 'span' for icon targeting."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    # The updateAlertCards function must use .alert-icon
    func = re.search(r'function updateAlertCards\(.*?\).*?\n\s{2}\}', js, re.DOTALL)
    assert func, "Could not find updateAlertCards function"
    body = func.group(0)

    # Must use .alert-icon
    assert "'.alert-icon'" in body or '".alert-icon"' in body, (
        "Fix 3 FAILED: updateAlertCards does NOT use '.alert-icon' selector"
    )
    # Must NOT use bare 'span' for icon selection (could match wrong span)
    # But it CAN use querySelector('span') for other things — just not for the icon
    # Check that the icon variable assignment uses .alert-icon
    assert "querySelector('.alert-icon')" in body or 'querySelector(".alert-icon")' in body, (
        "Fix 3 FAILED: Icon querySelector does not target .alert-icon"
    )
    print("PASS: Fix 3 — JS uses '.alert-icon' selector")


def test_fix3_green_checkmark_rendered_for_healthy():
    """Fix 3: When healthy, green checkmark (✓, #10b981) is rendered."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function updateAlertCards\(.*?\).*?\n\s{2}\}', js, re.DOTALL)
    body = func.group(0)

    assert "healthy" in body, "Fix 3 FAILED: No 'healthy' branch in updateAlertCards"
    assert '#10b981' in body, (
        "Fix 3 FAILED: Green color #10b981 not found in healthy icon styling"
    )
    # Check for checkmark character
    assert '\\u2713' in body or '✓' in body or '\u2713' in body, (
        "Fix 3 FAILED: Checkmark character ✓ not found in healthy icon"
    )
    print("PASS: Fix 3 — Healthy state renders green checkmark")


# ============================================================
# FIX 4: Local mode insight page message
# ============================================================
def test_fix4_local_mode_insight_not_loading():
    """Fix 4: Local mode insight cards show proper message, not '加载中...'."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function updateInsights\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find updateInsights function"
    body = func.group(0)

    # In local mode branch, must NOT show "加载中..."
    local_mode_section = body[body.index('_aiEnabled === false'):body.index('updateAiVisibility()')]
    assert '加载中' not in local_mode_section, (
        "Fix 4 FAILED: Local mode still shows '加载中...'"
    )
    assert 'LLM 模式专属功能' in body, (
        "Fix 4 FAILED: Local mode does not mention 'LLM 模式专属功能'"
    )
    assert '模式切换按钮' in body, (
        "Fix 4 FAILED: Local mode does not instruct to switch mode"
    )
    print("PASS: Fix 4 — Local mode insight shows proper message")


# ============================================================
# FIX 5: Ask "问" buttons hidden in local mode
# ============================================================
def test_fix5_ask_btn_style_injection_in_local_mode():
    """Fix 5: Local mode injects a <style> rule hiding ALL .ask-btn permanently."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function bindAskButtons\(\) \{.*?\n\}', js, re.DOTALL)
    assert func, "Could not find bindAskButtons function"
    body = func.group(0)

    # Must inject a <style> element with id
    assert "createElement('style')" in body, (
        "Fix 5 FAILED: bindAskButtons does not create a <style> element in local mode"
    )
    assert "ask-btn-hide-style" in body, (
        "Fix 5 FAILED: Injected style does not have id 'ask-btn-hide-style'"
    )
    # The style rule must hide .ask-btn
    assert '.ask-btn' in body and 'display' in body and 'none' in body, (
        "Fix 5 FAILED: Injected style does not hide .ask-btn with display:none"
    )
    # Must use !important to override any inline styles
    assert '!important' in body, (
        "Fix 5 FAILED: Injected style does not use !important — inline styles may override it"
    )
    print("PASS: Fix 5 — Local mode injects <style> rule to hide .ask-btn")


def test_fix5_style_removed_in_llm_mode():
    """Fix 5: When switching to LLM mode, the hide style is removed."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function bindAskButtons\(\) \{.*?\n\}', js, re.DOTALL)
    body = func.group(0)

    assert "ask-btn-hide-style" in body, "Fix 5 FAILED: No reference to ask-btn-hide-style"
    assert ".remove()" in body or "remove()" in body, (
        "Fix 5 FAILED: No removal of hide style when switching to LLM mode"
    )
    print("PASS: Fix 5 — Hide style removed when switching to LLM mode")


def test_fix5_mutation_observer_skips_in_local_mode():
    """Fix 5: MutationObserver's addAskButtons also skips in local mode (not just bindAskButtons)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function bindAskButtons\(\) \{.*?\n\}', js, re.DOTALL)
    body = func.group(0)

    # addAskButtons (inner function) must also check _aiEnabled
    assert body.count('_aiEnabled === false') >= 2, (
        f"Fix 5 FAILED: _aiEnabled === false appears only {body.count('_aiEnabled === false')} times "
        f"in bindAskButtons (need >= 2: one in bindAskButtons outer, one in addAskButtons inner)"
    )
    print("PASS: Fix 5 — addAskButtons inner function also guards on _aiEnabled")


# ============================================================
# FIX 6: Tray bar — persistent dock for minimized "问一问" windows
# ============================================================
def test_fix6_tray_bar_never_removed_on_empty():
    """Fix 6: removeTrayTab must NOT remove the tray bar itself when empty."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function removeTrayTab\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find removeTrayTab function"
    body = func.group(0)

    # Must NOT contain "tray.remove()" or ".remove()" on the tray
    assert 'tray.remove()' not in body and "tray.remove" not in body, (
        "Fix 6 FAILED: removeTrayTab still removes the tray bar when empty!"
    )
    print("PASS: Fix 6 — removeTrayTab does NOT remove the tray bar")


def test_fix6_restore_does_not_remove_tray_tab():
    """Fix 6: restoreAskWindow must NOT remove the tray tab (dock persists)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function restoreAskWindow\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find restoreAskWindow function"
    body = func.group(0)

    # Must NOT call removeTrayTab
    assert 'removeTrayTab' not in body, (
        "Fix 6 FAILED: restoreAskWindow still calls removeTrayTab — tab should persist as dock!"
    )
    print("PASS: Fix 6 — restoreAskWindow does NOT remove tray tab")


def test_fix6_tray_bar_has_fixed_position():
    """Fix 6: Tray bar uses position:fixed so it survives scrolling."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function getTrayBar\(\) \{.*?\n\}', js, re.DOTALL)
    assert func, "Could not find getTrayBar function"
    body = func.group(0)

    assert 'position:fixed' in body, (
        "Fix 6 FAILED: Tray bar does NOT use position:fixed — will scroll away!"
    )
    assert 'bottom:0' in body, (
        "Fix 6 FAILED: Tray bar not positioned at bottom:0"
    )
    assert 'z-index:99999' in body, (
        "Fix 6 FAILED: Tray bar z-index too low, may be hidden behind other elements"
    )
    print("PASS: Fix 6 — Tray bar is position:fixed at bottom:0 with high z-index")


def test_fix6_tray_tabs_show_minimized_state():
    """Fix 6+7: Minimized tabs get blue border (#60a5fa), active get darker blue (#3b82f6)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    # addTrayTab must set blue border for minimized
    func = re.search(r'function addTrayTab\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find addTrayTab function"
    body = func.group(0)

    assert '#60a5fa' in body, (
        "Fix 6 FAILED: addTrayTab does not use blue border #60a5fa for minimized tabs"
    )
    assert '#1e40af' in body, (
        "Fix 6 FAILED: addTrayTab does not use dark blue text #1e40af"
    )

    # updateTrayTabActive must set active blue
    func2 = re.search(r'function updateTrayTabActive\(.*?\).*?\n\}', js, re.DOTALL)
    assert func2, "Could not find updateTrayTabActive function"
    body2 = func2.group(0)
    assert '#3b82f6' in body2, (
        "Fix 6 FAILED: updateTrayTabActive does not use active blue border #3b82f6"
    )
    assert '#dbeafe' in body2, (
        "Fix 6 FAILED: updateTrayTabActive does not use active blue bg #dbeafe"
    )

    print("PASS: Fix 6 — Tray tabs have blue (minimized) / darker blue (active) visual states")


def test_fix6_close_window_removes_tray_when_no_windows_left():
    """Fix 6: closeAskWindow only removes the tray bar when NO windows remain at all."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function closeAskWindow\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find closeAskWindow function"
    body = func.group(0)

    # Must iterate chatWindows and only remove tray if none have .el
    assert 'hasAnyWindow' in body or 'hasAny' in body, (
        "Fix 6 FAILED: closeAskWindow does not check if any windows remain before removing tray"
    )
    # Must call removeTrayTab for the closed window's tab
    assert 'removeTrayTab' in body, (
        "Fix 6 FAILED: closeAskWindow does not call removeTrayTab"
    )
    print("PASS: Fix 6 — closeAskWindow only removes tray when all windows are gone")


# ============================================================
# FIX 7: Tray bar — blue translucent theme matching AI panel
# ============================================================
def test_fix7_tray_bar_blue_theme():
    """Fix 7: Tray bar uses blue translucent theme (#dbeafe / #bfdbfe) matching AI panel."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function getTrayBar\(\) \{.*?\n\}', js, re.DOTALL)
    assert func, "Could not find getTrayBar function"
    body = func.group(0)

    assert '#dbeafe' in body or '219,234,254' in body, (
        "Fix 7 FAILED: Tray bar background is not blue (#dbeafe)"
    )
    assert '#bfdbfe' in body, (
        "Fix 7 FAILED: Tray bar border is not blue (#bfdbfe)"
    )
    print("PASS: Fix 7 — Tray bar uses blue translucent theme")


def test_fix7_tray_tabs_blue_theme():
    """Fix 7: Tray tabs use blue color scheme (#60a5fa, #3b82f6, #1e40af)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function addTrayTab\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find addTrayTab function"
    body = func.group(0)

    assert '#60a5fa' in body, (
        "Fix 7 FAILED: Tray tab border does not use blue (#60a5fa)"
    )
    assert '#1e40af' in body, (
        "Fix 7 FAILED: Tray tab text does not use dark blue (#1e40af)"
    )
    print("PASS: Fix 7 — Tray tabs use blue color scheme")


# ============================================================
# FIX 8: Local mode — skip all AI/LLM API endpoints
# ============================================================
def test_fix8_local_mode_skips_ai_endpoints():
    """Fix 8: loadAll() skips /api/insight, /api/anomalies, /api/kmeans in local mode."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'async function loadAll\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find loadAll function"
    body = func.group(0)

    # Must check _aiEnabled before adding AI endpoints
    assert '_aiEnabled' in body, (
        "Fix 8 FAILED: loadAll does not check _aiEnabled for AI endpoints"
    )
    # Must NOT include /api/insight unconditionally
    # (should be inside a conditional block)
    insight_lines = [l for l in body.split('\n') if '/api/insight' in l]
    assert any('_aiEnabled' in l or 'push' in l for l in insight_lines), (
        "Fix 8 FAILED: /api/insight fetch is not gated by _aiEnabled check"
    )

    # In local mode, fallback data must be injected
    assert "insight" in body and "anomalies" in body and "kmeans" in body, (
        "Fix 8 FAILED: Missing fallback data for insight/anomalies/kmeans in local mode"
    )
    print("PASS: Fix 8 — Local mode skips AI API endpoints and injects fallbacks")


def test_fix8_local_mode_fallbacks_injected():
    """Fix 8: When _aiEnabled===false, data.insight/anomalies/kmeans get empty fallbacks."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'async function loadAll\(.*?\).*?\n\}', js, re.DOTALL)
    body = func.group(0)

    # After results processing, local mode must set data.insight = {}
    local_block = body[body.index('_aiEnabled === false'):] if '_aiEnabled === false' in body else ''
    assert 'insight' in local_block, (
        "Fix 8 FAILED: No insight fallback in local mode block"
    )
    assert 'anomalies' in local_block, (
        "Fix 8 FAILED: No anomalies fallback in local mode block"
    )
    assert 'kmeans' in local_block, (
        "Fix 8 FAILED: No kmeans fallback in local mode block"
    )
    print("PASS: Fix 8 — Local mode injects empty fallbacks for all AI data keys")


# ============================================================
# FIX 9: ROI alert card green checkmark
# ============================================================
def test_fix9_html_roi_alert_has_alert_icon_class():
    """Fix 9: ROI alert card SVG has class='alert-icon' for JS targeting."""
    html = read_file(os.path.join(PROJECT_ROOT, 'webapp/templates/index.html'))

    # Both alert-roi and alert-roi-struct must have class="alert-icon" on the SVG
    assert 'id="alert-roi"' in html, "Fix 9 FAILED: #alert-roi not found in HTML"
    assert 'id="alert-roi-struct"' in html, "Fix 9 FAILED: #alert-roi-struct not found in HTML"

    # Count alert-icon in HTML — now should be >= 4 (2 structure spans + 2 ROI SVGs)
    alert_icon_count = html.count('class="alert-icon"')
    assert alert_icon_count >= 4, (
        f"Fix 9 FAILED: Found {alert_icon_count} .alert-icon elements (expected >= 4)"
    )
    print(f"PASS: Fix 9 — {alert_icon_count} .alert-icon elements in HTML (ROI SVGs included)")


def test_fix9_roi_alert_icon_switched_on_healthy():
    """Fix 9: ROI alert card icon switches to green checkmark when healthy."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    # Must have ROI icon update logic (outerHTML replacement)
    assert "roiIcon.outerHTML" in js, (
        "Fix 9 FAILED: dashboard.js does not use roiIcon.outerHTML for ROI icon replacement"
    )
    # ROI healthy branch must render green checkmark (structure already has one, ROI adds second)
    assert js.count('#10b981') >= 2, (
        f"Fix 9 FAILED: #10b981 appears only {js.count('#10b981')} times "
        f"(need >= 2: structure + ROI healthy icons)"
    )
    # ROI warning/severe must render colored '!' icon
    assert "roiColor" in js, (
        "Fix 9 FAILED: ROI warning icon does not use roiColor for dynamic styling"
    )
    print("PASS: Fix 9 — ROI alert icon switches green checkmark / colored warning based on level")


def test_fix9_roi_alert_for_each_covers_both_cards():
    """Fix 9: forEach loop covers both alert-roi and alert-roi-struct cards."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    assert "alert-roi-struct" in js, (
        "Fix 9 FAILED: dashboard.js does not reference alert-roi-struct"
    )
    print("PASS: Fix 9 — forEach covers both alert-roi and alert-roi-struct")


# ============================================================
# FIX 10: KPI card color differentiation — gradient backgrounds
# ============================================================
def test_fix10_kpi_card_gradient_backgrounds():
    """Fix 10: Each .kpi-card color variant has a distinct gradient background."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))

    colors = {
        'green': '#ecfdf5',
        'blue': '#eff6ff',
        'purple': '#f5f3ff',
        'gold': '#fffbeb',
    }

    for color_name, hex_color in colors.items():
        # Find .kpi-card.{color} block
        pattern = rf'\.kpi-card\.{color_name}\s*\{{[^}}]*\}}'
        match = re.search(pattern, css)
        assert match, f"Fix 10 FAILED: .kpi-card.{color_name} block not found"
        block = match.group(0)
        assert 'linear-gradient' in block, (
            f"Fix 10 FAILED: .kpi-card.{color_name} missing linear-gradient background"
        )
        assert hex_color in block, (
            f"Fix 10 FAILED: .kpi-card.{color_name} gradient does not contain {hex_color}"
        )
        # Gradient should go from tint color to #ffffff at ~25%
        assert '#ffffff' in block, (
            f"Fix 10 FAILED: .kpi-card.{color_name} gradient does not fade to #ffffff"
        )

    print("PASS: Fix 10 — All 4 KPI card color variants have distinct gradient backgrounds")


def test_fix10_kpi_card_border_top_preserved():
    """Fix 10: Border-top color bars are preserved alongside gradients."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))

    for color in ['green', 'blue', 'purple', 'gold']:
        pattern = rf'\.kpi-card\.{color}\s*\{{[^}}]*\}}'
        match = re.search(pattern, css)
        assert match, f"Fix 10 FAILED: .kpi-card.{color} block not found"
        block = match.group(0)
        assert 'border-top' in block, (
            f"Fix 10 FAILED: .kpi-card.{color} lost its border-top"
        )

    print("PASS: Fix 10 — Border-top color bars preserved for all KPI card variants")


# ============================================================
# FIX 11: Insight page lock overlay — 100% opaque
# ============================================================
def test_fix11_insight_lock_overlay_fully_opaque():
    """Fix 11: Insight page lock overlay is 100% opaque (#ffffff, not rgba with transparency)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    func = re.search(r'function updateInsightPageLock\(.*?\).*?\n\}', js, re.DOTALL)
    assert func, "Could not find updateInsightPageLock function"
    body = func.group(0)

    # Must use #ffffff (opaque) not rgba with alpha < 1
    assert '#ffffff' in body, (
        "Fix 11 FAILED: Lock overlay does not use #ffffff (fully opaque white)"
    )
    # Must NOT have semi-transparent rgba white
    assert 'rgba(255,255,255,0.92)' not in body and 'rgba(255, 255, 255, 0.92)' not in body, (
        "Fix 11 FAILED: Lock overlay still uses semi-transparent rgba(255,255,255,0.92)"
    )
    print("PASS: Fix 11 — Insight page lock overlay is 100% opaque white")


# ============================================================
# FIX 12: Lag chart Y-axis auto-range
# ============================================================
def test_fix12_lag_chart_y_axis_auto_range():
    """Fix 12: Lag chart Y-axis dynamically computes range from all r values."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    # Must collect all r values including original data
    assert 'allRValues' in js, (
        "Fix 12 FAILED: dashboard.js does not create allRValues array"
    )
    assert 'rMin' in js and 'rMax' in js, (
        "Fix 12 FAILED: dashboard.js does not compute rMin/rMax"
    )
    # Must use 0.05 buffer (not old 0.1)
    assert '- 0.05' in js or '-0.05' in js, (
        "Fix 12 FAILED: Y-axis buffer is not 0.05"
    )
    # Must have minimum 0.3 range guard
    assert '0.3' in js, (
        "Fix 12 FAILED: dashboard.js missing minimum 0.3 range guard for lag chart"
    )
    print("PASS: Fix 12 — Lag chart Y-axis dynamically computes range with 0.05 buffer")


def test_fix12_lag_chart_includes_original_r_values():
    """Fix 12: When simulationMode is on, original lag r values are included in Y range."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    # Must push original r values into allRValues when origLagMap exists
    assert "d.r != null" in js or "d.r !==" in js, (
        "Fix 12 FAILED: Original r values not pushed into allRValues"
    )
    print("PASS: Fix 12 — Original lag r values included in Y-axis range calculation")


def test_fix12_lag_chart_grace_percent():
    """Fix 12: Both chart instances use grace:'5%' for Chart.js padding."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    # grace:'5%' must appear at least twice (once for lagCorrChart, once for lagChart)
    grace_count = js.count("grace: '5%'")
    assert grace_count >= 2, (
        f"Fix 12 FAILED: grace:'5%' found {grace_count} times (expected >= 2)"
    )
    print(f"PASS: Fix 12 — grace:'5%' applied to both lag chart instances ({grace_count}x)")


def test_fix12_lag_bar_chart_has_base_zero():
    """Fix 12: Bar chart dataset has base:0 so bars extend from 0 axis."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))

    # The bar chart dataset must include base: 0
    assert 'base: 0' in js, (
        "Fix 12 FAILED: Bar chart dataset missing base: 0"
    )
    print("PASS: Fix 12 — Bar chart dataset uses base: 0 for proper negative bar rendering")


# ============================================================
# FIX 13: KPI card text — no ellipsis, auto-shrink, uniform height (Fix 1)
# ============================================================
def test_fix13_kpi_card_sub_no_ellipsis():
    """Fix 1: .kpi-card-sub must NOT have text-overflow:ellipsis; must allow wrap."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))
    # Find the .kpi-card-sub block
    sub_match = re.search(r'\.kpi-card-sub\s*\{[^}]+\}', css, re.DOTALL)
    assert sub_match, "Fix 13 FAILED: .kpi-card-sub block not found in CSS"
    sub_block = sub_match.group(0)
    assert 'text-overflow: ellipsis' not in sub_block, (
        "Fix 13 FAILED: .kpi-card-sub still has text-overflow:ellipsis"
    )
    assert '-webkit-line-clamp' in sub_block, (
        "Fix 13 FAILED: .kpi-card-sub missing -webkit-line-clamp for multi-line wrap"
    )
    print("PASS: Fix 13 — KPI subtitle allows 2-line wrap, no ellipsis truncation")


def test_fix13_kpi_card_uniform_height():
    """Fix 1: .kpi-card must have min-height for uniform card heights."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))
    kpi_card_match = re.search(r'\.kpi-card\s*\{([^}]+)\}', css, re.DOTALL)
    assert kpi_card_match, "Fix 13 FAILED: .kpi-card block not found"
    block = kpi_card_match.group(1)
    assert 'min-height' in block, (
        "Fix 13 FAILED: .kpi-card missing min-height for uniform heights"
    )
    print("PASS: Fix 13 — KPI cards have uniform min-height")


def test_fix13_auto_shrink_min_12():
    """Fix 1: fillKPI auto-shrink allows down to 12px (was 14)."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    assert 'size > 12' in js, (
        "Fix 13 FAILED: auto-shrink minPx not lowered to 12"
    )
    print("PASS: Fix 13 — KPI value auto-shrinks down to 12px")


# ============================================================
# FIX 14: Simulated cards NOT changing to blue border (Fix 2)
# ============================================================
def test_fix14_simulated_card_no_border_override():
    """Fix 2: .kpi-card.simulated must NOT override border-color or box-shadow."""
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))
    sim_match = re.search(r'\.kpi-card\.simulated\s*\{([^}]*)\}', css, re.DOTALL)
    assert sim_match, "Fix 14 FAILED: .kpi-card.simulated block not found"
    sim_block = sim_match.group(1)
    assert 'border-color' not in sim_block, (
        "Fix 14 FAILED: .kpi-card.simulated still overrides border-color"
    )
    assert 'box-shadow' not in sim_block, (
        "Fix 14 FAILED: .kpi-card.simulated still overrides box-shadow"
    )
    print("PASS: Fix 14 — Simulated cards preserve original border/background colors")


# ============================================================
# FIX 15: ROI alert icon — round circle, no sharp triangle (Fix 3)
# ============================================================
def test_fix15_roi_alert_icon_no_svg_polygon():
    """Fix 3: ROI alert cards use round span (not SVG polygon triangle)."""
    html = read_file(os.path.join(PROJECT_ROOT, 'webapp/templates/index.html'))
    assert '<polygon points="12,2 2,22 22,22"' not in html, (
        "Fix 15 FAILED: Sharp SVG polygon triangle still present in ROI alert"
    )
    assert 'border-radius:50%' in html, (
        "Fix 15 FAILED: ROI alert icon missing border-radius:50% (round circle)"
    )
    print("PASS: Fix 15 — ROI alert uses round circle icon, no sharp triangle")


# ============================================================
# FIX 16: Ask buttons visible in LLM mode (Fix 4)
# ============================================================
def test_fix16_ask_btn_force_restore_in_llm_mode():
    """Fix 4: bindAskButtons forces display:inline-flex in LLM mode."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    # Must restore display for existing buttons
    assert "display = 'inline-flex'" in js or 'display:inline-flex' in js, (
        "Fix 16 FAILED: bindAskButtons does not force-restore ask-btn display"
    )
    # Must have retry setTimeout
    assert "setTimeout(function() { addAskButtons(); }, 300)" in js, (
        "Fix 16 FAILED: bindAskButtons missing 300ms retry"
    )
    print("PASS: Fix 16 — Ask buttons force-restored with 300ms retry in LLM mode")


def test_fix16_adopt_suggestion_calls_bind_ask():
    """Fix 4: adoptSuggestion calls bindAskButtons after entering simulation."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    assert 'setTimeout(function() { bindAskButtons(); }, 500)' in js, (
        "Fix 16 FAILED: adoptSuggestion does not call bindAskButtons after renderAll"
    )
    print("PASS: Fix 16 — adoptSuggestion re-binds ask buttons after 500ms")


def test_fix16_mode_toggle_retry_bind_ask():
    """Fix 4: updateModeToggleUI has 500ms retry for bindAskButtons."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    # Count setTimeout for bindAskButtons in updateModeToggleUI context
    # We check the 500ms setTimeout after bindAskButtons() in updateModeToggleUI
    assert 'bindAskButtons();' in js
    # The 500ms retry should appear in the updateModeToggleUI area
    assert "setTimeout(function() { bindAskButtons(); }, 500);" in js, (
        "Fix 16 FAILED: updateModeToggleUI missing 500ms bindAskButtons retry"
    )
    print("PASS: Fix 16 — updateModeToggleUI retries bindAskButtons after 500ms")


# ============================================================
# FIX 17: Engine label shows DeepSeek LLM in LLM mode (Fix 5)
# ============================================================
def test_fix17_engine_label_deepseek_in_llm_mode():
    """Fix 5: modeLabel shows 'DeepSeek LLM' when _aiEnabled is true."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    assert "DeepSeek LLM" in js, (
        "Fix 17 FAILED: 'DeepSeek LLM' not found in dashboard.js"
    )
    assert "本地规则" in js, (
        "Fix 17 FAILED: '本地规则' not found for local mode label"
    )
    print("PASS: Fix 17 — Engine label shows DeepSeek LLM in LLM mode, 本地规则 in local")


def test_fix17_ai_insight_engine_tag():
    """Fix 5: updateAIInsight adds engine tag to diagnostic cards."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    assert 'engineTag' in js, (
        "Fix 17 FAILED: engineTag variable not found in updateAIInsight"
    )
    assert "generated_by" in js, (
        "Fix 17 FAILED: generated_by check not found for engine tag"
    )
    print("PASS: Fix 17 — Diagnostic cards show engine tag from insight.generated_by")


# ============================================================
# FIX 18: Lock button visible in simulation mode (Fix 6)
# ============================================================
def test_fix18_lock_button_in_sim_mode():
    """Fix 6: Lock button HTML is generated regardless of simulationMode."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    # The old guard 'if (!simulationMode)' around lock button must be gone
    assert "if (!simulationMode)" not in js, (
        "Fix 18 FAILED: Old 'if (!simulationMode)' guard still present for lock button"
    )
    print("PASS: Fix 18 — Lock button always shown, including simulation mode")


# ============================================================
# FIX 19: Simulation analysis uses shared DeepSeek key (Fix 7)
# ============================================================
def test_fix19_sim_analysis_uses_shared_key():
    """Fix 7: api_simulation_analysis uses _get_deepseek_key() not inline tomli."""
    py = read_file(os.path.join(PROJECT_ROOT, 'webapp/app.py'))
    assert '_get_deepseek_key' in py, (
        "Fix 19 FAILED: api_simulation_analysis does not use _get_deepseek_key()"
    )
    assert "tomli" not in py, (
        "Fix 19 FAILED: Old tomli import still present in app.py"
    )
    print("PASS: Fix 19 — Simulation analysis uses shared _get_deepseek_key()")


# ============================================================
# FIX 20: Race condition — fetchSimAnalysisForPanel aborts old requests (Fix 8)
# ============================================================
def test_fix20_sim_analysis_abort_controller():
    """Fix 8: fetchSimAnalysisForPanel uses AbortController to prevent race."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    assert 'aiPanelAbortController' in js, (
        "Fix 20 FAILED: fetchSimAnalysisForPanel missing AbortController"
    )
    assert 'signal: signal' in js, (
        "Fix 20 FAILED: fetchSimAnalysisForPanel fetch call missing signal option"
    )
    print("PASS: Fix 20 — fetchSimAnalysisForPanel cancels pending requests via AbortController")


# ============================================================
# Integration tests
# ============================================================
def test_all_fixes_present_in_files():
    """Integration: verify all fix markers are present in source files."""
    js = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/js/dashboard.js'))
    css = read_file(os.path.join(PROJECT_ROOT, 'webapp/static/css/dashboard.css'))
    html = read_file(os.path.join(PROJECT_ROOT, 'webapp/templates/index.html'))

    checks = {
        'Fix 1': 'AI正在分析中...' in js,
        'Fix 2 CSS single .kpi-card-value': len(re.findall(r'\.kpi-card-value\s*\{', css)) == 1,
        'Fix 3 HTML .alert-icon': 'class="alert-icon"' in html,
        'Fix 3 JS .alert-icon': "'.alert-icon'" in js,
        'Fix 4 local mode message': 'LLM 模式专属功能' in js,
        'Fix 5 style injection': "ask-btn-hide-style" in js,
        'Fix 9 ROI icon outerHTML': "roiIcon.outerHTML" in js,
        'Fix 10 KPI gradients': 'linear-gradient' in css,
        'Fix 11 lock opaque': '#ffffff' in js,
        'Fix 12 grace': "grace: '5%'" in js,
    }

    for name, result in checks.items():
        assert result, f"Integration FAILED: {name} check failed"

    print("PASS: Integration — All fixes verified present")


# ============================================================
# Runner
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("5 Critical Fixes — Unit Test Suite")
    print("=" * 60)

    all_tests = [
        # Fix 1
        test_fix1_ai_panel_initial_text,
        # Fix 2
        test_fix2_css_no_duplicate_kpi_card_value,
        test_fix2_css_no_duplicate_kpi_card_sub,
        test_fix2_css_no_duplicate_kpi_card_ai_note,
        test_fix2_css_no_duplicate_color_bars,
        test_fix2_kpi_card_value_has_overflow_hidden,
        test_fix2_css_no_gap_zero_override,
        # Fix 3
        test_fix3_html_has_alert_icon_class,
        test_fix3_js_uses_alert_icon_selector,
        test_fix3_green_checkmark_rendered_for_healthy,
        # Fix 4
        test_fix4_local_mode_insight_not_loading,
        # Fix 5
        test_fix5_ask_btn_style_injection_in_local_mode,
        test_fix5_style_removed_in_llm_mode,
        test_fix5_mutation_observer_skips_in_local_mode,
        # Fix 6
        test_fix6_tray_bar_never_removed_on_empty,
        test_fix6_restore_does_not_remove_tray_tab,
        test_fix6_tray_bar_has_fixed_position,
        test_fix6_tray_tabs_show_minimized_state,
        test_fix6_close_window_removes_tray_when_no_windows_left,
        # Fix 7
        test_fix7_tray_bar_blue_theme,
        test_fix7_tray_tabs_blue_theme,
        # Fix 8
        test_fix8_local_mode_skips_ai_endpoints,
        test_fix8_local_mode_fallbacks_injected,
        # Fix 9
        test_fix9_html_roi_alert_has_alert_icon_class,
        test_fix9_roi_alert_icon_switched_on_healthy,
        test_fix9_roi_alert_for_each_covers_both_cards,
        # Fix 10
        test_fix10_kpi_card_gradient_backgrounds,
        test_fix10_kpi_card_border_top_preserved,
        # Fix 11
        test_fix11_insight_lock_overlay_fully_opaque,
        # Fix 12
        test_fix12_lag_chart_y_axis_auto_range,
        test_fix12_lag_chart_includes_original_r_values,
        test_fix12_lag_chart_grace_percent,
        test_fix12_lag_bar_chart_has_base_zero,
        # Fix 13 (Fix 1: KPI card text)
        test_fix13_kpi_card_sub_no_ellipsis,
        test_fix13_kpi_card_uniform_height,
        test_fix13_auto_shrink_min_12,
        # Fix 14 (Fix 2: No blue border on simulated cards)
        test_fix14_simulated_card_no_border_override,
        # Fix 15 (Fix 3: ROI round icon)
        test_fix15_roi_alert_icon_no_svg_polygon,
        # Fix 16 (Fix 4: Ask buttons)
        test_fix16_ask_btn_force_restore_in_llm_mode,
        test_fix16_adopt_suggestion_calls_bind_ask,
        test_fix16_mode_toggle_retry_bind_ask,
        # Fix 17 (Fix 5: Engine label)
        test_fix17_engine_label_deepseek_in_llm_mode,
        test_fix17_ai_insight_engine_tag,
        # Fix 18 (Fix 6: Lock button in sim mode)
        test_fix18_lock_button_in_sim_mode,
        # Fix 19 (Fix 7: Shared API key)
        test_fix19_sim_analysis_uses_shared_key,
        # Fix 20 (Fix 8: Race condition)
        test_fix20_sim_analysis_abort_controller,
        # Integration
        test_all_fixes_present_in_files,
    ]

    passed = 0
    for t in all_tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"\nFAIL: {t.__name__}")
            print(f"  {e}")

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{len(all_tests)} passed")

    if passed < len(all_tests):
        print(f"\n{len(all_tests) - passed} test(s) FAILED!")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED!")
