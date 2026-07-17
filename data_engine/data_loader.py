"""
Schema-driven data loader.
Reads CSV files and auto-maps external column names to internal standard names
using config/schema_mapping.yaml.
"""

import pandas as pd
import yaml
import streamlit as st
from config.mappings import VIP_MAPPING, get_age_group_by_birth_year


SCHEMA_PATH = "config/schema_mapping.yaml"


# 注意: 故意不使用 @st.cache_data 装饰器
# Streamlit 1.36+ 在文件改动时会弹出"Clear caches"窗口，
# 这会干扰用户与侧边栏筛选器的交互体验。
# CSV 数据文件本身不大，每次直接重读性能可接受。


def _load_schema() -> dict:
    """Load schema mapping configuration."""
    try:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception:
        return {}


def _map_columns(df: pd.DataFrame, template: dict) -> pd.DataFrame:
    """
    Rename DataFrame columns according to schema template.
    Template format: {internal_name: external_name}
    """
    rename_map = {}
    for internal, external in template.items():
        if external in df.columns:
            rename_map[external] = internal

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def _validate_columns(df: pd.DataFrame, expected: list, table_name: str) -> list:
    """Check which expected internal columns are present."""
    missing = [c for c in expected if c not in df.columns]
    if missing:
        st.warning(f"Table '{table_name}' is missing columns: {', '.join(missing)}")
    return missing


@st.cache_data(show_spinner=False)
def load_and_clean_data(coupon_file_path, sales_file_path,
                        template_name: str = None):
    """
    Read two CSV files, apply schema mapping, clean and align dimensions.

    Args:
        coupon_file_path: Path or file-like object for coupon CSV
        sales_file_path: Path or file-like object for sales CSV
        template_name: Schema template to use (defaults to active_template in yaml)

    Returns:
        Tuple of (cleaned coupon DataFrame, cleaned sales DataFrame)
    """
    schema = _load_schema()

    if template_name is None and schema:
        template_name = schema.get('active_template', 'parkview_green')

    # ---- Load raw CSVs ----
    df_coupon = pd.read_csv(coupon_file_path)
    df_sales = pd.read_csv(sales_file_path)

    # ---- Apply schema mapping ----
    if schema and template_name:
        coupon_templates = schema.get('coupon_table', {}).get('templates', {})
        sales_templates = schema.get('sales_table', {}).get('templates', {})

        if template_name in coupon_templates:
            df_coupon = _map_columns(df_coupon, coupon_templates[template_name])
        if template_name in sales_templates:
            df_sales = _map_columns(df_sales, sales_templates[template_name])

        # Validate columns
        coupon_expected = schema.get('coupon_table', {}).get('internal_columns', [])
        sales_expected = schema.get('sales_table', {}).get('internal_columns', [])
        _validate_columns(df_coupon, coupon_expected, 'Coupon')
        _validate_columns(df_sales, sales_expected, 'Sales')

    # ==========================================
    # COUPON TABLE CLEANING
    # ==========================================
    if 'create_time' in df_coupon.columns:
        df_coupon['create_time'] = pd.to_datetime(df_coupon['create_time'])
    else:
        st.error("Fatal: 'create_time' column not found in coupon data.")
        raise ValueError("Missing 'create_time' column in coupon data.")

    if 'update_time' in df_coupon.columns:
        df_coupon['update_time'] = pd.to_datetime(df_coupon['update_time'])
    else:
        df_coupon['update_time'] = df_coupon['create_time']

    # Status code calculation
    df_coupon['time_diff_hours'] = (
        (df_coupon['update_time'] - df_coupon['create_time']).dt.total_seconds() / 3600
    )

    def get_status_code(row):
        if row.get('coupon_status', '') == 'available':
            return 3  # idle
        elif row.get('coupon_status', '') == 'unavailable' and row.get('time_diff_hours', 0) > 23.5:
            return 2  # system expired
        else:
            return 1  # real redemption

    df_coupon['status_code'] = df_coupon.apply(get_status_code, axis=1)

    # VIP level mapping
    if 'level' in df_coupon.columns:
        df_coupon['business_level'] = df_coupon['level'].map(VIP_MAPPING).fillna('Non-Member')
    else:
        df_coupon['business_level'] = 'Non-Member'

    if 'age_group' in df_coupon.columns:
        df_coupon['age_group'] = df_coupon['age_group'].fillna('Unknown')
    else:
        df_coupon['age_group'] = 'Unknown'

    # ==========================================
    # SALES TABLE CLEANING
    # ==========================================
    if '销售额' in df_sales.columns:
        df_sales['销售额'] = pd.to_numeric(df_sales['销售额'], errors='coerce').fillna(0)
    else:
        st.error("Fatal: '销售额' column not found in sales data.")
        raise ValueError("Missing '销售额' column in sales data.")

    if '销售时间' in df_sales.columns:
        df_sales['销售时间'] = pd.to_datetime(df_sales['销售时间'])
    else:
        st.error("Fatal: '销售时间' column not found in sales data.")
        raise ValueError("Missing '销售时间' column in sales data.")

    if '会员等级' in df_sales.columns:
        df_sales['business_level'] = df_sales['会员等级'].fillna('Non-Member')
    else:
        df_sales['business_level'] = 'Non-Member'

    if '生日' in df_sales.columns:
        df_sales['age_group'] = df_sales['生日'].apply(get_age_group_by_birth_year)
    else:
        df_sales['age_group'] = 'Unknown'

    return df_coupon, df_sales
