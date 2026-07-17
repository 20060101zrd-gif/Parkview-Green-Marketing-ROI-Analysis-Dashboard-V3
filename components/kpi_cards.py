"""
KPI Card components — Parkview Green enterprise BI style.
亮色大厂风设计系统：白色卡片 + 顶部色条 + 简洁排版。
"""

import streamlit as st


def render_kpi_card(
    title: str,
    value: str,
    subtitle: str = "",
    change_pct: float = None,
    accent_color: str = "#10b981",
    icon_html: str = "",
):
    """
    Render a single enterprise KPI card.

    Args:
        title: Card label (e.g. "Marketing ROI")
        value: Main value (e.g. "42.3%")
        subtitle: Secondary line (e.g. "vs. last month")
        change_pct: Optional percentage change (positive = green up, negative = red down)
        accent_color: Hex color for the top accent stripe
        icon_html: Optional inline SVG or Unicode icon
    """
    change_html = ""
    if change_pct is not None:
        if change_pct >= 0:
            change_html = (
                f'<span class="kpi-card-change-up">'
                f'&#9650; {abs(change_pct):.1f}%</span>'
            )
        else:
            change_html = (
                f'<span class="kpi-card-change-down">'
                f'&#9660; {abs(change_pct):.1f}%</span>'
            )

    html = f"""
    <div class="kpi-glass-card" style="--card-accent: {accent_color};">
        <div class="kpi-card-glow" style="
            background: radial-gradient(circle, {accent_color}15, transparent 70%);
        "></div>
        <div style="position:absolute;top:0;left:0;right:0;height:3px;
            background:{accent_color};
            border-radius:12px 12px 0 0;
        "></div>
        <div class="kpi-card-title">
            {icon_html} {title}
        </div>
        <div class="kpi-card-value">
            {value}
        </div>
        <div class="kpi-card-sub">
            {subtitle} &nbsp;{change_html}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_kpi_row(cards: list):
    """
    Render a row of KPI cards.

    Args:
        cards: List of dicts with keys:
            - title, value, subtitle (optional), change_pct (optional)
            - accent_color (optional, default "#10b981")
    """
    cols = st.columns(len(cards))
    for i, card in enumerate(cards):
        with cols[i]:
            render_kpi_card(
                title=card.get("title", ""),
                value=card.get("value", ""),
                subtitle=card.get("subtitle", ""),
                change_pct=card.get("change_pct"),
                accent_color=card.get("accent_color", "#10b981"),
                icon_html=card.get("icon_html", ""),
            )


def render_skeleton_card():
    """Render a placeholder skeleton card during data loading."""
    html = """
    <div class="kpi-glass-card skeleton" style="height:120px;">
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_skeleton_row(n: int = 4):
    """Render N skeleton placeholder cards."""
    cols = st.columns(n)
    for col in cols:
        with col:
            render_skeleton_card()
