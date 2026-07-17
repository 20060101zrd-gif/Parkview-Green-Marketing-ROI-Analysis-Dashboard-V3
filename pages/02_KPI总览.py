"""
02 — KPI 总览
详细 KPI 分解，含同比环比对比。
"""

import streamlit as st
import sys
import os

st.set_page_config(
    page_title="02 KPI 总览",
    page_icon="📈",
    layout="wide",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import inject_global_css
from components.header import render_global_header
from components.kpi_cards import render_kpi_card, render_kpi_row
from components.export_utils import csv_download_button
from semantic_layer.metric_engine import MetricEngine
from semantic_layer.comparison import ComparisonEngine

inject_global_css()
render_global_header()

if not st.session_state.get('data_loaded', False):
    st.warning("尚未加载数据。")
    st.stop()

df_coupon = st.session_state.get('df_coupon_filtered', st.session_state.get('df_coupon'))
df_sales = st.session_state.get('df_sales_filtered', st.session_state.get('df_sales'))

if df_coupon is None or df_sales is None or df_coupon.empty:
    st.info("当前筛选范围内无数据。")
    st.stop()

engine = MetricEngine()
metrics = engine.compute_all(df_coupon, df_sales)

st.markdown('<div class="section-title">KPI 指标详情总览</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">涵盖发券、核销、销售、会员贡献等全维度关键指标。</div>', unsafe_allow_html=True)

# 第一行: 量级指标
st.markdown("##### 量级指标")
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_kpi_card(
        "总发券量", f"{metrics['total_issued']:,}",
        "累计发放优惠券", accent_color="#3b82f6",
    )
with col2:
    render_kpi_card(
        "真实核销量", f"{metrics['real_used']:,}",
        f"核销转化率: {metrics['conversion_rate']:.2f}%", accent_color="#8b5cf6",
    )
with col3:
    render_kpi_card(
        "总交易笔数", f"{metrics['total_orders']:,}",
        "销售侧订单数", accent_color="#ec4899",
    )
with col4:
    render_kpi_card(
        "整体核销率", f"{metrics['redeem_rate']:.2f}%",
        "全量券使用率", accent_color="#f59e0b",
    )

st.markdown("---")

# 第二行: 收入与价值指标
st.markdown("##### 收入与价值指标")
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_kpi_card(
        "总销售额", f"CNY {metrics['total_sales']:,.0f}",
        "全业态营业总收入", accent_color="#10b981",
    )
with col2:
    render_kpi_card(
        "整体客单价", f"CNY {metrics['aov']:,.0f}",
        "笔均消费金额", accent_color="#3b82f6",
    )
with col3:
    render_kpi_card(
        "会员消费总额", f"CNY {metrics['member_sales']:,.0f}",
        f"占大盘: {metrics['member_contribution']:.1f}%", accent_color="#8b5cf6",
    )
with col4:
    render_kpi_card(
        "营销投资回报率", f"{metrics['roi']:.1f}%",
        "投入产出比", accent_color="#10b981" if metrics['roi'] > 30 else "#ef4444",
    )

st.markdown("---")

# 第三行: 营销杠杆指标
st.markdown("##### 营销杠杆指标")
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_kpi_card(
        "券带动估算销售额", f"CNY {metrics['estimated_coupon_sales']:,.0f}",
        "核销量 x 客单价", accent_color="#3b82f6",
    )
with col2:
    render_kpi_card(
        "发券动销渗透率", f"{metrics['coupon_leverage']:.4f}%",
        "券带动销售占总额比例", accent_color="#f59e0b",
    )
with col3:
    coupon_structure = metrics.get('coupon_structure', {})
    parking = coupon_structure.get('parking_share', 0)
    render_kpi_card(
        "停车券占比", f"{parking:.1f}%",
        "占发券总量比例", accent_color="#ef4444" if parking > 70 else "#64748b",
    )
with col4:
    render_kpi_card(
        "数据规模", f"{len(df_coupon):,} / {len(df_sales):,}",
        "发券 | 销售记录条数", accent_color="#64748b",
    )

st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

# 导出
with st.expander("导出 KPI 报表"):
    import pandas as pd
    rows = [
        {"指标": "总发券量", "数值": metrics['total_issued'], "单位": "张"},
        {"指标": "真实核销量", "数值": metrics['real_used'], "单位": "张"},
        {"指标": "核销转化率", "数值": f"{metrics['conversion_rate']:.2f}", "单位": "%"},
        {"指标": "总销售额", "数值": f"{metrics['total_sales']:,.0f}", "单位": "CNY"},
        {"指标": "客单价", "数值": f"{metrics['aov']:,.0f}", "单位": "CNY"},
        {"指标": "会员贡献占比", "数值": f"{metrics['member_contribution']:.1f}", "单位": "%"},
        {"指标": "投资回报率", "数值": f"{metrics['roi']:.1f}", "单位": "%"},
        {"指标": "动销渗透率", "数值": f"{metrics['coupon_leverage']:.4f}", "单位": "%"},
        {"指标": "整体核销率", "数值": f"{metrics['redeem_rate']:.2f}", "单位": "%"},
    ]
    csv_download_button(pd.DataFrame(rows), "kpi_report.csv", "下载 KPI 报表 (CSV)")
