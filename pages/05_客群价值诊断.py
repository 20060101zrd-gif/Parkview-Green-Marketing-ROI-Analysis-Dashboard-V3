"""
05 — 客群价值诊断
跨系统客群分层: 四象限自动标记 + KMeans 聚类。
"""

import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="05 客群价值诊断",
    page_icon="👥",
    layout="wide",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import inject_global_css
from components.header import render_global_header
from components.export_utils import csv_download_button
from ai_engine.cohort_clustering import CohortClusterer

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

st.markdown('<div class="section-title">客群价值诊断与投入产出对标</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">跨系统定位高 ROI 转化客群与券效耗损客群，支撑营销资源精准投放与客群精细化运营。</div>', unsafe_allow_html=True)

# 分层规则说明
st.markdown("""
| 标签 | 客群类型 | 核心判定规则 | 运营建议 |
|:---|:---|:---|:---|
| <span style="color:#ef4444;">RED</span> | 券效耗损型 | 人均领券 >= 5 张 且 客单价 < CNY 200 | 熔断止损，缩减投放 |
| <span style="color:#f59e0b;">GOLD</span> | 自然高价值型 | 客单价 >= CNY 1,000 且 核销率 < 2% | 重点维护，侧重留存 |
| <span style="color:#10b981;">GREEN</span> | 高 ROI 转化型 | 核销率 >= 1% 且 客单价 >= CNY 500 | 加大倾斜，放大杠杆 |
| <span style="color:#64748b;">GRAY</span> | 常规基石型 | 无显著特征的基础人群 | 常态化运营，稳步提升 |
""", unsafe_allow_html=True)

# 构建客群聚合
if 'business_level' not in df_coupon.columns or 'age_group' not in df_coupon.columns:
    st.warning("缺少必要字段 (会员等级、年龄段)，无法完成客群诊断。")
    st.stop()

df_c_agg = df_coupon.groupby(['business_level', 'age_group']).agg(
    总发券量=('coupon_record_id', 'count'),
    核销量=('status_code', lambda x: (x == 1).sum()),
    发券人数=('userid', 'nunique'),
).reset_index()
df_c_agg['人均领券'] = (df_c_agg['总发券量'] / df_c_agg['发券人数'].replace(0, 1)).round(1)
df_c_agg['核销率'] = df_c_agg['核销量'] / df_c_agg['总发券量'].replace(0, 1)

df_s_agg = df_sales.groupby(['business_level', 'age_group']).agg(
    总销售额=('销售额', 'sum'),
    订单数=('科创编号', 'count'),
    消费人数=('电话', 'nunique'),
).reset_index()
df_s_agg['客单价'] = (df_s_agg['总销售额'] / df_s_agg['订单数'].replace(0, 1)).round(0)
df_s_agg['消费频次'] = (df_s_agg['订单数'] / df_s_agg['消费人数'].replace(0, 1)).round(1)

cohort_df = pd.merge(df_c_agg, df_s_agg, on=['business_level', 'age_group'], how='outer').fillna(0)
cohort_df = cohort_df[(cohort_df['总发券量'] > 0) | (cohort_df['总销售额'] > 0)]

# 自动标签
def tag_cohort(row):
    avg_cpn = float(row.get('人均领券', 0))
    rd_rate = float(row.get('核销率', 0))
    atv = float(row.get('客单价', 0))

    if avg_cpn >= 5 and atv < 200:
        return 'RED — 券效耗损型'
    elif atv >= 1000 and rd_rate < 0.02:
        return 'GOLD — 自然高价值型'
    elif rd_rate >= 0.01 and atv >= 500:
        return 'GREEN — 高ROI转化型'
    else:
        return 'GRAY — 常规基石型'

cohort_df['诊断标签'] = cohort_df.apply(tag_cohort, axis=1)

color_map = {
    'RED — 券效耗损型': '#ef4444',
    'GOLD — 自然高价值型': '#f59e0b',
    'GREEN — 高ROI转化型': '#10b981',
    'GRAY — 常规基石型': '#64748b',
}
cohort_df['标签颜色'] = cohort_df['诊断标签'].map(color_map)

# KMeans 聚类分析
st.markdown("##### KMeans 聚类分析 (算法自动分段)")

feature_cols = ['人均领券', '核销率', '客单价']
available_features = [c for c in feature_cols if c in cohort_df.columns]

if len(available_features) >= 2:
    n_clusters = min(4, max(2, len(cohort_df) // 2))
    clusterer = CohortClusterer(n_clusters=n_clusters)
    cohort_clustered = clusterer.cluster(cohort_df.copy(), available_features)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig_cluster = go.Figure()
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
        for cluster_id in sorted(cohort_clustered['cluster'].unique()):
            subset = cohort_clustered[cohort_clustered['cluster'] == cluster_id]
            sales_numeric = pd.to_numeric(subset['总销售额'], errors='coerce').fillna(0)
            max_sales = sales_numeric.max()
            bubble_size = (sales_numeric / max_sales * 40).clip(lower=15) if max_sales > 0 else 20
            fig_cluster.add_trace(go.Scatter(
                x=subset['客单价'],
                y=subset['核销率'] * 100,
                mode='markers+text',
                name=subset['cluster_label'].iloc[0] if 'cluster_label' in subset.columns else f'聚类 {cluster_id+1}',
                text=subset.apply(lambda r: f"{r['business_level']}/{r['age_group']}", axis=1),
                textposition='top center',
                textfont=dict(size=10),
                marker=dict(
                    size=bubble_size,
                    opacity=0.75,
                    color=colors[cluster_id % len(colors)],
                ),
            ))
        fig_cluster.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title="客单价 (CNY)",
            yaxis_title="核销率 (%)",
            font=dict(color='#334155'),
            legend=dict(font=dict(color='#334155')),
            margin=dict(l=20, r=20, t=20, b=20),
        )
        fig_cluster.update_xaxes(showgrid=True, gridcolor='rgba(0,0,0,0.06)')
        fig_cluster.update_yaxes(showgrid=True, gridcolor='rgba(0,0,0,0.06)')
        st.plotly_chart(fig_cluster, use_container_width=True)

    with col2:
        profiles = clusterer.get_cluster_profiles(cohort_clustered, available_features)
        for cid, profile in profiles.items():
            st.markdown(f"**{profile.get('label', f'聚类 {cid+1}')}** ({profile['size']} 个客群)")
            st.caption(
                f"均客单价: CNY {profile.get('客单价_mean', 0):,.0f} | "
                f"均核销率: {profile.get('核销率_mean', 0):.2%}"
            )
else:
    st.info("特征列不足，无法执行 KMeans 聚类。至少需要 2 个数值型特征。")

st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

# 客群明细表
st.markdown("##### 客群诊断明细表")

display_cols = [
    'business_level', 'age_group',
    '发券人数', '人均领券', '核销率',
    '消费人数', '客单价', '总销售额',
    '诊断标签',
]
display_cols = [c for c in display_cols if c in cohort_df.columns]

display_df = cohort_df[display_cols].sort_values('总销售额', ascending=False).reset_index(drop=True)

column_rename = {
    'business_level': '会员等级',
    'age_group': '世代人群',
    '发券人数': '发券人数',
    '人均领券': '人均领券',
    '核销率': '核销率',
    '消费人数': '消费人数',
    '客单价': '客单价',
    '总销售额': '总销售额',
    '诊断标签': '诊断标签',
}

def style_tag(val):
    color = color_map.get(val, '#64748b')
    return f'color: {color}; font-weight: 600;'

display_df_renamed = display_df.rename(columns=column_rename)

if '诊断标签' in display_df_renamed.columns:
    styled = display_df_renamed.style.format({
        '核销率': '{:.2%}',
        '客单价': 'CNY {:,.0f}',
        '总销售额': 'CNY {:,.0f}',
        '人均领券': '{:.1f}',
    }).map(style_tag, subset=['诊断标签'])
else:
    styled = display_df_renamed.style.format({
        '核销率': '{:.2%}',
        '客单价': 'CNY {:,.0f}',
        '总销售额': 'CNY {:,.0f}',
    })

st.dataframe(styled, use_container_width=True, height=430)

csv_download_button(display_df_renamed, "cohort_diagnosis.csv", "下载客群诊断报告")
