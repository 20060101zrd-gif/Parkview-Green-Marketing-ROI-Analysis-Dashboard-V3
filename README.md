# 侨福芳草地 · 营销效能战情室

> **Parkview Green Marketing ROI Command Center**
>
> 商业综合体优惠券营销 ROI 全链路分析平台 · Streamlit + Flask 双应用 · DeepSeek AI 业务诊断

![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B?style=flat-square&logo=streamlit)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?style=flat-square&logo=flask)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3%2B-F7931E?style=flat-square&logo=scikit-learn)
![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?style=flat-square&logo=docker)

---

## 这是什么

商场每年投放数万张优惠券，运营只能看到「发出去多少张」，看不到「到底赚回来多少钱」。这个系统把发券记录和 POS 消费流水打通，自动计算每张券的 ROI，把顾客分成四类（薅羊毛的 / 高价值的 / 对券敏感的 / 路人），用 AI 写出诊断报告，告诉你该砍哪类券、该投哪类人。

---

## 一、数据接入：自动拉取 & 发送邮件

**说明**：定时轮询监控目录发现新 CSV 文件即自动加载，配 SMTP 可在出现严重告警时自动发邮件。拉取间隔、监控目录、收件人邮箱均可在页面内配置并保存。

![自动拉取与邮件通知配置](screenshots/00_flask_upload.png)

---

## 二、六个核心分析页面

### 1. 战情摘要 — 指挥中心

**说明**：首页。顶部三级告警横幅（严重 / 预警 / 健康，红黄绿圆角胶囊），4 张核心 KPI 卡片（ROI、总销售额、核销转化率、会员贡献占比），下方双轴趋势图与券种成本结构环形图，一页纵览全局。

![战情摘要](screenshots/01_executive_summary_alerts_kpi.png)

四象限的简版视图（不带触发条件表）：

![客群四象限简版](screenshots/02_cohort_quadrant_matrix.png)

### 2. KPI 总览

**说明**：8 张 KPI 详情卡片，含数值、单位、同比/环比变化箭头、数据来源提示。

![KPI 总览](screenshots/04_kpi_overview_cards.png)

### 3. 投入产出结构

**说明**：左侧券种环形图（成本侧）vs 右侧业态销售额条形图（产出侧），结构性失衡一目了然。

![投入产出结构](screenshots/05_cost_revenue.png)

### 4. 趋势滞后分析

**说明**：Pearson 相关系数在 0~30 天滞后窗口上自动计算，找出最优转化周期（当前为 3 天）。下方数据表展示每个滞后天数的相关系数与强度判断。

![趋势滞后分析](screenshots/06_trend_lag_correlation.png)

### 5. 客群价值诊断

**说明**：四象限散点图（红：券效耗损型 / 金：自然高价值型 / 绿：高 ROI 转化型 / 灰：常规基石型）+ 标签触发条件表（每条规则的阈值）+ 客群分布概览（含建议策略）。

![客群四象限矩阵 + 触发条件](screenshots/07_cohort_quadrant_with_rules.png)

下方为 Top 5 客群明细表（按销售额），含发券量、核销量、核销率、客单价、标签：

![客群 Top 5 明细表](screenshots/08_cohort_top5_detail.png)

---

## 三、LLM 模式 — DeepSeek AI 业务诊断

系统默认**本地模式**（零外部调用），点击右上角切换到 LLM 模式后，DeepSeek 大模型接入。

### 本地模式下的智能诊室

**说明**：本地模式下，智能诊室页面提示「LLM 模式专属功能，请点击右上角模式切换按钮后启用」。这是数据隐私优先的设计。

![智能诊室 - 本地模式提示](screenshots/09_insight_local_mode.png)

### LLM 模式 · 四种 AI 分析卡片

**说明**：切换到 LLM 模式后，DeepSeek 自动生成四类诊断卡片（严重告警 / 预警提示 / 信息摘要 / 优化建议），每条建议可一键采纳进模拟参数。引擎标识「引擎：DeepSeek LLM」。

![智能诊室 - LLM 四种诊断卡片](screenshots/10_insight_llm_diagnostic_cards.png)

### LLM 模式 · 滑动选取进行分析（可锁定当前分析）

**说明**：可以滑动选取任意模块标题进行 AI 分析。顶部诊断卡片支持「解锁 / 收起」按钮——锁定时卡片固定悬浮在页面顶部不随滚动消失；收起后所有当前分析都隐藏，需要时一键展开。下图展示的就是锁定状态下的 KPI 总览诊断卡片。

![LLM 模式 · 锁定当前分析（KPI 总览诊断）](screenshots/13_kpi_overview_with_ai.png)

### LLM 模式 · 综合诊断摘要（战情摘要页）

**说明**：智能诊室的综合诊断卡片，作为"战情指挥"悬浮在页面顶部，把所有分析浓缩为一段话。

![战情摘要 + AI 综合诊断摘要](screenshots/12_executive_with_ai_summary.png)

### LLM 模式 · 四种 AI 分析卡片

**说明**：切换到 LLM 模式后，DeepSeek 自动生成四类诊断卡片（严重告警 / 预警提示 / 信息摘要 / 优化建议），每条建议可一键采纳进模拟参数。引擎标识「引擎：DeepSeek LLM」。

![智能诊室 - LLM 四种诊断卡片](screenshots/10_insight_llm_diagnostic_cards.png)

---

## 四、问一问 — 跨页悬浮 / 可隐藏 / 左下角找回

**说明**：点击任意模块旁的「问」按钮，弹出针对该模块的 AI 问答抽屉。**支持三个特性**：

- **跨页悬浮**：抽屉弹出后，切换到其他页面时它仍跟随显示
- **可隐藏**：点击最小化按钮可把抽屉隐藏到左下角的"找回栏"
- **左下角栏可找回**：隐藏的抽屉以蓝色 tab 形式常驻在左下角 tray bar，点一下即可恢复

![问一问抽屉 · 跨页悬浮 + 最小化到左下角 tray bar](screenshots/14_ask_drawer_cross_page.png)

---

## 五、AI 智能问答 — 全局数据上下文

**说明**：在战情摘要页的 AI 智能问答面板。预置四个高频追问（你能做什么？会员贡献占比多？为什么停车券转化这么低？哪个客群的转化效率最高？），也支持自由提问。基于全局数据上下文，DeepSeek 给出针对性回答。

![AI 智能问答面板](screenshots/11_ai_chat_panel.png)

---

## 六、採纳建议 — 模拟推演

**说明**：在 AI 诊断卡片上点击「采纳建议」后，建议会自动加入模拟参数集合。顶部模拟横幅实时显示已采纳的所有参数（带 × 可单独移除），KPI 卡片同步展示模拟值 vs 原始值对比，趋势图叠加原始曲线（实色）与模拟曲线（虚线）。

### 模拟模式 · KPI 对比

![模拟模式 - 4 条参数已采纳 + KPI 对比](screenshots/15_flask_simulation_mode.png)

模拟横幅显示 4 条已采纳参数（削减停车券 60% / 优化滞后窗口 / GREEN 客群 +30% / RED 客群 -80%），每条参数带 × 移除按钮。KPI 卡片底部显示「AI分析」注解，对比模拟值与原始值的变化。

### 模拟模式 · 趋势线对比

![模拟模式 - 趋势线对比](screenshots/16_trend_lag_with_simulation.png)

趋势滞后分析页的模拟对比，绿色实线为发券量原始曲线，灰色虚线为模拟后曲线，可直观看到调整后的时序变化。

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
9 KPI 统一     ├── DeepSeek 大模型（主力）
计算引擎       ├── 本地规则引擎（零依赖降级）
同比环比       ├── IsolationForest 异常检测
               └── KMeans 客群聚类 (k=4)
          │
    ┌─────┴─────┐
    ▼           ▼
Streamlit      Flask
(端口 8501)    (端口 8050)
6 页 BI 看板    REST API + SPA
```

两个应用共享同一套数据、同一套 KPI 定义、同一个 AI 引擎。Streamlit 适合分析师深度探索，Flask Web 应用适合嵌入内部系统或分享只读链接。

---

## 功能模块

| 模块 | 做什么 | 技术实现 |
|:---|:---|:---|
| 战情摘要 | 4 张 KPI 卡片 + 告警横幅 + 趋势图 + 结构图，一眼看清全局 | Streamlit + Plotly + 自定义玻璃态 CSS |
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
| AI 诊断报告 | 本地规则引擎生成结构化文本 | DeepSeek 大模型生成自然语言分析 |
| AI 追问 | 不可用 | 可用，多轮对话 |
| 模拟推演 | 不可用 | 可用 |
| 数据隐私 | 零外部调用，数据不出内网 | 指标摘要发送到 DeepSeek API |
| 成本 | 免费 | ~¥0.002/次，~¥3/月 |

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
#    也可以在启动后通过侧边栏直接上传

# 3. 启动 Streamlit 看板
streamlit run app.py
# → http://localhost:8501

# 4. 启动 Flask Web 应用（可选）
pip install -r webapp/requirements.txt
python webapp/app.py
# → http://localhost:8050
```

**Docker 一键部署：**

```bash
docker compose up -d
# Streamlit → http://localhost:8501
# Flask     → http://localhost:8050
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
├── app.py                    # Streamlit 入口
├── agent_scheduler.py        # 定时巡检脚本
├── Dockerfile                # Streamlit 容器
├── Dockerfile.webapp         # Flask 容器
├── docker-compose.yml        # 双服务编排
├── render.yaml               # Render.com 部署
├── requirements.txt
│
├── pages/                    # Streamlit 6 个页面
├── config/                   # YAML 配置（所有业务规则）
├── semantic_layer/           # 统一 KPI 计算
├── ai_engine/                # AI & ML
├── data_engine/              # 数据加载
├── components/               # Streamlit 复用组件
├── webapp/                   # Flask Web 应用
├── tests/                    # 测试
├── screenshots/              # 产品截图 (17 张)
├── data/                     # CSV 数据文件
├── assets/                   # Logo 等静态资源
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
4. python tests/test_hover_analysis.py
5. python tests/test_lag_chart.py
6. pytest tests/test_scheduler.py -v
7. docker build Dockerfile
8. docker build Dockerfile.webapp
```

---

## 技术栈

| 层 | 技术 |
|:---|:---|
| BI 框架 | Streamlit 1.32+ |
| Web 框架 | Flask 3.0+ |
| 可视化 | Plotly, Matplotlib, Chart.js, ECharts |
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

## License

MIT
