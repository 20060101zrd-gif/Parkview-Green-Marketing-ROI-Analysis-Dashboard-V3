# 侨福芳草地 · 营销效能战情室

> 全栈营销 ROI 分析平台，打通「发券 → 核销 → POS 消费」全链路数据

一句话：帮商场自动算清楚每一张优惠券投下去到底赚了多少钱、哪类客群最值得投、发券到消费的最优时间窗口是多少天。支持 Streamlit BI 看板 + Flask Web 应用双交付形态，内置 AI 业务诊断引擎。

---

## 这个系统是做什么的？

30 秒看懂：商场每年发几万张优惠券（停车券、满减券、体验券），但运营人员只能看到发出去多少张，看不到这些券到底拉动了多少实际消费、ROI 是正还是负。本系统把发券数据（16 万条记录）和 POS 销售流水（3.2 万条交易）打通，自动计算 9 个核心 KPI，按 4 象限对客群自动分类，检测发券与消费之间的滞后天数，并在一个 6 页的 BI 看板上完成可视化呈现。

工作方式：就像给运营团队配了一个随身数据分析师——上传 CSV 就能看全局战情，点侧边栏能按会员等级、年龄段、时间范围自由筛选，点「智能诊室」DeepSeek 大模型会直接写出一段业务诊断报告告诉你哪里有问题、该怎么调。

---

## 系统怎么分析？

通俗类比（像体检报告，五道分析层层深入）：

> 第一道：全局战情 —— 今天 ROI 多少？有没有严重告警？一眼看清健康度。第二道：KPI 拆解 —— 9 个指标逐个看，每个指标都有公式、都有同比环比。第三道：结构诊断 —— 停车券是不是发太多了？餐饮业态产出够不够？左边成本右边产出，失衡一目了然。第四道：趋势与滞后 —— 周一发的券周几产生消费？系统自动算 Pearson 相关系数找出最优转化窗口。第五道：客群画像 —— 把顾客分成四类（薅羊毛的、自然高消费的、对券敏感的、普通路人），告诉你每一类该怎么区别对待。

技术实现：

五道分析，层层深入每一次数据刷新：

```
运营人员打开看板
      |
      v
[第一道：战情摘要]
4 张 KPI 卡片 + 三级告警横幅（严重/预警/健康，红/黄/绿圆角胶囊）
--> 一眼看清全局健康度，有告警立刻知道哪里出问题
      | 继续
      v
[第二道：KPI 总览]
9 个指标详情卡 + 度量值字典表（每项指标都有公式、单位、同比变化）
--> 想了解具体数字？这里每个指标怎么算的都写清楚了
      | 继续
      v
[第三道：投入产出结构]
左侧券种环形图（成本侧）+ 右侧业态销售额条形图（产出侧）
--> 停车券占发券总量 91.8%？结构单一风险一目了然
      | 继续
      v
[第四道：趋势与滞后分析]
双轴时间序列 + Pearson 相关系数（0/1/2/3/5/7/14/30 天偏移窗口）
+ IsolationForest 异常检测自动标记离群时间点
--> 发现发券后第 3 天是消费高峰，调整核销有效期到 3 天
      | 继续
      v
[第五道：客群价值诊断]
四象限散点图自动着色 + KMeans 聚类 + 交叉下钻详情表
--> 找出「高 ROI 转化型」客群，加大投入；冻结「券效耗损型」客群
      |
      v
AI 智能诊室：DeepSeek 大模型读完以上所有数据，生成自然语言诊断报告
```

| 场景 | 触发条件 | 系统反应 | 含义 |
|------|----------|----------|------|
| 正常运营 | 无异常 | 绿色告警 + 对勾图标 | 一切正常 |
| ROI 偏低 | ROI < 30% | 黄色预警 + 圆角三角图标 | 利润空间受压，需关注 |
| ROI 严重偏低 | ROI < 10% | 红色告警 + 圆形图标 | 紧急审查投放策略 |
| 停车券占比过高 | 停车券 > 发券总量 70% | 红色告警 | 严重结构性错配 |
| 核销率偏低 | 核销率 < 1% | 黄色预警 | 券激励力度不足 |
| 会员贡献偏低 | 会员销售 < 50% | 蓝色提示 | 会员运营存在缺口 |
| 券拉动销售过低 | 券渗透率 < 0.05% | 黄色预警 | 营销对整体业务杠杆不足 |

---

## 项目亮点

| 亮点 | 说明 |
|------|------|
| 完整业务闭环 | 覆盖「数据上传 → 指标计算 → 可视化 → AI 诊断 → 模拟推演 → 定时巡检 → 邮件告警 → 报告导出」全流程 |
| 全链路数据打通 | 将发券日志与 POS 销售流水跨系统关联，实现从「券」到「钱」的端到端归因 |
| 双 AI 模式 | DeepSeek 大模型（主力）+ 本地规则引擎（零依赖自动降级）。API 不可用时功能不受影响，仅叙事质量下降 |
| 本地模式保护数据隐私 | 一键切换到本地模式，系统完全离线运行，零外部 API 调用。适合对数据安全敏感的甲方内部部署 |
| 双应用架构 | Streamlit BI 看板（端口 8501，Python 原生，分析师探索用）+ Flask Web 应用（端口 8050，REST API + SPA，嵌入内部系统用） |
| 配置驱动 | 所有业务规则（KPI 公式、告警阈值、客群分类规则、CSV 列名映射）均为 YAML 文件，修改规则无需改代码 |
| Schema 灵活接入 | 支持多商场数据源，不同商场的 CSV 列名不同？改一行 YAML 配置即可，Python 代码零修改 |
| 开箱即用 | Docker 一键部署 + Render.com 免费部署，内置健康探针，拿到代码 3 分钟跑起来 |

---

## 系统整体结构

| 层 | 技术 | 职责 |
|----|------|------|
| BI 看板 | Streamlit 1.32+ + Plotly | 6 页交互式分析看板，侨福生态绿 × 奢侈金品牌配色 |
| Web 应用 | Flask 3.0+ + Chart.js + ECharts | 20+ REST API + 单页 SPA 看板，纯原生 JS（127KB） |
| 语义层 | MetricEngine + ComparisonEngine | 9 个统一 KPI 计算 + 同比环比引擎，全页面数值一致 |
| AI 引擎 | DeepSeek（OpenAI SDK） + 本地规则 | 双模洞察生成，LLM 不可用时自动降级，无感切换 |
| 机器学习 | scikit-learn IsolationForest + KMeans | 异常时间点检测 + 客群自动聚类（k=4） |
| 数据处理 | Pandas + NumPy | CSV 加载、清洗、维度对齐、VIP 等级映射 |
| 配置管理 | PyYAML | 5 个 YAML 配置文件驱动全部业务规则 |
| 定时任务 | schedule | Agent 独立进程，定时巡检 + 自动邮件告警 |
| 部署 | Docker + Render.com | 单容器部署，Render 免费额度一键上线 |

---

## 系统截图

### 数据上传与全局配置

数据上传页 — 侧边栏上传 CSV、选择场景书签、按会员等级/年龄段/时间范围筛选

### 一、战情摘要（指挥中心）

战情摘要 — 顶部三级告警横幅（严重/预警/健康，红/黄/绿圆角胶囊），4 张核心 KPI 卡片（ROI、总销售额、核销转化率、会员贡献占比），每张卡片底部附带 AI 分析注解行

战情摘要 — 双轴趋势图（发券量柱状图 + 销售额折线图）+ 券种结构环形图 + 业态销售额条形图，一页纵览全局

### 二、KPI 总览

KPI 总览 — 8 张 KPI 详情卡片，每张含数值、单位、同比/环比变化箭头、数据来源提示。支持模拟模式下的原始值 vs 模拟值对比

KPI 总览 — 度量值字典表：每个指标的 Key、显示名称、计算公式、当前值、单位、状态

### 三、投入产出结构

投入产出结构 — 左侧券种环形图（成本侧）+ 右侧业态销售额条形图（产出侧），即时识别停车券占比过高、餐饮/零售业态产出不足等结构性失衡

### 四、趋势滞后分析

趋势滞后分析 — 可调粒度（日/周/月）双轴时间序列，同时展示发券量、核销量、销售额三条曲线。支持切换滞后期数（0/1/2/3/5/7/14/30 天）

趋势滞后分析 — Pearson 相关系数矩阵 + 异常检测标注（IsolationForest 自动识别离群时间点），下方给出最优转化窗口建议

### 五、客群价值诊断

客群价值诊断 — 四象限散点图，按规则自动着色：红（券效耗损型）、金（自然高价值型）、绿（高ROI转化型）、灰（常规基石型），每个象限附带建议动作

客群价值诊断 — KMeans 自动聚类气泡图 + 客群详情表（人均领券、核销率、客单价、总销售额），支持按会员等级 × 年龄段交叉下钻

### 六、智能诊室

智能诊室 — DeepSeek LLM 自动生成 4 类诊断卡片：严重告警、预警提示、信息摘要、优化建议。每条建议可一键添加到模拟参数

智能诊室 — 自由多轮追问，DeepSeek 基于当前数据上下文实时回答，支持追问具体指标、客群、策略

智能诊室 — Agent 控制面板：手动触发巡检、一键导出 Markdown 报告、发送告警邮件、查看操作历史

### 模拟推演模式

模拟模式 — 采纳 AI 建议后的模拟状态：顶部横幅显示已应用的调整参数（带 × 移除按钮），KPI 卡片实时展示模拟值 vs 原始值对比

模拟模式 — 趋势图叠加原始曲线（虚线）与模拟曲线（实线），直观对比调整前后的时序变化

### Flask Web 应用

Flask Web 应用 — Chart.js + ECharts 单页看板（端口 8050），6 个分析模块集成在可折叠滚动页面中，右侧 AI 聊天抽屉支持逐模块追问

Flask Web 应用 — 告警卡片与模拟模式交互：圆形/圆角三角/圆形对勾三级图标体系，实时 KPI 更新

---

## 本地模式与数据安全

### 为什么要做本地模式？

甲方公司的数据安全部门通常有一条硬规定：**业务数据不允许通过任何外部 API 传输到第三方服务器**。如果系统接入了 DeepSeek 等云端大模型，每次 AI 洞察生成都会把指标摘要发给外部 API——这在严格的内网环境里是红线。

本系统提供「本地模式」开关（前端页面顶部按钮，一键切换），开启后：

- **零外部 API 调用**：所有 AI/LLM 相关的 HTTP 请求全部跳过，系统不向任何外部服务发送数据
- **AI 洞察自动降级**：DeepSeek 大模型不可用，自动切换为本地规则引擎，基于 YAML 配置文件中的告警规则 + 客群分类规则生成结构化的诊断文本
- **功能完全保留**：KPI 计算、趋势图、结构分析、客群分类、异常检测、模拟推演——这些全部在本地 Pandas/scikit-learn 完成，不受影响
- **降级后仅叙事质量略有下降**：本地引擎能告诉你「停车券占比 91.8%，严重告警」，DeepSeek 能告诉你「建议削减停车券预算 50%，将释放资源重定向至餐饮体验券，预计 ROI 可提升 15-20 个百分点」。两者的区别是「有结论」vs「有结论+有推演」

```javascript
// 前端模式切换逻辑（dashboard.js）
if (window._aiEnabled === false) {
  // 本地模式：跳过所有 AI/LLM API 端点
  // 不发送 /api/insight、/api/chat、/api/simulate 等请求
  // 注入空 fallback 数据，保证页面正常渲染
}
```

```python
# 后端降级逻辑（ai_service.py）
def generate_insight(data):
    if not AI_ENABLED:
        return local_rule_engine(data)  # 零依赖，纯 Python
    try:
        return deepseek_llm(data)       # 需 API Key
    except Exception:
        return local_rule_engine(data)  # 网络故障自动降级
```

---

## 与 Power BI / Tableau 的对比

很多商场的运营团队会问：「这跟 Power BI 有什么区别？我们已经有 Power BI 了。」

| 维度 | Power BI / Tableau | 本系统 |
|------|-------------------|--------|
| **上手门槛** | 需要会 DAX 公式、会拖拽字段建图表 | 上传 CSV 即用，零学习成本 |
| **分析灵活性** | 极高，可自由设计任意图表组合 | 固定 6 页分析模块，覆盖 90% 的日常分析场景 |
| **AI 诊断能力** | 需要额外购买 Copilot 订阅（$20/人/月） | 内置 DeepSeek，成本约 ¥3/月（全团队共享） |
| **部署成本** | Power BI Pro $10/人/月，Tableau $75/人/月 | 开源免费，Docker 自部署，Render 免费额度 |
| **数据隐私** | 数据上传到微软/Tableau 云端 | 本地运行，数据不出内网 |
| **业务定制** | 通用 BI，不懂「券效耗损型」是什么意思 | 内置商场营销领域知识，客群分类、滞后分析直接可用 |
| **维护成本** | 专人维护数据模型和仪表板 | YAML 配置改规则，运营人员自己就能调 |

**通俗总结**：Power BI 像 Excel 的高级版——什么都能做，但得你自己会做。本系统像是一个已经帮你搭好的「营销 ROI 分析模板」——打开就能用，不用学 DAX，不用拖字段，AI 直接告诉你结论。**Power BI 适合有专职数据分析师的团队做深度探索；本系统适合运营人员日常快速看数、发现异常、拿到行动建议。**

如果团队已经有 Power BI，本系统可以作为一个「快速诊断入口」——日常巡检用本系统（秒级出结论），深度钻取再用 Power BI（灵活自定义）。

---

## 技术选型

### Streamlit + Plotly（BI 看板）

本项目核心是一套从数据到洞察的完整分析链路。Streamlit 的纯 Python 特性让数据分析师可以直接把 Pandas DataFrame 渲染成交互图表，省去了前后端分离的开发成本。6 个分析页面各自独立，Streamlit 的 `st.navigation` 自动生成顶部导航栏，配合 `st.session_state` 实现跨页面的筛选条件同步。

```python
# 页面路由（app.py）
pages = {
    "战情摘要": "pages/01_战情摘要.py",
    "KPI总览": "pages/02_KPI总览.py",
    "投入产出结构": "pages/03_投入产出结构.py",
    "趋势滞后分析": "pages/04_趋势滞后分析.py",
    "客群价值诊断": "pages/05_客群价值诊断.py",
    "智能诊室": "pages/06_智能诊室.py",
}
```

### Flask + Chart.js + ECharts（Web 应用）

Flask Web 应用面向的是不需要安装 Python 的终端用户（分享链接即可访问）。后端 20+ REST API 端点覆盖 KPI 计算、趋势数据、客群数据、AI 洞察、模拟推演全流程，前端纯原生 JavaScript（127KB）通过 Fetch API 调用后端，Chart.js 渲染 KPI 趋势图、ECharts 渲染环形图和聚类散点图。

```javascript
// API 调用示例（dashboard.js）
const endpoints = [
  { key: 'kpis', url: '/api/kpis' },
  { key: 'trend', url: '/api/trend?granularity=weekly' },
  { key: 'structure', url: '/api/structure' },
  { key: 'cohorts', url: '/api/cohorts' },
  { key: 'insight', url: '/api/insight' },
];
```

### 双存储：Pandas DataFrame + YAML 配置

Pandas 和 YAML 在本系统中分工明确：

**Pandas 负责数据计算**。16 万条发券记录 + 3.2 万条销售流水全部加载为 DataFrame，通过 MetricEngine 统一计算 9 个 KPI。`status_code` 字段（1=真实核销, 2=系统过期, 3=闲置未用）通过 `df['status_code'] = df['coupon_status'].map(...)` 一行代码完成状态映射。pandas 的 `groupby` + `agg` 天然适合按会员等级、年龄段、时间维度的多维聚合。

**YAML 负责规则管理**。5 个配置文件各司其职：`metrics.yaml` 定义 9 个 KPI 的公式和单位，`alerts.yaml` 定义 6 条告警规则的阈值和严重程度，`cohort_rules.yaml` 定义 4 象限客群分类逻辑，`schema_mapping.yaml` 定义外部 CSV 列名到内部标准列名的映射。运营人员想调「ROI 低于多少算告警」？改 `alerts.yaml` 一行数字即可，无需碰 Python 代码。

### scikit-learn（机器学习）

两个场景使用 scikit-learn：

- **IsolationForest 异常检测**：在趋势滞后分析页，对时间序列数据逐点计算异常分数，自动标记发券量或销售额的离群时间点。contamination=0.1，即预期约 10% 的数据点为异常。帮助运营人员发现「哪个周末的数据明显不对」。
- **KMeans 客群聚类**：在客群诊断页，按核销率 × 客单价 × 人均领券量三个维度自动聚为 4 簇（k=4），与四象限规则分类互相印证。如果规则说「这是 GREEN 客群」但聚类分到了 RED 簇，说明规则阈值可能需要调整。

### Docker Compose（部署）

单容器部署（python:3.11-slim），EXPOSE 8501。`render.yaml` 预配置了 Render.com 免费额度一键部署（新加坡区域），自动检测 Dockerfile，推送代码即上线。

---

## 自动化巡检

Agent 定时巡检脚本独立于 Streamlit 运行：

```bash
python agent_scheduler.py              # 默认每 24 小时
python agent_scheduler.py --interval 6  # 每 6 小时
```

5 步巡检流程：加载数据 → 计算 KPI → 异常检测 → AI 诊断 → Agent 行动（发送邮件 + 导出 Markdown 报告）。配置在 `data/agent_config.json`，Streamlit 页面可远程修改开关和间隔。

---

## 快速启动

### 1. 克隆并配置

```bash
git clone <仓库地址>
cd Parkview_Green_Marketing_ROI_Analysis_Dashboard
pip install -r requirements.txt
```

### 2. 准备数据

将以下文件放入 `data/` 目录：
- `BI_Dashboard_Ready_Data.csv` — 优惠券发放记录
- `销售查询.csv` — POS 销售流水

也可以启动后在侧边栏直接上传。

### 3. 一键启动

```bash
# Streamlit BI 看板（端口 8501）
streamlit run app.py

# Flask Web 应用（端口 8050）
pip install -r webapp/requirements.txt
python webapp/app.py
```

### 4. 启用 AI 洞察（可选）

在 [platform.deepseek.com](https://platform.deepseek.com) 注册获取 API Key，存入 `.streamlit/secrets.toml`：

```toml
DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxx"
```

或设置环境变量 `DEEPSEEK_API_KEY`（Docker / Render 部署时使用）。

不配置也可以正常使用，系统自动降级为本地规则引擎。

### 5. Docker 部署

```bash
docker build -t parkview-roi .
docker run -p 8501:8501 -e DEEPSEEK_API_KEY=sk-xxx parkview-roi
```

### 6. 运行测试

```bash
python tests/run_tests.py
```

---

## API 接口清单

### Streamlit 应用（无 REST API，纯 Python 页面渲染）

所有 6 个分析页面通过 `st.navigation` 路由，`st.session_state` 传递筛选条件。

### Flask Web 应用

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/kpis` | 9 个核心 KPI 数据 |
| GET | `/api/trend` | 趋势时间序列，支持 granularity=daily/weekly/monthly |
| GET | `/api/structure` | 券种结构 + 业态销售额 |
| GET | `/api/cohorts` | 客群分类数据 |
| GET | `/api/cohort-detail` | 客群下钻详情 |
| GET | `/api/lag` | 滞后相关分析数据 |
| GET | `/api/category` | 业态分类数据 |
| GET | `/api/insight` | AI 洞察生成（需 DeepSeek API Key） |
| POST | `/api/chat` | AI 多轮追问 |
| POST | `/api/simulate` | 模拟推演参数提交 |
| GET | `/api/anomalies` | 异常检测结果 |
| GET | `/api/kmeans` | KMeans 聚类结果 |
| GET | `/api/filter-opts` | 筛选器可选项（会员等级、年龄段等） |
| GET | `/api/suggested-questions` | AI 建议追问列表 |
| POST | `/api/ai/toggle` | 切换 AI 模式（本地模式 / LLM 模式） |
| GET | `/api/health` | 健康探针 |

---

## 项目结构

```
Parkview_Green_Marketing_ROI_Analysis_Dashboard/
├── app.py                              # Streamlit 入口文件
├── agent_scheduler.py                  # 独立后台定时巡检脚本
├── requirements.txt                    # Streamlit 依赖（8 个包）
├── Dockerfile                          # 容器构建文件
├── render.yaml                         # Render.com 一键部署配置
│
├── pages/                              # Streamlit 6 页 BI 看板
│   ├── 01_战情摘要.py                  # 指挥中心
│   ├── 02_KPI总览.py                   # KPI 详情
│   ├── 03_投入产出结构.py               # 成本 vs 产出
│   ├── 04_趋势滞后分析.py               # 趋势与滞后
│   ├── 05_客群价值诊断.py               # 客群诊断
│   └── 06_智能诊室.py                  # AI 洞察室
│
├── config/                             # 配置层（YAML + Python）
│   ├── theme.py                        # CSS 设计系统（600行）
│   ├── schema_mapping.yaml             # 多商场 CSV 列名映射
│   ├── metrics.yaml                    # 9 个 KPI 定义（公式/单位/告警阈值）
│   ├── alerts.yaml                     # 6 条告警规则
│   ├── cohort_rules.yaml               # 4 象限客群分类规则
│   └── mappings.py                     # VIP 等级 + 年龄段映射
│
├── semantic_layer/                     # 语义层 — 统一指标计算
│   ├── metric_engine.py                # 9-KPI 计算引擎
│   └── comparison.py                   # 同比 / 环比引擎
│
├── ai_engine/                          # AI 与机器学习
│   ├── insight_generator.py            # DeepSeek LLM + 本地规则降级
│   ├── anomaly_detector.py             # IsolationForest 异常检测
│   ├── cohort_clustering.py            # KMeans 客群聚类（k=4）
│   └── agent_actions.py                # 邮件 / 报告 / 日志动作
│
├── data_engine/
│   └── data_loader.py                  # Schema 驱动 CSV 加载与清洗
│
├── components/                         # Streamlit 复用组件
│   ├── header.py                       # 全局导航栏
│   ├── kpi_cards.py                    # 玻璃态 KPI 卡片
│   ├── filters.py                      # 侧边栏筛选器 + 场景书签
│   └── export_utils.py                 # CSV/Excel 导出
│
├── views/                              # 独立可复用视图层
│   ├── view_kpi.py                     # KPI 首屏对标
│   ├── view_structure.py               # 券种 vs 业态结构拆解
│   ├── view_cohorts.py                 # 客群分层与投入产出对标
│   └── view_trends.py                  # 趋势与滞后性对标
│
├── webapp/                             # Flask Web 应用（端口 8050）
│   ├── app.py                          # 20+ REST API 路由
│   ├── requirements.txt
│   ├── templates/index.html            # SPA 外壳（39KB）
│   ├── static/
│   │   ├── css/dashboard.css           # 看板样式（24KB）
│   │   ├── js/dashboard.js             # 前端逻辑（127KB 原生 JS）
│   │   └── images/
│   └── services/                       # 业务逻辑层
│       ├── data_service.py             # 数据加载 / 缓存 / 筛选
│       ├── kpi_service.py              # KPI 计算（含券种成本模型）
│       ├── ai_service.py               # AI 服务（DeepSeek + 三级分析）
│       ├── ml_service.py               # ML 服务（IsolationForest + KMeans）
│       └── scheduler_service.py        # 数据调度器
│
├── tests/                              # 测试套件
│   ├── run_tests.py
│   ├── test_five_fixes.py              # 5 项修复回归测试
│   ├── test_hover_analysis.py          # 悬浮交互测试
│   ├── test_lag_chart.py               # 滞后图测试
│   └── test_scheduler.py               # 调度器测试（含邮件通知）
│
├── data/                               # 数据目录（示例数据已脱敏）
│   ├── BI_Dashboard_Ready_Data.csv
│   ├── 销售查询.csv
│   ├── parkviewgreen_v2_user_coupon(1).csv
│   ├── user_info.csv
│   ├── build_dashboard_data.py         # 数据预处理脚本
│   ├── agent_config.json               # Agent 配置
│   └── reports/                        # 自动导出的报告
│
├── assets/                             # 品牌资源
│   ├── parkview_green_logo.png
│   └── parkview_green_logo_dark.png
│
├── screenshots/                        # 产品截图（17 张）
│
├── .streamlit/
│   └── secrets.toml                    # DEEPSEEK_API_KEY
│
├── UI_DESIGN_SYSTEM.md                 # UI 设计系统规范文档
├── ui_design_prototype.html            # 高保真 HTML 原型
└── 北京侨福芳草地_数字化营销投入产出 (ROI) 分析战情室.md  # 项目答辩文档
```

---

## 已知局限

- **单机部署**：当前为单节点部署，无分布式扩展。数据量超过百万级建议将数据引擎迁移至 Polars / DuckDB。
- **固定分析模块**：6 个分析页面覆盖 90% 日常场景，但不支持像 Power BI 那样自由拖拽自定义图表。如需深度自定义分析，建议搭配 Power BI 使用（本系统做快速诊断入口，Power BI 做深度钻取）。
- **AI 依赖网络**：DeepSeek 大模型模式需要网络连接。本地模式下 AI 洞察降级为规则引擎，结论质量下降（但结构化指标不受影响）。
- **数据源限制**：当前仅支持 CSV 文件上传或本地文件路径。如需对接数据库（MySQL/PostgreSQL），需自行扩展 `data_engine/data_loader.py`。

---

## 开源协议

MIT License — 详见 LICENSE

---

**关于**

侨福芳草地 · 营销效能战情室 — Streamlit BI 看板 + Flask Web 应用 + DeepSeek AI 诊断，Docker 一键部署

**技术栈**

- Python 71.8%
- JavaScript 15.2%
- HTML 9.1%
- CSS 3.7%
- Other 0.2%
