"""
全局筛选器: 时间范围 + 客群选择 + 书签系统。
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime


def render_global_filters(df_coupon, df_sales):
    """渲染侧边栏全局筛选器，返回过滤后的数据框。"""

    st.sidebar.markdown("---")
    st.sidebar.header("控制面板")

    # ---- 时间范围 ----
    min_date = df_coupon['create_time'].dt.date.min()
    max_date = df_coupon['create_time'].dt.date.max()

    selected_date = st.sidebar.date_input(
        "数据时间范围",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(selected_date) == 2:
        start_date, end_date = selected_date
    else:
        start_date, end_date = selected_date[0], selected_date[0]

    st.session_state['date_min_str'] = start_date.strftime('%Y-%m')
    st.session_state['date_max_str'] = end_date.strftime('%Y-%m')

    st.sidebar.markdown("---")

    # ---- 客群选择器 ----
    st.sidebar.subheader("客群筛选")
    st.sidebar.caption("选择需要聚焦的客群组合，默认包含全部。")

    ordered_ages = ['70前', '70后', '80后', '90后', '00后', '未知年龄']
    all_ages = [age for age in ordered_ages if age in df_coupon['age_group'].unique()]

    all_levels = ['平台会员', '绿意会员', '悦意会员', '菁英会员']

    # 构建客群统计
    cohort_stats = {}
    for lv in all_levels:
        for ag in all_ages:
            key = f"{ag} | {lv}"
            c = df_coupon[(df_coupon['age_group'] == ag) & (df_coupon['business_level'] == lv)]
            s = df_sales[(df_sales['age_group'] == ag) & (df_sales['business_level'] == lv)]
            if c.empty and s.empty:
                continue
            issued = len(c)
            redeemed = int((c['status_code'] == 1).sum()) if 'status_code' in c.columns else 0
            sales_amt = float(s['销售额'].sum()) if '销售额' in s.columns else 0
            cohort_stats[key] = {
                'issued': issued,
                'redeemed': redeemed,
                'sales': sales_amt,
                'redeem_rate': redeemed / issued if issued > 0 else 0,
            }

    cohort_options = sorted(cohort_stats.keys())
    cohort_labels = {}
    for k in cohort_options:
        ag, lv = k.split('|')
        stats = cohort_stats.get(k, {})
        rate = stats.get('redeem_rate', 0)
        cohort_labels[k] = f"{ag} / {lv}  [核销率: {rate:.1%}]"

    selected_cohorts = st.sidebar.multiselect(
        "选择客群",
        options=cohort_options,
        default=[],
        format_func=lambda x: cohort_labels.get(x, x),
        placeholder="全部客群 (点击筛选)...",
    )

    st.sidebar.markdown("---")

    # ---- 书签系统 ----
    st.sidebar.subheader("场景书签")

    bookmark_name = st.sidebar.text_input(
        "书签名称",
        placeholder="例如: 80后菁英高ROI客群",
        key="bookmark_name_input",
        label_visibility="collapsed",
    )

    if st.sidebar.button("保存当前视角", use_container_width=True):
        if bookmark_name.strip():
            if 'bookmarks' not in st.session_state:
                st.session_state.bookmarks = {}
            st.session_state.bookmarks[bookmark_name.strip()] = {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'cohorts': selected_cohorts,
                'saved_at': datetime.now().isoformat(),
            }
            st.sidebar.success(f"书签 '{bookmark_name}' 已保存。")
        else:
            st.sidebar.warning("请先输入书签名称。")

    if 'bookmarks' in st.session_state and st.session_state.bookmarks:
        saved = list(st.session_state.bookmarks.keys())
        load_bm = st.sidebar.selectbox(
            "加载书签",
            [""] + saved,
            format_func=lambda x: "— 选择 —" if x == "" else x,
        )
        if load_bm and load_bm in st.session_state.bookmarks:
            bm = st.session_state.bookmarks[load_bm]
            if st.sidebar.button(f"加载 '{load_bm}'", use_container_width=True):
                st.session_state['_load_start_date'] = pd.Timestamp(bm['start_date']).date()
                st.session_state['_load_end_date'] = pd.Timestamp(bm['end_date']).date()
                st.session_state['_load_cohorts'] = bm['cohorts']
                st.rerun()

    # ---- 执行筛选 ----
    final_age_filter = all_ages
    final_level_filter = all_levels

    if selected_cohorts:
        ages = set()
        levels = set()
        for c in selected_cohorts:
            ag, lv = c.split('|')
            ages.add(ag)
            levels.add(lv)
        final_age_filter = list(ages) if ages else all_ages
        final_level_filter = list(levels) if levels else all_levels

    mask_coupon = (
        (df_coupon['create_time'].dt.date >= start_date) &
        (df_coupon['create_time'].dt.date <= end_date) &
        (df_coupon['age_group'].isin(final_age_filter)) &
        (df_coupon['business_level'].isin(final_level_filter))
    )
    df_coupon_f = df_coupon[mask_coupon].copy()

    mask_sales = (
        (df_sales['销售时间'].dt.date >= start_date) &
        (df_sales['销售时间'].dt.date <= end_date) &
        (df_sales['age_group'].isin(final_age_filter)) &
        (df_sales['business_level'].isin(final_level_filter))
    )
    df_sales_f = df_sales[mask_sales].copy()

    return df_coupon_f, df_sales_f
