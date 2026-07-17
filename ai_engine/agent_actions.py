"""
Agent 行动层 — 让 AI 诊断结果落地为可执行动作。
纯 Python 标准库，零外部 API 依赖。

支持:
- 发邮件 (smtplib, 无需 API Key)
- 导出 Markdown 报告
- 写入执行日志
"""

import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


class AgentActions:
    """将 AI 诊断结果转化为实际动作。"""

    def __init__(self, email_config: dict = None):
        self.email_config = email_config or self._load_email_config()

    # ================================================================
    # 公共入口
    # ================================================================

    def execute(self, action_type: str, context: dict) -> dict:
        """统一执行入口。"""
        actions = {
            "send_email": self.send_alert_email,
            "export_report": self.export_report,
        }
        fn = actions.get(action_type)
        if not fn:
            return {"success": False, "message": f"未知动作: {action_type}"}
        try:
            return fn(**context)
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ================================================================
    # 邮件
    # ================================================================

    def send_alert_email(self, subject: str, metrics: dict,
                         alerts: list, insight_text: str) -> dict:
        """发送告警邮件。"""
        if not self.email_config:
            return {"success": False, "message": "邮件未配置 (缺少 SMTP 信息)"}

        body = self._build_email_body(metrics, alerts, insight_text)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[战情室] {subject}"
        msg["From"] = self.email_config["sender"]
        msg["To"] = ", ".join(self.email_config["recipients"])
        msg.attach(MIMEText(body, "html", "utf-8"))

        try:
            with smtplib.SMTP(
                self.email_config["smtp_host"],
                int(self.email_config["smtp_port"]),
                timeout=15
            ) as server:
                server.starttls()
                server.login(
                    self.email_config["sender"],
                    self.email_config["password"]
                )
                server.sendmail(
                    self.email_config["sender"],
                    self.email_config["recipients"],
                    msg.as_string()
                )
            return {
                "success": True,
                "message": f"邮件已发送至 {len(self.email_config['recipients'])} 位收件人"
            }
        except Exception as e:
            return {"success": False, "message": f"邮件发送失败: {e}"}

    def _build_email_body(self, metrics, alerts, insight_text) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        critical = [a for a in alerts if a.get("severity") == "critical"]
        warnings = [a for a in alerts if a.get("severity") == "warning"]

        alert_rows = ""
        sev_icon = {"critical": "[严重]", "warning": "[预警]", "info": "[提示]"}
        for a in alerts:
            icon = sev_icon.get(a.get("severity", ""), "[?]")
            alert_rows += f"<tr><td>{icon}</td><td>{a.get('message', '')}</td></tr>"

        return f"""<html>
<body style="font-family: -apple-system, sans-serif; max-width: 640px;">
<h2 style="color: #1a1a2e;">营销 ROI 战情室 — 自动巡检报告</h2>
<p style="color: #666;">巡检时间: {now}</p><hr>
<h3>核心指标</h3>
<table style="border-collapse: collapse; width: 100%;">
<tr style="background: #f0f4ff;"><td style="padding: 8px;"><b>ROI</b></td><td style="padding: 8px;">{metrics.get('roi', 'N/A')}%</td></tr>
<tr><td style="padding: 8px;"><b>核销转化率</b></td><td style="padding: 8px;">{metrics.get('conversion_rate', 'N/A')}%</td></tr>
<tr style="background: #f0f4ff;"><td style="padding: 8px;"><b>总销售额</b></td><td style="padding: 8px;">CNY {metrics.get('total_sales', 0):,.0f}</td></tr>
<tr><td style="padding: 8px;"><b>会员贡献占比</b></td><td style="padding: 8px;">{metrics.get('member_contribution', 'N/A')}%</td></tr>
<tr style="background: #f0f4ff;"><td style="padding: 8px;"><b>发券总量</b></td><td style="padding: 8px;">{metrics.get('total_issued', 0):,}</td></tr>
</table>
<h3>AI 诊断摘要</h3>
<p style="background: #f8f9fa; padding: 12px; border-left: 4px solid #3b82f6;">{insight_text}</p>
<h3>告警 ({len(alerts)} 项 | 严重: {len(critical)} | 警告: {len(warnings)})</h3>
<table style="border-collapse: collapse; width: 100%;">{alert_rows}</table>
<hr><p style="color: #999; font-size: 12px;">此邮件由 AI 战情室自动巡检生成</p>
</body></html>"""

    # ================================================================
    # 报告导出
    # ================================================================

    def export_report(self, metrics: dict, alerts: list,
                      insight_text: str, recommendations: list = None) -> dict:
        """导出 Markdown 诊断报告到 data/reports/ 目录。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        recommendations = recommendations or []
        critical = [a for a in alerts if a.get("severity") == "critical"]
        warnings = [a for a in alerts if a.get("severity") == "warning"]

        alert_lines = ""
        for a in alerts:
            alert_lines += f"- **[{a.get('severity', '')}]** {a.get('message', '')}\n"

        rec_lines = ""
        for i, r in enumerate(recommendations, 1):
            rec_lines += f"{i}. {r}\n"

        report = f"""# 营销 ROI 战情室 — 诊断报告

> 生成时间: {now}

## 核心指标

| 指标 | 数值 |
|:---|---:|
| ROI | {metrics.get('roi', 'N/A')}% |
| 核销转化率 | {metrics.get('conversion_rate', 'N/A')}% |
| 总销售额 | CNY {metrics.get('total_sales', 0):,.0f} |
| 客单价 | CNY {metrics.get('aov', 0):,.0f} |
| 会员贡献占比 | {metrics.get('member_contribution', 'N/A')}% |
| 券销售渗透率 | {metrics.get('coupon_leverage', 'N/A')}% |
| 总发券量 | {metrics.get('total_issued', 0):,} |
| 实际核销量 | {metrics.get('total_redeemed', 0):,} |

## AI 诊断

{insight_text}

## 告警详情 ({len(alerts)} 项 | 严重 {len(critical)} | 警告 {len(warnings)})

{alert_lines}

## 执行建议

{rec_lines if rec_lines else '暂无具体建议。'}

---

*此报告由 AI 战情室 Agent 自动生成*
"""

        os.makedirs("data/reports", exist_ok=True)
        filename = f"data/reports/战情报告_{file_ts}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)

        return {
            "success": True,
            "message": f"报告已保存: {filename}",
            "filepath": filename,
            "content": report,
        }

    # ================================================================
    # 日志
    # ================================================================

    def write_log(self, entry: dict):
        """写入执行日志到 data/logs/agent.log。"""
        os.makedirs("data/logs", exist_ok=True)
        entry["timestamp"] = datetime.now().isoformat()
        with open("data/logs/agent.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ================================================================
    # 配置加载
    # ================================================================

    def _load_email_config(self) -> dict | None:
        """从多个来源加载邮件配置。优先级: secrets > 环境变量。"""
        # 1. Streamlit secrets
        try:
            import streamlit as st
            cfg = st.secrets.get("email", {})
            required = ["smtp_host", "smtp_port", "sender", "password", "recipients"]
            if all(k in cfg for k in required):
                return cfg
        except Exception:
            pass

        # 2. 环境变量
        env_map = {
            "smtp_host": os.getenv("AGENT_SMTP_HOST"),
            "smtp_port": os.getenv("AGENT_SMTP_PORT", "0"),
            "sender": os.getenv("AGENT_SMTP_SENDER"),
            "password": os.getenv("AGENT_SMTP_PASSWORD"),
            "recipients": os.getenv("AGENT_SMTP_RECIPIENTS", "").split(",") if os.getenv("AGENT_SMTP_RECIPIENTS") else [],
        }
        if all(v for v in env_map.values()):
            return env_map

        return None
