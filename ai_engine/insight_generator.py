"""
Dual-mode Insight Generator
- Mode A: DeepSeek LLM (requires API key)
- Mode B: Local template engine (zero-dependency fallback)
"""

import os
import json
import streamlit as st
from typing import Optional


class InsightGenerator:
    """Generates business insights from KPI metrics using DeepSeek or templates."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.client = None
        self.mode = "template"

        if self.api_key and self.api_key.strip():
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.deepseek.com/v1"
                )
                self.mode = "deepseek"
            except Exception:
                pass

    def generate(self, metrics: dict, anomaly_results: dict = None,
                 clustering_results: dict = None) -> dict:
        """Unified entry point. Auto-selects mode with graceful fallback."""
        if self.mode == "deepseek":
            try:
                return self._generate_deepseek(metrics, anomaly_results, clustering_results)
            except Exception:
                pass
        return self._generate_template(metrics, anomaly_results, clustering_results)

    def _generate_deepseek(self, metrics, anomaly_results, clustering_results) -> dict:
        prompt = self._build_prompt(metrics, anomaly_results, clustering_results)

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一名商业综合体的高级数据分析师。"
                            "请根据提供的营销数据指标，生成简洁、专业、可执行的业务洞察。"
                            "回复必须为严格的 JSON 格式，包含以下字段:"
                            "{'executive_summary': '120字以内的核心摘要(中文)',"
                            "'alerts': [{'severity': 'critical/warning/info', 'message': '...'}],"
                            "'recommendations': ['建议1', '建议2'],"
                            "'top_finding': '最重要发现(50字内)'}"
                            "不要使用 emoji。语言专业克制。直接返回 JSON 字符串，不要 Markdown 代码块。"
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600,
                timeout=30,
            )
        except Exception as e:
            raise RuntimeError(f"DeepSeek API 调用失败: {type(e).__name__}: {e}") from e

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"DeepSeek 返回非 JSON 内容: {content[:200]}") from e

        result['generated_by'] = 'DeepSeek LLM'
        return result

    def _build_prompt(self, metrics, anomaly_results, clustering_results) -> str:
        lines = ["Analyze the following marketing performance data and provide insights:\n"]

        lines.append("## Core KPIs")
        lines.append(f"- ROI: {metrics.get('roi', 'N/A')}%")
        lines.append(f"- Conversion Rate: {metrics.get('conversion_rate', 'N/A')}%")
        lines.append(f"- Total Coupons Issued: {metrics.get('total_issued', 'N/A'):,}")
        lines.append(f"- Total Sales: CNY {metrics.get('total_sales', 'N/A'):,.0f}")
        lines.append(f"- Avg Order Value: CNY {metrics.get('aov', 'N/A'):,.0f}")
        lines.append(f"- Member Sales Share: {metrics.get('member_contribution', 'N/A')}%")
        lines.append(f"- Coupon Sales Penetration: {metrics.get('coupon_leverage', 'N/A')}%")

        structure = metrics.get('coupon_structure', {})
        if structure:
            lines.append("\n## Coupon Type Structure")
            for k, v in structure.get('percentages', {}).items():
                lines.append(f"- {k}: {v:.1f}%")

        cohort_data = metrics.get('cohort_data', [])
        if cohort_data:
            lines.append("\n## Cohort Overview (top 5 by sales)")
            for c in cohort_data[:5]:
                lines.append(
                    f"- {c['level']}/{c['age_group']}: "
                    f"Sales CNY {c['sales']:,.0f}, ATV CNY {c['atv']:,.0f}, "
                    f"Redeem Rate {c['redeem_rate']:.1%}"
                )

        if anomaly_results:
            lines.append(f"\n## Anomaly Detection: {anomaly_results.get('anomaly_count', 0)} anomalies found")

        lines.append("\nFocus on: 1) structural misallocation of marketing resources, "
                     "2) which cohort to scale up / scale down, "
                     "3) top 1-2 actionable recommendations.")

        return "\n".join(lines)

    def _generate_template(self, metrics, anomaly_results, clustering_results) -> dict:
        """Local rule-based insight generator — zero dependency fallback."""
        alerts = []
        recommendations = []
        insights = []

        roi = metrics.get('roi', 0)
        conversion = metrics.get('conversion_rate', 0)
        penetration = metrics.get('coupon_leverage', 0)
        member_pct = metrics.get('member_contribution', 0)

        structure = metrics.get('coupon_structure', {})
        parking_share = structure.get('parking_share', 0)

        # Alert: Parking coupon over-allocation
        if parking_share > 70:
            alerts.append({
                'severity': 'critical',
                'message': f'停车券占发券总量 {parking_share:.0f}%,核销率极低,存在严重结构性错配。'
            })
            recommendations.append(
                f'将停车券预算削减 50% (约 CNY 120,000),重新分配至高 ROI 客群专属体验券。'
            )

        # Alert: Low ROI
        if roi < 10:
            alerts.append({
                'severity': 'critical',
                'message': f'营销投资回报率仅 {roi:.1f}%,需立即审查营销活动效果。'
            })
        elif roi < 30:
            alerts.append({
                'severity': 'warning',
                'message': f'营销投资回报率为 {roi:.1f}%,利润空间承压。'
            })

        # Alert: Low conversion
        if conversion < 1.0:
            alerts.append({
                'severity': 'warning',
                'message': f'Redemption conversion at {conversion:.2f}% — coupon incentive design may need re-evaluation.'
            })

        # Alert: Low penetration
        if penetration < 0.05:
            alerts.append({
                'severity': 'warning',
                'message': f'Coupon-driven sales penetration is only {penetration:.3f}% — minimal marketing leverage on total business.'
            })

        # Find top cohort
        cohort_data = metrics.get('cohort_data', [])
        high_roi_cohorts = [c for c in cohort_data if c.get('redeem_rate', 0) >= 0.01 and c.get('atv', 0) >= 500]
        drain_cohorts = [c for c in cohort_data if c.get('avg_coupons_per_person', 0) >= 5 and c.get('atv', 0) < 200]

        if high_roi_cohorts:
            best = high_roi_cohorts[0]
            insights.append(
                f'{best["level"]}/{best["age_group"]} 是最优 ROI 转化客群:'
                f'客单价 CNY {best["atv"]:,.0f},核销率 {best["redeem_rate"]:.1%}。'
                f'建议加大该客群的营销预算倾斜。'
            )
            recommendations.append(
                f'将 80% 营销预算集中投放至 {best["level"]}/{best["age_group"]} 客群,'
                f'预计 ROI 可提升 3 倍。'
            )

        if drain_cohorts:
            worst = drain_cohorts[0]
            alerts.append({
                'severity': 'warning',
                'message': f'{worst["level"]}/{worst["age_group"]} 被判定为券效耗损型客群:'
                           f'人均领券 {worst["avg_coupons_per_person"]:.0f} 张,'
                           f'客单价仅 CNY {worst["atv"]:,.0f}。'
            })
            recommendations.append(
                f'对 {worst["level"]}/{worst["age_group"]} 客群实施发券熔断,'
                f'限制 3 张/人/月。'
            )

        # Executive summary
        exec_insights = []
        if roi > 30:
            exec_insights.append(f'当前营销投资回报率为 {roi:.1f}%,整体呈正向回报。')
        else:
            exec_insights.append(f'当前营销投资回报率为 {roi:.1f}%,需要密切关注。')

        if parking_share > 70:
            exec_insights.append(
                f'However, parking coupons dominate {parking_share:.0f}% of issuance with near-zero conversion, '
                f'representing a significant resource misallocation.'
            )

        if high_roi_cohorts:
            best = high_roi_cohorts[0]
            exec_insights.append(
                f'{best["level"]}/{best["age_group"]} 被识别为最优转化客群,'
                f'兼具营销敏感度与单笔回报,建议作为预算倾斜的核心对象。'
            )

        return {
            'executive_summary': ' '.join(exec_insights) if exec_insights else '当前数据范围不足,无法生成完整诊断。',
            'alerts': alerts if alerts else [{'severity': 'info', 'message': '当前数据范围内未检测到关键告警。'}],
            'recommendations': recommendations if recommendations else ['持续监控各客群表现,关注新出现的转化模式。'],
            'top_finding': insights[0][:50] if insights else '数据范围过窄,无法形成明确结论。',
            'generated_by': '本地规则引擎',
        }

    def ask_followup(self, question: str, context_metrics: dict,
                     previous_insight: str = "") -> str:
        """基于当前数据上下文的自由追问。"""
        if self.mode != "deepseek" or self.client is None:
            return "DeepSeek API 暂未配置,无法进行追问。请在 .streamlit/secrets.toml 中设置 DEEPSEEK_API_KEY。"

        try:
            prompt = (
                f"当前战情室数据上下文:\n"
                f"- 营销投资回报率: {context_metrics.get('roi', 'N/A')}%\n"
                f"- 总销售额: CNY {context_metrics.get('total_sales', 'N/A'):,.0f}\n"
                f"- 核销转化率: {context_metrics.get('conversion_rate', 'N/A')}%\n"
                f"- 会员贡献占比: {context_metrics.get('member_contribution', 'N/A')}%\n\n"
                f"先前的诊断摘要: {previous_insight}\n\n"
                f"用户提问: {question}\n\n"
                f"请以商业综合体高级数据分析师的身份回答。要求:数据驱动、可落地、简洁。"
                f"使用中文,不要使用 emoji。"
            )

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=500,
                timeout=30,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"暂时无法处理追问 (DeepSeek API 错误): {type(e).__name__}: {e}"
