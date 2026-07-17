"""
04 — 营销趋势与滞后效应分析
时间序列双轴对比 + 滞后相关性 + 异常检测。
"""

import streamlit as st
import sys
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="04 趋势滞后分析",
    page_icon="📉",
    layout="wide",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import inject_global_css
from components.header import render_global_header
from components.kpi_cards import render_kpi_card
from ai_engine.anomaly_detector import AnomalyDetector

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

st.markdown('<div class="section-title">营销节奏与业绩滞后效应分析</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">观测营销投入与终端销售的联动关系，识别最优转化周期，定位异常波动点。</div>', unsafe_allow_html=True)

# 控制面板
col1, col2, col3, col4 = st.columns(4)
with col1:
    time_granularity = st.selectbox("时间粒度", ["月度", "周度"], index=0)
with col2:
    analysis_metric = st.selectbox("营销指标", ["发券量", "核销量"], index=0)
with col3:
    if time_granularity == "月度":
        lag_options = [0, 1, 2, 3, 6]
        lag_unit = "个月"
    else:
        lag_options = [0, 1, 2, 4, 8]
        lag_unit = "周"
    lag_period = st.selectbox(f"滞后周期 ({lag_unit})", lag_options, index=0)
with col4:
    all_levels = ["全部客群"] + sorted(df_coupon["business_level"].unique().tolist()) if 'business_level' in df_coupon.columns else ["全部客群"]
    selected_level = st.selectbox("会员等级筛选", all_levels, index=0)

# 数据准备
df_c = df_coupon.copy()
df_s = df_sales.copy()

if selected_level != "全部客群" and 'business_level' in df_c.columns:
    df_c = df_c[df_c["business_level"] == selected_level]
    df_s = df_s[df_s["business_level"] == selected_level]

if time_granularity == "月度":
    df_c['time_period'] = df_c['create_time'].dt.strftime('%Y-%m')
    df_s['time_period'] = df_s['销售时间'].dt.strftime('%Y-%m')
    df_c['sort_key'] = df_c['create_time'].dt.to_period('M').dt.to_timestamp()
    df_s['sort_key'] = df_s['销售时间'].dt.to_period('M').dt.to_timestamp()
else:
    df_c['iso_year'] = df_c['create_time'].dt.isocalendar().year
    df_c['iso_week'] = df_c['create_time'].dt.isocalendar().week
    df_c['time_period'] = df_c['iso_year'].astype(str) + "-W" + df_c['iso_week'].astype(str).str.zfill(2)
    df_c['sort_key'] = df_c['create_time'] - pd.to_timedelta(df_c['create_time'].dt.weekday, unit='D')
    df_s['iso_year'] = df_s['销售时间'].dt.isocalendar().year
    df_s['iso_week'] = df_s['销售时间'].dt.isocalendar().week
    df_s['time_period'] = df_s['iso_year'].astype(str) + "-W" + df_s['iso_week'].astype(str).str.zfill(2)
    df_s['sort_key'] = df_s['销售时间'] - pd.to_timedelta(df_s['销售时间'].dt.weekday, unit='D')

trend_coupon = df_c.groupby(['time_period', 'sort_key']).agg(
    issued_count=('coupon_record_id', 'count'),
    redeemed_count=('status_code', lambda x: (x == 1).sum())
).reset_index()

trend_sales = df_s.groupby(['time_period', 'sort_key'])['销售额'].sum().reset_index(name='sales_amount')

df_trend = pd.merge(trend_coupon, trend_sales, on=['time_period', 'sort_key'], how='outer').fillna(0)
df_trend = df_trend.sort_values('sort_key').reset_index(drop=True)

metric_col = 'issued_count' if analysis_metric == "发券量" else 'redeemed_count'
metric_name = f"{analysis_metric} (滞后 {lag_period} {lag_unit})"

# 相关性计算
def calc_lag_corr(lag):
    lagged = df_trend[metric_col].shift(lag)
    valid = pd.DataFrame({'lagged': lagged, 'sales': df_trend['sales_amount']}).dropna()
    if len(valid) < 3:
        return 0
    return valid['lagged'].corr(valid['sales'])

lag_corr_results = {lag: calc_lag_corr(lag) for lag in lag_options}
best_lag = max(lag_corr_results, key=lag_corr_results.get)
best_corr = lag_corr_results[best_lag]

df_trend['metric_lagged'] = df_trend[metric_col].shift(lag_period)
valid_data = df_trend[['metric_lagged', 'sales_amount']].dropna()
current_corr = valid_data['metric_lagged'].corr(valid_data['sales_amount']) if len(valid_data) >= 3 else 0

# 摘要卡片
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_kpi_card(
        f"累计{analysis_metric}", f"{int(df_trend[metric_col].sum()):,}",
        "周期内总量", accent_color="#3b82f6",
    )
with col2:
    render_kpi_card(
        "累计销售额", f"CNY {df_trend['sales_amount'].sum():,.0f}",
        "周期内总收入", accent_color="#10b981",
    )
with col3:
    total_iss = int(df_trend['issued_count'].sum())
    total_red = int(df_trend['redeemed_count'].sum())
    redeem_pct = total_red / total_iss * 100 if total_iss > 0 else 0
    render_kpi_card(
        "整体核销率", f"{redeem_pct:.1f}%",
        f"{total_red} / {total_iss} 张", accent_color="#8b5cf6",
    )
with col4:
    render_kpi_card(
        "当前相关性", f"{current_corr:.3f}",
        f"最优: 滞后 {best_lag} ({best_corr:.3f})", accent_color="#f59e0b",
    )

# 相关性洞察
if abs(current_corr) >= 0.7:
    st.success(f"滞后 {lag_period} {lag_unit} 时呈强正相关: {analysis_metric}对销售额具有较强预测力。")
elif abs(current_corr) >= 0.4:
    st.info(f"滞后 {lag_period} {lag_unit} 时呈中等正相关: {analysis_metric}对销售有一定拉动作用。")
else:
    st.warning(f"滞后 {lag_period} {lag_unit} 时相关性较弱: 业绩波动受其他因素影响更大。")

# 双轴趋势图
fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(
    go.Bar(
        x=df_trend['time_period'],
        y=df_trend['metric_lagged'],
        name=metric_name,
        marker_color='#3b82f6',
        opacity=0.75,
        text=df_trend['metric_lagged'].apply(lambda x: int(x) if pd.notna(x) and x > 0 else ""),
        textposition='outside',
        textfont=dict(color='#64748b', size=10),
    ),
    secondary_y=False,
)

fig.add_trace(
    go.Scatter(
        x=df_trend['time_period'],
        y=df_trend['sales_amount'],
        name="销售额 (CNY)",
        mode='lines+markers',
        line=dict(color='#ef4444', width=3),
        marker=dict(size=8, color='#ef4444'),
    ),
    secondary_y=True,
)

fig.update_layout(
    title_text=f"{time_granularity}{analysis_metric} vs 销售业绩对比",
    title_font=dict(color='#0f172a', size=16),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#334155')),
    margin=dict(l=20, r=20, t=60, b=20),
    font=dict(color='#334155'),
)

fig.update_yaxes(title_text=f"{analysis_metric} (张)", secondary_y=False, showgrid=False, rangemode='tozero', title_font=dict(color='#334155'), tickfont=dict(color='#64748b'))
fig.update_yaxes(title_text="销售额 (CNY)", secondary_y=True, showgrid=True, gridcolor='rgba(0,0,0,0.06)', rangemode='tozero', title_font=dict(color='#334155'), tickfont=dict(color='#64748b'))
fig.update_xaxes(tickangle=-45, tickfont=dict(size=10, color='#64748b'), showgrid=False)

st.plotly_chart(fig, use_container_width=True)

# 异常检测
st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)
st.markdown("##### 异常波动检测")

detector = AnomalyDetector(contamination=0.1)
anomaly_result = detector.detect(df_trend, 'sales_amount', 'time_period')

if anomaly_result['anomaly_count'] > 0:
    st.markdown(f"检测到 **{anomaly_result['anomaly_count']}** 个异常周期:")
    anomaly_df = pd.DataFrame(anomaly_result['anomalies'])
    anomaly_df['销售额'] = anomaly_df['value'].apply(lambda x: f"CNY {x:,.0f}")
    anomaly_df = anomaly_df.rename(columns={
        'time': '周期', 'deviation_sigma': '偏离度 (sigma)',
        'direction': '方向', '销售额': '销售额',
    })
    anomaly_df['方向'] = anomaly_df['方向'].map({'high': '异常偏高', 'low': '异常偏低'})
    st.dataframe(
        anomaly_df[['周期', '销售额', '偏离度 (sigma)', '方向']],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("当前数据范围内未检测到显著异常波动。")

# 技术调试面板
with st.expander("技术明细: 原始数据与全量相关性矩阵"):
    tab1, tab2, tab3 = st.tabs(["聚合数据", "相关性矩阵", "散点图"])
    with tab1:
        st.dataframe(df_trend[['time_period', metric_col, 'metric_lagged', 'sales_amount']], use_container_width=True, hide_index=True)
    with tab2:
        corr_df = pd.DataFrame({
            f"滞后 ({lag_unit})": lag_options,
            "相关系数": [round(lag_corr_results[lag], 4) for lag in lag_options]
        })
        st.dataframe(corr_df, use_container_width=True, hide_index=True)
    with tab3:
        fig_scatter = go.Figure()
        fig_scatter.add_trace(go.Scatter(
            x=valid_data['metric_lagged'], y=valid_data['sales_amount'],
            mode='markers', name='数据点', marker=dict(color='#3b82f6', size=8, opacity=0.7),
        ))
        if len(valid_data) >= 3:
            z = np.polyfit(valid_data['metric_lagged'], valid_data['sales_amount'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(valid_data['metric_lagged'].min(), valid_data['metric_lagged'].max(), 100)
            fig_scatter.add_trace(go.Scatter(
                x=x_line, y=p(x_line), mode='lines',
                name=f'拟合线 (R={current_corr:.3f})', line=dict(color='#ef4444', width=2, dash='dash')
            ))
        fig_scatter.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title=f"{analysis_metric} (滞后 {lag_period} {lag_unit})",
            yaxis_title="销售额 (CNY)",
            font=dict(color='#334155'),
            margin=dict(l=20, r=20, t=20, b=20),
        )
        fig_scatter.update_xaxes(showgrid=True, gridcolor='rgba(0,0,0,0.06)')
        fig_scatter.update_yaxes(showgrid=True, gridcolor='rgba(0,0,0,0.06)')
        st.plotly_chart(fig_scatter, use_container_width=True)
