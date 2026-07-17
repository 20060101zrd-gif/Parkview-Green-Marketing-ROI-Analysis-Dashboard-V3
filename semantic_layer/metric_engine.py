"""
Centralized Metric Engine
All KPI calculations in one place. Every page calls this engine
instead of computing metrics inline.
"""

import pandas as pd
import numpy as np


class MetricEngine:
    """Unified KPI computation engine for the entire dashboard."""

    def __init__(self):
        self._cache = {}

    def compute_all(self, df_coupon: pd.DataFrame, df_sales: pd.DataFrame) -> dict:
        """Compute all KPIs from raw coupon and sales dataframes."""
        if df_coupon.empty and df_sales.empty:
            return self._empty_result()

        total_issued = len(df_coupon)
        real_used = int((df_coupon['status_code'] == 1).sum()) if 'status_code' in df_coupon.columns else 0
        conversion_rate = (real_used / total_issued * 100) if total_issued > 0 else 0

        total_sales = float(df_sales['销售额'].sum()) if '销售额' in df_sales.columns else 0
        total_orders = len(df_sales)
        aov = total_sales / total_orders if total_orders > 0 else 0

        member_sales = float(
            df_sales[df_sales['business_level'] != '平台会员']['销售额'].sum()
        ) if 'business_level' in df_sales.columns and '销售额' in df_sales.columns else 0
        member_contribution = (member_sales / total_sales * 100) if total_sales > 0 else 0

        estimated_coupon_sales = real_used * aov
        coupon_leverage = (estimated_coupon_sales / total_sales * 100) if total_sales > 0 else 0

        # ROI: assume coupon cost is ~15% of face value (configurable)
        estimated_cost = real_used * aov * 0.15
        roi = ((estimated_coupon_sales - estimated_cost) / estimated_cost * 100) if estimated_cost > 0 else 0

        total_redeemed = real_used
        redeem_rate = (total_redeemed / total_issued * 100) if total_issued > 0 else 0

        # Coupon type structure
        coupon_structure = {}
        if 'coupon_type' in df_coupon.columns and not df_coupon.empty:
            coupon_counts = df_coupon['coupon_type'].value_counts().to_dict()
            coupon_pct = {k: v / total_issued * 100 for k, v in coupon_counts.items()}
            coupon_structure = {
                'counts': coupon_counts,
                'percentages': coupon_pct,
                'parking_share': coupon_pct.get('daily_parking_coupon',
                                    coupon_pct.get('parking_coupon', 0))
            }

        # Cohort overview
        cohort_data = []
        if 'business_level' in df_coupon.columns and 'age_group' in df_coupon.columns:
            cohort_data = self._build_cohort_overview(df_coupon, df_sales)

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
            'roi': round(roi, 2),
            'total_redeemed': total_redeemed,
            'redeem_rate': round(redeem_rate, 2),
            'coupon_structure': coupon_structure,
            'cohort_data': cohort_data,
        }

    def _build_cohort_overview(self, df_coupon, df_sales) -> list:
        """Build a summary of each cohort for AI/Insight consumption."""
        cohorts = []
        levels = sorted(df_coupon['business_level'].unique())
        ages = sorted(df_coupon['age_group'].unique())

        for lv in levels:
            for ag in ages:
                c = df_coupon[(df_coupon['business_level'] == lv) & (df_coupon['age_group'] == ag)]
                s = df_sales[(df_sales['business_level'] == lv) & (df_sales['age_group'] == ag)]
                if c.empty and s.empty:
                    continue

                issued = len(c)
                redeemed = int((c['status_code'] == 1).sum()) if 'status_code' in c.columns else 0
                sales_amt = float(s['销售额'].sum()) if '销售额' in s.columns else 0
                orders = len(s)
                consumers = s['电话'].nunique() if '电话' in s.columns else 0
                atv = sales_amt / orders if orders > 0 else 0
                redeem_r = redeemed / issued if issued > 0 else 0
                avg_cpn = issued / consumers if consumers > 0 else 0

                cohorts.append({
                    'level': lv,
                    'age_group': ag,
                    'issued': issued,
                    'redeemed': redeemed,
                    'sales': round(sales_amt, 2),
                    'orders': orders,
                    'consumers': consumers,
                    'atv': round(atv, 2),
                    'redeem_rate': round(redeem_r, 4),
                    'avg_coupons_per_person': round(avg_cpn, 2),
                })

        return sorted(cohorts, key=lambda x: x['sales'], reverse=True)

    def _empty_result(self) -> dict:
        return {
            'total_issued': 0, 'real_used': 0, 'conversion_rate': 0,
            'total_sales': 0, 'total_orders': 0, 'aov': 0,
            'member_sales': 0, 'member_contribution': 0,
            'estimated_coupon_sales': 0, 'coupon_leverage': 0,
            'roi': 0, 'total_redeemed': 0, 'redeem_rate': 0,
            'coupon_structure': {}, 'cohort_data': [],
        }
