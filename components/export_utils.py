"""
Data export utilities.
CSV download, chart PNG export, report generation.
"""

import streamlit as st
import pandas as pd
import base64
from io import BytesIO


def csv_download_button(
    df: pd.DataFrame,
    filename: str = "export.csv",
    label: str = "Download CSV"
):
    """Streamlit download button for a DataFrame as CSV."""
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv",
    )


def excel_download_button(
    df: pd.DataFrame,
    filename: str = "export.xlsx",
    label: str = "Download Excel"
):
    """Streamlit download button for a DataFrame as Excel."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    st.download_button(
        label=label,
        data=buffer.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def export_metrics_dict(metrics: dict, filename: str = "kpi_report.csv"):
    """Export a flat metrics dict as CSV."""
    rows = []
    for k, v in metrics.items():
        if isinstance(v, (int, float, str)):
            rows.append({"metric": k, "value": v})
    df = pd.DataFrame(rows)
    csv_download_button(df, filename, f"Export KPI Report")


def export_section_header(label: str):
    """Render a small export button group with consistent styling."""
    col1, col2, col3 = st.columns([6, 1, 1])
    with col1:
        st.markdown(f'<div class="section-title">{label}</div>', unsafe_allow_html=True)
    return col2, col3
