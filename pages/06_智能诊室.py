"""
06 — 智能诊室
AI 驱动分析: DeepSeek 生成业务洞察 + 异常检测 + 自由追问。
"""

import streamlit as st
import sys
import os
import json
from datetime import datetime

st.set_page_config(
    page_title="06 智能诊室",
    page_icon="🤖",
    layout="wide",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.theme import inject_global_css
from components.header import render_global_header
from semantic_layer.metric_engine import MetricEngine
from ai_engine.insight_generator import InsightGenerator
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

st.markdown('<div class="section-title">智能诊室 — AI 驱动业务诊断</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">基于 DeepSeek 大语言模型生成自然语言业务洞察，结合本地机器学习异常检测。API 不可用时自动降级为本地规则引擎。</div>', unsafe_allow_html=True)

# 引擎初始化
api_key = os.getenv("DEEPSEEK_API_KEY") or st.secrets.get("DEEPSEEK_API_KEY", None)
insight_gen = InsightGenerator(api_key=api_key)

engine = MetricEngine()
metrics = engine.compute_all(df_coupon, df_sales)

# 异常检测
detector = AnomalyDetector(contamination=0.1)
import pandas as pd
df_c = df_coupon.copy()
df_c['month'] = df_c['create_time'].dt.to_period('M').dt.to_timestamp()
trend = df_c.groupby('month').agg(
    issued=('coupon_record_id', 'count'),
    redeemed=('status_code', lambda x: (x == 1).sum()),
).reset_index()

df_s = df_sales.copy()
df_s['month'] = df_s['销售时间'].dt.to_period('M').dt.to_timestamp()
sales_trend = df_s.groupby('month')['销售额'].sum().reset_index(name='sales')

trend_merged = pd.merge(trend, sales_trend, on='month', how='outer').fillna(0)
anomaly_result = detector.detect(trend_merged, 'sales', 'month')

# 生成洞察
st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)

with st.spinner("正在生成智能洞察报告..."):
    insight = insight_gen.generate(metrics, anomaly_results={
        'anomaly_count': anomaly_result['anomaly_count'],
        'anomalies': anomaly_result['anomalies'][:3] if anomaly_result['anomalies'] else [],
    })

generated_by = insight.get('generated_by', '未知')
engine_label = "DeepSeek 大模型" if "DeepSeek" in str(generated_by) else "本地规则引擎"

st.markdown(f"##### 核心诊断摘要")
st.markdown(f'<div class="alert-banner-info">{insight.get("executive_summary", "暂无摘要。")}</div>', unsafe_allow_html=True)
st.caption(f"生成引擎: {engine_label}")

# 第2层: 预警清单
with st.expander("查看详细预警清单", expanded=False):
    alerts = insight.get('alerts', [])
    if alerts:
        for a in alerts:
            sev = a.get('severity', 'info')
            sev_labels = {'critical': '严重', 'warning': '预警', 'info': '提示'}
            cls = f"alert-banner-{sev}"
            st.markdown(f'<div class="{cls}">[{sev_labels.get(sev, sev)}] {a.get("message", "")}</div>', unsafe_allow_html=True)
    else:
        st.info("未生成预警信息。")

# 第3层: 优化建议
with st.expander("查看可执行优化建议", expanded=False):
    recs = insight.get('recommendations', [])
    if recs:
        for i, r in enumerate(recs):
            st.markdown(f'<div class="alert-banner-success">{i+1}. {r}</div>', unsafe_allow_html=True)
    else:
        st.info("未生成优化建议。")

# 第4层: 异常检测结果
with st.expander("查看异常波动检测结果", expanded=False):
    anomalies = anomaly_result.get('anomalies', [])
    if anomalies:
        anom_df = pd.DataFrame(anomalies)
        anom_df['销售额'] = anom_df['value'].apply(lambda x: f"CNY {x:,.0f}")
        anom_df['方向'] = anom_df['direction'].map({'high': '异常偏高', 'low': '异常偏低'})
        anom_df = anom_df.rename(columns={
            'time': '周期', 'deviation_sigma': '偏离度',
            'score': '异常分数', '销售额': '销售额',
        })
        st.dataframe(
            anom_df[['周期', '销售额', '偏离度', '方向', '异常分数']],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("未检测到显著异常波动。")

# 自由追问
st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)
st.markdown("##### 追问 DeepSeek")
st.caption("基于当前数据上下文，向 DeepSeek 提出具体业务问题。")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

question = st.text_input(
    "输入你的问题",
    placeholder="例如: 如果砍掉全部停车券，会损失多少业绩?",
    key="insight_question",
)

if st.button("向 DeepSeek 提问", type="primary"):
    if question.strip():
        with st.spinner("DeepSeek 分析中..."):
            prev_insight = insight.get('executive_summary', '')
            answer = insight_gen.ask_followup(
                question.strip(),
                metrics,
                prev_insight,
            )
            st.session_state.chat_history.append({
                'question': question.strip(),
                'answer': answer,
            })

# 对话历史
if st.session_state.chat_history:
    st.markdown("##### 对话历史")
    for i, chat in enumerate(st.session_state.chat_history):
        with st.expander(f"Q{i+1}: {chat['question'][:80]}...", expanded=(i == len(st.session_state.chat_history) - 1)):
            st.markdown(f"**Q:** {chat['question']}")
            st.markdown(f"**A:** {chat['answer']}")

# ================================================================
# Agent 控制面板 (方案 B: 一键操作，所见即所得)
# ================================================================
st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)
st.markdown("##### Agent 控制面板")
st.caption("一键导出诊断报告、发送告警邮件。所有操作即时生效，无需额外配置终端。")

from ai_engine.agent_actions import AgentActions

col_b1, col_b2, col_b3 = st.columns(3)

with col_b1:
    if st.button("导出诊断报告", use_container_width=True, type="primary"):
        with st.spinner("正在生成报告..."):
            agent = AgentActions()
            patrol_alerts = insight.get("alerts", [])
            patrol_summary = insight.get("executive_summary", "")
            patrol_recs = insight.get("recommendations", [])

            report_result = agent.export_report(
                metrics=metrics,
                alerts=patrol_alerts,
                insight_text=patrol_summary,
                recommendations=patrol_recs,
            )

            if report_result["success"]:
                st.success(f"报告已保存")
                st.download_button(
                    "下载 Markdown 报告",
                    data=report_result["content"],
                    file_name=os.path.basename(report_result["filepath"]),
                    mime="text/markdown",
                    key="agent_download_report",
                )
            else:
                st.error(report_result["message"])

            # 写日志
            critical_alerts = [a for a in patrol_alerts if a.get("severity") == "critical"]
            agent.write_log({
                "patrol_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "completed",
                "metrics": {
                    "roi": metrics.get("roi"),
                    "conversion_rate": metrics.get("conversion_rate"),
                    "total_sales": metrics.get("total_sales"),
                },
                "alerts_count": len(patrol_alerts),
                "critical_count": len(critical_alerts),
                "report_saved": report_result["success"],
            })

with col_b2:
    if st.button("发送告警邮件", use_container_width=True):
        patrol_alerts = insight.get("alerts", [])
        critical_alerts = [a for a in patrol_alerts if a.get("severity") == "critical"]
        if not critical_alerts:
            st.info("当前无严重告警，无需发送邮件。")
        else:
            with st.spinner("发送中..."):
                agent = AgentActions()
                result = agent.send_alert_email(
                    subject=f"{len(critical_alerts)}项严重告警 — ROI {metrics.get('roi', 0):.1f}%",
                    metrics=metrics,
                    alerts=patrol_alerts,
                    insight_text=insight.get("executive_summary", ""),
                )
                if result["success"]:
                    st.success(result["message"])
                else:
                    st.warning(result["message"])
                    if "未配置" in result.get("message", ""):
                        st.caption("提示: 在 .streamlit/secrets.toml 中配置 [email] 段即可启用邮件功能。")

with col_b3:
    if st.button("查看操作历史", use_container_width=True):
        log_path = "data/logs/agent.log"
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if lines:
                st.caption(f"最近 {min(5, len(lines))} 条记录:")
                for line in reversed(lines[-5:]):
                    try:
                        log = json.loads(line.strip())
                        ts = log.get("timestamp", log.get("patrol_time", "?"))
                        status = log.get("status", "?")
                        alerts_n = log.get("alerts_count", 0)
                        critical_n = log.get("critical_count", 0)
                        st.markdown(
                            f"`{ts[:16]}` | 状态: **{status}** | "
                            f"告警: {alerts_n} (严重: {critical_n}) | "
                            f"报告: {'已保存' if log.get('report_saved') else '未保存'}"
                        )
                    except Exception:
                        st.text(line.strip()[:120])
            else:
                st.info("暂无操作记录。")
        else:
            st.info("暂无操作记录。点「导出诊断报告」后会生成记录。")

# ================================================================
# API 状态
# ================================================================
st.markdown('<div class="glow-divider"></div>', unsafe_allow_html=True)
api_status = "DeepSeek API (已连接)" if insight_gen.mode == "deepseek" else "本地模板引擎 (API 未配置或不可用)"
st.caption(f"引擎状态: {api_status} | 数据规模: {len(df_coupon):,} 条发券记录, {len(df_sales):,} 条销售记录")
