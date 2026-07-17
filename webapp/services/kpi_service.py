"""
KPI Service — all metric computations.
Pure functions; no Flask dependency.
"""
import numpy as np
import pandas as pd


def compute_all_kpis(df_c, df_s):
    """Compute full KPI set from filtered coupon + sales DataFrames.

    ROI NOTE: Real marketing cost data (coupon face value, subsidy amount)
    is not available in the source CSVs. We estimate cost per coupon by type
    based on business-domain assumptions (parking ~20 CNY, exchange ~50 CNY, etc.).
    This is an ESTIMATED metric for trend reference only, not a precise financial figure.
    """
    total_issued = len(df_c)
    real_used = int((df_c['status_code'] == 1).sum())
    conversion_rate = (real_used / total_issued * 100) if total_issued > 0 else 0

    total_sales = float(df_s['销售额'].sum())
    total_orders = len(df_s)
    aov = total_sales / total_orders if total_orders > 0 else 0

    member_mask = df_s['business_level'] != '平台会员'
    member_sales = float(df_s.loc[member_mask, '销售额'].sum()) if 'business_level' in df_s.columns else 0
    member_contribution = (member_sales / total_sales * 100) if total_sales > 0 else 0

    # Estimated coupon-driven sales (redeemed count × AOV — rough proxy)
    estimated_coupon_sales = real_used * aov
    coupon_leverage = (estimated_coupon_sales / total_sales * 100) if total_sales > 0 else 0

    # Estimated cost: per-coupon-type cost assumptions (CNY)
    # Based on typical commercial-complex coupon economics:
    #   parking coupon ≈ 20 CNY, exchange/activity coupon ≈ 50 CNY,
    #   others ≈ 30 CNY default
    COST_PER_TYPE = {
        'daily_parking_coupon': 40,
        'consumption_parking_coupon': 50,
        'upgradelevel_parking_coupon': 50,
        'user_exchange': 80,
    }
    DEFAULT_COST = 50  # fallback for unknown coupon types

    if 'coupon_type' in df_c.columns and not df_c.empty:
        type_counts = df_c['coupon_type'].value_counts()
        estimated_cost = sum(
            int(type_counts.get(ct, 0)) * COST_PER_TYPE.get(ct, DEFAULT_COST)
            for ct in type_counts.index
        )
    else:
        estimated_cost = real_used * DEFAULT_COST

    roi = ((estimated_coupon_sales - estimated_cost) / estimated_cost * 100) if estimated_cost > 0 else 0

    return {
        'total_issued': total_issued,
        'real_used': real_used,
        'conversion_rate': round(conversion_rate, 2),
        'total_sales': round(total_sales, 2),
        'total_orders': total_orders,
        'aov': round(aov, 2),
        'member_sales': round(member_sales, 2),
        'member_contribution': round(member_contribution, 2),
        'estimated_coupon_sales': round(estimated_coupon_sales, 2),
        'coupon_leverage': round(coupon_leverage, 4),
        'estimated_cost': round(estimated_cost, 2),
        'roi': round(roi, 2),
        'roi_note': '估算值，基于券种均成本假设，仅供趋势参考',
        'total_redeemed': real_used,
        'redeem_rate': round(real_used / total_issued * 100, 2) if total_issued > 0 else 0,
    }


def compute_coupon_structure(df_c):
    """Coupon type distribution for donut charts."""
    if df_c.empty or 'coupon_type' not in df_c.columns:
        return []
    counts = df_c['coupon_type'].value_counts().to_dict()
    total = len(df_c)
    color_map = {
        'daily_parking_coupon': {'name': '日常停车券', 'color': '#10b981'},
        'parking_coupon': {'name': '停车券', 'color': '#10b981'},
        'user_exchange': {'name': '用户兑换券', 'color': '#0ea5e9'},
        'consumption_parking_coupon': {'name': '消费停车券', 'color': '#3b82f6'},
        'upgradelevel_parking_coupon': {'name': '升级停车券', 'color': '#8b5cf6'},
    }
    default_colors = ['#ec4899', '#f59e0b', '#06b6d4', '#f97316']
    structure = []
    for idx, (ctype, cnt) in enumerate(sorted(counts.items(), key=lambda x: -x[1])):
        info = color_map.get(ctype, {})
        structure.append({
            'name': info.get('name', ctype),
            'count': int(cnt),
            'pct': round(cnt / total * 100, 1),
            'color': info.get('color', default_colors[idx % len(default_colors)]),
        })
    return structure


def compute_cohort_data(df_c, df_s):
    """Cross-tab cohort analysis with GREEN/GOLD/RED/GRAY tags."""
    cohorts = []
    # Include ALL unique (level, age) combos from BOTH tables to avoid missing groups
    c_pairs = set(zip(df_c['business_level'], df_c['age_group']))
    s_pairs = set(zip(df_s['business_level'], df_s['age_group']))
    all_pairs = c_pairs | s_pairs  # Union — don't miss sales-only or coupon-only groups

    for lv, ag in sorted(all_pairs):
        c = df_c[(df_c['business_level'] == lv) & (df_c['age_group'] == ag)]
        s = df_s[(df_s['business_level'] == lv) & (df_s['age_group'] == ag)]
        if c.empty and s.empty:
            continue
        issued = len(c)
        redeemed = int((c['status_code'] == 1).sum())
        sales_amt = float(s['销售额'].sum())
        orders = len(s)
        atv = sales_amt / orders if orders > 0 else 0
        redeem_r = (redeemed / issued * 100) if issued > 0 else 0
        consumers = s['电话'].nunique()
        # For avg_cpn: use issued_users from coupon table, fallback to consumers from sales
        issued_users = c['userid'].nunique() if 'userid' in c.columns and not c.empty else 0
        effective_people = max(1, issued_users, consumers)
        avg_cpn = round(issued / effective_people, 2)

        # Tag logic: zero-sales + high coupon = RED (pure drain)
        if issued > 0 and sales_amt == 0 and avg_cpn >= 2:
            tag = 'RED'
        elif redeem_r >= 0.5 and atv >= 300:
            tag = 'GREEN'
        elif atv >= 800 and redeem_r < 1:
            tag = 'GOLD'
        elif avg_cpn >= 2 and atv < 500:
            tag = 'RED'
        else:
            tag = 'GRAY'

        cohorts.append({
            'level': lv, 'age_group': ag, 'name': f'{lv} / {ag}',
            'issued': issued, 'redeemed': redeemed,
            'sales': round(sales_amt, 2), 'orders': orders,
            'atv': round(atv, 2), 'redeem_rate': round(redeem_r, 2),
            'avg_coupons': avg_cpn, 'tag': tag, 'consumers': consumers,
            'issued_users': issued_users,
        })

    # Data integrity check
    total_people = sum(c.get('issued_users', 0) or c.get('consumers', 0) or 0 for c in cohorts)
    tag_counts = {'GREEN': 0, 'GOLD': 0, 'RED': 0, 'GRAY': 0}
    for c in cohorts:
        tag_counts[c['tag']] = tag_counts.get(c['tag'], 0) + (c.get('issued_users', 0) or c.get('consumers', 0) or 0)
    tag_total = sum(tag_counts.values())
    if total_people > 0 and abs(tag_total - total_people) / total_people > 0.05:
        print(f'[Cohort Integrity] WARNING: tag sum ({tag_total}) != total people ({total_people}), diff={abs(tag_total - total_people)}')

    return sorted(cohorts, key=lambda x: x['sales'], reverse=True)


def compute_cohort_detail(df_c, df_s):
    """Detailed cohort table (matches Streamlit page 05)."""
    c_agg = df_c.groupby(['business_level', 'age_group']).agg(
        总发券量=('coupon_record_id', 'count'),
        核销量=('status_code', lambda x: (x == 1).sum()),
        发券人数=('userid', 'nunique'),
    ).reset_index()
    c_agg['人均领券'] = (c_agg['总发券量'] / c_agg['发券人数'].replace(0, 1)).round(1)
    c_agg['核销率'] = (c_agg['核销量'] / c_agg['总发券量'].replace(0, 1) * 100).round(2)

    s_agg = df_s.groupby(['business_level', 'age_group']).agg(
        总销售额=('销售额', 'sum'),
        订单数=('科创编号', 'count'),
        消费人数=('电话', 'nunique'),
    ).reset_index()
    s_agg['客单价'] = (s_agg['总销售额'] / s_agg['订单数'].replace(0, 1)).round(0)
    s_agg['消费频次'] = (s_agg['订单数'] / s_agg['消费人数'].replace(0, 1)).round(1)

    merged = pd.merge(c_agg, s_agg, on=['business_level', 'age_group'], how='outer').fillna(0)
    merged = merged[(merged['总发券量'] > 0) | (merged['总销售额'] > 0)]

    def tag(r):
        avg_cpn = float(r.get('人均领券', 0))
        rd = float(r.get('核销率', 0))
        atv = float(r.get('客单价', 0))
        # Issue 6: Adjusted thresholds matching compute_cohort_data
        if avg_cpn >= 2 and atv < 500: return 'RED'
        if atv >= 800 and rd < 1: return 'GOLD'
        if rd >= 0.5 and atv >= 300: return 'GREEN'
        return 'GRAY'

    merged['诊断标签'] = merged.apply(tag, axis=1)
    merged = merged.sort_values('总销售额', ascending=False).reset_index(drop=True)
    return merged.rename(columns={
        'business_level': '会员等级', 'age_group': '世代人群',
    }).to_dict('records')


def compute_category_revenue(df_s):
    """Top-8 business categories by revenue."""
    if '业态' not in df_s.columns:
        return []
    rev = df_s.groupby('业态')['销售额'].sum().sort_values(ascending=False).head(8)
    total = float(df_s['销售额'].sum())
    colors = ['#10b981', '#c9a961', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#06b6d4', '#f97316']
    return [
        {
            'name': cat, 'sales': round(float(amt), 2),
            'pct': round(float(amt) / total * 100, 1) if total > 0 else 0,
            'color': colors[i % len(colors)],
        }
        for i, (cat, amt) in enumerate(rev.items())
    ]


def compute_trend_data(df_c, df_s, granularity='weekly'):
    """Weekly/Monthly/Daily trend with Pearson r."""
    if df_c.empty or df_s.empty:
        return [], [], [], 0

    c = df_c.copy(); s = df_s.copy()
    if granularity == 'monthly':
        c['period'] = c['create_time'].dt.to_period('M').apply(lambda r: r.start_time)
        s['period'] = s['销售时间'].dt.to_period('M').apply(lambda r: r.start_time)
    elif granularity == 'daily':
        c['period'] = pd.to_datetime(c['create_time'].dt.date)
        s['period'] = pd.to_datetime(s['销售时间'].dt.date)
    else:
        c['period'] = c['create_time'].dt.to_period('W').apply(lambda r: r.start_time)
        s['period'] = s['销售时间'].dt.to_period('W').apply(lambda r: r.start_time)

    c_agg = c.groupby('period').size()
    s_agg = s.groupby('period')['销售额'].sum()
    periods = sorted(set(c_agg.index) | set(s_agg.index))[-26:]

    if granularity == 'daily':
        labels = [p.strftime('%m/%d') if hasattr(p, 'strftime') else str(p) for p in periods]
    else:
        labels = [p.strftime('%Y-%m-%d') if hasattr(p, 'strftime') else str(p) for p in periods]

    coupon_data = [int(c_agg.get(p, 0)) for p in periods]
    sales_data = [round(float(s_agg.get(p, 0)), 2) for p in periods]

    r = 0
    if len(coupon_data) > 1 and len(sales_data) > 1:
        r = float(np.corrcoef(coupon_data, sales_data)[0, 1])
        r = 0 if np.isnan(r) else round(r, 2)

    return labels, coupon_data, sales_data, r


def compute_lag_data(df_c, df_s):
    """Pearson r at lag days [0,1,2,3,5,7,14,30]."""
    if df_c.empty or df_s.empty:
        return []

    cp_daily = df_c.groupby(df_c['create_time'].dt.date).size()
    sl_daily = df_s.groupby(df_s['销售时间'].dt.date)['销售额'].sum()
    all_dates = sorted(set(cp_daily.index) | set(sl_daily.index))
    if len(all_dates) < 10:
        return []

    cp_arr = np.array([cp_daily.get(d, 0) for d in all_dates])
    sl_arr = np.array([sl_daily.get(d, 0) for d in all_dates])

    results = []
    for lag in [0, 1, 2, 3, 5, 7, 14, 30]:
        if lag >= len(cp_arr) - 2:
            continue
        x, y = cp_arr[:len(cp_arr) - lag], sl_arr[lag:]
        if len(x) > 1:
            r = float(np.corrcoef(x, y)[0, 1])
            r = 0 if np.isnan(r) else round(r, 2)
            if r >= 0.7: strength = 'strong'
            elif r >= 0.4: strength = 'moderate'
            elif r >= 0.2: strength = 'weak'
            else: strength = 'none'
            results.append({'lag': lag, 'r': r, 'strength': strength})
    return results
