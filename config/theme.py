"""
Parkview Green Marketing ROI Dashboard — Design System
侨福芳草地 · 营销效能战情室 — 亮色大厂风设计系统
Based on: 侨福生态绿 + 奢侈金 brand palette, enterprise BI clean aesthetics.
"""

import streamlit as st

# ================================================================
# DESIGN TOKENS
# ================================================================
COLORS = {
    # 侨福生态绿 — 主色系统
    "green_50": "#ecfdf5",
    "green_100": "#d1fae5",
    "green_200": "#a7f3d0",
    "green_300": "#6ee7b7",
    "green_400": "#34d399",
    "green_500": "#10b981",  # Primary
    "green_600": "#059669",
    "green_700": "#047857",
    "green_800": "#065f46",
    "green_900": "#064e3b",
    # 奢侈金 — 辅色系统
    "gold_50": "#fdf8f0",
    "gold_100": "#f9edcc",
    "gold_200": "#f0d68a",
    "gold_300": "#e5c058",
    "gold_400": "#d4ac34",
    "gold_500": "#c9a961",  # Secondary accent
    "gold_600": "#b8932e",
    "gold_700": "#8c6e22",
    "gold_800": "#6b5216",
    # 语义色
    "blue_500": "#3b82f6",
    "purple_500": "#8b5cf6",
    "pink_500": "#ec4899",
    "red_500": "#ef4444",
    "red_50": "#fef2f2",
    "red_100": "#fee2e2",
    "orange_500": "#f59e0b",
    "orange_50": "#fffbeb",
    "orange_100": "#fef3c7",
    "teal_500": "#14b8a6",
    # 中性色
    "gray_50": "#f8fafc",
    "gray_100": "#f1f5f9",
    "gray_200": "#e2e8f0",
    "gray_300": "#cbd5e1",
    "gray_400": "#94a3b8",
    "gray_500": "#64748b",
    "gray_600": "#475569",
    "gray_700": "#334155",
    "gray_800": "#1e293b",
    "gray_900": "#0f172a",
    # 语义映射
    "bg": "#f8fafc",
    "bg_card": "#ffffff",
    "bg_sidebar": "#ffffff",
    "text_primary": "#0f172a",
    "text_secondary": "#475569",
    "text_muted": "#94a3b8",
    "border": "#e2e8f0",
    "border_light": "#f1f5f9",
}

CSS_CONTENT = """
/* ======================================== */
/* 0. RESET & BASE */
/* ======================================== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* { font-family: 'Inter', -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; }

.stApp {
    background: #f8fafc;
    color: #0f172a;
}

.stMainBlockContainer {
    padding: 1.5rem 2rem;
}

/* ======================================== */
/* 1. KPI CARDS — Enterprise BI Style */
/* ======================================== */
.kpi-glass-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 24px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.kpi-glass-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #10b981, #34d399, #10b981);
    border-radius: 12px 12px 0 0;
}

.kpi-glass-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.10);
    border-color: #a7f3d0;
}

.kpi-card-title {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #64748b;
    margin-bottom: 8px;
    font-weight: 600;
}

.kpi-card-value {
    font-size: 28px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.2;
    letter-spacing: -0.5px;
}

.kpi-card-sub {
    font-size: 13px;
    color: #94a3b8;
    margin-top: 6px;
}

.kpi-card-change-up {
    color: #059669;
    font-size: 13px;
    font-weight: 600;
}

.kpi-card-change-down {
    color: #ef4444;
    font-size: 13px;
    font-weight: 600;
}

.kpi-card-glow {
    position: absolute;
    top: -30px; right: -30px;
    width: 90px; height: 90px;
    border-radius: 50%;
    pointer-events: none;
}

/* ======================================== */
/* 2. GLOBAL NAVIGATION — Brand Header */
/* ======================================== */
.global-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 24px;
    margin-bottom: 20px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.nav-brand {
    font-size: 15px;
    font-weight: 600;
    color: #0f172a;
    letter-spacing: 0.3px;
}

.nav-badge {
    background: #ecfdf5;
    color: #059669;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}

.nav-page-tabs {
    display: flex;
    gap: 4px;
    margin-top: 10px;
}

.nav-tab {
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    color: #64748b;
    text-decoration: none;
    transition: all 0.2s;
    cursor: pointer;
}

.nav-tab:hover {
    color: #0f172a;
    background: #f1f5f9;
}

.nav-tab.active {
    color: #059669;
    background: #ecfdf5;
    font-weight: 600;
}

/* ======================================== */
/* 3. ALERT BANNERS */
/* ======================================== */
.alert-banner-critical {
    background: #fef2f2;
    border-left: 4px solid #ef4444;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 8px 0;
    color: #991b1b;
    font-size: 14px;
}

.alert-banner-warning {
    background: #fffbeb;
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 8px 0;
    color: #92400e;
    font-size: 14px;
}

.alert-banner-info {
    background: #f0f9ff;
    border-left: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 8px 0;
    color: #1e40af;
    font-size: 14px;
}

.alert-banner-success {
    background: #ecfdf5;
    border-left: 4px solid #10b981;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 8px 0;
    color: #065f46;
    font-size: 14px;
}

/* ======================================== */
/* 4. BUTTON STYLES */
/* ======================================== */
.btn-glass {
    background: #ecfdf5;
    color: #059669 !important;
    border: 1px solid #a7f3d0;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    display: inline-block;
}

.btn-glass:hover {
    background: #d1fae5;
    border-color: #6ee7b7;
}

/* ======================================== */
/* 5. CUSTOM SCROLLBAR */
/* ======================================== */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* ======================================== */
/* 6. GLOW DIVIDER */
/* ======================================== */
.glow-divider {
    height: 1px;
    background: linear-gradient(90deg,
        transparent,
        #cbd5e1,
        #94a3b8,
        #cbd5e1,
        transparent
    );
    margin: 24px 0;
}

/* ======================================== */
/* 7. HIDE STREAMLIT NATIVE ELEMENTS */
/* ======================================== */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }

/* ======================================== */
/* 8. SIDEBAR — Clean Enterprise Style */
/* ======================================== */
section[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}

section[data-testid="stSidebar"] * {
    color: #334155 !important;
}

section[data-testid="stSidebar"] .st-emotion-cache-1oe5ca3 {
    color: #0f172a !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4 {
    color: #0f172a !important;
}

/* Sidebar divider */
section[data-testid="stSidebar"] hr {
    border-color: #e2e8f0 !important;
}

/* Sidebar caption */
section[data-testid="stSidebar"] .st-caption {
    color: #94a3b8 !important;
}

/* ======================================== */
/* 9. TILE GRID COHORT SELECTOR */
/* ======================================== */
.cohort-tile {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 16px;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

.cohort-tile:hover {
    border-color: #a7f3d0;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.08);
}

.cohort-tile.selected {
    border-color: #10b981;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.12);
    background: #f0fdf4;
}

.cohort-tile-label {
    font-size: 14px;
    font-weight: 600;
    color: #0f172a;
}

.cohort-tile-stat {
    font-size: 11px;
    color: #94a3b8;
    margin-top: 2px;
}

.cohort-tile-value {
    font-size: 16px;
    font-weight: 600;
    color: #334155;
}

/* ======================================== */
/* 10. SKELETON LOADING */
/* ======================================== */
@keyframes shimmer {
    0% { background-position: -200px 0; }
    100% { background-position: 200px 0; }
}

.skeleton {
    background: linear-gradient(90deg,
        #f1f5f9 25%,
        #e2e8f0 50%,
        #f1f5f9 75%
    );
    background-size: 200px 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 8px;
}

/* ======================================== */
/* 11. SECTION HEADERS */
/* ======================================== */
.section-title {
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: 0.2px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #f1f5f9;
}

.section-subtitle {
    font-size: 13px;
    color: #64748b;
    margin-bottom: 16px;
    line-height: 1.5;
}

/* ======================================== */
/* 12. EXPANDER OVERRIDE */
/* ======================================== */
.streamlit-expanderHeader {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #334155 !important;
}

.streamlit-expanderHeader:hover {
    border-color: #10b981 !important;
}

.streamlit-expanderContent {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
}

/* ======================================== */
/* 13. SELECTBOX / INPUT OVERRIDES */
/* ======================================== */
div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border-color: #e2e8f0 !important;
    border-radius: 8px !important;
}

div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    background-color: #ffffff !important;
    border-color: #e2e8f0 !important;
    color: #0f172a !important;
    border-radius: 8px !important;
}

/* ======================================== */
/* 14. TOAST / MESSAGE OVERRIDES */
/* ======================================== */
div[data-testid="stNotification"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
}

/* ======================================== */
/* 15. PAGE LINK / TAB STYLING */
/* ======================================== */
.st-emotion-cache-1oe5ca3 a,
a[data-testid="stPageLink-NavLink"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #475569 !important;
    font-weight: 500 !important;
}

.st-emotion-cache-1oe5ca3 a:hover,
a[data-testid="stPageLink-NavLink"]:hover {
    border-color: #a7f3d0 !important;
    color: #0f172a !important;
    background: #f8fafc !important;
}

/* ======================================== */
/* 16. TABLE STYLING */
/* ======================================== */
.stDataFrame {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
}

.stDataFrame thead th {
    background: #f8fafc !important;
    color: #475569 !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    border-bottom: 2px solid #e2e8f0 !important;
}

.stDataFrame tbody td {
    color: #334155 !important;
    font-size: 13px !important;
}

/* ======================================== */
/* 17. BUTTON OVERRIDES */
/* ======================================== */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    transition: all 0.2s !important;
}

.stButton > button[kind="primary"] {
    background: #10b981 !important;
    border-color: #10b981 !important;
    color: #ffffff !important;
}

.stButton > button[kind="primary"]:hover {
    background: #059669 !important;
    border-color: #059669 !important;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25) !important;
}

.stButton > button[kind="secondary"] {
    background: #ffffff !important;
    border-color: #e2e8f0 !important;
    color: #475569 !important;
}

.stButton > button[kind="secondary"]:hover {
    border-color: #10b981 !important;
    color: #059669 !important;
}

/* ======================================== */
/* 18. WELCOME PAGE */
/* ======================================== */
.welcome-container {
    text-align: center;
    padding: 80px 40px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.welcome-icon {
    font-size: 48px;
    margin-bottom: 20px;
    width: 80px;
    height: 80px;
    line-height: 80px;
    border-radius: 20px;
    background: linear-gradient(135deg, #ecfdf5, #d1fae5);
    display: inline-block;
}

.welcome-title {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 8px;
}

.welcome-subtitle {
    font-size: 15px;
    color: #64748b;
    margin-bottom: 24px;
    line-height: 1.6;
}

.welcome-hint {
    font-size: 13px;
    color: #94a3b8;
}

/* ======================================== */
/* 19. GLOBAL CAPTION */
/* ======================================== */
.st-caption {
    color: #94a3b8 !important;
}
"""


def inject_global_css():
    """Inject the Parkview Green enterprise design system CSS."""
    st.markdown(f"<style>{CSS_CONTENT}</style>", unsafe_allow_html=True)
