# 侨福芳草地 · 营销效能战情室

> **Parkview Green Marketing ROI Command Center**
>
> 商业综合体优惠券营销 ROI 全链路分析平台 · Flask Web 应用 · DeepSeek AI 业务诊断

![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?style=flat-square&logo=flask)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3%2B-F7931E?style=flat-square&logo=scikit-learn)
![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?style=flat-square&logo=docker)

---

## 这是什么

商场每年投放数万张优惠券，运营只能看到「发出去多少张」，看不到「到底赚回来多少钱」。这个系统把发券记录和 POS ( Point of Sale ) 消费流水打通，自动计算每张券的 ROI ( Return on Investment )，把顾客分成四类（薅羊毛的 / 高价值的 / 对券敏感的 / 路人），用 AI 写出诊断报告，告诉你该砍哪类券、该投哪类人。

---

## 一、数据接入：自动拉取 & 发送邮件

定时轮询监控目录发现新 CSV 文件即自动加载，配 SMTP 可在出现严重告警时自动发邮件。拉取间隔、监控目录、收件人邮箱均可在页面内配置并保存。

![自动拉取与邮件通知配置](screenshots/00_flask_upload.png)

---

## 二、六个核心分析页面

### 1. 战情摘要 — 指挥中心

首页。顶部三级告警横幅（严重 / 预警 / 健康，红黄绿圆角胶囊），4 张核心 KPI 卡片（ROI、总销售额、核销转化率、会员贡献占比），下方双轴趋势图与券种成本结构环形图，一页纵览全局。

![战情摘要](screenshots/01_executive_summary_alerts_kpi.png)

四象限的简版视图（不带触发条件表）：

![客群四象限简版](screenshots/02_cohort_quadrant_matrix.png)

### 2. KPI 总览

8 张 KPI 详情卡片，含数值、单位、同比/环比变化箭头、数据来源提示。

![KPI 总览](screenshots/04_kpi_overview_cards.png)

### 3. 投入产出结构

左侧券种环形图（成本侧）vs 右侧业态销售额条形图（产出侧），结构性失衡一目了然。

![投入产出结构](screenshots/05_cost_revenue.png)

### 4. 趋势滞后分析

Pearson 相关系数在 0~30 天滞后窗口上自动计算，找出最优转化周期（当前为 3 天）。下方数据表展示每个滞后天数的相关系数与强度判断。

![趋势滞后分析](screenshots/06_trend_lag_correlation.png)

### 5. 客群价值诊断

四象限散点图（红：券效耗损型 / 金：自然高价值型 / 绿：高 ROI 转化型 / 灰：常规基石型）+ 标签触发条件表（每条规则的阈值）+ 客群分布概览（含建议策略）。

![客群四象限矩阵 + 触发条件](screenshots/07_cohort_quadrant_with_rules.png)

下方为 Top 5 客群明细表（按销售额），含发券量、核销量、核销率、客单价、标签：

![客群 Top 5 明细表](screenshots/08_cohort_top5_detail.png)

---

## 三、LLM 模式 — DeepSeek AI 业务诊断

系统默认**本地模式**（本地规则引擎生成结构化诊断，零外部调用），点击右上角切换到 LLM 模式后，DeepSeek 大模型接入。

### 本地模式下的智能诊室

本地模式下，智能诊室页面提示「LLM 模式专属功能，请点击右上角模式切换按钮后启用」。这是数据隐私优先的设计。

![智能诊室 - 本地模式提示](screenshots/09_insight_local_mode.png)

### 3.1 AI 分析

按工作流顺序：页面分析 → 选取 → 问一问 → AI 问答。

**页面分析 · 综合诊断摘要（战情摘要页）**

智能诊室的综合诊断卡片，作为"战情指挥"悬浮在页面顶部，把全页分析浓缩为一段话。

![战情摘要 + AI 综合诊断摘要](screenshots/12_executive_with_ai_summary.png)

**滑动选取进行分析（针对某模块的详细分析）**

可以滑动选取任意模块标题，针对所选模块做详细 AI 分析。顶部诊断卡片支持「解锁 / 收起」按钮——锁定时卡片固定悬浮在页面顶部不随滚动消失；收起后所有当前分析都隐藏，需要时一键展开。

![LLM 模式 · 锁定当前分析（KPI 总览诊断）](screenshots/13_kpi_overview_with_ai.png)

**问一问（对模块更详细的提问分析）**

点击任意模块旁的「问」按钮，弹出针对该模块的 AI 问答抽屉，可对该模块做更详细的提问分析。支持三个特性：

- **跨页悬浮**：抽屉弹出后，切换到其他页面时它仍跟随显示
- **可隐藏**：点击最小化按钮可把抽屉隐藏到左下角的"找回栏"
- **左下角栏可找回**：隐藏的抽屉以蓝色 tab 形式常驻在左下角 tray bar，点一下即可恢复

![问一问抽屉 · 跨页悬浮 + 最小化到左下角 tray bar](screenshots/14_ask_drawer_cross_page.png)

**AI 智能问答（全局数据上下文，随机四个可换一批）**

在战情摘要页的 AI 智能问答面板。随机展示四个追问，可点「换一批」刷新，也支持自由提问。基于全局数据上下文，DeepSeek 给出针对性回答。面板下方展示当前核心 KPI 快照，便于追问时快速参考数据。

![AI 智能问答面板](screenshots/11_ai_chat_panel.png)

### 3.2 模拟模式

在 AI 诊断卡片上点击「采纳建议」后，建议会自动加入模拟参数集合。顶部模拟横幅实时显示已采纳的所有参数（带 × 可单独移除），KPI 卡片同步展示模拟值 vs 原始值对比，趋势图叠加原始曲线（实色）与模拟曲线（虚线）。

进入模拟模式后，顶部智能分析面板会自动切入**模拟前后对比分析**。面板右上角的「模拟分析」按钮可切换回**页面分析**视图，方便在模拟数据与页面上下文之间来回对照。

**智能诊室动态诊断卡片**

智能诊室采用**本地诊断 + AI 建议**双层架构：

**本地规则引擎负责诊断（100% 确定性，每次刷新结果一致）：**
1. 分析当前 KPI、客群、券种、滞后数据 → 遍历 9 个诊断维度，与硬编码阈值比对 → 输出**场景标签**（如 `parking_over_70`、`roi_below_10` 等 14 个标签）+ 严重程度
2. 本地 `SCENARIO_MAP` 查表 → 得到确定性的 `effect + pct`
3. 本地引擎生成卡片的**标题、严重度徽章、effect_label、action 短标签**——这些字段永远由代码确定，不受 AI 影响

**DeepSeek 负责建议文案（自然语言生成）：**
- 每条卡片的 **text 正文**（50-80 字诊断描述，结合实际数据）
- 每条卡片的 **how_to 3 步操作指南**（具体、可量化、有时限的执行步骤）
- 智能诊室顶部 **executive_summary** 总结段落
- 各页面 **page_overview** / **module_focus** 分析
- 模拟模式 **commentary**、**chat_followup** 自由问答

**为什么这样分工？** 诊断结论（停车券占比 > 70% → `parking_over_70`，ROI < 10% → `roi_below_10`）由代码锁死，同一条数据永远出同一组卡片。DeepSeek 拿到确定性的诊断结果后，用自然语言写"具体怎么做"——因为输入数据一样、诊断标签一样、pct 一样，建议方向也自然一致。LLM 不可用时，本地模板引擎提供完整 fallback。

![智能诊室 - LLM 诊断卡片](screenshots/10_insight_llm_diagnostic_cards.png)

**模拟模式 · KPI 对比**

模拟横幅显示 5 条已采纳参数（修正跟车时效应 135% / 削减停车券 70% / 加大青英会员客群投放 / 提升核销率 110% / 扩大渗透 15%），每条参数带 × 移除按钮。顶部"智能分析·模拟前后对比"面板由 DeepSeek 撰写三段文字：**整体评价**（如"优化策略显著提升 ROI 和销售额，但发券量大幅减少需关注长期影响"）、**关键变化点**（逐条数据事实，如"ROI 从 254% 升至 371%，核销率从 3.7% 提至 8.83%"）、**潜在风险**（如"发券量削减 70% 可能抑制新客获取"）。KPI 卡片数值旁直接显示 ↑↓ 变化箭头与百分比（绿色上升、红色下降），底部「AI分析」注解补充说明变化原因。

![模拟模式 - 5 条参数已采纳 + 模拟前后对比 commentary + KPI 对比](screenshots/15_flask_simulation_mode.png)

**模拟模式 · 趋势线对比**

趋势滞后分析页的模拟对比，绿色实线为发券量原始曲线，灰色虚线为模拟后曲线，可直观看到调整后的时序变化。

![模拟模式 - 趋势线对比](screenshots/16_trend_lag_with_simulation.png)

---

## 架构

```
数据层：CSV 文件（发券记录 + POS 销售流水）
          │ schema_mapping.yaml 列名映射
          ▼
数据引擎：Pandas 加载清洗 · status_code 推导 · VIP 等级映射 · 年龄世代推算
          │
    ┌─────┴─────┐
    ▼           ▼
语义层         AI 引擎
9 KPI 统一     ├── 本地规则引擎（主力 · 100% 确定性）
计算引擎       │   ├── 9 维度场景检测（阈值比对）
同比环比       │   ├── SCENARIO_MAP 查表（effect + pct）
               │   ├── _build_rec_text 模板（中文诊断文案 + how_to）
               │   └── DIMENSION_TRANSFORM 数学变换（趋势模拟）
               ├── DeepSeek 大模型（增强 · 自然语言表达）
               │   ├── executive_summary 总结文案
               │   ├── page_overview / module_focus 页面分析
               │   └── chat_followup 自由问答
               ├── IsolationForest 异常检测
               └── KMeans 客群聚类 (k=4)
          │
          ▼
        Flask
    (端口 8050)
  REST API + SPA
```

应用共享同一套数据、同一套 KPI 定义、同一个 AI 引擎。Flask Web 应用适合嵌入内部系统或分享只读链接。

---

## 功能模块

| 模块 | 做什么 | 技术实现 |
|:---|:---|:---|
| 战情摘要 | 4 张 KPI 卡片 + 告警横幅 + 趋势图 + 结构图，一眼看清全局 | Flask + Chart.js + 自定义玻璃态 CSS |
| KPI 总览 | 8 张 KPI 详情卡 + 度量值字典表（含公式） | MetricEngine 统一计算 + ComparisonEngine 同比环比 |
| 投入产出结构 | 券种（成本）vs 业态销售额（产出）左右对比 | Plotly 环形图 + 横向条形图 |
| 趋势滞后分析 | 双轴时间序列 + 可调滞后窗口 + Pearson 相关 + 异常检测 | Plotly + scikit-learn IsolationForest |
| 客群价值诊断 | 四象限自动分类 + KMeans 聚类 + 交叉下钻 | YAML 规则引擎 + scikit-learn KMeans |
| 智能诊室 | AI 生成诊断报告 + 自由追问 + 模拟推演 + Agent 巡检 | DeepSeek API + 本地规则降级 |

---

## 业务模型

### 核心 KPI（9 个）

| KPI | 公式 | 说明 |
|:----|:-----|:-----|
| 营销 ROI | `(券拉动销售额 − 估算成本) / 估算成本 × 100` | 核心指标，营销投入的真实回报 |
| 核销转化率 | `真实核销量 / 发券总量 × 100` | 券 → 消费转化效率 |
| 总销售额 | `sum(销售额)` | 全量销售业绩 |
| 客单价 | `总销售额 / 交易笔数` | 单笔交易价值 |
| 会员贡献占比 | `会员销售额 / 总销售额 × 100` | 会员体系贡献度 |
| 券销售渗透率 | `券拉动销售额 / 总销售额 × 100` | 营销对整体收入的杠杆效应 |
| 发券总量 | `count(发券记录)` | 投放规模 |
| 真实核销量 | `sum(status=1)` | 真正被使用的券数 |
| 整体核销率 | `总核销量 / 发券总量 × 100` | 综合核销效率 |

### 客群四象限

| 标签 | 判定条件 | 策略 |
|:-----|:---------|:-----|
| RED 券效耗损型 | 人均领券 ≥ 5 且 客单价 < ¥200 | 冻结发券，限 3 张/人/月 |
| GOLD 自然高价值型 | 客单价 ≥ ¥1,000 且 核销率 < 2% | 重服务留存，低券敏感度 |
| GREEN 高ROI转化型 | 核销率 ≥ 1% 且 客单价 ≥ ¥500 | 加大投入，提高券配额 |
| GRAY 常规基石型 | 无明显特征 | 标准运营节奏 |

### 告警规则（6 条）

| 条件 | 级别 | 含义 |
|:-----|:-----|:-----|
| ROI < 10% | 严重 | 营销投入产出严重失衡 |
| ROI < 30% | 预警 | 利润空间受压 |
| 停车券占比 > 70% | 严重 | 券种结构严重单一 |
| 核销率 < 1% | 预警 | 券激励力度不足 |
| 券渗透率 < 0.05% | 预警 | 营销杠杆效应过低 |
| 会员贡献 < 50% | 提示 | 会员运营存在缺口 |

---

## 本地模式 vs LLM 模式

系统默认以**本地模式**运行，不依赖任何外部 API。点击页面顶部按钮可切换到 **LLM 模式**（需配置 DeepSeek API Key）。

| | 本地模式 | LLM 模式 |
|:---|:---|:---|
| KPI 计算 / 图表 / 告警 / 异常检测 / 聚类 | 正常 | 正常 |
| 智能诊室诊断卡片（场景检测、严重度、建议、pct 数值） | 本地规则引擎（100% 确定性） | **同本地**——卡片永远由本地规则引擎生成 |
| 智能诊室总结文案（executive_summary + top_finding） | 本地规则引擎模板文本 | DeepSeek 大模型生成自然语言 |
| 页面分析 / 模块聚焦分析 | 本地规则引擎（阈值匹配 + 模板文本） | DeepSeek 大模型 |
| AI 追问 | 关键词匹配（基础回答） | 可用，多轮对话，全量数据上下文 |
| 模拟推演（趋势预测数值 + KPI 对比） | 可用（本地 DIMENSION_TRANSFORM 做确定性数学变换） | 可用（同上，分析文案由 DeepSeek 生成） |
| 数据隐私 | 零外部调用，数据不出内网 | 指标摘要发送到 DeepSeek API |
| 成本 | 免费 | ~¥0.002/次，~¥3/月 |

**关键设计原则**：诊断卡片的数量、标题、严重度、建议方向和 pct 数值由本地规则引擎 100% 确定。同一份数据，无论是本地模式还是 LLM 模式，诊断卡片**完全一致**。DeepSeek 仅增强文字表达的自然度和丰富度，不影响诊断结论本身。

本地模式的存在是因为甲方数据安全部门通常不允许业务数据通过外部 API 传输。即使永远不开 LLM 模式，所有数据分析和可视化功能完整可用。

---

## 与 Power BI 的对比

| 维度 | Power BI / Tableau | 本系统 |
|:---|:---|:---|
| 上手门槛 | 需要学 DAX、拖拽建图 | 上传 CSV 即用 |
| 分析灵活性 | 极高，自由设计任意图表 | 固定 6 页模块，覆盖 90% 日常场景 |
| AI 能力 | 需额外购买 Copilot（$20/人/月） | 内置 DeepSeek，全团队 ~¥3/月 |
| 部署成本 | Power BI Pro $10/人/月 | 免费开源，Docker 自部署 |
| 数据隐私 | 数据上传云端 | 本地运行，数据不出内网 |
| 业务适配 | 通用 BI，不懂营销术语 | 内置客群分类、滞后分析等营销领域知识 |
| 维护 | 需要专人维护数据模型 | YAML 改规则，运营自己就能调 |

本系统定位为**营销 ROI 快速诊断入口**。日常巡检用本系统秒级出结论，深度自定义分析再用 Power BI。

---

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 准备数据（放入 data/ 目录）
#    - BI_Dashboard_Ready_Data.csv  （发券记录）
#    - 销售查询.csv                 （POS 销售流水）
#    也可以在启动后通过页面上传

# 3. 启动 Flask Web 应用
pip install -r webapp/requirements.txt
python webapp/app.py
# → http://localhost:8050
```

**Docker 一键部署：**

```bash
docker compose up -d
# Flask → http://localhost:8050
```

**启用 AI 洞察（可选）：** 在 [platform.deepseek.com](https://platform.deepseek.com) 获取 API Key，写入 `.streamlit/secrets.toml`：

```toml
DEEPSEEK_API_KEY = "sk-xxxxxxxx"
```

---

## 配置驱动

所有业务规则均为 YAML 文件，修改无需动代码：

| 文件 | 内容 | 例子：改什么 |
|:---|:---|:---|
| `config/metrics.yaml` | 9 个 KPI 的定义、公式、单位 | 改 ROI 计算公式 |
| `config/alerts.yaml` | 6 条告警规则、阈值、严重程度 | 把 ROI 告警线从 10% 调到 20% |
| `config/cohort_rules.yaml` | 4 象限客群分类条件 | 调整"高价值"客群的客单价门槛 |
| `config/schema_mapping.yaml` | CSV 列名 → 内部标准列名映射 | 接入另一个商场的数据源 |

---

## 项目结构

```
Parkview_Green_Marketing_ROI_Analysis_Dashboard/
├── Dockerfile.webapp         # Flask 容器
├── docker-compose.yml        # 服务编排
├── render.yaml               # Render.com 部署
├── requirements.txt
│
├── config/                   # YAML 配置（所有业务规则）
├── webapp/                   # Flask Web 应用
│   ├── app.py                # Flask 入口
│   ├── services/             # 后端 API 服务
│   ├── static/               # 前端静态资源（CSS/JS）
│   └── templates/            # HTML 模板
├── tests/                    # 测试
├── screenshots/              # 产品截图
├── data/                     # CSV 数据文件
└── .github/workflows/ci.yml  # GitHub Actions CI
```

---

## CI / 测试

每次 Push 自动运行 GitHub Actions（47+ 个测试用例）：

```yaml
# .github/workflows/ci.yml
1. pip install 依赖 (含 pytest)
2. python tests/run_tests.py
3. python tests/test_five_fixes.py
4. python tests/test_fix_three_issues.py
5. python tests/test_hover_analysis.py
6. python tests/test_lag_chart.py
7. python tests/test_dimension_simulation.py
8. python tests/test_global_integration.py
9. python tests/test_scenario_map.py
10. pytest tests/test_scheduler.py -v
11. docker build Dockerfile.webapp
```

---

## 技术栈

| 层 | 技术 |
|:---|:---|
| Web 框架 | Flask 3.0+ |
| 可视化 | Chart.js, Plotly, Matplotlib, ECharts |
| 数据处理 | Pandas 2.0+, NumPy |
| 机器学习 | scikit-learn 1.3+ (IsolationForest, KMeans) |
| AI 大模型 | DeepSeek (OpenAI SDK) |
| 配置管理 | PyYAML |
| 定时任务 | schedule |
| 容器化 | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## 已知局限

- 单机部署，百万级以上数据建议迁移至 Polars / DuckDB
- 固定 6 页分析模块，不支持像 Power BI 一样自由拖拽自定义图表
- DeepSeek 模式下 AI 洞察需网络连接；本地模式下降级为规则引擎
- 当前仅支持 CSV 文件，数据库直连需自行扩展

---

## 预测运行逻辑

采纳建议后的趋势预测分四步走，**本地规则引擎**和 DeepSeek 各司其职：

**第一步 · 本地规则引擎场景检测**：遍历 9 个维度（停车券占比、ROI、核销率、渗透率、会员贡献、客单价、GREEN/RED 客群、滞后相关性），将每个维度的实际数据与硬编码阈值比对，生成**场景标签 + 严重程度**（low/medium/high）。例如 ROI=5% → `roi_below_10` + high；核销率=3% → `conversion_below_1` + low。**这一步完全在本地执行，不调用 DeepSeek，100% 确定性。**

**第二步 · 本地 SCENARIO_MAP 查表**：拿场景标签 + 严重程度 → 查表得到固定的 `effect + pct`。例如停车券占比 > 70% + high severity → `coupon_volume: -70`。同样场景标签 + 同样严重度 = 同样的 pct，**100% 确定性**。运营可在 `SCENARIO_MAP` 中手动调整 pct，无需动 AI prompt。

**第三步 · DIMENSION_TRANSFORM 确定性变换**：拿 `effect + pct` 对趋势和滞后数据做纯数学运算（乘法/加法）。同输入永远同输出，图表线不会每次刷新都不同。

**第四步 · DeepSeek 生成文字解读**：基于诊断卡片的结果和变换后的数值，用自然语言写 **executive_summary**（诊室顶部总结）、**模拟前后对比 commentary**（"整体评价 / 关键变化点 / 潜在风险"三段文字）、**page_overview** / **module_focus** 页面分析、**chat_followup** 自由问答。卡片标题、严重度、建议内容、pct 数值**全部由本地引擎生成**，DeepSeek 不参与卡片内容。如 API 不可用，本地引擎自动 fallback。

### 场景标签 → effect + pct 映射表

| 场景标签 | 含义 | effect (效果维度) | 轻度 | 中度 | 重度 |
|:---|:---|:---|:---|:---|:---|
| `parking_over_70` | 停车券占比 > 70% | 发券量 | -30% | -50% | -70% |
| `parking_over_40` | 停车券占比 > 40% | 发券量 | -15% | -30% | -50% |
| `red_cohort_drain` | RED 耗损客群 | 发券量 | -50% | -70% | -90% |
| `over_issuance` | 过度投放 | 发券量 | -20% | -40% | -60% |
| `roi_below_10` | ROI < 10% | 销售效率 | +10% | +20% | +30% |
| `roi_below_30` | ROI < 30% | 销售效率 | +5% | +10% | +15% |
| `conversion_below_1` | 核销率 < 1% | 销售效率 | +10% | +20% | +30% |
| `penetration_below_5` | 渗透率 < 0.05% | 销售效率 | +5% | +15% | +25% |
| `high_green_cohort` | GREEN 高转化客群 | 销售效率 | +15% | +25% | +40% |
| `member_contribution_low` | 会员贡献偏低 | 销售效率 | +5% | +10% | +20% |
| `low_aov` | 客单价偏低 | 销售效率 | +5% | +10% | +20% |
| `weak_lag_correlation` | 滞后相关性偏弱 | 滞后效应 | +10% | +20% | +30% |
| `negative_lag` | 滞后呈负相关 | 滞后效应 | +15% | +25% | +35% |
| `healthy_overall` | 整体健康 | 销售效率 | 0% | +5% | +10% |

DeepSeek 和本地规则引擎**共享同一张表**。无论走哪条路径，同样的数据场景得到同样的 `effect + pct`。

为什么不给 AI 直接生成数值？LLM 是概率模型，不是计算器。即使 `temperature=0`，同样的输入每次调用数值仍可能不同，趋势线和 KPI 卡片需要绝对确定、可复现。

### 为什么选择本地规则引擎

这个架构不是技术妥协，而是针对战情室场景的刻意设计。

**稳定性：同一份数据，两次刷新必须看到同样的诊断。**

早期版本让 DeepSeek 负责场景检测和严重度判断，`temperature=0.4`，同样的数据每次刷新卡片内容和数量都不一样。降到 `temperature=0` 后依然不稳定——LLM 本质是概率模型，同一个 prompt 两次调用返回的 JSON 可能微妙不同，一个标签丢了、严重度变了、卡片数量也变了。运营总监打开战情室看到不同诊断，不可接受。

现在改为：阈值比对（`if parking_share > 0.7 → parking_over_70`）由 Python 代码执行，100% 确定性。同样的数据永远得到同样的场景标签、同样的严重度、同样的卡片。

**离线可用：甲方数据安全部门不允许业务数据走外部 API。**

如果诊断卡片依赖 DeepSeek，没网就没诊断——那本地模式就是个空壳。现在本地规则引擎独立跑完整诊断流程，DeepSeek 只是锦上添花的文案优化，有没有它都不影响核心功能。

**速度和成本：本地规则毫秒级响应，零 API 费用。**

9 个维度阈值比对 + SCENARIO_MAP 查表 + 模板渲染，全部在本地完成，不到 1ms。DeepSeek API 调用则需要 2-5 秒网络往返。

**运营可调：改阈值和 pct 不需要改 prompt，直接改代码里的常量。**

`SCENARIO_MAP` 是一个 Python dict，运营想调整"停车券占比 > 70% 时削减 50% 而不是 70%"，直接改数值即可，不需要理解 prompt engineering。

总结一句话：**数字和结论归代码管，表达和解读归 AI 管。**

### 本地规则引擎 vs DeepSeek 职责总览

| 职责 | 谁来做 |
|:---|:---|
| 诊断（场景检测、严重度、effect、pct、卡片标题、action 短标签） | 本地规则引擎 100% |
| 建议文案（卡片 text 正文、how_to 3 步操作指南） | DeepSeek（temperature=0），失败则本地模板 fallback |
| 趋势模拟数值（发券量/销售额/滞后 r 值变换） | 本地 DIMENSION_TRANSFORM 100% |
| executive_summary + top_finding 总结文字 | DeepSeek（temperature=0），失败则本地 fallback |
| page_overview / module_focus 页面分析 | DeepSeek，失败则本地 fallback |
| chat_followup 自由问答 | DeepSeek，失败则本地关键词匹配 |
| 模拟分析 commentary 文字 | DeepSeek，失败则无 commentary |

### 三个底层维度（DIMENSION_TRANSFORM）

所有场景标签最终都映射到以下三个底层维度中的一个，由 `DIMENSION_TRANSFORM` 执行数学变换：

| 维度 | 变换方式 | 方向 |
|:---|:---|:---|
| 发券量 (`coupon_volume`) | 发券量 × (1 + pct/100) | 正=增发，负=削减 |
| 销售效率 (`sales_efficiency`) | 销售额 × (1 + pct/100) | 正=提升，负=下降 |
| 滞后效应 (`lag_correlation`) | 滞后 r 值 + pct/100 | 正=增强，负=减弱 |

新增维度只需在 `DIMENSION_TRANSFORM` 中注册变换函数 + 在 `SCENARIO_MAP` 中添加场景标签，AI 和前端自动适配。

---
## License

MIT
