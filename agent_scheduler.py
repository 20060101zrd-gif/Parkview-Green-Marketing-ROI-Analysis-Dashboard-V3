"""
后台 Agent 定时巡检脚本 (可选启用)
独立于 Streamlit 运行，每 N 小时自动执行一次巡检。

用法:
    python agent_scheduler.py              # 使用默认配置
    python agent_scheduler.py --interval 6  # 每 6 小时

配置:
    data/agent_config.json 控制开关和间隔，Streamlit 页面可远程修改。
    默认 enabled=false，即不自动巡检。需要手动在页面打开。

依赖:
    pip install schedule
"""

import sys
import os
import time
import json
import traceback
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import schedule
import pandas as pd

from data_engine.data_loader import load_and_clean_data
from semantic_layer.metric_engine import MetricEngine
from ai_engine.insight_generator import InsightGenerator
from ai_engine.anomaly_detector import AnomalyDetector
from ai_engine.agent_actions import AgentActions

# ============================================================
# 路径配置
# ============================================================
COUPON_CSV = "data/BI_Dashboard_Ready_Data.csv"
SALES_CSV = "data/销售查询.csv"
CONFIG_FILE = "data/agent_config.json"


def load_agent_config() -> dict:
    """加载 Agent 配置，不存在则创建默认 (关闭状态)。"""
    default = {"enabled": False, "interval_hours": 4}
    if not os.path.exists(CONFIG_FILE):
        os.makedirs(os.path.dirname(CONFIG_FILE) or ".", exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _load_api_key() -> str:
    """加载 DeepSeek API Key。"""
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if key and key.strip():
        return key.strip()

    try:
        secrets_path = ".streamlit/secrets.toml"
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "DEEPSEEK_API_KEY" in line and "=" in line:
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if key:
                            return key
    except Exception:
        pass
    return ""


def run_patrol():
    """执行一次完整巡检。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"  Agent 巡检开始 — {now}")
    print(f"{'='*60}")

    agent = AgentActions()
    log_entry = {
        "patrol_time": now,
        "status": "started",
        "metrics": {},
        "alerts_count": 0,
        "critical_count": 0,
        "email_sent": False,
        "report_saved": False,
        "errors": [],
    }

    try:
        # Step 1: 加载数据
        print("  [1/5] 加载数据...")
        df_coupon, df_sales = load_and_clean_data(COUPON_CSV, SALES_CSV)

        # Step 2: 计算指标
        print("  [2/5] 计算 KPI 指标...")
        engine = MetricEngine()
        metrics = engine.compute_all(df_coupon, df_sales)
        log_entry["metrics"] = {
            "roi": metrics.get("roi"),
            "conversion_rate": metrics.get("conversion_rate"),
            "total_sales": metrics.get("total_sales"),
            "member_contribution": metrics.get("member_contribution"),
            "total_issued": metrics.get("total_issued"),
        }

        # Step 3: 异常检测
        print("  [3/5] 运行异常检测...")
        detector = AnomalyDetector(contamination=0.1)
        df_c = df_coupon.copy()
        df_c["month"] = df_c["create_time"].dt.to_period("M").dt.to_timestamp()
        trend = df_c.groupby("month").agg(
            issued=("coupon_record_id", "count"),
            redeemed=("status_code", lambda x: (x == 1).sum()),
        ).reset_index()

        df_s = df_sales.copy()
        df_s["month"] = df_s["销售时间"].dt.to_period("M").dt.to_timestamp()
        sales_trend = df_s.groupby("month")["销售额"].sum().reset_index(name="sales")

        trend_merged = pd.merge(trend, sales_trend, on="month", how="outer").fillna(0)
        anomaly_result = detector.detect(trend_merged, "sales", "month")

        # Step 4: AI 诊断
        print("  [4/5] AI 诊断中...")
        api_key = _load_api_key()
        insight_gen = InsightGenerator(api_key=api_key if api_key else None)
        insight = insight_gen.generate(metrics, anomaly_results={
            "anomaly_count": anomaly_result["anomaly_count"],
            "anomalies": anomaly_result["anomalies"][:3] if anomaly_result["anomalies"] else [],
        })

        alerts = insight.get("alerts", [])
        recommendations = insight.get("recommendations", [])
        summary = insight.get("executive_summary", "")
        generated_by = insight.get("generated_by", "unknown")

        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
        log_entry["alerts_count"] = len(alerts)
        log_entry["critical_count"] = len(critical_alerts)

        print(f"  诊断完成 ({generated_by})")
        print(f"  告警: {len(alerts)} 项 (严重: {len(critical_alerts)})")
        for a in alerts:
            print(f"    [{a.get('severity', '?')}] {a.get('message', '')[:80]}")

        # Step 5: Agent 行动 (仅在有 critical 告警时发邮件)
        print("  [5/5] Agent 行动...")

        if critical_alerts:
            subject = f"{len(critical_alerts)}项严重告警 — ROI {metrics.get('roi', 0):.1f}%"
            email_result = agent.send_alert_email(
                subject=subject,
                metrics=metrics,
                alerts=alerts,
                insight_text=summary,
            )
            log_entry["email_sent"] = email_result.get("success", False)
            print(f"  邮件: {email_result['message']}")
        else:
            print(f"  邮件: 跳过 (无严重告警)")

        # 始终导出报告
        report_result = agent.export_report(
            metrics=metrics,
            alerts=alerts,
            insight_text=summary,
            recommendations=recommendations,
        )
        log_entry["report_saved"] = report_result.get("success", False)
        print(f"  报告: {report_result['message']}")

        log_entry["status"] = "completed"

    except Exception as e:
        log_entry["status"] = "failed"
        log_entry["errors"].append(str(e))
        traceback.print_exc()

    agent.write_log(log_entry)
    print(f"{'='*60}")
    print(f"  巡检结束 — 状态: {log_entry['status']}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Agent 定时巡检服务")
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=None,
        help="巡检间隔 (小时)，不指定则读取配置文件"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  营销 ROI 战情室 — Agent 定时巡检服务")
    print(f"  数据文件: {COUPON_CSV} / {SALES_CSV}")
    print(f"  DeepSeek API: {'已配置' if _load_api_key() else '未配置 (使用本地规则引擎)'}")
    print("=" * 60)

    # 立即执行一次
    run_patrol()

    # 定时循环 — 每 30 秒检查配置变更
    print("\n  进入定时循环 (每 30 秒检查配置变更)...")
    print("  按 Ctrl+C 停止...\n")

    current_interval = None

    while True:
        cfg = load_agent_config()

        if not cfg.get("enabled", False):
            # Agent 已暂停
            if current_interval is not None:
                schedule.clear()
                current_interval = None
                print(f"  [{datetime.now():%H:%M:%S}] Agent 已暂停 (enabled=false)")
            time.sleep(30)
            continue

        # Agent 启用中
        interval = args.interval or cfg.get("interval_hours", 4)

        if interval != current_interval:
            schedule.clear()
            schedule.every(interval).hours.do(run_patrol)
            current_interval = interval
            print(f"  [{datetime.now():%H:%M:%S}] 巡检间隔已更新: 每 {interval} 小时")

        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
