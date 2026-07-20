
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

    secrets_path = os.path.join(BASE_DIR, '.streamlit', 'secrets.toml')
    if not os.path.exists(secrets_path):
        print('[DeepSeek] No secrets.toml found, using local engine')
        return ''

    # Python 3.11+ has tomllib in stdlib; fall back to tomli for older versions
    try:
        import tomllib
        with open(secrets_path, 'rb') as f:
            key = tomllib.load(f).get('DEEPSEEK_API_KEY', '')
    except ImportError:
        try:
            import tomli
            with open(secrets_path, 'rb') as f:
                key = tomli.load(f).get('DEEPSEEK_API_KEY', '')
        except Exception as e:
            print(f'[DeepSeek] TOML parse error: {e}')
            return ''

    if key:
        print(f'[DeepSeek] Key loaded from secrets.toml ({len(key)} chars)')
    else:
        print('[DeepSeek] No API key found in secrets.toml, using local engine')
    return key or ''


def generate_insight(kpis, structure, cohorts, lag_data, anomalies):
    """
    Generate diagnostic insight with LLM narrative + local rule engine.

    Architecture:
      - LOCAL (100% deterministic): scenario detection, severity, effect, pct,
        card titles. Same data = same diagnosis, every time.
      - LLM (DeepSeek, temperature=0): executive_summary, card body text (text),
        and how_to action steps. The LLM writes natural-language suggestions
        based on the local engine's structured diagnosis.

    If LLM fails or no API key, local template fallback handles everything.
    """
    # 1. Local engine: deterministic diagnosis (scenarios → cards with title/effect/pct)
    template = _build_template_insight(kpis, structure, cohorts, lag_data)
    template['anomaly'] = anomalies

    api_key = _get_deepseek_key()
    if not api_key:
        print('[Insight] No DeepSeek key, using local template')
        return template

    # 2. LLM writes: executive_summary + top_finding + per-card text & how_to
    try:
        llm_result = _call_deepseek_full_narrative(kpis, structure, cohorts, lag_data, template, api_key)
        if llm_result:
            template['executive_summary'] = llm_result.get('executive_summary', template['executive_summary'])
            template['top_finding'] = llm_result.get('top_finding', template['top_finding'])
            # Override per-card text and how_to with LLM-generated suggestions
            card_texts = llm_result.get('card_texts', {})
            for i, rec in enumerate(template.get('recommendations', [])):
                tag = rec.get('_tag', '')
                if tag and tag in card_texts:
                    ct = card_texts[tag]
                    rec['text'] = ct.get('text', rec.get('text', ''))
                    rec['how_to'] = ct.get('how_to', rec.get('how_to', []))
            template['generated_by'] = 'DeepSeek LLM + 本地规则引擎'
    except Exception as e:
        print(f'[Insight] DeepSeek narrative failed: {type(e).__name__}: {e}')

    return template


def _build_template_insight(kpis, structure, cohorts, lag_data):
    """Local rule-based insight generator.

    Recommendations now derive from SCENARIO_MAP (same table as DeepSeek path).
    This ensures pct values are consistent whether LLM or local engine runs.
    """
    alerts = []
    recommendations = []
    insights = []

    roi = kpis.get('roi', 0)
    conversion = kpis.get('conversion_rate', 0)
    penetration = kpis.get('coupon_leverage', 0)
    member_contribution = kpis.get('member_contribution', 0)
    aov = kpis.get('aov', 0)

    parking_share = 0
    for s in structure:
        if '停车' in s.get('name', ''):
            parking_share = s.get('pct', 0)
            break

    # === Alerts (same as before) ===
    if parking_share > 70:
        alerts.append({
            'severity': 'critical',
            'message': f'停车券占发券总量 {parking_share:.0f}%，核销率极低，存在严重结构性错配。'
        })
    elif parking_share > 40:
        alerts.append({
            'severity': 'warning',
            'message': f'停车券占发券总量 {parking_share:.0f}%，券种结构存在优化空间。'
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

    if member_contribution < 50:
        alerts.append({
            'severity': 'info',
            'message': f'会员贡献占比 {member_contribution}%，会员运营存在缺口。'
        })

    high_roi = [c for c in cohorts if c.get('redeem_rate', 0) >= 1 and c.get('atv', 0) >= 500]
    drain = [c for c in cohorts if c.get('avg_coupons', 0) >= 5 and c.get('atv', 0) < 200]

    if drain:
        worst = drain[0]
        alerts.append({
            'severity': 'warning',
            'message': f'{worst["level"]}/{worst["age_group"]} 被判定为券效耗损型客群：'
                       f'人均领券 {worst["avg_coupons"]:.0f} 张，客单价仅 CNY {worst["atv"]:,.0f}。'
        })

    # === Build scenario list — every relevant dimension gets a card ===
    # Thresholds are deliberately broad: even "healthy" data gets an info-level card
    # so users see the full picture, not just alerts.  Severity reflects actual risk.
    scenarios = []

    # 1. Coupon structure — always assessed
    if parking_share > 70:
        scenarios.append({"tag": "parking_over_70", "severity": "high", "reasoning": f"停车券占比{parking_share:.0f}%"})
    elif parking_share > 40:
        scenarios.append({"tag": "parking_over_40", "severity": "medium", "reasoning": f"停车券占比{parking_share:.0f}%"})
    elif parking_share > 0:
        # Even if parking share is low, note the coupon structure
        scenarios.append({"tag": "healthy_overall", "severity": "low", "reasoning": f"停车券占比{parking_share:.0f}% 健康"})

    # 2. ROI — always assessed
    if roi < 10:
        scenarios.append({"tag": "roi_below_10", "severity": "high", "reasoning": f"ROI仅{roi:.1f}%"})
    elif roi < 30:
        scenarios.append({"tag": "roi_below_30", "severity": "medium", "reasoning": f"ROI仅{roi:.1f}%"})

    # 3. Conversion rate — always assessed
    if conversion < 1.0:
        scenarios.append({"tag": "conversion_below_1", "severity": "high", "reasoning": f"核销率{conversion:.2f}%"})
    elif conversion < 5.0:
        # Moderate conversion — still room to improve
        scenarios.append({"tag": "conversion_below_1", "severity": "low", "reasoning": f"核销率{conversion:.2f}%"})

    # 4. Penetration — always assessed
    if penetration < 0.05:
        scenarios.append({"tag": "penetration_below_5", "severity": "high", "reasoning": f"渗透率{penetration:.3f}%"})
    elif penetration < 0.5:
        scenarios.append({"tag": "penetration_below_5", "severity": "low", "reasoning": f"渗透率{penetration:.3f}%"})

    # 5. Member contribution — always assessed
    if member_contribution < 50:
        severity = "high" if member_contribution < 30 else "medium"
        scenarios.append({"tag": "member_contribution_low", "severity": severity, "reasoning": f"会员贡献{member_contribution}%"})
    elif member_contribution < 80:
        scenarios.append({"tag": "member_contribution_low", "severity": "low", "reasoning": f"会员贡献{member_contribution}%"})

    # 6. AOV — always assessed
    if aov < 300:
        scenarios.append({"tag": "low_aov", "severity": "high", "reasoning": f"客单价{aov:.0f}"})
    elif aov < 800:
        scenarios.append({"tag": "low_aov", "severity": "low", "reasoning": f"客单价{aov:.0f}"})

    # 7. GREEN cohorts — high conversion + high AOV segments
    if high_roi:
        scenarios.append({"tag": "high_green_cohort", "severity": "medium", "reasoning": "GREEN高转化客群"})
    else:
        # Even without explicit GREEN cohorts, encourage nurturing
        scenarios.append({"tag": "high_green_cohort", "severity": "low", "reasoning": "培育高转化客群"})

    # 8. RED drain cohorts
    if drain:
        scenarios.append({"tag": "red_cohort_drain", "severity": "high", "reasoning": "RED耗损客群"})

    # 9. Lag correlation — always assessed (this is a core analysis dimension)
    if lag_data and len(lag_data) > 0:
        best_lag = max(lag_data, key=lambda x: abs(x.get('r', 0) or 0))
        best_r = best_lag.get('r', 0) or 0
        if best_r < 0.2 and best_r > -0.1:
            scenarios.append({"tag": "weak_lag_correlation", "severity": "medium", "reasoning": f"最佳r={best_r:.2f}偏弱"})
        elif best_r < 0:
            scenarios.append({"tag": "negative_lag", "severity": "high", "reasoning": f"最佳r={best_r:.2f}负相关"})
        elif best_r < 0.5:
            scenarios.append({"tag": "weak_lag_correlation", "severity": "low", "reasoning": f"最佳r={best_r:.2f}"})

    # === Resolve scenarios → deterministic recommendations via SCENARIO_MAP ===
    if scenarios:
        recommendations = _resolve_scenarios_to_recs(scenarios, kpis, structure, cohorts)

    # Insights (keep original logic)
    if high_roi:
        best = high_roi[0]
        insights.append(
            f'{best["level"]}/{best["age_group"]} 是最优 ROI 转化客群：'
            f'客单价 CNY {best["atv"]:,.0f}，核销率 {best["redeem_rate"]:.1f}%。'
            f'建议加大该客群的营销预算倾斜。'
        )

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
        'recommendations': recommendations or [
            {
                '_tag': 'healthy_overall',
                'text': '当前各指标处于健康区间，建议维持现有营销节奏。',
                'action': '保持监控',
                'effect': 'sales_efficiency',
                'effect_label': '销售效率',
                'pct': 5,
                'title': '常规监控',
                'severity': 'info',
                'how_to': [
                    '维持现有营销节奏，每两周做一次券种结构复盘',
                    '重点监控 ROI 与核销率走势，阈值触发即自动告警',
                    '尝试 1-2 个新券型的小规模 A/B 测试，持续寻找增量空间',
                ],
            }
        ],
        'top_finding': insights[0][:80] if insights else '数据范围过窄，无法形成明确结论。',
        'generated_by': '本地规则引擎',
        '_scenarios': scenarios,  # Pass to generate_insight for LLM severity judgment
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

    # Build the list of available scenario tags for the LLM prompt
    scenario_tags_str = ", ".join(sorted(SCENARIO_MAP.keys()))

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": (
                "你是侨福芳草地的高级营销数据分析师。请基于给定数据生成专业洞察。\n"
                "严格返回 JSON 格式，不要 markdown 代码块，字段如下：\n"
                '{"executive_summary": "100字以内中文核心结论",'
                '"alerts": [{"severity":"critical/warning/info","message":"..."}],'
                '"scenarios": [{"tag": "场景标签", "severity": "low|medium|high", "reasoning": "为什么判断为此场景"}],'
                '"top_finding": "最重要发现50字以内"}\n'
                "\n"
                "【重要】scenarios 中的 tag 必须从以下预定义标签中选择，不要自己编造标签：\n"
                f"{scenario_tags_str}\n"
                "\n"
                "severity 表示严重程度：low=轻度, medium=中度, high=重度。\n"
                "reasoning 用 20 字以内说明为什么判断为此场景。\n"
                "每个 scenario 独立判断，不要重复同一个标签。\n"
                "最多返回 4 个 scenarios，按严重程度从高到低排序。\n"
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




def _call_deepseek_full_narrative(kpis, structure, cohorts, lag_data, template, api_key):
    """
    Ask DeepSeek to write:
      - executive_summary + top_finding (narrative text)
      - Per-card text (diagnosis body) and how_to (3 concrete action steps)

    The local engine provides the structured diagnosis (tag, title, effect, pct,
    severity). DeepSeek translates these into natural-language suggestions with
    concrete, data-aware how_to steps.
    """
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

    # Summarize the local diagnosis for LLM context
    rec_summary = []
    rec_tags = []
    for r in template.get('recommendations', [])[:6]:
        sev = {'critical': '严重', 'warning': '预警', 'info': '信息'}.get(r.get('severity', ''), '信息')
        tag = r.get('_tag', '')
        rec_tags.append(tag)
        rec_summary.append(
            f"  [{sev}] tag={tag} | 标题={r['title']} | effect={r.get('effect_label','')} | pct={r.get('pct',0):+d}%"
        )

    lines = ["营销数据："]
    lines.append(f"ROI: {kpis.get('roi')}% | 核销率: {kpis.get('conversion_rate')}%")
    lines.append(f"停车券占比: {parking_share:.1f}% | 客单价: CNY {kpis.get('aov'):,.0f}")
    lines.append(f"会员贡献: {kpis.get('member_contribution')}% | 发券总量: {kpis.get('total_issued', 0):,}")
    lines.append(f"渗透率: {kpis.get('coupon_leverage', 0):.3f}%")
    lines.append(f"\n系统已自动诊断出以下问题：")
    lines.extend(rec_summary)

    if lag_data:
        best = max(lag_data, key=lambda x: abs(x.get('r', 0) or 0))
        lines.append(f"\n滞后分析: 最佳窗口 {best.get('lag', '?')}天, r={best.get('r', 0):.2f}")

    # Build the expected card_texts schema
    card_schema_parts = []
    for tag in rec_tags:
        card_schema_parts.append(
            f'    "{tag}": {{"text": "诊断正文（50-80字）", "how_to": ["步骤1", "步骤2", "步骤3"]}}'
        )
    card_schema = ",\n".join(card_schema_parts)

    system_prompt = (
        "你是侨福芳草地的高级营销数据分析师。\n"
        "系统已经自动完成了数据诊断（场景识别、严重程度、effect维度、pct数值），"
        "请基于诊断结果撰写自然语言的建议文案。\n\n"
        "返回 JSON（不要 markdown 代码块）：\n"
        "{\n"
        '  "executive_summary": "120字以内核心结论，涵盖最重要的2-3个发现",\n'
        '  "top_finding": "最重要发现，40字以内",\n'
        '  "card_texts": {\n'
        f'{card_schema}\n'
        '  }\n'
        "}\n\n"
        "要求：\n"
        "- text: 50-80字的诊断正文，自然语言，结合数据事实（如 ROI 数值、停车券占比）\n"
        "- how_to: 3条具体可执行的操作步骤，每条20-40字，要可量化、有时限、可落地\n"
        "- 每条 card 的 how_to 要呼应其 effect 方向和 pct 数值\n"
        "不要 emoji，不要 markdown，纯中文。"
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n".join(lines)},
        ],
        temperature=0, max_tokens=1200, timeout=25,
    )

    content = response.choices[0].message.content.strip()
    print(f'[Insight Narrative] DeepSeek raw (first 300): {content[:300]}')

    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    result = json.loads(content)
    print(f'[Insight Narrative] summary: {result.get("executive_summary", "")[:80]}...')
    cards = result.get('card_texts', {})
    print(f'[Insight Narrative] cards written: {list(cards.keys())}')
    return result


# ===== Scenario-to-Effect Mapping Table =====
# AI (DeepSeek) analyzes data → returns scenario tags + severity → local lookup
# produces deterministic effect + pct. Same scenario + same severity = same pct.
#
# Format: scenario_tag: (effect, mild_pct, moderate_pct, severe_pct)
# Severity levels: "low" / "medium" / "high"

SCENARIO_MAP = {
    # --- Coupon Volume adjustments ---
    "parking_over_70":      ("coupon_volume",    -30,  -50,  -70),
    "parking_over_40":      ("coupon_volume",    -15,  -30,  -50),
    "red_cohort_drain":     ("coupon_volume",    -50,  -70,  -90),
    "over_issuance":        ("coupon_volume",    -20,  -40,  -60),

    # --- Sales Efficiency adjustments ---
    "roi_below_10":         ("sales_efficiency",  10,   20,   30),
    "roi_below_30":         ("sales_efficiency",   5,   10,   15),
    "conversion_below_1":   ("sales_efficiency",  10,   20,   30),
    "penetration_below_5":  ("sales_efficiency",   5,   15,   25),
    "high_green_cohort":    ("sales_efficiency",  15,   25,   40),
    "member_contribution_low": ("sales_efficiency", 5,  10,   20),
    "low_aov":              ("sales_efficiency",   5,   10,   20),

    # --- Lag Correlation adjustments ---
    "weak_lag_correlation": ("lag_correlation",   10,   20,   30),
    "negative_lag":         ("lag_correlation",   15,   25,   35),

    # --- Fallback / generic ---
    "healthy_overall":      ("sales_efficiency",   0,    5,   10),
}

VALID_SEVERITIES = {"low", "medium", "high"}


def _resolve_scenarios_to_recs(scenarios, kpis, structure, cohorts):
    """Convert DeepSeek scenario tags + severity → fixed effect + pct recommendations.

    Deduplication strategy: by scenario **tag** (not by effect dimension).
    Multiple cards can share the same effect dimension (e.g. ROI 10% and
    conversion 1% both map to sales_efficiency but are different diagnoses).
    This way the user sees the full picture — one card per unique problem.

    Args:
        scenarios: list of {"tag": str, "severity": "low"|"medium"|"high", "reasoning": str}
        kpis: KPI dict (used for dynamic text generation)
        structure: coupon structure list
        cohorts: cohort list

    Returns:
        list of recommendation dicts with fixed effect + pct values
    """
    recommendations = []
    seen_tags = set()
    sev_rank = {"high": 3, "medium": 2, "low": 1}

    # Sort scenarios by severity (high first) so critical issues are surfaced first
    sorted_scenarios = sorted(
        scenarios,
        key=lambda s: -sev_rank.get(s.get("severity", "medium").lower(), 2)
    )

    for sc in sorted_scenarios:
        tag = sc.get("tag", "").strip()
        severity = sc.get("severity", "medium").strip().lower()
        reasoning = sc.get("reasoning", "")

        if severity not in VALID_SEVERITIES:
            severity = "medium"

        # Deduplicate by tag: each unique scenario gets its own card
        if tag in seen_tags:
            continue
        seen_tags.add(tag)

        entry = SCENARIO_MAP.get(tag)
        if not entry:
            continue

        effect, mild_pct, moderate_pct, severe_pct = entry

        # Pick pct based on severity
        if severity == "high":
            pct = severe_pct
        elif severity == "low":
            pct = mild_pct
        else:
            pct = moderate_pct

        # Build card skeleton: deterministic fields from local engine
        # text and how_to are populated by local template initially;
        # LLM overrides them in generate_insight() if available.
        text, action, title, sev_label, how_to, effect_label = _build_rec_text(
            tag, effect, pct, severity, kpis, structure, cohorts, reasoning
        )
        recommendations.append({
            "_tag": tag,
            "text": text,
            "action": action,
            "effect": effect,
            "effect_label": effect_label,
            "pct": pct,
            "title": title,
            "severity": sev_label,
            "how_to": how_to,
        })

    return recommendations


def _build_rec_text(tag, effect, pct, severity, kpis, structure, cohorts, reasoning):
    """Build natural-language text + action + how-to list + metadata.

    Returns (text, action, title, sev_label, how_to, effect_label).
    - text:         the diagnosis (1-2 sentence)
    - action:       the one-line summary (shown in card action box)
    - title:        short title for the card header
    - sev_label:    'critical' | 'warning' | 'info'
    - how_to:       list of 3 concrete actionable steps (the "how")
    - effect_label: Chinese label for the effect dimension (e.g. '发券量')
    """
    parking_share = 0
    for s in (structure or []):
        if "停车" in s.get("name", ""):
            parking_share = s.get("pct", 0)
            break

    roi = kpis.get("roi", 0)
    conversion = kpis.get("conversion_rate", 0)
    aov = kpis.get("aov", 0)
    total_issued = kpis.get("total_issued", 0)
    member_contribution = kpis.get("member_contribution", 0)
    coupon_leverage = kpis.get("coupon_leverage", 0)

    # Find best/worst cohorts for context
    green = [c for c in (cohorts or []) if c.get("tag") == "GREEN"]
    red = [c for c in (cohorts or []) if c.get("tag") == "RED"]
    best_green = green[0] if green else None
    worst_red = red[0] if red else None

    # Effect dimension → Chinese label
    effect_label = {
        "coupon_volume": "发券量",
        "sales_efficiency": "销售效率",
        "lag_correlation": "滞后效应",
    }.get(effect, "营销效能")

    # Severity → label mapping
    sev_label = {"high": "critical", "medium": "warning", "low": "info"}.get(severity, "info")
    pct_abs = abs(pct)
    arrow = "↑" if pct > 0 else "↓"

    if tag == "parking_over_70":
        title = "停车券结构错配"
        text = f"停车券当前占比 {parking_share:.0f}%，但核销率极低，大量营销预算被低效券种消耗，是当前 ROI 承压的核心来源。"
        action = f"削减停车券 {pct_abs}%"
        how_to = [
            f"下月排期将停车券发放量削减 {pct_abs}%，优先停发 30 元以下小额停车券",
            f"将腾出的预算重新分配至 3-5 个高转化 GREEN 客群的体验券（满减 / 折扣 / 业态专属）",
            f"同步将 RED 标签客群（人均领券 ≥ 5 张但客单价 < ¥200）的领券上限收紧至 3 张/月",
        ]

    elif tag == "parking_over_40":
        title = "停车券结构优化"
        text = f"停车券当前占比 {parking_share:.0f}%，券种结构过度依赖单一券型，存在结构性优化空间。"
        action = f"优化停车券 -{pct_abs}%"
        how_to = [
            f"按业态分层调整停车券发放策略：餐饮、零售、亲子业态降低 10%，其余业态维持",
            f"新增 2-3 个高核销率券种（如满 200 减 50 体验券、品类专属券）填补释放的预算",
            f"建立月度券种结构评审机制，跟踪停车券占比目标 ≤ 30%",
        ]

    elif tag == "roi_below_10":
        title = "ROI 严重告警"
        text = f"营销 ROI 仅 {roi:.1f}%，远低于 10% 安全线，每投入 1 元营销成本回报不足 0.1 元。"
        action = f"紧急提升 ROI {arrow}{pct_abs}%"
        how_to = [
            f"立即审计近 30 天所有券种的 ROI，砍掉 ROI 为负或 < 5% 的券种（预计可释放 30-40% 预算）",
            f"将释放预算倾斜至 GREEN 高转化客群（核销率 ≥ 1% 且客单价 ≥ ¥500），目标 ROI 提升至 {roi:.1f}% → {roi * (1 + pct/100):.1f}%",
            "建立 ROI 周看板：每周一更新各券种 ROI，超阈值的券种自动告警并暂停发放",
        ]

    elif tag == "roi_below_30":
        title = "ROI 利润承压"
        text = f"营销 ROI 为 {roi:.1f}%，低于 30% 警戒线，每元营销投入回报不及预期。"
        action = f"提升 ROI {arrow}{pct_abs}%"
        how_to = [
            f"识别 ROI 最低的 3 个券种，将其发券量减少 {pct_abs}%，转投 ROI 更高的券种",
            f"对 GOLD 自然高价值客群减少直接折扣券发放，改为体验式服务（VIP 专场 / 私人造型师）以保护毛利",
            f"A/B 测试 2 种新券设计（满减梯度券 / 限时品类券），2 周后对比 ROI 选择优胜方案",
        ]

    elif tag == "conversion_below_1":
        title = "核销转化堵点"
        text = f"核销转化率仅 {conversion:.2f}%，券→消费链路存在明显堵点，大量券被领走但未带来实际消费。"
        action = f"提升核销率 {arrow}{pct_abs}%"
        how_to = [
            "缩短券有效期：现有券有效期普遍较长，缩短至 7-14 天制造紧迫感（核销率通常可提升 30-50%）",
            "提高券面额与客单价的匹配度：对客单价 ¥300-500 的客群发放满 200 减 50 券，避免满 1000 减 100 这类难触达券",
            "增加券使用提醒：在券到期前 3 天通过短信 / 微信推送提醒，引导到店核销",
        ]

    elif tag == "penetration_below_5":
        title = "营销渗透不足"
        text = f"发券动销渗透率仅 {coupon_leverage:.3f}%，发券对整体销售的拉动作用很弱，营销杠杆效应未释放。"
        action = f"扩大渗透 {arrow}{pct_abs}%"
        how_to = [
            "扩大发券客群覆盖：从当前活跃客群扩展至近 6 个月有消费的客群，预计可增加 40-60% 触达",
            "在客流高峰前 3 天集中投放（参考滞后分析的最佳窗口），而非均匀分布",
            "打通线上线下券核销链路：会员小程序、POS 收银台、停车缴费系统全部支持券识别",
        ]

    elif tag == "high_green_cohort":
        title = "GREEN 高转化客群深挖"
        if best_green:
            text = f"{best_green['level']}/{best_green['age_group']} 是当前最优 ROI 转化客群，客单价 CNY {best_green.get('atv', 0):,.0f}、核销率 {best_green.get('redeem_rate', 0):.1f}%，预算倾斜空间充足。"
            action = f"加大 {best_green['level']} 客群投放"
            how_to = [
                f"为 {best_green['level']}/{best_green['age_group']} 客群定制专属券（如满 500 减 80），发券量提升 30%",
                f"建立该客群的 VIP 复购激励：每月消费满 ¥{int(best_green.get('atv', 0) * 1.2):,} 即赠送一次专属体验服务",
                "搭建自动识别→定向推送闭环：客群画像每日更新，命中即通过企微推送个性化券",
            ]
        else:
            text = "识别到高转化潜力客群，但当前未单独追踪，建议加大精准投放力度。"
            action = f"加大高转化投放 {arrow}{pct_abs}%"
            how_to = [
                "在 KMeans 聚类结果中圈定核销率前 20% 的客群组，建立专属运营策略",
                "为该客群设计阶梯奖励券：消费满 ¥300 减 ¥50、满 ¥600 减 ¥120",
                "每周复盘客群消费数据，动态调整券面额和有效期",
            ]

    elif tag == "red_cohort_drain":
        title = "RED 耗损客群熔断"
        if worst_red:
            text = f"{worst_red['level']}/{worst_red['age_group']} 是典型耗损客群：人均领券 {worst_red.get('avg_coupons', 0):.1f} 张但客单价仅 CNY {worst_red.get('atv', 0):,.0f}，正在侵蚀营销预算。"
            action = f"熔断 {worst_red['level']} 客群"
            how_to = [
                f"立即对 {worst_red['level']}/{worst_red['age_group']} 客群实施发券熔断：每月领券上限收紧至 3 张",
                "已领券未使用的回收 50%（重新分配给 GREEN 客群），减少沉睡券占用预算",
                "对熔断后 3 个月仍未转化的客群，从活跃运营名单中移除，释放运营资源",
            ]
        else:
            text = f"识别到耗损型客群：人均领券多但客单价低，建议实施发券熔断机制削减无效投放 {pct_abs}%。"
            action = f"熔断耗损客群 -{pct_abs}%"
            how_to = [
                f"将耗损客群的月发券量削减 {pct_abs}%，优先砍掉小额高频券",
                "建立耗损客群预警规则：人均领券 ≥ 5 张且客单价 < ¥200 自动加入熔断名单",
                "为熔断客群提供 1 次高门槛券（如满 1000 减 200），如仍未转化则放弃持续投入",
            ]

    elif tag == "weak_lag_correlation":
        title = "滞后效应偏弱"
        text = "发券与销售之间的时间关联性弱，发券时点未能有效踩中消费决策节点。"
        action = f"优化滞后窗口 {arrow}{pct_abs}%"
        how_to = [
            "将主要发券日固定到消费前 3-5 天的窗口（参考最佳滞后分析结果）",
            "提前在消费高峰前 7 天发布预告券（小额面值，制造期待）→ 高峰前 3 天发放主券（高面值，促成转化）",
            "设置补发窗口：高峰后 1 天针对未转化客群发放 1 次高门槛券，覆盖边缘人群",
        ]

    elif tag == "negative_lag":
        title = "滞后效应异常"
        text = "部分滞后天数呈负相关，当天发券反而抑制消费，说明发券与消费决策时机错位。"
        action = f"修正滞后效应 {arrow}{pct_abs}%"
        how_to = [
            "立即暂停当天即时发券（lag=0），全部改为提前 3-7 天预发",
            "排查负相关背后的券种：这些券可能在消费后被触发，造成统计假象，识别后剔除或重新设计",
            "建立 A/B 测试机制：新券设计先小范围测试滞后效应，确认正向后全量推广",
        ]

    elif tag == "member_contribution_low":
        title = "会员贡献偏低"
        text = f"会员销售额占比仅 {member_contribution}%，意味着过半销售来自非会员，会员体系对销售的拉动作用偏弱。"
        action = f"提升会员贡献 {arrow}{pct_abs}%"
        how_to = [
            "在收银台、小程序首页强引导非会员顾客扫码注册，会员注册即赠 ¥20 体验券",
            "为会员设计专享权益：每月 1 次会员日（双倍积分）、生日月 5 折券、生日礼包",
            "打通会员消费数据：会员每次消费后推送个性化推荐券，提升复购频次",
        ]

    elif tag == "low_aov":
        title = "客单价偏低"
        text = f"客单价仅 CNY {aov:,.0f}，单笔消费金额偏小，整体销售受限于件数而非件数 × 单价。"
        action = f"提升客单价 {arrow}{pct_abs}%"
        how_to = [
            "推出阶梯满减券：满 300 减 30、满 500 减 70、满 800 减 150，引导客单提升 30%",
            "设计品类组合券：餐饮 + 零售、亲子 + 餐饮的组合券，提升跨业态连带率",
            "在收银台展示凑单提示：当前差 ¥XX 即可使用满减券，刺激加购",
        ]

    elif tag == "over_issuance":
        title = "过度投放"
        text = f"发券总量 {total_issued:,} 张，单客平均领券过多，存在过度投放导致券贬值、用户疲劳的风险。"
        action = f"削减过度投放 -{pct_abs}%"
        how_to = [
            f"将全量发券量削减 {pct_abs}%，优先砍掉领券 ≥ 10 张的客群加发券",
            "建立单客月度领券上限：普通会员 8 张、银卡 12 张、金卡 15 张",
            "提高券品质：减少 5 元以下小额券比例至 20% 以下，专注 30-100 元面值高价值券",
        ]

    elif tag == "healthy_overall":
        title = "整体健康"
        text = "当前各项指标处于健康区间，营销体系运行良好。"
        action = "保持监控"
        how_to = [
            "维持现有营销节奏，每两周做一次券种结构复盘",
            "重点监控 ROI 与核销率走势，阈值触发即自动告警",
            "尝试 1-2 个新券型的小规模 A/B 测试，持续寻找增量空间",
        ]

    else:
        # Generic fallback: use reasoning from DeepSeek + generic text
        title = reasoning[:20] if reasoning else "策略优化"
        text = reasoning if reasoning else f"基于数据分析，建议{'提升' if pct > 0 else '削减'}{abs(pct)}%。"
        action = f"优化调整 {pct:+d}%"
        how_to = [
            f"按建议方向调整幅度 {pct_abs}%",
            "建立 2 周观察期，监控关键 KPI（核销率、ROI、客单价）变化",
            "如效果未达预期，叠加下一轮建议微调参数",
        ]

    return text, action, title, sev_label, how_to, effect_label


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

        # Per-page focus instructions so DeepSeek generates differentiated analysis
        page_focus = {
            'summary': '全局概览：综合所有维度的核心结论，关注整体 ROI、客群结构、关键告警。',
            'kpi': 'KPI 诊断：逐项分析 ROI、核销率、客单价、会员贡献、发券渗透率等指标，判断每项的健康度。',
            'structure': '券种结构分析：聚焦停车券占比和券种分布，分析结构性错配和成本效率。',
            'trend': '趋势滞后分析：聚焦发券-消费的滞后关系、相关系数强度、最佳发券窗口。',
            'cohort': '客群价值诊断：聚焦 GREEN/GOLD/RED/GRAY 四象限客群，分析各组特征和策略方向。',
            'insight': '综合诊室：汇总告警、异常检测结果和优化建议，给出最优先行动项。',
        }
        focus_instruction = page_focus.get(page, page_focus['summary'])

        system_prompt = (
            "你是侨福芳草地购物中心的商业智能分析师。请基于当前页面数据输出结构化整体洞察。"
            f"【重要】当前页面是「{page_label}」，分析重点：{focus_instruction}"
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
        # Local fallback for page overview — per-page differentiated findings
        findings = []
        recommendation = ''
        summary = f'当前{page_label}页面已加载数据。'

        roi = kpis.get('roi', 0) if kpis else 0
        conversion = kpis.get('conversion_rate', 0) if kpis else 0
        aov = kpis.get('aov', 0) if kpis else 0
        member_contribution = kpis.get('member_contribution', 0) if kpis else 0
        total_sales = kpis.get('total_sales', 0) if kpis else 0
        total_issued = kpis.get('total_issued', 0) if kpis else 0
        coupon_leverage = kpis.get('coupon_leverage', 0) if kpis else 0

        parking_share = 0
        parking_name = '停车券'
        if structure:
            for s in structure:
                if '停车' in s.get('name', ''):
                    parking_share = s.get('pct', 0)
                    parking_name = s.get('name', '停车券')
                    break

        if cohorts:
            tags = {'GREEN': 0, 'GOLD': 0, 'RED': 0, 'GRAY': 0}
            for c in cohorts:
                tags[c.get('tag', 'GRAY')] = tags.get(c.get('tag', 'GRAY'), 0) + 1
        else:
            tags = {'GREEN': 0, 'GOLD': 0, 'RED': 0, 'GRAY': 0}

        # ================================================================
        # Per-page differentiated analysis
        # ================================================================
        if page == 'summary':
            # 战情摘要：全局 KPI 概览 + 客群结构 + 告警
            summary = f'全局概览：ROI {roi}%，核销率 {conversion}%，整体呈{"正向" if roi > 30 else "承压"}状态。'
            if roi < 10:
                findings.append(f'ROI 仅 {roi}%，低于 10% 安全线，需立即审查营销效果')
            elif roi < 30:
                findings.append(f'ROI 为 {roi}%，低于 30% 警戒线，利润空间承压')
            else:
                findings.append(f'ROI 达到 {roi}%，整体回报健康')
            if parking_share > 70:
                findings.append(f'停车券占发券总量 {parking_share}%，结构单一，存在资源错配')
            if tags['RED'] > 0:
                findings.append(f'{tags["RED"]} 个 RED 耗损客群 + {tags["GREEN"]} 个 GREEN 高转化客群，整体客群健康度需关注')
            if conversion < 1.0:
                findings.append(f'核销率 {conversion}%，券激励设计需重新评估')
            recommendation = '建议从客群诊断和投入产出结构入手，优先解决停车券占比过高问题'

        elif page == 'kpi':
            # KPI 总览：逐项指标分析
            summary = f'KPI 诊断：ROI {roi}%，客单价 CNY {aov:,.0f}，会员贡献 {member_contribution}%。'
            if roi < 10:
                findings.append(f'营销 ROI 仅 {roi}% — 投入产出严重失衡，建议立即审计低效券种')
            elif roi < 30:
                findings.append(f'ROI {roi}% 处于警戒区间，需持续监控')
            else:
                findings.append(f'ROI {roi}% 处于健康区间')
            if conversion < 1.0:
                findings.append(f'核销转化率 {conversion}% — 券→消费链路存在堵点')
            else:
                findings.append(f'核销率 {conversion}% 正常，券激励方向基本正确')
            if coupon_leverage < 0.05:
                findings.append(f'发券动销渗透率仅 {coupon_leverage}% — 营销杠杆效应弱')
            if member_contribution < 50:
                findings.append(f'会员贡献 {member_contribution}%，会员运营存在缺口')
            recommendation = '建议重点提升核销转化率和发券动销渗透率两个指标'

        elif page == 'structure':
            # 投入产出结构：券种结构 + 成本分布
            summary = f'券种结构分析：共 {len(structure) if structure else 0} 种券，停车券占比 {parking_share}%。'
            if parking_share > 70:
                findings.append(f'停车券占比高达 {parking_share}%，核销率极低，是结构性错配的核心来源')
                recommendation = '建议削减停车券预算 50-60%，转移至高 ROI 体验券种'
            elif parking_share > 40:
                findings.append(f'停车券占比 {parking_share}%，存在优化空间')
                recommendation = '建议逐步降低停车券比例，增发高转化业态专属券'
            else:
                findings.append(f'停车券占比 {parking_share}%，券种结构相对合理')
                recommendation = '保持当前券种配比，关注各券种的核销效率差异'
            if structure:
                top_coupons = sorted(structure, key=lambda x: x.get('count', 0), reverse=True)[:3]
                findings.append(f'Top 3 券种: ' + ', '.join(f"{s['name']}({s.get('pct',0)}%)" for s in top_coupons))
            if total_sales > 0 and total_issued > 0:
                findings.append(f'单券产出约 CNY {total_sales / max(total_issued, 1):.0f}，可作为券种优化的基准线')

        elif page == 'trend':
            # 趋势滞后分析：发券-消费滞后关系 + 趋势方向
            best_lag = max(lag_data, key=lambda x: x.get('r', 0)) if lag_data else {}
            best_lag_day = best_lag.get('lag', 0)
            best_lag_r = best_lag.get('r', 0)
            summary = f'滞后分析：最佳发券窗口为消费前 {best_lag_day} 天（r={best_lag_r:.2f}）。'
            if best_lag_r >= 0.5:
                findings.append(f'发券-消费滞后相关性较强（r={best_lag_r:.2f}），建议在消费前 {best_lag_day} 天集中投放')
            elif best_lag_r >= 0.3:
                findings.append(f'滞后相关性中等（r={best_lag_r:.2f}），发券时间窗口有一定参考价值')
            else:
                findings.append(f'滞后相关性偏弱（r={best_lag_r:.2f}），发券时间点对消费拉动作用有限')
            if lag_data:
                neg_lags = [l for l in lag_data if (l.get('r', 0) or 0) < 0]
                if neg_lags:
                    findings.append(f'{len(neg_lags)} 个滞后天数呈负相关，当天发券反而抑制消费')
            findings.append(f'建议将发券节奏调整到消费前 {best_lag_day} 天的窗口期')
            recommendation = f'核心建议：将发券时间窗口前移至消费前 {best_lag_day} 天'

        elif page == 'cohort':
            # 客群价值诊断：四象限客群分析
            total_cohorts = len(cohorts) if cohorts else 0
            summary = f'客群诊断：共 {total_cohorts} 个客群组，GREEN {tags["GREEN"]} / GOLD {tags["GOLD"]} / RED {tags["RED"]} / GRAY {tags["GRAY"]}。'
            if tags['GREEN'] > 0:
                findings.append(f'{tags["GREEN"]} 个 GREEN 高转化客群 → 应加大精准投放，预算倾斜')
            else:
                findings.append('暂无 GREEN 高转化客群，需培育高潜力人群')
            if tags['GOLD'] > 0:
                findings.append(f'{tags["GOLD"]} 个 GOLD 自然高价值客群 → 适合体验式营销，避免折扣侵蚀毛利')
            if tags['RED'] > 0:
                findings.append(f'{tags["RED"]} 个 RED 耗损型客群 → 建议实施发券熔断，限制领券数量')
            else:
                findings.append('暂无 RED 耗损型客群，客群结构整体健康')
            if tags['RED'] > tags['GREEN']:
                recommendation = 'RED 客群多于 GREEN 客群，建议优先清理耗损客群，再逐步培育高转化人群'
            else:
                recommendation = '客群结构相对健康，建议持续监控 RED 客群的转化趋势变化'

        elif page == 'insight':
            # 智能诊室：综合诊断结论
            summary = f'综合诊断：ROI {roi}%，核销率 {conversion}%，停车券占比 {parking_share}%。'
            # Aggregate alerts from template insight
            if kpis and (structure or cohorts):
                template = _build_template_insight(kpis, structure or [], cohorts or [], lag_data or [])
                alert_msgs = [a['message'] for a in template.get('alerts', [])]
                recs = template.get('recommendations', [])
                if alert_msgs:
                    findings = alert_msgs[:3]
                else:
                    findings = ['当前数据范围内未检测到关键告警，各项指标处于正常区间']
                if recs:
                    first_rec = recs[0]
                    rec_text = first_rec.get('text', first_rec.get('action', '')) if isinstance(first_rec, dict) else str(first_rec)
                    recommendation = rec_text
                else:
                    recommendation = '持续监控各客群表现，关注新出现的转化模式'
            else:
                findings = ['暂无足够数据生成综合诊断，请先加载数据']
                recommendation = '请确保已上传发券记录和销售流水 CSV 文件'

        # ================================================================
        # Fallback if no findings generated
        # ================================================================
        if not findings:
            findings = ['数据已加载完成，可进入各模块查看详细分析']
        if not recommendation:
            recommendation = '可点击各模块标题查看针对性分析'

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
        # Local fallback for module focus — derive analysis from actual data
        # Uses broad keyword matching on module name, falling back to data-driven heuristics
        mod_lower = mod.lower()
        insight_text = ''
        finding_text = ''

        roi = kpis.get('roi', 0) if kpis else 0
        conversion = kpis.get('conversion_rate', 0) if kpis else 0
        aov = kpis.get('aov', 0) if kpis else 0
        member = kpis.get('member_contribution', 0) if kpis else 0
        total_sales = kpis.get('total_sales', 0) if kpis else 0
        total_issued = kpis.get('total_issued', 0) if kpis else 0

        parking_share = 0
        if structure:
            for s in structure:
                if '停车' in s.get('name', ''):
                    parking_share = s.get('pct', 0)
                    break

        tags = {'GREEN': 0, 'GOLD': 0, 'RED': 0, 'GRAY': 0}
        if cohorts:
            for c in cohorts:
                tags[c.get('tag', 'GRAY')] = tags.get(c.get('tag', 'GRAY'), 0) + 1

        best_lag = max(lag_data, key=lambda x: x.get('r', 0)) if lag_data else {}
        best_lag_day = best_lag.get('lag', 0)
        best_lag_r = best_lag.get('r', 0)

        # Broad semantic matching — prioritize specific module names, fall back to keyword groups
        if any(kw in mod for kw in ['资源错配', '资源', '停车券', '券种', '结构']):
            insight_text = f'「{mod}」停车券占比 {parking_share}%，共 {len(structure) if structure else 0} 种券。'
            if parking_share > 70:
                finding_text = f'停车券占 {parking_share}%，核销率极低，是 ROI 低迷的主因。建议削减 50-60%，转移预算至高转化体验券。'
            elif parking_share > 40:
                finding_text = f'停车券占 {parking_share}%，存在优化空间，建议逐步降低比例。'
            else:
                finding_text = f'停车券占 {parking_share}%，券种结构相对合理。'

        elif any(kw in mod for kw in ['核心指挥', '指挥看板', '指挥', '看板', '核心']):
            insight_text = f'「{mod}」全局 ROI {roi}%，核销率 {conversion}%，客单价 CNY {aov:,.0f}。'
            if roi < 10:
                finding_text = f'ROI 仅 {roi}%，低于安全线。停车券占比 {parking_share}% 是主要拖累因素。'
            elif roi < 30:
                finding_text = f'ROI {roi}% 处于警戒区间，需关注停车券占比和核销率变化。'
            else:
                finding_text = f'ROI {roi}% 健康，核心指标正常。'

        elif any(kw in mod for kw in ['KPI', 'kpi', 'ROI', 'roi', '指标', '核销', '客单价', '会员贡献', '发券']):
            insight_text = f'「{mod}」ROI {roi}%，核销率 {conversion}%，客单价 CNY {aov:,.0f}，会员贡献 {member}%。'
            if roi < 10:
                finding_text = f'ROI {roi}% 低于 10% 安全线，营销投入产出严重失衡，建议立即审计低效券种。'
            elif roi < 30:
                finding_text = f'ROI {roi}% 处于警戒区间，利润空间承压。'
            else:
                finding_text = f'ROI {roi}% 处于健康区间。核销率 {conversion}%，客单价 CNY {aov:,.0f}。'

        elif any(kw in mod for kw in ['趋势', 'trend', '滞后', '窗口', 'lag']):
            insight_text = f'「{mod}」最佳发券窗口为消费前 {best_lag_day} 天（r={best_lag_r:.2f}）。'
            if best_lag_r >= 0.5:
                finding_text = f'滞后相关性较强（r={best_lag_r:.2f}），建议在消费前 {best_lag_day} 天集中投放。'
            elif best_lag_r >= 0.3:
                finding_text = f'滞后相关性中等（r={best_lag_r:.2f}），发券时间窗口有参考价值。'
            else:
                finding_text = f'滞后相关性偏弱（r={best_lag_r:.2f}），发券时点对消费拉动作用有限。'

        elif any(kw in mod for kw in ['客群', 'cohort', 'GREEN', 'GOLD', 'RED', 'GRAY', '诊断', '价值']):
            insight_text = f'「{mod}」共 {len(cohorts) if cohorts else 0} 组客群，GREEN {tags["GREEN"]}/GOLD {tags["GOLD"]}/RED {tags["RED"]}/GRAY {tags["GRAY"]}。'
            if tags['RED'] > 0:
                finding_text = f'{tags["RED"]} 组 RED 耗损客群需实施发券熔断；{tags["GREEN"]} 组 GREEN 客群应加大投放。'
            elif tags['GREEN'] > 0:
                finding_text = f'{tags["GREEN"]} 组 GREEN 高转化客群，建议预算倾斜。'
            else:
                finding_text = '客群结构正常，无极端异常分组。'

        elif any(kw in mod for kw in ['销售', 'sales', '业绩', '营收', '成本']):
            insight_text = f'「{mod}」总销售额 CNY {total_sales:,.0f}，发券 {total_issued:,} 张。'
            finding_text = f'单券产出约 CNY {total_sales / max(total_issued, 1):.0f}，可作为券种优化基准线。'

        else:
            # Ultimate fallback: use the most relevant data available
            insight_text = f'「{mod}」当前 ROI {roi}%，核销率 {conversion}%，客单价 CNY {aov:,.0f}。'
            if parking_share > 70:
                finding_text = f'停车券占比 {parking_share}% 是核心风险点，建议削减至 30% 以下。'
            elif roi < 10:
                finding_text = f'ROI {roi}% 低于安全线，需全面审查营销策略。'
            elif tags['RED'] > 0:
                finding_text = f'{tags["RED"]} 组 RED 耗损客群需要重点关注。'
            else:
                finding_text = f'核心指标处于正常区间。停车券占比 {parking_share}%，客群 GREEN {tags["GREEN"]}/RED {tags["RED"]} 组。'

        return {
            'insight': insight_text,
            'finding': finding_text,
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
    Trend + lag prediction after simulation.
    
    Architecture (Fix: AI never generates numeric values):
    - DeepSeek LLM: only generates a natural-language analysis (ai_analysis) of the
      expected trend change — NOT numeric arrays.
    - Local DIMENSION_TRANSFORM: always computes the actual trend/lag numbers.
      This guarantees deterministic output: same input → same output every time.
    
    Why not let AI generate numbers:
      LLMs are probabilistic — even with temperature=0 + seed=42, numeric outputs
      drift between calls. For trend data that feeds charts and KPI cards,
      determinism is mandatory. AI's strength is narrative interpretation,
      not arithmetic precision.
    
    Returns { trend, lag, best_lag_day, predicted_by, ai_analysis (optional) }.
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

    # === Step 1: Always compute numeric trend via local DIMENSION_TRANSFORM ===
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

    predicted_by = '本地规则引擎'

    # === Step 2: DeepSeek generates narrative analysis only (NO numeric generation) ===
    ai_analysis = None
    api_key = _get_deepseek_key()
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key.strip(), base_url="https://api.deepseek.com/v1")

            # Build a compact summary of the changes for the LLM
            actions_desc = []
            for a in actions:
                if isinstance(a, dict):
                    eff = a.get('effect', '?')
                    p = a.get('pct', 0)
                    actions_desc.append(f"{eff} ({p:+d}%)")
                else:
                    actions_desc.append(str(a))

            # Summarize key numeric changes (computed locally, just for context)
            changes_summary = []
            if before_trend and before_trend.get('coupon') and trend.get('coupon'):
                old_total_coupon = sum(before_trend['coupon'])
                new_total_coupon = sum(trend['coupon'])
                if old_total_coupon > 0:
                    chg = (new_total_coupon - old_total_coupon) / old_total_coupon * 100
                    changes_summary.append(f"发券总量: {old_total_coupon:,} → {new_total_coupon:,} ({chg:+.1f}%)")
            if before_trend and before_trend.get('sales') and trend.get('sales'):
                old_total_sales = sum(before_trend['sales'])
                new_total_sales = sum(trend['sales'])
                if old_total_sales > 0:
                    chg = (new_total_sales - old_total_sales) / old_total_sales * 100
                    changes_summary.append(f"销售额: {old_total_sales:,} → {new_total_sales:,} ({chg:+.1f}%)")
            if before_lag and lag:
                old_best_r = max(lag, key=lambda x: x.get('r', 0) or 0).get('r', 0) if lag else 0
                new_best_r = max(lag, key=lambda x: x.get('r', 0) or 0).get('r', 0) if lag else 0
                changes_summary.append(f"最佳滞后相关系数: {old_best_r:.2f} → {new_best_r:.2f} (最佳窗口: {best_lag_day}天)")

            system_prompt = (
                "你是侨福芳草地购物中心的高级营销数据分析师。"
                "请根据采纳的优化建议及其预期数值变化，生成一段简洁的趋势变化解读。"
                "不需要生成任何数值数据（数值由系统计算），只需要做文字解读。"
                "纯中文，不要 emoji，不要 markdown，控制在 100 字以内。"
            )
            user_prompt = (
                f"采纳建议: {', '.join(actions_desc)}\n"
                f"数值变化:\n" + '\n'.join(changes_summary) + "\n\n"
                "请解读：这些变化意味着什么？趋势走向如何？"
            )

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4, max_tokens=300, timeout=15,
            )
            ai_analysis = response.choices[0].message.content.strip()
            predicted_by = 'DeepSeek LLM + 本地规则引擎'
            print(f'[Trend Prediction] DeepSeek analysis generated ({len(ai_analysis)} chars)')
        except Exception as e:
            print(f'[Trend Prediction] DeepSeek analysis failed: {e}')

    result = {
        'trend': trend,
        'lag': lag,
        'best_lag_day': best_lag_day,
        'predicted_by': predicted_by,
    }
    if ai_analysis:
        result['ai_analysis'] = ai_analysis

    _TREND_SIMULATION_CACHE[cache_key] = copy.deepcopy(result)
    return result
