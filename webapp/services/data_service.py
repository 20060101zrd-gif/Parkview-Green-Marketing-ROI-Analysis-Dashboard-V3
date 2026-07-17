"""
Data Service — loads, cleans, and filters CSV data.
Pure business logic; no Flask dependency.
"""
import os
import pandas as pd

# Resolve project root: webapp/services/data_service.py -> ../../ -> project root
_SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))  # .../webapp/services
_WEBAPP_DIR = os.path.dirname(_SERVICE_DIR)                 # .../webapp
BASE_DIR = os.path.dirname(_WEBAPP_DIR)                     # .../Parkview_Green_Marketing_ROI_Analysis_Dashboard
DATA_DIR = os.path.join(BASE_DIR, 'data')
COUPON_CSV = os.path.join(DATA_DIR, 'BI_Dashboard_Ready_Data.csv')
SALES_CSV = os.path.join(DATA_DIR, '销售查询.csv')

VIP_MAPPING = {
    '非会员': '平台会员', 'VIP 1001': '绿意会员', 'VIP 1002': '悦意会员',
    'VIP 1003': '菁英会员', 'VIP 1004': '菁英会员',
    '绿意会员': '绿意会员', '悦意会员': '悦意会员',
    '菁英会员': '菁英会员', '平台会员': '平台会员',
}


class DataService:
    """Central data access layer. Loads once, caches in memory."""

    def __init__(self):
        self._coupon = None
        self._sales = None

    # ----------------------------------------------------------------
    # Load
    # ----------------------------------------------------------------
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls().load()
        return cls._instance

    def load(self):
        """Load and clean raw CSVs. Called once on startup."""
        self._coupon = self._clean_coupon(pd.read_csv(COUPON_CSV))
        self._sales = self._clean_sales(pd.read_csv(SALES_CSV))
        print(f"[DataService] Coupon: {len(self._coupon)} rows | Sales: {len(self._sales)} rows")
        return self

    def reload(self):
        """Reload data from CSV files (used by scheduler after file pull)."""
        self._coupon = None
        self._sales = None
        return self.load()

    @property
    def coupon(self):
        if self._coupon is None:
            self.load()
        return self._coupon

    @property
    def sales(self):
        if self._sales is None:
            self.load()
        return self._sales

    # ----------------------------------------------------------------
    # Filter
    # ----------------------------------------------------------------
    def filter(self, start_date=None, end_date=None, levels=None, ages=None):
        """Apply time-range + cohort filters. Returns (coupon_df, sales_df)."""
        df_c = self.coupon.copy()
        df_s = self.sales.copy()

        if start_date:
            start = pd.Timestamp(start_date).date()
            df_c = df_c[df_c['create_time'].dt.date >= start]
            df_s = df_s[df_s['销售时间'].dt.date >= start]
        if end_date:
            end = pd.Timestamp(end_date).date()
            df_c = df_c[df_c['create_time'].dt.date <= end]
            df_s = df_s[df_s['销售时间'].dt.date <= end]
        if levels:
            df_c = df_c[df_c['business_level'].isin(levels)]
            df_s = df_s[df_s['business_level'].isin(levels)]
        if ages:
            df_c = df_c[df_c['age_group'].isin(ages)]
            df_s = df_s[df_s['age_group'].isin(ages)]

        return df_c, df_s

    def filter_options(self):
        """Return available filter dimensions."""
        ages_all = ['00后', '90后', '80后', '70后', '未知', '其他']
        return {
            'levels': sorted(self.coupon['business_level'].unique().tolist()),
            'ages': [a for a in ages_all if a in self.coupon['age_group'].unique()],
            'date_min': self.coupon['create_time'].min().strftime('%Y-%m-%d'),
            'date_max': self.coupon['create_time'].max().strftime('%Y-%m-%d'),
        }

    def summary(self):
        """Quick data summary."""
        c = self.coupon
        s = self.sales
        return {
            'total_coupon_records': len(c),
            'total_sales_records': len(s),
            'date_range': {
                'coupon': {
                    'min': c['create_time'].min().strftime('%Y-%m-%d') if not c.empty else 'N/A',
                    'max': c['create_time'].max().strftime('%Y-%m-%d') if not c.empty else 'N/A',
                },
                'sales': {
                    'min': s['销售时间'].min().strftime('%Y-%m-%d') if not s.empty else 'N/A',
                    'max': s['销售时间'].max().strftime('%Y-%m-%d') if not s.empty else 'N/A',
                },
            },
        }

    # ----------------------------------------------------------------
    # Clean helpers
    # ----------------------------------------------------------------
    def _clean_coupon(self, df):
        df['create_time'] = pd.to_datetime(df['create_time'], dayfirst=True)
        df['update_time'] = pd.to_datetime(df['update_time'], dayfirst=True)
        df['status_code'] = df.apply(
            lambda r: 1 if r.get('coupon_status', '') != 'available'
                      and (r['update_time'] - r['create_time']).total_seconds() / 3600 <= 23.5
                      else (3 if r.get('coupon_status', '') == 'available' else 2),
            axis=1)
        df['business_level'] = df['level'].map(VIP_MAPPING).fillna('平台会员')
        df['age_group'] = df['age_group'].fillna('未知')
        return df

    def _clean_sales(self, df):
        df['销售额'] = pd.to_numeric(df['销售额'], errors='coerce').fillna(0)
        df['销售时间'] = pd.to_datetime(df['销售时间'])
        df['business_level'] = df['会员等级'].fillna('平台会员')
        df['birth_year'] = pd.to_datetime(df['生日'], errors='coerce').dt.year
        df['age_group'] = df['birth_year'].apply(self._birth_to_age)
        return df

    @staticmethod
    def _birth_to_age(y):
        if pd.isna(y): return '未知'
        if y >= 2000: return '00后'
        if y >= 1990: return '90后'
        if y >= 1980: return '80后'
        if y >= 1970: return '70后'
        return '未知'


# Singleton instance
ds = DataService().load()
