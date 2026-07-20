
"""
AI Service — DeepSeek LLM + local template engine for business insights.
Graceful fallback: if DeepSeek API is unavailable, uses rule-based templates.
"""
import os
import json

# Resolve project root: webapp/services/ai_service.py -> ../../ -> project root
_SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
_WEBAPP_DIR = os.path.dirname(_SERVICE_DIR)
BASE_DIR = os.path.dirname(_WEBAPP_DIR)

# Global AI toggle
AI_ENABLED = False  # Default: local rule mode

def set_ai_enabled(enabled):
    global AI_ENABLED
    AI_ENABLED = bool(enabled)

def get_ai_enabled():
    return AI_ENABLED


def _get_deepseek_key():
    """Try to load DeepSeek API key from env or .streamlit/secrets.toml."""
    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        print(f'[DeepSeek] Key loaded from env ({len(key)} chars)')
        return key
    try:
        import tomli
        secrets_path = os.path.join(BASE_DIR, '.streamlit', 'secrets.toml')
        print(f'[DeepSeek] Checking secrets: {secrets_path} (exists={os.path.exists(secrets_path)})')
        if os.path.exists(secrets_path):
            with open(secrets_path, 'rb') as f:
                key = tomli.load(f).get('DEEPSEEK_API_KEY', '')
                if key:
                    print(f'[DeepSeek] Key loaded from secrets.toml ({len(key)} chars)')
                return key
    except Exception as e:
        print(f'[DeepSeek] Load error: {e}')
    print('[DeepSeek] No API key found, using local engine')
    return ''


def generate_insight(kpis, structure, cohorts, lag_data, anomalies):
    """
    Generate AI-powered business insight. DeepSeek first, local fallback.
    """
    template = _build_template_insight(kpis, structure, cohorts, lag_data)
    template['anomaly'] = anomalies

    api_key = _get_deepseek_key()
    if not api_key:
        print('[Insight] No DeepSeek key, using local template')
        return template

    try:
        deepseek = _call_deepseek(kpis, structure, cohorts, anomalies, api_key)
        if deepseek:
            deepseek['anomaly'] = anomalies
            return deepseek
    except Exception as e:
        print(f'[Insight] DeepSeek failed: {type(e).__name__}: {e}')

    return template


def _build_template_insight(kpis, structure, cohorts, lag_data):
    """Local rule-based insight generator (matches Streamlit ai_engine)."""
    alerts = []
    recommendations = []
    insights = []

    roi = kpis.get('roi', 0)
    conversion = kpis.get('conversion_rate', 0)
    penetration = kpis.get('coupon_leverage', 0)

    parking_share = 0
    for s in structure:
        if '停车' in s.get('name', ''):
            parking_share = s.get('pct', 0)
            break

    if parking_share > 70:
        alerts.append({
            'severity': 'critical',
            'message': f'停车券占发券总量 {parking_share:.0f}%，核销率极低，存在严重结构性错配。'
        })
        recommendations.append({
            'text': f'将停车券预算削减 50%（约 CNY 120,000），重新分配至高 ROI 客群专属体验券。',
            'action': '削减停车券50%',
            'effect': 'coupon_volume',
            'pct': -50,
        })

    if roi < 10:
        alerts.append({
            'severity': 'critical',
            'message': f'营销投资回报率仅 {roi:.1f}%，需立即审查营销活动效果。'
        })
    elif roi < 30:
        alerts.append({
            'severity': 'warning',
            'message': f'营销投资回报率为 {roi:.1f}%，利润空间承压。'
        })

    if conversion < 1.0:
        alerts.append({
            'severity': 'warning',
            'message': f'核销转化率仅 {conversion:.2f}% — 券激励设计可能需要重新评估。'
        })

    if penetration < 0.05:
        alerts.append({
            'severity': 'warning',
            'message': f'发券动销渗透率仅 {penetration:.3f}% — 营销杠杆效应极弱。'
        })

    high_roi = [c for c in cohorts if c.get('redeem_rate', 0) >= 1 and c.get('atv', 0) >= 500]
    drain = [c for c in cohorts if c.get('avg_coupons', 0) >= 5 and c.get('atv', 0) < 200]

    if high_roi:
        best = high_roi[0]
        insights.append(
            f'{best["level"]}/{best["age_group"]} 是最优 ROI 转化客群：'
            f'客单价 CNY {best["atv"]:,.0f}，核销率 {best["redeem_rate"]:.1f}%。'
            f'建议加大该客群的营销预算倾斜。'
        )
        recommendations.append({
            'text': f'将 80% 营销预算集中投放至 {best["level"]}/{best["age_group"]} 客群，预计 ROI 可提升 3 倍。',
            'action': f'加大{best["level"]}客群投放',
            'effect': 'sales_efficiency',
            'pct': 30,
        })

    if drain:
        worst = drain[0]
        alerts.append({
            'severity': 'warning',
            'message': f'{worst["level"]}/{worst["age_group"]} 被判定为券效耗损型客群：'
                       f'人均领券 {worst["avg_coupons"]:.0f} 张，客单价仅 CNY {worst["atv"]:,.0f}。'
        })
        recommendations.append({
            'text': f'对 {worst["level"]}/{worst["age_group"]} 客群实施发券熔断，限制 3 张/人/月。',
            'action': f'熔断{worst["level"]}客群',
            'effect': 'coupon_volume',
            'pct': -80,
        })

    # Executive summary
    exec_parts = []
    exec_parts.append(
        f'当前营销投资回报率为 {roi:.1f}%，{"整体呈正向回报" if roi > 30 else "需要密切关注"}。'
    )
    if parking_share > 70:
        exec_parts.append(f'停车券占发券总量 {parking_share:.0f}%，但核销率极低，代表严重的资源错配。')
    if high_roi:
        best = high_roi[0]
        exec_parts.append(
            f'{best["level"]}/{best["age_group"]} 被识别为最优转化客群，建议作为预算倾斜的核心对象。'
        )

    return {
        'executive_summary': ' '.join(exec_parts) if exec_parts else '当前数据范围不足，无法生成完整诊断。',
        'alerts': alerts or [{'severity': 'info', 'message': '当前数据范围内未检测到关键告警。'}],
        'recommendations': recommendations or [{'text': '持续监控各客群表现，关注新出现的转化模式。', 'action': '持续监控', 'effect': 'sales_efficiency', 'pct': 5}],
        'top_finding': insights[0][:80] if insights else '数据范围过窄，无法形成明确结论。',
        'generated_by': '本地规则引擎',
    }


def _call_deepseek(kpis, structure, cohorts, anomalies, api_key):
    """Call DeepSeek API with full data context. Returns dict on success, None on failure."""
    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(api_key=api_key.strip(), base_url="https://api.deepseek.com/v1")

    parking_share = 0
    for s in structure:
        if '停车' in s.get('name', ''):
            parking_share = s.get('pct', 0)
            break

    lines = ["营销数据洞察分析，数据如下：\n"]
    lines.append(f"- ROI: {kpis.get('roi')}%")
    lines.append(f"- 核销率: {kpis.get('conversion_rate')}%")
    lines.append(f"- 总发券: {kpis.get('total_issued'):,} 张")
    lines.append(f"- 总销售额: CNY {kpis.get('total_sales'):,.0f}")
    lines.append(f"- 客单价: CNY {kpis.get('aov'):,.0f}")
    lines.append(f"- 会员贡献: {kpis.get('member_contribution')}%")
    lines.append(f"- 停车券占比: {parking_share:.1f}%")

    green = [c for c in cohorts if c.get('tag') == 'GREEN']
    red = [c for c in cohorts if c.get('tag') == 'RED']
    gold = [c for c in cohorts if c.get('tag') == 'GOLD']
    lines.append(f"- GREEN 高转化客群: {len(green)} 组")
    lines.append(f"- RED 耗损客群: {len(red)} 组")
    lines.append(f"- GOLD 高价值客群: {len(gold)} 组")
    if green:
        best = green[0]
        lines.append(f"  · 最优客群: {best.get('level')}/{best.get('age_group')}, 客单价¥{best.get('atv',0):,.0f}")
    if red:
        worst = red[0]
        lines.append(f"  · 耗损客群: {worst.get('level')}/{worst.get('age_group')}, 人均领券{worst.get('avg_coupons',0)}张")

    if anomalies:
        lines.append(f"- 异常检测: {anomalies.get('anomaly_count', 0)} 个异常点")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": (
                "你是侨福芳草地的高级营销数据分析师。请基于给定数据生成专业洞察。"
                "严格返回 JSON 格式，不要 markdown 代码块，字段如下："
                '{"executive_summary": "100字以内中文核心结论",'
                '"alerts": [{"severity":"critical/warning/info","message":"..."}],'
                '"recommendations": [{"text": "建议文字描述", "action": "建议标题", "effect": "coupon_volume|sales_efficiency|lag_correlation", "pct": 数值}],'
                '"top_finding": "最重要发现50字以内"}\n'
                "effect 字段只能从以下三个对称维度中选择：\n"
                "- coupon_volume: 调整发券量，正数为增发，负数为削减\n"
                "- sales_efficiency: 调整销售额/转化效率，正数为提升，负数为下降\n"
                "- lag_correlation: 调整发券滞后效应强度，正数为增强相关性，负数为减弱\n"
                "pct 为百分比数值，如 30 表示 +30%，-60 表示 -60%。"
                "不要用 emoji，不要用 ** 加粗，纯中文。"
            )},
            {"role": "user", "content": "\n".join(lines)}
        ],
        temperature=0.4, max_tokens=600, timeout=30,
    )

    content = response.choices[0].message.content.strip()
    print(f'[Insight] DeepSeek raw (first 200): {content[:200]}')

    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    result = json.loads(content)
    result['generated_by'] = 'DeepSeek LLM'
    print('[Insight] DeepSeek success')
    return result


# ===== Three-Tier Unified Analysis Architecture =====

def _call_deepseek_raw(system_prompt, user_prompt, temperature=0.4, max_tokens=600):
    """Shared DeepSeek call — returns raw string or None on failure."""
    if not AI_ENABLED:
        return None
    api_key = _get_deepseek_key()
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key.strip(), base_url="https://api.deepseek.com/v1")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature, max_tokens=max_tokens, timeout=10,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f'[DeepSeek Raw] Error: {e}')
        return None


def _build_kpi_context(kpis, structure, cohorts, lag_data):
    """Build a compact data context string from all data sources."""
    lines = []
    if kpis:
        lines.append(f"ROI: {kpis.get('roi', 0)}% | 核销率: {kpis.get('conversion_rate', 0)}% | 发券: {kpis.get('total_issued', 0):,}张 | 销售额: CNY{kpis.get('total_sales', 0):,.0f} | 客单价: CNY{kpis.get('aov', 0):,.0f} | 会员贡献: {kpis.get('member_contribution', 0)}%")
    if structure:
        lines.append("券种: " + ", ".join(f"{s['name']}({s['pct']}%)" for s in structure[:5]))
    if cohorts:
        tags = {'GREEN': 0, 'GOLD': 0, 'RED': 0, 'GRAY': 0}
        for c in cohorts: tags[c.get('tag', 'GRAY')] = tags.get(c.get('tag', 'GRAY'), 0) + 1
        lines.append(f"客群: GREEN{tags['GREEN']}组 GOLD{tags['GOLD']}组 RED{tags['RED']}组 GRAY{tags['GRAY']}组")
    if lag_data:
        best = max(lag_data, key=lambda x: x.get('r', 0)) if lag_data else {}
        lines.append(f"最佳滞后: {best.get('lag','?')}天 r={best.get('r', 0):.2f}")
    return '\n'.join(lines)


def generate_analysis(analysis_type, kpis=None, structure=None, cohorts=None, lag_data=None, page=None, module_name=None, extra_context=None):
    """
    Unified dispatcher for three-tier analysis.
    analysis_type: 'page_overview' | 'module_focus' | 'chat'
    Returns dict with 'content' (or structured fields) + 'generated_by'.
    """
    ctx = _build_kpi_context(kpis, structure, cohorts, lag_data)

    # ---- PAGE OVERVIEW ----
    if analysis_type == 'page_overview':
        page_map = {
            'summary': '战情摘要（整体概览）', 'kpi': 'KPI 总览', 'structure': '投入产出结构',
            'trend': '趋势滞后分析', 'cohort': '客群价值诊断', 'insight': '智能诊室'
        }
        page_label = page_map.get(page, '战情摘要')
        system_prompt = (
            "你是侨福芳草地购物中心的商业智能分析师。请基于当前页面数据输出结构化整体洞察。"
            "严格返回 JSON（不要 markdown 代码块）："
            '{"summary": "1-2句核心结论", "findings": ["关键发现1", "关键发现2", "关键发现3"], "recommendation": "1条最优先建议"}'
            "纯中文，不要 emoji，不要 ** 加粗。"
        )
        user_prompt = f"当前页面：{page_label}\n\n数据：\n{ctx}"
        result = _call_deepseek_raw(system_prompt, user_prompt)
        if result:
            try:
                if result.startswith("```"): result = result.replace("```json", "").replace("```", "").strip()
                data = json.loads(result)
                data['generated_by'] = 'DeepSeek LLM'
                return data
            except Exception:
                pass
        # Local fallback for page overview — derive findings from real data
        findings = []
        recommendation = '可点击各模块标题查看针对性分析'
        summary = f'当前{page_label}页面已加载数据。'

        if kpis:
            roi = kpis.get('roi', 0)
            conversion = kpis.get('conversion_rate', 0)
            summary = f'营销投资回报率 {roi}%，核销率 {conversion}%，整体呈{"正向" if roi > 30 else "承压"}状态。'
            if roi < 10:
                findings.append(f'ROI 仅 {roi}%，低于 10% 安全线，需立即审查营销效果')
            elif roi < 30:
                findings.append(f'ROI 为 {roi}%，低于 30% 警戒线，利润空间承压')
            else:
                findings.append(f'ROI 达到 {roi}%，整体回报健康')
            if conversion < 1.0:
                findings.append(f'核销转化率仅 {conversion}%，券激励设计需要重新评估')

        if structure:
            parking = next((s for s in structure if '停车' in s.get('name', '')), None)
            if parking and parking.get('pct', 0) > 70:
                findings.append(f'停车券占比 {parking["pct"]}%，结构单一，存在资源错配')
                recommendation = '建议削减停车券预算，转移至高 ROI 客群专属体验券'

        if cohorts:
            tags = {'GREEN': 0, 'GOLD': 0, 'RED': 0, 'GRAY': 0}
            for c in cohorts: tags[c.get('tag', 'GRAY')] = tags.get(c.get('tag', 'GRAY'), 0) + 1
            if tags['RED'] > 0:
                findings.append(f'识别出 {tags["RED"]} 个 RED 耗损型客群，建议实施发券熔断')
            if tags['GREEN'] > 0:
                findings.append(f'识别出 {tags["GREEN"]} 个 GREEN 高转化客群，建议加大投放')

        if lag_data:
            best = max(lag_data, key=lambda x: x.get('r', 0))
            findings.append(f'最佳发券窗口为消费前 {best.get("lag", 0)} 天（r={best.get("r", 0):.2f}）')

        if not findings:
            findings = ['数据已加载完成，可进入各模块查看详细分析']

        return {
            'summary': summary,
            'findings': findings[:3],
            'recommendation': recommendation,
            'generated_by': '本地规则引擎',
        }

    # ---- MODULE FOCUS ----
    elif analysis_type == 'module_focus':
        mod = module_name or '未知模块'
        system_prompt = (
            "你是侨福芳草地购物中心的数据解读专家。针对指定模块给出精炼分析。"
            "返回 JSON（不要 markdown 代码块）："
            '{"insight": "2-3句针对性分析（不超过100字）", "finding": "1个关键数据发现"}'
            "纯中文，不要 emoji，不要 ** 加粗。"
        )
        user_prompt = f"分析模块：{mod}\n\n数据：\n{ctx}"
        result = _call_deepseek_raw(system_prompt, user_prompt, max_tokens=300)
        if result:
            try:
                if result.startswith("```"): result = result.replace("```json", "").replace("```", "").strip()
                data = json.loads(result)
                data['generated_by'] = 'DeepSeek LLM'
                return data
            except Exception:
                pass
        # Local fallback for module focus
        return {
            'insight': f'「{mod}」模块数据已加载，可在此查看详细指标。建议结合其他模块进行交叉分析。',
            'finding': '数据正常，未检测到异常',
            'generated_by': '本地规则引擎',
        }

    # ---- CHAT (delegates to existing) ----
    elif analysis_type == 'chat':
        return {'content': '请使用 /api/chat 接口进行对话问答', 'generated_by': '路由提示'}

    return {'content': '未知分析类型', 'generated_by': '系统'}


def chat_followup(question, kpis, cohorts=None, structure=None, lag_data=None):
    """Free-form Q&A with DeepSeek (falls back to template answer).

    Injects full data context (KPIs + cohorts + structure + lag) so the LLM
    can answer specific questions about customer segments, coupon types, etc.
    """
    roi_val = kpis.get('roi', 0)
    conversion_val = kpis.get('conversion_rate', 0)
    member_val = kpis.get('member_contribution', 0)
    total_sales = kpis.get('total_sales', 0)
    total_issued = kpis.get('total_issued', 0)
    total_orders = kpis.get('total_orders', 0)
    real_used = kpis.get('real_used', 0)
    aov = kpis.get('aov', 0)
    coupon_leverage = kpis.get('coupon_leverage', 0)
    redeem_rate = kpis.get('redeem_rate', 0)

    api_key = _get_deepseek_key()
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key.strip(), base_url="https://api.deepseek.com/v1")

            # Build full data context
            data_lines = ["当前数据面板的真实数值（回答时必须严格引用，禁止编造）：\n"]
            data_lines.append("【核心KPI】")
            data_lines.append(f"- 营销投资回报率 (ROI): {roi_val}%")
            data_lines.append(f"- 总发券量: {total_issued:,} 张")
            data_lines.append(f"- 真实核销量: {real_used:,} 张")
            data_lines.append(f"- 核销转化率: {conversion_val}%")
            data_lines.append(f"- 整体核销率: {redeem_rate}%")
            data_lines.append(f"- 总销售额: CNY {total_sales:,.0f}")
            data_lines.append(f"- 总交易笔数: {total_orders:,} 笔")
            data_lines.append(f"- 客单价 (AOV): CNY {aov:,.0f}")
            data_lines.append(f"- 会员贡献占比: {member_val}%")
            data_lines.append(f"- 发券动销渗透率: {coupon_leverage}%")

            # Cohort data
            if cohorts and len(cohorts) > 0:
                data_lines.append("\n【客群四象限分类】（会员等级+年龄段交叉分组）")
                data_lines.append("标签定义：GREEN=高ROI转化(核销率>=0.5%且客单价>=300元)；GOLD=自然高价值(客单价>=800元且核销率<1%)；RED=耗损型(人均领券>=2张且客单价<500元)；GRAY=基础客群")
                data_lines.append(f"共 {len(cohorts)} 个客群组，明细如下：")
                for c in cohorts[:8]:
                    data_lines.append(f"  · {c.get('level','?')}/{c.get('age_group','?')}: 发券{c.get('issued',0)}张, 核销{c.get('redeemed',0)}张, 核销率{c.get('redeem_rate',0)}%, 客单价CNY{c.get('atv',0)}, 销售额{c.get('sales',0):,.0f}元 -> 标签{c.get('tag','GRAY')}")

            # Coupon structure
            if structure and len(structure) > 0:
                data_lines.append("\n【券种结构】")
                for s in structure:
                    data_lines.append(f"- {s.get('name','?')}: {s.get('count',0)} 张 ({s.get('pct',0)}%)")

            # Lag analysis
            if lag_data and len(lag_data) > 0:
                best = max(lag_data, key=lambda x: x.get('r', 0))
                data_lines.append(f"\n【滞后分析】最佳滞后窗口: {best.get('lag','?')}天, 皮尔逊相关系数 r={best.get('r',0)}")

            kpi_block = '\n'.join(data_lines)

            system_prompt = (
                "你是侨福芳草地购物中心的高级营销数据分析师。\n"
                "【严格规则】\n"
                "1. 所有数据必须严格使用用户提供的数据，绝对禁止编造、估算或推算\n"
                "2. 数据中没有的信息，直接回答「数据中未包含此信息」\n"
                "3. 回答简洁专业，数据驱动，给出可落地的建议\n"
                "4. 用户问寒暄/闲聊，友好回应并引导回数据分析话题\n"
                "5. 使用中文，不要用 emoji，不要用 markdown 格式（不要 ** 加粗、不要 # 标题）\n"
                "6. 重要结论用分点呈现\n"
                "7. 客群分析、券种结构、滞后效应的数据都已提供，可以直接引用\n"
                "8. 如果用户问「你是谁」「你能做什么」，介绍自己是侨福芳草地营销战情室的 AI 分析师"
            )

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": kpi_block + f"\n\n用户提问: {question}"},
                ],
                temperature=0.3, max_tokens=600, timeout=30,
            )

            answer = response.choices[0].message.content
            return {'answer': answer, 'engine': 'DeepSeek LLM'}
        except Exception as e:
            print(f'[DeepSeek Chat Error] {type(e).__name__}: {e}')

    # ===== Local template engine (enhanced keyword matching) =====
    q = question.strip().lower()
    clean_q = q.rstrip('?!.。？！ ')

    # 1. Greetings
    greetings = {'hi', 'hello', 'hey', '你好', '嗨', '哈喽', '在吗', '在么', '您好', 'hi!', 'hello!'}
    if clean_q in greetings or question.strip() in greetings:
        return {
            'answer': '你好！我是侨福芳草地营销战情室的数据分析师。\n\n我可以帮你分析：\n\u2022 营销 ROI 和投入产出\n\u2022 券种结构和核销表现\n\u2022 客群分层与转化效率\n\u2022 发券滞后效应\n\n试试点击上方的建议提问，或者直接问「当前最大的问题是什么？」',
            'engine': '本地规则引擎'
        }

    # 2. Self-intro
    if any(k in q for k in ['你是谁', '你能做什么', '介绍一下', 'what can you do', 'who are you', '功能']):
        return {
            'answer': '我是营销战情室 AI 助手，基于侨福芳草地真实的发券和销售数据提供分析。\n\n核心能力：\n1. KPI 指标解读（ROI、核销率、客单价等）\n2. 券种结构诊断（停车券占比过高问题）\n3. 客群四象限分析（GREEN/GOLD/RED/GRAY）\n4. 发券滞后效应分析\n5. 模拟优化（采纳建议功能，一键看改良后预期效果）',
            'engine': '本地规则引擎'
        }

    # 3. Boundary: irrelevant questions
    if any(k in q for k in ['天气', 'weather', 'today', '时间', '几点', '星期', 'date', '吃饭', '新闻']):
        return {
            'answer': '抱歉，我是专注于营销数据分析的助手，只能回答发券、销售、客群、ROI 相关的问题。\n\n你可以问：\n\u2022 ROI 现在怎么样？\n\u2022 停车券核销率多少？\n\u2022 哪个客群表现最好？\n\u2022 当前最大的问题是什么？',
            'engine': '本地规则引擎'
        }

    # 4. Data-driven keyword matching
    if 'roi' in q or '回报率' in question or '效果' in question or '投入产出' in question:
        status = '低于 10% 安全线，情况严峻' if roi_val < 10 else '处于正常区间'
        answer = f'当前营销 ROI 为 {roi_val}%，{status}。估算营销成本约 {kpis.get("estimated_cost", 0):,.0f} 元，核心问题是停车券占比过高但核销率极低，大量预算被低效消耗。'
    elif '停车' in q or '核销' in q or '券种' in question:
        answer = f'总发券 {total_issued:,} 张，整体核销率仅 {conversion_val}%。停车券占发券总量约 90%+，但核销率极低，是资源错配的核心来源。建议削减停车券预算 60% 以上，转向高净值业态体验营销。'
    elif '客群' in question or '人群' in question or '哪个客群' in question or '转化效率' in question:
        answer = '四类客群：① GREEN 高ROI转化客群 → 加大精准投放；② GOLD 自然高价值客群 → 体验式营销避免折扣侵蚀毛利；③ RED 耗损型客群 → 建议熔断止损；④ GRAY 基础客群 → 常规运营覆盖。核心策略是把停车券预算转移到 GREEN 和 GOLD。'
    elif '最大' in q or '核心问题' in question or '总结' in question or '概括' in question or '现状' in question:
        answer = f'当前最大问题是资源错配：约 90% 营销预算投入停车券，但核销率仅 {conversion_val}%，导致整体 ROI 仅 {roi_val}%。建议三件事：① 削减低效停车券 60% ② 聚焦 GREEN/GOLD 高价值客群 ③ 调整发券时点节奏。'
    elif '销售' in question or '业绩' in question or '营收' in question or '客单价' in question or '会员' in question:
        answer = f'统计周期内总销售额 CNY {total_sales:,.0f}，客单价 CNY {aov:,.0f}，总交易 {total_orders:,} 笔，会员贡献占比 {member_val}%。'
    elif 'red' in q or '耗损' in question or '熔断' in question:
        answer = 'RED（耗损型）客群指：人均领券 ≥ 5 张但客单价 < ¥200 的人群。这类客群大量领券但几乎不产生实质消费，纯薅羊毛，正在消耗营销预算。建议实施发券熔断机制（限制每人每月领券数量）。'
    elif 'green' in q or 'gold' in q or '高价值' in question:
        answer = 'GREEN 客群 = 高核销 + 高客单价 → 最优质转化人群，应加大投放；GOLD 客群 = 自然高消费 + 低核销 → 本身就会买，不需要折扣驱动，适合体验式营销（服务、专属活动），避免直接发券侵蚀毛利。'
    else:
        answer = f'数据概览：发券 {total_issued:,} 张，核销率 {conversion_val}%，ROI {roi_val}%，总销售额 CNY {total_sales:,.0f}。核心问题是停车券占比过高导致资源错配。你可以具体问：ROI、停车券、客群、最大问题 等方向。'

    return {'answer': answer, 'engine': '本地规则引擎'}


def _contains_inconsistent_roi(answer: str, actual_roi: float) -> bool:
    """Check if the LLM answer mentions an ROI that deviates >10% from actual."""
    import re
    # Find patterns like "ROI: 123%" or "ROI 为 123%" or "123%"
    matches = re.findall(r'ROI[^\d]*(\d+\.?\d*)\s*%', answer)
    for m in matches:
        try:
            val = float(m)
            if abs(actual_roi) > 0 and abs(val - actual_roi) / abs(actual_roi) > 0.10:
                return True
        except ValueError:
            pass
    return False


# ===== Symmetric Dimension Architecture =====
# Each dimension is bidirectional: positive pct = enhance, negative pct = reduce.
# Extensible: add a new row to this dict + one transform function to support new dimensions.

def _scale_coupon(trend, lag, pct):
    """coupon_volume: scale all coupon values by (1 + pct/100)."""
    factor = 1 + pct / 100.0
    for i in range(len(trend.get('coupon', []))):
        trend['coupon'][i] = max(0, int((trend['coupon'][i] or 0) * factor))
    return trend, lag

def _scale_sales(trend, lag, pct):
    """sales_efficiency: scale all sales values by (1 + pct/100)."""
    factor = 1 + pct / 100.0
    for i in range(len(trend.get('sales', []))):
        trend['sales'][i] = max(1, int((trend['sales'][i] or 0) * factor))
    return trend, lag

def _offset_lag(trend, lag, pct):
    """lag_correlation: shift all lag r-values by +pct/100 (additive, clamped to [-1, 1])."""
    delta = pct / 100.0
    for l in lag:
        l['r'] = round(max(-1.0, min(1.0, (l.get('r', 0) or 0) + delta)), 2)
    return trend, lag

DIMENSION_TRANSFORM = {
    'coupon_volume':     _scale_coupon,
    'sales_efficiency':  _scale_sales,
    'lag_correlation':   _offset_lag,
}

# Backward-compatible legacy action name mapping
_LEGACY_ACTION_MAP = {
    'cut_parking':   ('coupon_volume',    -60),
    'boost_green':   ('sales_efficiency',  15),
    'melt_red':      ('coupon_volume',    -80),
    'optimize_lag':  ('lag_correlation',   15),
}

# 模拟预测结果缓存，避免重复调用LLM导致结果波动
_TREND_SIMULATION_CACHE = {}

def predict_trend_simulation(before_trend, before_lag, actions):
    """
    Prompt 1: AI-powered trend + lag prediction after simulation.
    Returns { trend, lag, best_lag_day, predicted_by }.
    Falls back to local rules if DeepSeek is unavailable.
    """
    import copy
    import hashlib
    import json

    # 生成缓存key：原始数据+动作的哈希
    def _serialize_action(a):
        if isinstance(a, dict):
            return json.dumps(a, sort_keys=True, default=str)
        return str(a)
    cache_key_raw = json.dumps({
        'before_trend': before_trend,
        'before_lag': before_lag,
        'actions': sorted([_serialize_action(a) for a in actions])
    }, sort_keys=True, default=str)
    cache_key = hashlib.md5(cache_key_raw.encode('utf-8')).hexdigest()
    
    # 命中缓存直接返回
    if cache_key in _TREND_SIMULATION_CACHE:
        return copy.deepcopy(_TREND_SIMULATION_CACHE[cache_key])

    api_key = _get_deepseek_key()
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key.strip(), base_url="https://api.deepseek.com/v1")

            trend_summary = []
            if before_trend and before_trend.get('labels'):
                for i in range(min(5, len(before_trend['labels']))):
                    trend_summary.append(
                        f"  {before_trend['labels'][i]}: coupons={before_trend['coupon'][i]}, sales={before_trend['sales'][i]}"
                    )
            lag_summary = []
            if before_lag:
                for l in sorted(before_lag, key=lambda x: x.get('lag', 0))[:5]:
                    lag_summary.append(f"  lag {l.get('lag', 0)}d: r={l.get('r', 0)}")

            actions_str = ', '.join(actions) if actions else 'none'
            prompt = (
                "你是营销数据分析师。以下是原始趋势和滞后数据，以及采纳的优化建议。"
                "请预测优化后的趋势和滞后数据，严格返回 JSON（不要 markdown 代码块）：\n\n"
                f"优化建议：{actions_str}\n\n"
                f"原始趋势（部分）：\n" + '\n'.join(trend_summary) + f"\n... (共 {len(before_trend.get('labels', []))} 个时间点)\n\n"
                f"原始滞后分析（部分）：\n" + '\n'.join(lag_summary) + f"\n... (共 {len(before_lag) if before_lag else 0} 个滞后天数)\n\n"
                "返回格式：\n"
                '{"trend": [{"date": "2024-01-07", "coupons": 123, "sales": 45600}, ...],'
                '"lag": [{"days": 0, "r": -0.30}, ...], "best_lag_day": 3}\n\n'
                "约束：coupons 必须是整数；sales 必须是正数；r 在 -1 到 1 之间；"
                "trend 数组长度必须等于原始数据长度；lag 数组长度必须等于原始数据长度。"
            )

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0, max_tokens=1500, timeout=30,
                seed=42  # 固定随机种子，进一步保证输出确定性
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()

            result = json.loads(content)
            # Normalize field names to match frontend expectations
            trend_raw = result.get('trend', [])
            lag_raw = result.get('lag', [])
            normalized_trend = {
                'labels': [t.get('date', '') for t in trend_raw],
                'coupon': [max(0, int(t.get('coupons', t.get('coupon', 0)) or 0)) for t in trend_raw],
                'sales': [max(1, int(t.get('sales', 0) or 0)) for t in trend_raw],
                'correlation': before_trend.get('correlation', 0) if before_trend else 0,
            }
            normalized_lag = []
            for l in lag_raw:
                normalized_lag.append({
                    'lag': int(l.get('days', l.get('lag', 0)) or 0),
                    'r': max(-1.0, min(1.0, float(l.get('r', 0) or 0))),
                    'strength': 'strong' if abs(l.get('r', 0) or 0) >= 0.7 else ('moderate' if abs(l.get('r', 0) or 0) >= 0.4 else 'weak'),
                })
            best_lag_day = int(result.get('best_lag_day', 0) or 0)
            if not best_lag_day and normalized_lag:
                best_lag_day = max(normalized_lag, key=lambda x: x.get('r', 0)).get('lag', 3)
            result = {
                'trend': normalized_trend,
                'lag': normalized_lag,
                'best_lag_day': best_lag_day,
                'predicted_by': 'DeepSeek LLM',
            }
            _TREND_SIMULATION_CACHE[cache_key] = copy.deepcopy(result)
            return result
        except Exception as e:
            print(f'[Trend Prediction] DeepSeek failed: {e}')

    # === Local fallback rules (symmetric dimension architecture) ===
    trend = copy.deepcopy(before_trend) if before_trend else {'labels': [], 'coupon': [], 'sales': [], 'correlation': 0}
    lag = copy.deepcopy(before_lag) if before_lag else []
    best_lag_day = max(lag, key=lambda x: x.get('r', 0)).get('lag', 3) if lag else 3

    for action in actions:
        effect = None
        pct = 0

        # New format: action is a dict with {effect, pct}
        if isinstance(action, dict):
            effect = action.get('effect', '')
            pct = action.get('pct', 0)
        # Backward compatible: action is a legacy string name
        elif isinstance(action, str):
            mapped = _LEGACY_ACTION_MAP.get(action)
            if mapped:
                effect, pct = mapped
            else:
                # Try substring match for legacy partial names
                for legacy_key, (eff, p) in _LEGACY_ACTION_MAP.items():
                    if legacy_key in action:
                        effect, pct = eff, p
                        break

        if effect and effect in DIMENSION_TRANSFORM:
            trend, lag = DIMENSION_TRANSFORM[effect](trend, lag, pct)
            if effect == 'lag_correlation' and lag:
                best_lag_day = max(lag, key=lambda x: x.get('r', 0) or 0).get('lag', best_lag_day)

    # Ensure no None/NaN values
    for i in range(len(trend.get('coupon', []))):
        if trend['coupon'][i] is None or (isinstance(trend['coupon'][i], float) and (trend['coupon'][i] != trend['coupon'][i])):
            trend['coupon'][i] = 0
        if trend['sales'][i] is None or (isinstance(trend['sales'][i], float) and (trend['sales'][i] != trend['sales'][i])):
            trend['sales'][i] = 1
    for l in lag:
        if l.get('r') is None or (isinstance(l['r'], float) and (l['r'] != l['r'])):
            l['r'] = 0

    result = {
        'trend': trend,
        'lag': lag,
        'best_lag_day': best_lag_day,
        'predicted_by': '本地规则引擎',
    }
    _TREND_SIMULATION_CACHE[cache_key] = copy.deepcopy(result)
    return result
