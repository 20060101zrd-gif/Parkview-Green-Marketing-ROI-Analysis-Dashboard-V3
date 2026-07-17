"""
全局导航栏，每个页面顶部统一渲染。
使用 st.page_link 提供可点击的页面跳转。
侨福芳草地 · 亮色大厂风设计。
"""

import streamlit as st
import os
import base64


PAGES = [
    ("01", "战情摘要", "01_战情摘要"),
    ("02", "KPI 总览", "02_KPI总览"),
    ("03", "投入产出结构", "03_投入产出结构"),
    ("04", "趋势滞后分析", "04_趋势滞后分析"),
    ("05", "客群价值诊断", "05_客群价值诊断"),
    ("06", "智能诊室", "06_智能诊室"),
]


@st.cache_data
def _brand_logo_base64(dark: bool = False) -> str:
    """加载品牌 Logo 并返回 base64 编码，用于 HTML 内嵌图片。"""
    # 从项目根目录定位 assets
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filename = "parkview_green_logo_dark.png" if dark else "parkview_green_logo.png"
    path = os.path.join(root, "assets", filename)
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def _current_page_id() -> str:
    """获取当前页面标识。"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx and ctx.script_path:
            name = os.path.basename(ctx.script_path)
            stem = os.path.splitext(name)[0]
            for num, _, page_id in PAGES:
                if page_id == stem:
                    return page_id
    except Exception:
        pass
    return "01_战情摘要"


def render_global_header():
    """渲染统一品牌导航栏 + 可点击的页面跳转。"""
    date_min = st.session_state.get('date_min_str', '--')
    date_max = st.session_state.get('date_max_str', '--')
    data_loaded = st.session_state.get('data_loaded', False)

    status_text = "运行中" if data_loaded else "待加载"
    status_color = "#059669" if data_loaded else "#94a3b8"
    status_bg = "#ecfdf5" if data_loaded else "#f1f5f9"

    logo_b64 = _brand_logo_base64(dark=False)
    logo_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else ""

    # 顶部品牌区 (HTML)
    brand_html = f"""
    <div style="
        display:flex;align-items:center;justify-content:space-between;
        padding:14px 24px;
        background:#ffffff;
        border:1px solid #e2e8f0;
        border-radius:14px;
        margin-bottom:12px;
        box-shadow:0 1px 3px rgba(0,0,0,0.03);
    ">
        <div style="display:flex;align-items:center;gap:16px;">
            <img src="{logo_src}" alt="Parkview Green 芳草地" style="height:32px;width:auto;object-fit:contain;" />
            <span style="font-size:15px;font-weight:700;color:#0f172a;letter-spacing:0.3px;">
                北京侨福芳草地 &middot; 营销效能战情室
            </span>
            <span style="
                background:{status_bg};
                color:{status_color};
                padding:4px 12px;
                border-radius:20px;
                font-size:11px;
                font-weight:600;
            ">
                &#9679; {status_text}
            </span>
        </div>
        <div style="display:flex;align-items:center;gap:16px;color:#64748b;font-size:12px;">
            <span>数据期间: {date_min} — {date_max}</span>
            <span style="color:#cbd5e1;">|</span>
            <span style="color:#059669;font-weight:500;">v2.0</span>
        </div>
    </div>
    """
    st.markdown(brand_html, unsafe_allow_html=True)

    # 导航链接 (使用 st.page_link 实现真正可点击跳转)
    current_id = _current_page_id()
    cols = st.columns(len(PAGES))
    for i, (num, name, page_id) in enumerate(PAGES):
        with cols[i]:
            page_file = f"pages/{page_id}.py"
            is_current = (page_id == current_id)
            label = f"{'● ' if is_current else ''}{num} {name}"
            st.page_link(
                page_file,
                label=label,
                use_container_width=True,
            )
