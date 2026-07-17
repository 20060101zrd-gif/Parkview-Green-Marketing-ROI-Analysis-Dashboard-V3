"""
Parkview Green Marketing ROI Dashboard — Flask Web Application
Thin routing layer. All business logic lives in services/.
"""
import os
import sys
import json
import csv
import webbrowser
from io import StringIO
from datetime import datetime

from flask import Flask, render_template, jsonify, request, Response

# Ensure project root is importable
_WEBAPP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_WEBAPP_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from webapp.services.data_service import ds
from webapp.services.kpi_service import (
    compute_all_kpis, compute_coupon_structure, compute_cohort_data,
    compute_cohort_detail, compute_category_revenue,
    compute_trend_data, compute_lag_data,
)
from webapp.services.ml_service import detect_anomalies, compute_kmeans
from webapp.services.ai_service import generate_insight, chat_followup, predict_trend_simulation, generate_analysis, get_ai_enabled, set_ai_enabled
from webapp.services.scheduler_service import DataScheduler

# ----------------------------------------------------------------
# Flask App
# ----------------------------------------------------------------
app = Flask(__name__)

# ----------------------------------------------------------------
# Helper: parse filter params
# ----------------------------------------------------------------
def _parse_filters():
    return {
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
        'levels': request.args.getlist('level') or None,
        'ages': request.args.getlist('age') or None,
    }

# ----------------------------------------------------------------
# PAGE
# ----------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

# ----------------------------------------------------------------
# DATA APIs
# ----------------------------------------------------------------
@app.route('/api/kpis')
def api_kpis():
    df_c, df_s = ds.filter(**_parse_filters())
    return jsonify(compute_all_kpis(df_c, df_s))

@app.route('/api/coupon-structure')
def api_coupon_structure():
    df_c, _ = ds.filter(**_parse_filters())
    return jsonify(compute_coupon_structure(df_c))

@app.route('/api/cohorts')
def api_cohorts():
    df_c, df_s = ds.filter(**_parse_filters())
    return jsonify(compute_cohort_data(df_c, df_s))

@app.route('/api/cohort-detail')
def api_cohort_detail():
    df_c, df_s = ds.filter(**_parse_filters())
    return jsonify(compute_cohort_detail(df_c, df_s))

@app.route('/api/category-revenue')
def api_category_revenue():
    _, df_s = ds.filter(**_parse_filters())
    return jsonify(compute_category_revenue(df_s))

@app.route('/api/trend')
def api_trend():
    df_c, df_s = ds.filter(**_parse_filters())
    granularity = request.args.get('granularity', 'weekly')
    labels, coupon, sales, r = compute_trend_data(df_c, df_s, granularity)
    return jsonify({'labels': labels, 'coupon': coupon, 'sales': sales, 'correlation': r})

@app.route('/api/lag')
def api_lag():
    df_c, df_s = ds.filter(**_parse_filters())
    return jsonify(compute_lag_data(df_c, df_s))

@app.route('/api/summary')
def api_summary():
    return jsonify(ds.summary())

@app.route('/api/filter-options')
def api_filter_options():
    return jsonify(ds.filter_options())

# ----------------------------------------------------------------
# AI & ML APIs
# ----------------------------------------------------------------
@app.route('/api/ai-config', methods=['GET', 'POST'])
def api_ai_config():
    if request.method == 'POST':
        data = request.get_json() or {}
        set_ai_enabled(data.get('enabled', True))
        return jsonify({'success': True, 'ai_enabled': get_ai_enabled()})
    return jsonify({'ai_enabled': get_ai_enabled()})

@app.route('/api/insight')
def api_insight():
    analysis_type = request.args.get('type', 'page_overview')  # page_overview | module_focus
    page = request.args.get('page', 'summary')
    module_name = request.args.get('module', '')

    df_c, df_s = ds.filter(**_parse_filters())
    kpis = compute_all_kpis(df_c, df_s)
    structure = compute_coupon_structure(df_c)
    cohorts = compute_cohort_data(df_c, df_s)
    lag_data = compute_lag_data(df_c, df_s)

    # Three-tier unified analysis
    if analysis_type in ('page_overview', 'module_focus'):
        result = generate_analysis(
            analysis_type=analysis_type,
            kpis=kpis, structure=structure, cohorts=cohorts, lag_data=lag_data,
            page=page, module_name=module_name
        )
        return jsonify(result)

    # Legacy fallback
    anomalies = detect_anomalies(df_c, df_s)
    return jsonify(generate_insight(kpis, structure, cohorts, lag_data, anomalies))

@app.route('/api/anomalies')
def api_anomalies():
    df_c, df_s = ds.filter(**_parse_filters())
    return jsonify(detect_anomalies(df_c, df_s))

@app.route('/api/kmeans')
def api_kmeans():
    df_c, df_s = ds.filter(**_parse_filters())
    cohorts = compute_cohort_data(df_c, df_s)
    return jsonify(compute_kmeans(cohorts))

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    context_module = data.get('context_module', '')  # R7: module context for focused Q&A
    if not question:
        return jsonify({'answer': '请输入问题。'})
    df_c, df_s = ds.filter(**_parse_filters())
    kpis = compute_all_kpis(df_c, df_s)
    cohorts = compute_cohort_data(df_c, df_s)
    structure = compute_coupon_structure(df_c)
    lag_data = compute_lag_data(df_c, df_s)
    # R7: If context_module is provided, prepend module focus to question
    full_question = question
    if context_module:
        full_question = '【当前聚焦模块：' + context_module + '】请专门针对此模块分析：' + question
    return jsonify(chat_followup(full_question, kpis, cohorts=cohorts, structure=structure, lag_data=lag_data))

@app.route('/api/simulation-analysis', methods=['POST'])
def api_simulation_analysis():
    data = request.get_json() or {}
    before = data.get('before', {})
    after = data.get('after', {})
    actions = data.get('actions', [])

    # Fix 7: Use shared DeepSeek key loader (consistent with other AI endpoints)
    from webapp.services.ai_service import _get_deepseek_key
    api_key = _get_deepseek_key()

    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key.strip(), base_url="https://api.deepseek.com/v1")
            prompt = (
                "你是侨福芳草地的营销数据分析师。以下是采纳优化建议前后的 KPI 对比，请给出简洁分析。\n\n"
                "已采纳建议：" + ', '.join(actions) + "\n\n"
                "优化前：\n"
                f"- ROI: {before.get('roi', 0)}%\n"
                f"- 发券量: {before.get('total_issued', 0)} 张\n"
                f"- 核销率: {before.get('conversion_rate', 0)}%\n"
                f"- 总销售额: {before.get('total_sales', 0)} 元\n"
                f"- 客单价: {before.get('aov', 0)} 元\n"
                f"- 会员贡献: {before.get('member_contribution', 0)}%\n\n"
                "优化后（预期）：\n"
                f"- ROI: {after.get('roi', 0)}%\n"
                f"- 发券量: {after.get('total_issued', 0)} 张\n"
                f"- 核销率: {after.get('conversion_rate', 0)}%\n"
                f"- 总销售额: {after.get('total_sales', 0)} 元\n"
                f"- 客单价: {after.get('aov', 0)} 元\n"
                f"- 会员贡献: {after.get('member_contribution', 0)}%\n\n"
                "请输出：\n1. 一句话整体评价\n2. 2-3个关键变化点\n3. 1个潜在风险\n\n"
                "不要 markdown、不要加粗符号、不要 emoji，纯文本分点。120字以内。"
            )
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=250, timeout=20,
            )
            print('[Sim Analysis] DeepSeek success')
            return jsonify({
                'analysis': response.choices[0].message.content.strip(),
                'engine': 'DeepSeek LLM'
            })
        except Exception as e:
            print(f'[Sim Analysis Error] DeepSeek call failed: {type(e).__name__}: {e}')

    # Local fallback
    print(f'[Sim Analysis] Using local rule engine (api_key present: {bool(api_key)})')
    roi_chg = ((after.get('roi', 0) - before.get('roi', 0)) / max(abs(before.get('roi', 1)), 1)) * 100
    return jsonify({
        'analysis': (
            f'整体评价：ROI 提升 {roi_chg:.1f}%，优化方向正确。\n'
            '关键变化：\n'
            '· 发券结构优化，低效停车券减少\n'
            '· 回报率提升，资源效率改善\n'
            '· 精准投放带动质量提升\n'
            '潜在风险：短期客流量可能下降'
        ),
        'engine': '本地规则引擎'
    })

# Prompt 1: AI trend + lag prediction after simulation
@app.route('/api/simulation-trend', methods=['POST'])
def api_simulation_trend():
    data = request.get_json() or {}
    before_trend = data.get('before_trend', {})
    before_lag = data.get('before_lag', [])
    actions = data.get('actions', [])
    result = predict_trend_simulation(before_trend, before_lag, actions)
    return jsonify(result)

# ----------------------------------------------------------------
# EXPORT APIs
# ----------------------------------------------------------------
@app.route('/api/export-report', methods=['POST'])
def api_export_report():
    data = request.get_json() or {}
    metrics = data.get('metrics') or compute_all_kpis(*ds.filter())
    alerts = data.get('alerts', [])
    insight_text = data.get('insight_text', '')
    recommendations = data.get('recommendations', [])

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    alert_lines = "".join(f"- **[{a.get('severity', '')}]** {a.get('message', '')}\n" for a in alerts)
    rec_lines = "".join(f"{i}. {r}\n" for i, r in enumerate(recommendations, 1))

    report = f"""# 营销 ROI 战情室 — 诊断报告

> 生成时间: {now}

## 核心指标
| 指标 | 数值 | 来源 |
|:---|---:|:---|
| ROI | {metrics.get('roi', 'N/A')}% | 估算值 |
| 核销转化率 | {metrics.get('conversion_rate', 'N/A')}% | 真实统计 |
| 总销售额 | CNY {metrics.get('total_sales', 0):,.0f} | 真实统计 |
| 客单价 | CNY {metrics.get('aov', 0):,.0f} | 真实统计 |
| 会员贡献占比 | {metrics.get('member_contribution', 'N/A')}% | 真实统计 |
| 券销售渗透率 | {metrics.get('coupon_leverage', 'N/A')}% | 真实统计 |
| 总发券量 | {metrics.get('total_issued', 0):,} | 真实统计 |
| 实际核销量 | {metrics.get('total_redeemed', 0):,} | 真实统计 |

## AI 诊断
[AI生成] {insight_text}

## 告警详情 ({len(alerts)} 项)
{alert_lines}

## 执行建议
{rec_lines or '暂无具体建议。'}

---
*数据真实性说明：发券量、销售额、核销率、客单价等基础指标均来自 CSV 原始数据真实聚合。ROI 为估算值，基于券种单张成本假设推算，非财务精确值。客群四象限标签由规则引擎自动判定，阈值可配置。LLM 模式下的文字洞察由 AI 生成，仅供参考。*

---
*此报告由 AI 战情室 Agent 自动生成*
"""
    os.makedirs(os.path.join(_PROJECT_ROOT, "data", "reports"), exist_ok=True)
    filename = f"data/reports/战情报告_{file_ts}.md"
    fullpath = os.path.join(_PROJECT_ROOT, filename)
    with open(fullpath, "w", encoding="utf-8") as f:
        f.write(report)

    return jsonify({"success": True, "message": f"报告已保存: {filename}", "filepath": filename, "content": report})

@app.route('/api/export-kpi-csv')
def api_export_kpi_csv():
    kpis = compute_all_kpis(*ds.filter())
    si = StringIO()
    w = csv.writer(si)
    w.writerow(['指标', '数值', '单位'])
    w.writerow(['总发券量', kpis['total_issued'], '张'])
    w.writerow(['真实核销量', kpis['real_used'], '张'])
    w.writerow(['核销转化率', kpis['conversion_rate'], '%'])
    w.writerow(['总销售额', kpis['total_sales'], 'CNY'])
    w.writerow(['客单价', kpis['aov'], 'CNY'])
    w.writerow(['会员贡献占比', kpis['member_contribution'], '%'])
    w.writerow(['营销投资回报率', kpis['roi'], '%'])
    w.writerow(['动销渗透率', kpis['coupon_leverage'], '%'])
    w.writerow(['整体核销率', kpis['redeem_rate'], '%'])
    return Response(si.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": "attachment; filename=kpi_report.csv"})

@app.route('/api/export-cohort-csv')
def api_export_cohort_csv():
    detail = compute_cohort_detail(*ds.filter())
    si = StringIO()
    if detail:
        w = csv.DictWriter(si, fieldnames=detail[0].keys())
        w.writeheader()
        w.writerows(detail)
    return Response(si.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": "attachment; filename=cohort_diagnosis.csv"})

# ----------------------------------------------------------------
# SCHEDULER APIs
# ----------------------------------------------------------------
@app.route('/api/scheduler-config', methods=['GET'])
def api_scheduler_config_get():
    return jsonify(DataScheduler.get_instance().get_config())

@app.route('/api/scheduler-config', methods=['POST'])
def api_scheduler_config_post():
    body = request.get_json() or {}
    result = DataScheduler.get_instance().configure(
        watch_dir=body.get('watch_dir'),
        interval_hours=body.get('interval_hours'),
        enabled=body.get('enabled'),
        # R2: Email notification config
        notify_email=body.get('notify_email'),
        email_enabled=body.get('email_enabled'),
        smtp_host=body.get('smtp_host'),
        smtp_port=body.get('smtp_port'),
        smtp_user=body.get('smtp_user'),
        smtp_pass=body.get('smtp_pass'),
    )
    return jsonify(result)

@app.route('/api/scheduler-trigger', methods=['POST'])
def api_scheduler_trigger():
    result = DataScheduler.get_instance().pull_and_reload()
    return jsonify({'success': True, 'result': result})

# ----------------------------------------------------------------
# UPLOAD API
# ----------------------------------------------------------------
import os as _os

@app.route('/api/upload-data', methods=['POST'])
def api_upload_data():
    input_file = request.files.get('input_file')
    output_file = request.files.get('output_file')
    if not input_file and not output_file:
        return jsonify({'success': False, 'message': '请至少选择一个文件'}), 400

    saved = []
    data_dir = _os.path.join(_PROJECT_ROOT, 'data')

    if input_file and input_file.filename:
        if not input_file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': '仅支持 CSV 文件'}), 400
        dest = _os.path.join(data_dir, 'BI_Dashboard_Ready_Data.csv')
        input_file.save(dest)
        saved.append('input_file')

    if output_file and output_file.filename:
        if not output_file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': '仅支持 CSV 文件'}), 400
        dest = _os.path.join(data_dir, '销售查询.csv')
        output_file.save(dest)
        saved.append('output_file')

    if saved:
        try:
            ds.reload()
        except Exception as e:
            return jsonify({'success': False, 'message': '文件已保存但重载失败: ' + str(e)}), 500

    return jsonify({'success': True, 'message': '已上传并刷新', 'files': saved})

# ----------------------------------------------------------------
# STARTUP
# ----------------------------------------------------------------
if __name__ == '__main__':
    url = "http://127.0.0.1:8050"
    print(f"\n{'='*60}")
    print(f"  侨福芳草地 · 营销效能战情室")
    print(f"  Flask Web Application v3.0")
    print(f"  Opening: {url}")
    print(f"{'='*60}\n")
    webbrowser.open(url)
    app.run(debug=False, host='0.0.0.0', port=8050)
