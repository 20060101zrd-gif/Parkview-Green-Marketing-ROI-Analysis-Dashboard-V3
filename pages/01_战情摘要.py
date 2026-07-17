"""
01 — 战情摘要
最高层级指挥中心：4 张核心 KPI 卡片 + 告警横幅 + 客群总览。
"""

import streamlit as st
import sys
import os

st.set_page_config(
    page_title="01 战情摘要",
    page_icon="📊",
    layout="wide",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import inject_global_css
from components.header import render_global_header
from components.kpi_cards import render_kpi_row, render_skeleton_row
from semantic_layer.metric_engine import MetricEngine

inject_global_css()
render_global_header()

if not st.session_state.get('data_loaded', False):
    st.warning("尚未加载数据，请先在主页上传 CSV 文件或确保 data/ 目录存在默认数据。")
    st.stop()

df_coupon = st.session_state.get('df_coupon_filtered', st.session_state.get('df_coupon'))
df_sales = st.session_state.get('df_sales_filtered', st.session_state.get('df_sales'))

if df_coupon is None or df_sales is None or df_coupon.empty:
    st.info("当前筛选范围内无数据，请放宽筛选条件。")
    st.stop()

engine = MetricEngine()
metrics = engine.compute_all(df_coupon, df_sales)

st.markdown("---")

# KPI 卡片行
st.markdown('<div class="section-title">核心指挥看板 — 关键业绩指标</div>', unsafe_allow_html=True)

render_kpi_row([
    {
        "title": "营销投资回报率",
        "value": f"{metrics['roi']:.1f}%",
        "subtitle": f"发券 {metrics['total_issued']:,} 张",
        "accent_color": "#10b981" if metrics['roi'] > 30 else ("#f59e0b" if metrics['roi'] > 10 else "#ef4444"),
    },
    {
        "title": "总销售额",
        "value": f"CNY {metrics['total_sales']:,.0f}",
        "subtitle": f"交易 {metrics['total_orders']:,} 笔",
        "accent_color": "#3b82f6",
    },
    {
        "title": "核销转化率",
        "value": f"{metrics['conversion_rate']:.2f}%",
        "subtitle": f"真实核销 {metrics['real_used']:,} 张",
        "accent_color": "#8b5cf6",
    },
    {
        "title": "会员贡献占比",
        "value": f"{metrics['member_contribution']:.1f}%",
        "subtitle": f"会员消费 CNY {metrics['member_sales']:,.0f}",
        "accent_color": "#ec4899",
    },
])

st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

# 告警横幅
structure = metrics.get('coupon_structure', {})
parking_share = structure.get('parking_share', 0)

alerts = []

if parking_share > 70:
    alerts.append({
        'severity': 'critical',
        'text': f'结构性告警: 停车券占发券总量 {parking_share:.0f}%，核销率极低，存在严重的资源错配，建议立即削减预算并重新分配。'
    })

if metrics['roi'] < 10:
    alerts.append({
        'severity': 'critical',
        'text': f'ROI 告警: 营销投资回报率仅 {metrics["roi"]:.1f}%，需立即审查投放策略。'
    })
elif metrics['roi'] < 30:
    alerts.append({
        'severity': 'warning',
        'text': f'ROI 预警: 营销投资回报率 {metrics["roi"]:.1f}%，利润空间承压，建议关注。'
    })

if metrics['conversion_rate'] < 1.0:
    alerts.append({
        'severity': 'warning',
        'text': f'转化率预警: 核销转化率仅 {metrics["conversion_rate"]:.2f}%，券激励强度可能不足。'
    })

if alerts:
    st.markdown('<div class="section-title">当前待处理告警</div>', unsafe_allow_html=True)
    for a in alerts:
        sev = a['severity']
        cls = f"alert-banner-{sev}"
        st.markdown(f'<div class="{cls}">{a["text"]}</div>', unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="alert-banner-info">'
        '未检测到关键告警。所有监控指标均在可接受范围内。'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

# 客群快速总览
cohort_data = metrics.get('cohort_data', [])
if cohort_data:
    st.markdown('<div class="section-title">客群概览 — 销售额 Top 5</div>', unsafe_allow_html=True)

    cols = st.columns(5)
    for i, c in enumerate(cohort_data[:5]):
        with cols[i]:
            rd_rate = c.get('redeem_rate', 0)
            rate_color = "#059669" if rd_rate >= 0.03 else ("#d97706" if rd_rate >= 0.01 else "#dc2626")
            st.markdown(f"""
            <div class="cohort-tile" style="text-align:center;">
                <div class="cohort-tile-label">{c['level'][:4]} / {c['age_group']}</div>
                <div class="cohort-tile-value" style="color:{rate_color};">{c['redeem_rate']:.1%}</div>
                <div class="cohort-tile-stat">核销率</div>
                <div class="cohort-tile-value" style="margin-top:4px;">CNY {c['atv']:,.0f}</div>
                <div class="cohort-tile-stat">客单价</div>
            </div>
            """, unsafe_allow_html=True)

# 底部
st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)
st.caption(
    f"数据范围: {len(df_coupon):,} 条发券记录 | {len(df_sales):,} 条销售记录 | "
    f"由度量值引擎 v1.0 生成"
)
