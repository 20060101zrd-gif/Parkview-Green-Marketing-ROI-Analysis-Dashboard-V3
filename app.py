"""
北京侨福芳草地 — 营销效能战情室
入口文件：本地运行或 Docker/Render 部署。
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.theme import inject_global_css
from data_engine.data_loader import load_and_clean_data
from components.filters import render_global_filters
from components.header import render_global_header, _brand_logo_base64

# ========================================
# 0. 页面全局配置
# ========================================
st.set_page_config(
    page_title="北京侨福芳草地 | 营销效能战情室",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========================================
# 1. 注入全局侨福绿大厂风设计系统
# ========================================
inject_global_css()

# ========================================
# 2. 侧边栏品牌区
# ========================================
logo_b64 = _brand_logo_base64(dark=True)
logo_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else ""
st.sidebar.markdown(f"""
<div style="padding:16px 0 8px 0;text-align:left;">
    <img src="{logo_src}" alt="Parkview Green 芳草地" style="height:36px;width:auto;object-fit:contain;max-width:100%;" />
    <div style="margin-top:6px;font-size:11px;color:#94a3b8;font-weight:400;">营销效能战情室</div>
</div>
""", unsafe_allow_html=True)

# ========================================
# 3. 数据加载
# ========================================
st.sidebar.header("数据源")

default_coupon = "data/BI_Dashboard_Ready_Data.csv"
default_sales = "data/销售查询.csv"

auto_loaded = False
if os.path.exists(default_coupon) and os.path.exists(default_sales):
    if 'df_coupon' not in st.session_state:
        with st.spinner("数据引擎启动中..."):
            try:
                df_coupon_clean, df_sales_clean = load_and_clean_data(
                    default_coupon, default_sales
                )
                st.session_state.df_coupon = df_coupon_clean
                st.session_state.df_sales = df_sales_clean
                st.session_state.data_loaded = True
                auto_loaded = True
            except Exception as e:
                st.sidebar.error(f"自动加载失败: {str(e)[:80]}")
else:
    st.sidebar.caption("未在 data/ 目录找到默认数据文件")

# 手动上传备用
if not auto_loaded or not st.session_state.get('data_loaded'):
    coupon_file = st.sidebar.file_uploader("上传发券数据 (CSV)", type=['csv'])
    sales_file = st.sidebar.file_uploader("上传销售数据 (CSV)", type=['csv'])

    if coupon_file is not None and sales_file is not None:
        with st.spinner("数据处理中..."):
            try:
                df_coupon_clean, df_sales_clean = load_and_clean_data(
                    coupon_file, sales_file
                )
                st.session_state.df_coupon = df_coupon_clean
                st.session_state.df_sales = df_sales_clean
                st.session_state.data_loaded = True
                st.sidebar.success("数据融合完成")
            except Exception as e:
                st.sidebar.error(f"加载失败: {str(e)[:100]}")
                st.session_state.data_loaded = False

# ========================================
# 4. 全局筛选器
# ========================================
if st.session_state.get('data_loaded'):
    df_coupon_clean = st.session_state.df_coupon
    df_sales_clean = st.session_state.df_sales

    df_coupon_f, df_sales_f = render_global_filters(df_coupon_clean, df_sales_clean)

    st.session_state.df_coupon_filtered = df_coupon_f
    st.session_state.df_sales_filtered = df_sales_f

    st.sidebar.success(f"筛选结果: {len(df_coupon_f):,} 条发券 | {len(df_sales_f):,} 条销售")
else:
    df_coupon_f = None
    df_sales_f = None

# ========================================
# 5. 全局导航栏
# ========================================
if st.session_state.get('data_loaded'):
    render_global_header()

# ========================================
# 6. 欢迎页（未加载数据时）
# ========================================
if not st.session_state.get('data_loaded'):
    st.markdown("""
    <div class="welcome-container">
        <div class="welcome-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2" style="vertical-align:middle;">
                <path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-7"/>
            </svg>
        </div>
        <div class="welcome-title">
            北京侨福芳草地 &middot; 营销效能战情室
        </div>
        <div class="welcome-subtitle">
            打通「发券 — 核销 — 消费」全链路，识别高 ROI 转化客群，优化营销资源配置。
        </div>
        <div class="welcome-hint">
            请在左侧边栏上传两份 CSV 数据文件，或将数据文件放入 <code style="color:#059669;background:#ecfdf5;padding:2px 6px;border-radius:4px;">data/</code> 目录自动加载。
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;padding:20px;color:#94a3b8;font-size:13px;">
        <p>页面导航: 01 战情摘要 | 02 KPI 总览 | 03 投入产出结构 | 04 趋势滞后分析 | 05 客群价值诊断 | 06 智能诊室</p>
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ========================================
# 7. 导航提示
# ========================================
if st.session_state.get('data_loaded'):
    st.caption(
        "使用顶部标签切换分析模块。左侧控制面板可调整时间范围与客群筛选，所有页面共享同一筛选状态。"
    )
