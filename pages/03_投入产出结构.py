"""
03 — 投入产出结构拆解
券种结构 vs 业态业绩结构对比分析。
"""

import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="03 投入产出结构",
    page_icon="🎯",
    layout="wide",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import inject_global_css
from components.header import render_global_header
from components.export_utils import csv_download_button

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

st.markdown('<div class="section-title">营销投入资源 vs 销售产出业绩结构拆解</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">对照分析"钱花在哪"与"钱从哪来"，辅助营销资源结构优化决策。</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

# ---- 券种结构 (环形图) ----
with col1:
    st.markdown("##### 营销投入分配 (券种发行占比)")

    if 'coupon_type' in df_coupon.columns:
        coupon_counts = df_coupon['coupon_type'].value_counts().reset_index()
        coupon_counts.columns = ['券种', '数量']
        total = coupon_counts['数量'].sum()

        coupon_name_map = {
            'daily_parking_coupon': '日常停车券',
            'user_exchange': '用户兑换券',
            'activity_coupon': '活动券',
            'parking_coupon': '停车券',
            'voucher': '代金券',
            'cash_coupon': '现金券',
            'discount_coupon': '折扣券',
        }
        coupon_counts['券种'] = coupon_counts['券种'].map(coupon_name_map).fillna(coupon_counts['券种'])

        top_type = coupon_counts.iloc[0]
        top_ratio = top_type['数量'] / total * 100

        fig1 = px.pie(
            coupon_counts,
            values='数量',
            names='券种',
            hole=0.45,
            color_discrete_sequence=px.colors.sequential.Blues_r,
        )
        fig1.update_traces(textposition='inside', textinfo='percent+label')
        fig1.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#334155'),
            margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False,
        )
        st.plotly_chart(fig1, use_container_width=True)

        st.caption(
            f"投入集中度分析: '{top_type['券种']}' 占发券总量 {top_ratio:.1f}%，"
            f"其余 {len(coupon_counts)-1} 个券种合计仅占 {100-top_ratio:.1f}%。"
        )
    else:
        st.info("当前数据 schema 中不存在券种字段。")

# ---- 业态结构 (条形图) ----
with col2:
    st.markdown("##### 销售业绩来源 (核心业态销售额排名)")

    if '业态' in df_sales.columns:
        sales_cat = df_sales.groupby('业态')['销售额'].sum().reset_index()
        sales_cat = sales_cat.sort_values('销售额', ascending=True)

        fig2 = px.bar(
            sales_cat,
            x='销售额',
            y='业态',
            orientation='h',
            text_auto='.2s',
            color='销售额',
            color_continuous_scale='Reds',
        )
        fig2.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#334155'),
            xaxis_title="销售额 (CNY)",
            yaxis_title="",
            coloraxis_showscale=False,
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

        top_cat = sales_cat.iloc[-1]
        cat_total = sales_cat['销售额'].sum()
        st.caption(
            f"业绩集中度: '{top_cat['业态']}' 贡献销售额 CNY {top_cat['销售额']:,.0f}，"
            f"占大盘 {top_cat['销售额']/cat_total*100:.1f}%。"
        )
    else:
        st.info("当前数据 schema 中不存在业态字段。")

st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

# 明细展开
st.markdown("##### 明细数据")

tab1, tab2 = st.tabs(["券种明细", "业态明细"])

with tab1:
    if 'coupon_type' in df_coupon.columns:
        coupon_detail = df_coupon.groupby('coupon_type').agg(
            发券量=('coupon_record_id', 'count'),
            核销量=('status_code', lambda x: (x == 1).sum()),
        ).reset_index()
        coupon_detail['券种'] = coupon_detail['coupon_type'].map(coupon_name_map).fillna(coupon_detail['coupon_type'])
        coupon_detail['核销率'] = (coupon_detail['核销量'] / coupon_detail['发券量'] * 100).round(2)
        coupon_detail = coupon_detail.sort_values('发券量', ascending=False)
        display = coupon_detail[['券种', '发券量', '核销量', '核销率']]
        display['核销率'] = display['核销率'].apply(lambda x: f"{x:.2f}%")
        st.dataframe(display, use_container_width=True, hide_index=True)
        csv_download_button(display, "coupon_type_detail.csv", "下载")
    else:
        st.info("券种明细不可用。")

with tab2:
    if '业态' in df_sales.columns:
        cat_detail = df_sales.groupby('业态').agg(
            销售额=('销售额', 'sum'),
            订单数=('科创编号', 'count'),
            笔均价=('销售额', 'mean'),
        ).reset_index()
        cat_detail = cat_detail.sort_values('销售额', ascending=False)
        cat_detail['销售额'] = cat_detail['销售额'].apply(lambda x: f"CNY {x:,.0f}")
        cat_detail['笔均价'] = cat_detail['笔均价'].apply(lambda x: f"CNY {x:,.0f}")
        st.dataframe(cat_detail, use_container_width=True, hide_index=True)
        csv_download_button(cat_detail, "category_detail.csv", "下载")
    else:
        st.info("业态明细不可用。")
