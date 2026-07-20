/**
 * Parkview Green Marketing ROI Dashboard — Frontend Engine v3.0
 * Handles data fetching, chart rendering, page routing, filters, simulation, export.
 */
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

// Issue 4: Strip [xxx] bracket tags from AI text
function cleanText(t) { return (t || '').replace(/\*\*(.+?)\*\*/g, '$1').replace(/#{1,6}\s/g, '').replace(/\[[A-Za-z]+\]/g, '').trim(); }

function fmt(n) {
  n = n || 0;
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(1) + '亿';
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(0) + '万';
  return Number(n).toLocaleString('zh-CN');
}
function fmtPct(n, decimals) { return Number(n || 0).toFixed(decimals || 2) + '%'; }

// ===== GLOBAL STATE =====
var globalData = {};
var currentGranularity = 'weekly';
var simulationMode = false;
var simulationParams = [];  // [{label, action, target, pct}]
var simulationTrendFetched = false;  // 标记当前模拟参数下是否已获取趋势预测，避免重复请求
var cohortExpanded = false;
var selectedLevels = [];
var selectedAges = [];
var selectedStartDate = '';
var selectedEndDate = '';

// ===== DATA FETCH =====
async function loadAll(filters) {
  filters = filters || {};
  var params = [];
  if (filters.levels && filters.levels.length) filters.levels.forEach(function(l) { params.push('level=' + encodeURIComponent(l)); });
  if (filters.ages && filters.ages.length) filters.ages.forEach(function(a) { params.push('age=' + encodeURIComponent(a)); });
  if (filters.start_date) params.push('start_date=' + encodeURIComponent(filters.start_date));
  if (filters.end_date) params.push('end_date=' + encodeURIComponent(filters.end_date));
  var qs = params.length ? '?' + params.join('&') : '';

  var endpoints = [
    ['kpis',           '/api/kpis' + qs,            {}],
    ['structure',      '/api/coupon-structure' + qs, []],
    ['cohorts',        '/api/cohorts' + qs,         []],
    ['category',       '/api/category-revenue' + qs, []],
    ['trend',          '/api/trend' + (qs ? qs + '&' : '?') + 'granularity=' + currentGranularity, {labels:[], coupon:[], sales:[], correlation:0}],
    ['lag',            '/api/lag' + qs,             []],
    ['summary',        '/api/summary' + qs,         {}],
    ['filterOpts',     '/api/filter-options',       {}],
    ['cohortDetail',   '/api/cohort-detail' + qs,   []],
  ];

  // In local mode, skip AI/LLM endpoints entirely — no API calls to external services
  if (window._aiEnabled !== false) {
    endpoints.push(['insight',    '/api/insight' + qs,    {}]);
    endpoints.push(['anomalies',  '/api/anomalies' + qs,  {anomalies:[], anomaly_count:0}]);
    endpoints.push(['kmeans',     '/api/kmeans' + qs,     {clusters:[], profiles:{}}]);
  }

  var results = await Promise.allSettled(
    endpoints.map(function(e) { return fetch(e[1]).then(function(r) { return r.json(); }); })
  );

  var data = {};
  // In local mode, inject empty fallbacks for skipped AI endpoints
  if (window._aiEnabled === false) {
    data.insight = {};
    data.anomalies = {anomalies:[], anomaly_count:0};
    data.kmeans = {clusters:[], profiles:{}};
  }
  results.forEach(function(result, i) {
    var key = endpoints[i][0], fallback = endpoints[i][2];
    if (result.status === 'fulfilled') { data[key] = result.value; }
    else { console.warn('[loadAll] ' + key + ' failed, using fallback'); data[key] = fallback; }
  });
  globalData = data;
  return data;
}

// R4: Track current page for AI panel
var currentPage = 'summary';

function renderAll(data) {
  if (simulationMode) {
    data = applySimulation(data);
    globalData = data;  // sync simulated data back to global
    updateSimulationBanner();
    loadSimulationAnalysis();
    // Prompt 1: Fetch AI trend prediction only once per simulation state
    if (!simulationTrendFetched) {
      fetchSimulationTrend();
      simulationTrendFetched = true;
    }
  } else {
    hideSimulationBanner();
    var oldBox = document.getElementById('sim-analysis-box');
    if (oldBox) oldBox.remove();
    // Prompt 1: Clear trend prediction label
    var predLabel = document.getElementById('trend-prediction-label');
    if (predLabel) predLabel.textContent = '';
  }
  updateDateRange(data.summary);
  updateSummary(data);
  updateTrendChart(data.trend);
  updateDonutCharts(data.structure);
  updateCohortMatrix(data.cohorts);
  updateCohortMatrixPage(data.cohorts);
  updateCategoryBars(data.category, data.structure);
  updateLagChart(data.lag);
  updateCohortTables(data.cohorts);
  updateKPITables(data.kpis);
  updateInsights(data);
  updateAIInsight(data.insight);
  updateFilterBar(data.filterOpts);
  updateCohortDetailTable(data.cohortDetail);
  updateSuggestedQuestions(data);
  buildFilterSelectors(data.filterOpts);
  updateSimulationNotes(data);
  updateAlertCards();
  // R4: Always-on AI panel — render after everything else
  // Defer to avoid blocking: the /api/insight (diagnostic) request is still
  // in-flight on Flask's single-threaded dev server.  Wait 500ms so the
  // diagnostic response can land first, then fetch page_overview.
  if (data.insight && data.insight.executive_summary) {
    // If diagnostic insight already returned, fill panel immediately from its summary
    var c = document.getElementById('ai-panel-content');
    var e = document.getElementById('ai-panel-engine');
    if (c) c.textContent = cleanText(data.insight.executive_summary);
    if (e && data.insight.generated_by) e.textContent = '引擎: ' + data.insight.generated_by;
  }
  setTimeout(function() { updateSmartAnalysisPanel(); }, 800);
}


// ===== R4: Smart Analysis Panel (always-on, renamed, page-aware) =====
var aiPanelFocus = null;     // R5: hover-set focus topic
var aiPanelLocked = false;   // R5: lock hover analysis (true = fully frozen)
var aiPanelForcePage = false; // Force page-level analysis even in simulation mode
var aiPanelRestoreTimer = null;
var aiPanelCollapsed = false;
var aiPanelLastContent = ''; // R5: cache content when locked
var aiPanelLockedTitle = ''; // R5: cache title when locked

function getPageTopic(page) {
  var map = {
    'summary':  '整体概览分析',
    'kpi':      'KPI维度深度分析',
    'structure':'券种结构与业态分析',
    'trend':    '趋势与滞后性解读',
    'cohort':   '客群分层分析',
    'insight':  '综合诊断结论'
  };
  return map[page] || '整体概览分析';
}

function updateSmartAnalysisPanel(forceRebuild) {
  // If in local mode, hide the panel entirely
  if (window._aiEnabled === false) {
    var box = document.getElementById('smart-analysis-panel');
    if (box) box.style.display = 'none';
    return;
  }

  // Plan B: Guard — don't fetch analysis if data isn't loaded yet.
  // In LLM mode, ensure the panel is visible but skip content fetch until data is ready.
  if (!globalData || !globalData.kpis) {
    var box = document.getElementById('smart-analysis-panel');
    if (box) box.style.display = 'block';
    return;
  }

  var boxId = 'smart-analysis-panel';
  var box = document.getElementById(boxId);

  // Create panel if not exists
  if (!box) {
    box = document.createElement('div');
    box.id = boxId;
    box.style.cssText = 'background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;margin:0 0 16px 0;overflow:hidden;';
    var contentEl = document.querySelector('.content');
    if (contentEl) {
      var simBanner = document.getElementById('simulation-banner');
      if (simBanner) simBanner.parentNode.insertBefore(box, simBanner.nextSibling);
      else contentEl.insertBefore(box, contentEl.firstChild);
    }
  }
  box.style.display = 'block';  // Ensure visible in LLM mode

  // Issue 10: Priority: hover module > simulation default > page default
  var titleText, titleExtraStyle = '';
  var isPageView = !aiPanelFocus && (!simulationMode || aiPanelForcePage);
  if (aiPanelFocus) {
    // Module-level hover: highlighted title (works in both sim and non-sim mode)
    var simTag = simulationMode ? '的模拟分析' : '';
    titleText = '智能分析 · 针对「' + aiPanelFocus + '」' + simTag;
    titleExtraStyle = 'background:#dbeafe;padding:2px 8px;border-radius:4px;';
  } else if (simulationMode && !aiPanelForcePage) {
    titleText = '智能分析 · 模拟前后对比';
  } else {
    // Page-level default
    titleText = '智能分析 · ' + getPageTopic(currentPage);
  }

  // Fix 6: Lock button — always show, even in simulation mode
  var lockBtnHtml = '';
  var lockStyle = aiPanelLocked
    ? 'font-size:11px;padding:2px 10px;margin-right:4px;background:#1e40af;color:#fff;border:1px solid #1e40af;border-radius:4px;font-weight:600;cursor:pointer;'
    : 'font-size:11px;padding:2px 10px;margin-right:4px;background:transparent;color:#1e40af;border:1px solid #93c5fd;border-radius:4px;cursor:pointer;';
  lockBtnHtml = '<button id="ai-panel-lock-btn" style="' + lockStyle + '">' + (aiPanelLocked ? '解锁' : '锁定') + '</button>';

  // Simulation-only toggle: "页面分析" ↔ "模拟分析"
  // Only visible in simulation mode, sits next to lock button
  var simToggleBtnHtml = '';
  if (simulationMode) {
    var simToggleStyle = aiPanelForcePage
      ? 'font-size:11px;padding:2px 10px;margin-right:4px;background:#1e40af;color:#fff;border:1px solid #1e40af;border-radius:4px;font-weight:600;cursor:pointer;'
      : 'font-size:11px;padding:2px 10px;margin-right:4px;background:transparent;color:#1e40af;border:1px solid #93c5fd;border-radius:4px;cursor:pointer;';
    simToggleBtnHtml = '<button id="ai-panel-sim-toggle-btn" style="' + simToggleStyle + '">' + (aiPanelForcePage ? '页面分析' : '模拟分析') + '</button>';
  }

  box.innerHTML =
    '<div style="padding:10px 16px;cursor:pointer;display:flex;align-items:center;justify-content:space-between;user-select:none;background:#dbeafe;border-bottom:1px solid #bfdbfe;">' +
      '<span style="font-weight:600;color:#1e40af;font-size:14px;' + titleExtraStyle + '">' + titleText + '</span>' +
      '<div style="display:flex;align-items:center;gap:4px;">' +
        simToggleBtnHtml +
        lockBtnHtml +
        '<span id="ai-panel-toggle" style="color:#60a5fa;font-size:12px;cursor:pointer;">' + (aiPanelCollapsed ? '▶ 展开' : '▼ 收起') + '</span>' +
      '</div>' +
    '</div>' +
    '<div id="ai-panel-content" style="padding:14px 16px 12px;font-size:13px;line-height:1.8;color:#1e3a5f;white-space:pre-line;min-height:40px;' + (aiPanelCollapsed ? 'display:none;' : '') + '">AI正在分析中...</div>' +
    '<div id="ai-panel-engine" style="padding:0 16px 10px;font-size:11px;color:#94a3b8;text-align:right;' + (aiPanelCollapsed ? 'display:none;' : '') + '"></div>';

  // Collapse/expand
  var headerEl = box.querySelector('div');
  headerEl.addEventListener('click', function(e) {
    if (e.target && e.target.id === 'ai-panel-lock-btn') return;
    aiPanelCollapsed = !aiPanelCollapsed;
    var toggle = document.getElementById('ai-panel-toggle');
    var content = document.getElementById('ai-panel-content');
    var engine = document.getElementById('ai-panel-engine');
    if (aiPanelCollapsed) {
      content.style.display = 'none';
      engine.style.display = 'none';
      toggle.textContent = '▶ 展开';
    } else {
      content.style.display = 'block';
      engine.style.display = 'block';
      toggle.textContent = '▼ 收起';
    }
  });

  // R5: Lock button handler — fully freeze/unfreeze content
  var lockBtn = document.getElementById('ai-panel-lock-btn');
  if (lockBtn) {
    lockBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      aiPanelLocked = !aiPanelLocked;
      if (aiPanelLocked) {
        // Kill all pending hover timers so nothing reverts us
        clearTimeout(hoverTimer);
        clearTimeout(aiPanelRestoreTimer);
        // Cache current content
        var c = document.getElementById('ai-panel-content');
        aiPanelLastContent = c ? c.textContent : '';
        updateSmartAnalysisPanel(true);
      } else {
        // Unlock: clear focus and restore page default, keep hover alive
        aiPanelFocus = null;
        aiPanelLastContent = '';
        aiPanelLockedTitle = '';
        clearTimeout(aiPanelRestoreTimer);
        updateSmartAnalysisPanel(true);
      }
    });
  }

  // Simulation toggle button — switches between simulation analysis and page analysis
  var simToggleBtn = document.getElementById('ai-panel-sim-toggle-btn');
  if (simToggleBtn) {
    simToggleBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      aiPanelForcePage = !aiPanelForcePage;
      if (aiPanelForcePage) {
        // Switching to page view: clear hover, fetch page analysis
        aiPanelFocus = null;
        aiPanelLastContent = '';
        aiPanelLockedTitle = '';
        clearTimeout(hoverTimer);
        clearTimeout(aiPanelRestoreTimer);
      }
      // Rebuild panel — button text + fetch dispatch follow aiPanelForcePage
      updateSmartAnalysisPanel(true);
    });
  }

  // Issue 10: Fetch dispatch — hover > page-force > simulation > page default
  if (aiPanelFocus) {
    fetchFocusedAnalysis(aiPanelFocus);
  } else if (aiPanelForcePage || !simulationMode) {
    fetchPageInsight();
  } else {
    fetchSimAnalysisForPanel();
  }
}

function fetchSimAnalysisForPanel() {
  var content = document.getElementById('ai-panel-content');
  var engine = document.getElementById('ai-panel-engine');
  if (!content) return;

  // Fix 8: Cancel any pending page_insight request to prevent race condition
  if (aiPanelAbortController) aiPanelAbortController.abort();
  aiPanelAbortController = new AbortController();
  var signal = aiPanelAbortController.signal;
  var timeoutId = setTimeout(function() { aiPanelAbortController.abort(); }, 15000);

  var before = (globalData._original && globalData._original.kpis) || {};
  var after = globalData.kpis || {};
  var actions = simulationParams.map(function(p) { return p.label; });

  fetch('/api/simulation-analysis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ before: before, after: after, actions: actions }),
    signal: signal
  })
  .then(function(r) { return r.json(); })
  .then(function(res) {
    clearTimeout(timeoutId);
    var text = cleanText(res.analysis || res.content || res.summary || '暂无分析结果');
    if (content) content.textContent = text;
    if (engine && (res.engine || res.generated_by)) engine.textContent = '引擎: ' + (res.engine || res.generated_by);
  })
  .catch(function(err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') return;
    if (content) content.textContent = '已采纳 ' + simulationParams.length + ' 项优化建议，核心 KPI 变化见各卡片标注。';
  });
}

// Three-tier unified: page-level analysis
function fetchPageInsight() {
  var content = document.getElementById('ai-panel-content');
  var engine = document.getElementById('ai-panel-engine');
  if (!content) return;
  content.textContent = '正在加载页面分析...';

  // Cancel any pending request
  if (aiPanelAbortController) aiPanelAbortController.abort();
  aiPanelAbortController = new AbortController();
  var signal = aiPanelAbortController.signal;
  var timeoutId = setTimeout(function() { aiPanelAbortController.abort(); }, 12000);

  var url = '/api/insight?type=page_overview&page=' + encodeURIComponent(currentPage);
  fetch(url, { signal: signal })
    .then(function(r) { return r.json(); })
    .then(function(res) {
      clearTimeout(timeoutId);
      var summary = cleanText(res.summary || res.executive_summary || '暂无分析结果');
      var extra = '';
      if (res.findings && res.findings.length) {
        extra += '\n\n关键发现：\n' + res.findings.map(function(f, i) { return (i + 1) + '. ' + f; }).join('\n');
      }
      if (res.recommendation) {
        extra += '\n\n建议：' + res.recommendation;
      }
      if (content) content.textContent = summary + extra;
      if (engine && res.generated_by) engine.textContent = '引擎: ' + res.generated_by;
      // Update panel title to reflect current page
      var titleEl = document.querySelector('#ai-panel-box div span');
      if (titleEl) titleEl.textContent = '智能分析 · ' + getPageTopic(currentPage);
    })
    .catch(function(err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') return;
      if (content) content.textContent = '页面分析暂不可用，请稍后刷新。';
    });
}

// Three-tier unified: module-level hover analysis (with timeout + abort)
var aiPanelAbortController = null;
var aiPanelSafetyTimer = null;
function fetchFocusedAnalysis(focus) {
  // Strip trailing "问" from ask button text
  focus = focus.replace(/\s*问\s*$/, '').trim();
  // Always get fresh element references
  var content = document.getElementById('ai-panel-content');
  var engine = document.getElementById('ai-panel-engine');
  if (!content) return;
  content.textContent = '正在分析「' + focus + '」...';

  // Cancel any pending request
  if (aiPanelAbortController) aiPanelAbortController.abort();
  aiPanelAbortController = new AbortController();
  var signal = aiPanelAbortController.signal;

  // 10 second timeout (DeepSeek typically responds in 5-8s)
  var timeoutId = setTimeout(function() { if (aiPanelAbortController) aiPanelAbortController.abort(); }, 10000);

  // Safety: after 4s, show "please wait" hint
  var progressTimer = setTimeout(function() {
    var c = document.getElementById('ai-panel-content');
    if (c && c.textContent.indexOf('正在分析') >= 0) {
      c.textContent = '「' + focus + '」分析中，AI 服务响应较慢，请稍候...';
    }
  }, 4000);

  // Hard safety: after 8s, fall back to local analysis
  if (aiPanelSafetyTimer) clearTimeout(aiPanelSafetyTimer);
  aiPanelSafetyTimer = setTimeout(function() {
    clearTimeout(progressTimer);
    var c = document.getElementById('ai-panel-content');
    if (c && (c.textContent.indexOf('正在分析') >= 0 || c.textContent.indexOf('响应较慢') >= 0)) {
      c.textContent = '「' + focus + '」模块数据已加载，当前显示为基于规则的本地分析。\n\n建议结合其他模块进行交叉分析。';
      var e = document.getElementById('ai-panel-engine');
      if (e) e.textContent = '引擎: 本地规则引擎';
    }
  }, 8000);

  var url = '/api/insight?type=module_focus&module=' + encodeURIComponent(focus);
  fetch(url, { signal: signal })
    .then(function(r) { return r.json(); })
    .then(function(res) {
      clearTimeout(timeoutId);
      clearTimeout(progressTimer);
      if (aiPanelSafetyTimer) { clearTimeout(aiPanelSafetyTimer); aiPanelSafetyTimer = null; }
      var text = cleanText(res.insight || res.content || '暂无分析');
      if (res.finding) text += '\n\n发现：' + res.finding;
      var c = document.getElementById('ai-panel-content');
      var e = document.getElementById('ai-panel-engine');
      if (c) c.textContent = text;
      if (e && res.generated_by) e.textContent = '引擎: ' + res.generated_by;
    })
    .catch(function(err) {
      clearTimeout(timeoutId);
      clearTimeout(progressTimer);
      if (aiPanelSafetyTimer) { clearTimeout(aiPanelSafetyTimer); aiPanelSafetyTimer = null; }
      if (err.name === 'AbortError') return;
      var c = document.getElementById('ai-panel-content');
      if (c) c.textContent = '「' + focus + '」模块分析暂不可用，3 秒后切回页面级分析。';
      clearTimeout(aiPanelRestoreTimer);
      aiPanelRestoreTimer = setTimeout(function() {
        aiPanelFocus = null;
        updateSmartAnalysisPanel();
      }, 3000);
    });
}

// R4: Legacy simulation analysis loader — now delegates to smart panel
function loadSimulationAnalysis() {
  if (simulationMode) updateSmartAnalysisPanel();
}

// Prompt 1: Fetch AI-predicted trend + lag data (with retry)
var trendRetryCount = 0;
var maxTrendRetries = 3;
function fetchSimulationTrend(retry) {
  if (!simulationMode || !globalData._original) return;
  if (!retry) trendRetryCount = 0;
  var beforeTrend = globalData._original.trend || {};
  var beforeLag = globalData._original.lag || [];
  // Send structured actions with effect + pct for dimension-based simulation
  var actions = simulationParams.map(function(p) {
    return { effect: p.action, pct: p.pct };
  });

  var predLabel = document.getElementById('trend-prediction-label');
  var retryMsg = trendRetryCount > 0 ? ('，第 ' + trendRetryCount + ' 次重试...') : '';
  if (predLabel) predLabel.textContent = '预测中' + retryMsg;

  fetch('/api/simulation-trend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ before_trend: beforeTrend, before_lag: beforeLag, actions: actions })
  })
  .then(function(r) { return r.json(); })
  .then(function(result) {
    // Validate trend: labels/coupon/sales arrays must match length
    var validTrend = result.trend && result.trend.labels && result.trend.labels.length > 0;
    if (validTrend) {
      var tl = result.trend.labels.length;
      var hasCoupon = result.trend.coupon && result.trend.coupon.length === tl;
      var hasSales = result.trend.sales && result.trend.sales.length === tl;
      if (!hasCoupon || !hasSales) validTrend = false;
      if (validTrend) {
        for (var i = 0; i < tl; i++) {
          if (isNaN(result.trend.coupon[i]) || isNaN(result.trend.sales[i])) { validTrend = false; break; }
        }
      }
    }
    // Validate lag: every item must have numeric lag and r
    var validLag = result.lag && result.lag.length > 0;
    if (validLag) {
      for (var j = 0; j < result.lag.length; j++) {
        if (result.lag[j].lag == null || isNaN(result.lag[j].lag) || result.lag[j].r == null || isNaN(result.lag[j].r)) {
          validLag = false; break;
        }
      }
    }
    if (validTrend) { globalData.trend = result.trend; updateTrendChart(result.trend); }
    if (validLag)   { globalData.lag = result.lag; updateLagChart(result.lag); }
    if (predLabel) predLabel.textContent = (validTrend || validLag) ? 'AI 预测值' : '趋势预测暂不可用';
    if (result.predicted_by) {
      var engine = document.getElementById('ai-panel-engine');
      if (engine) engine.textContent = '趋势预测: ' + result.predicted_by;
    }
    trendRetryCount = 0;
  })
  .catch(function() {
    trendRetryCount++;
    if (trendRetryCount < maxTrendRetries) {
      setTimeout(function() { fetchSimulationTrend(true); }, 1000);
    } else {
      if (predLabel) predLabel.textContent = '预测失败，点击重试';
      predLabel.style.cursor = 'pointer';
      predLabel.onclick = function() { trendRetryCount = 0; fetchSimulationTrend(); };
    }
  });
}

// ===== SIMULATION ENGINE =====
var originalData = null;
var baselineData = null;  // Issue 1: immutable baseline snapshot, never overwritten

function applySimulation(data) {
  if (!simulationMode || simulationParams.length === 0) return data;
  // Issue 1: Always start from baselineData, never mutate in-place
  if (!baselineData) baselineData = JSON.parse(JSON.stringify(data));
  var d = JSON.parse(JSON.stringify(baselineData));
  simulationParams.forEach(function(p) {
    // ---- Symmetric dimension branches (new architecture) ----
    if (p.action === 'coupon_volume') {
      var factor = 1 + p.pct / 100;
      if (d.structure) d.structure.forEach(function(s) {
        if (s.name.indexOf('停车') >= 0) { s.count = Math.max(0, Math.round(s.count * factor)); }
      });
      if (d.kpis) {
        d.kpis.total_issued = Math.round(d.kpis.total_issued * factor);
        // Fix: coupon_volume 削减的是低效券（如停车券），砍掉后 ROI 应微升而非下降
        // pct > 0 (增发) → ROI 有正向预期；pct < 0 (削减低效券) → ROI 微升（分母降得比分子多）
        // 系数 0.15 保证削减时 ROI 微升但不夸张，增发时 ROI 有合理提升
        d.kpis.roi = Math.round(d.kpis.roi * (1 - (p.pct / 100) * 0.15));
      }
    }
    if (p.action === 'sales_efficiency') {
      var sf = 1 + p.pct / 100;
      if (d.kpis) {
        d.kpis.roi = Math.round(d.kpis.roi * (1 + (p.pct / 100) * 0.3));
        d.kpis.total_sales = Math.round(d.kpis.total_sales * sf);
        d.kpis.aov = Math.round(d.kpis.aov * sf);
        // Fix: sales_efficiency actions (e.g. 提升核销率, 提升ROI, 提升客单价) must also
        // affect conversion_rate proportionally — otherwise the action's name promise
        // (e.g. "提升核销率 130%") contradicts the simulated KPI display.
        // 0.4x coefficient: applies the directional change to conversion without overshooting
        d.kpis.conversion_rate = Math.round((d.kpis.conversion_rate || 0) * (1 + (p.pct / 100) * 0.4) * 100) / 100;
      }
      if (d.cohorts) d.cohorts.forEach(function(c) {
        c.sales = Math.round(c.sales * sf);
      });
    }
    if (p.action === 'lag_correlation') {
      var lf = p.pct / 100;
      if (d.kpis) {
        d.kpis.conversion_rate = Math.round((d.kpis.conversion_rate || 0) * (1 + lf));
        d.kpis.real_used = Math.round((d.kpis.real_used || 0) * (1 + lf));
        d.kpis.roi = Math.round((d.kpis.roi || 0) * (1 + lf * 0.5));
      }
    }
    // ---- Legacy branches (backward compatible) ----
    if (p.action === 'cut_parking') {
      var pct = p.pct / 100;
      if (d.structure) d.structure.forEach(function(s) { if (s.name.indexOf('停车') >= 0) { s.count = Math.round(s.count * (1 - pct)); } });
      if (d.kpis) { d.kpis.roi = Math.round(d.kpis.roi * (1 + pct * 0.5)); d.kpis.estimated_cost = Math.round(d.kpis.estimated_cost * (1 - pct * 0.6)); }
    }
    if (p.action === 'boost_green') {
      var bp = p.pct / 100;
      if (d.cohorts) d.cohorts.forEach(function(c) { if (c.tag === 'GREEN') { c.issued = Math.round(c.issued * (1 + bp)); c.redeemed = Math.round(c.redeemed * (1 + bp)); c.sales = Math.round(c.sales * (1 + bp * 0.5)); } });
      if (d.kpis) { d.kpis.roi = Math.round(d.kpis.roi * (1 + bp * 0.3)); d.kpis.total_issued = Math.round(d.kpis.total_issued * (1 + bp * 0.1)); }
    }
    if (p.action === 'melt_red') {
      if (d.cohorts) d.cohorts.forEach(function(c) { if (c.tag === 'RED') { c.issued = 0; c.redeemed = 0; c.sales = Math.round(c.sales * 0.3); } });
      if (d.kpis) { d.kpis.roi = Math.round(d.kpis.roi * 1.1); d.kpis.total_issued = Math.round(d.kpis.total_issued * 0.85); }
    }
    if (p.action === 'optimize_lag') {
      var lp = p.pct / 100;
      if (d.kpis) {
        d.kpis.conversion_rate = Math.round((d.kpis.conversion_rate || 0) * (1 + lp));
        d.kpis.real_used = Math.round((d.kpis.real_used || 0) * (1 + lp));
        d.kpis.roi = Math.round((d.kpis.roi || 0) * (1 + lp * 0.5));
      }
    }
  });
  d._simulated = true;
  d._original = baselineData;
  return d;
}
function adoptSuggestion(label, action, pct) {
  if (simulationParams.find(function(p) { return p.label === label; })) return;
  simulationParams.push({ label: label, action: action, pct: pct });
  simulationMode = true;
  simulationTrendFetched = false;  // 模拟参数变化，需要重新获取预测
  // Issue 1: never reset baselineData — it's immutable once set
  renderAll(globalData);
  // Fix 4: Re-bind ask buttons after entering simulation mode (LLM mode)
  setTimeout(function() { bindAskButtons(); }, 500);
}
// Issue 2: Remove single suggestion
function removeSuggestion(label) {
  simulationParams = simulationParams.filter(function(p) { return p.label !== label; });
  if (simulationParams.length === 0) {
    // Auto-exit simulation when last suggestion removed
    resetSimulation();
  } else {
    renderAll(globalData);
  }
}
function resetSimulation() {
  // Issue 1: Restore from baselineData (the immutable true original)
  if (baselineData) {
    globalData = JSON.parse(JSON.stringify(baselineData));
  }
  simulationParams = [];
  simulationMode = false;
  aiPanelForcePage = false;  // Reset page-view force flag
  cohortExpanded = false;
  originalData = null;
  baselineData = null;
  if (globalData._simulated) delete globalData._simulated;
  if (globalData._original) delete globalData._original;
  var banner = document.getElementById('simulation-banner');
  if (banner) banner.remove();
  var box = document.getElementById('sim-analysis-box');
  if (box) box.remove();
  document.querySelectorAll('.kpi-card-ai-note').forEach(function(el) { el.remove(); });
  document.querySelectorAll('.kpi-card.simulated').forEach(function(el) { el.classList.remove('simulated'); });
  document.querySelectorAll('.delta').forEach(function(el) { el.remove(); });
  document.querySelectorAll('.sim-change-badge').forEach(function(el) { el.remove(); });
  document.querySelectorAll('.sim-changed').forEach(function(el) { el.classList.remove('sim-changed'); });
  renderAll(globalData);
}
// Expose for inline onclick handlers
window.adoptSuggestion = adoptSuggestion;
window.resetSimulation = resetSimulation;
window.removeSuggestion = removeSuggestion;

// ===== Symmetric Dimension Architecture — dynamic button renderer =====
// Renders "采纳建议" buttons from structured recommendation dicts {text, action, effect, pct}.
// Falls back to legacy string format (treats as label with defaultEffect/defaultPct).
// If recs is empty, synthesizes a single default button so the action is always available.
// Button style matches original: standalone btn btn-primary btn-sm with "采纳建议" text.
function renderActionableRecs(recs, defaultEffect, defaultPct, defaultLabel) {
  defaultEffect = defaultEffect || 'sales_efficiency';
  defaultPct = (defaultPct != null) ? defaultPct : 10;
  if (!recs || recs.length === 0) {
    // Synthesize a single fallback recommendation so the button is always present
    recs = [{ text: defaultLabel || '采纳此建议', action: defaultLabel || '采纳建议', effect: defaultEffect, pct: defaultPct }];
  }
  var html = '';
  recs.slice(0, 3).forEach(function(r) {
    var label, action, effect, pct;
    if (typeof r === 'object' && r !== null) {
      label = r.action || r.text || '';
      effect = r.effect || defaultEffect;
      pct = (r.pct != null) ? r.pct : defaultPct;
    } else {
      label = String(r);
      effect = defaultEffect;
      pct = defaultPct;
    }
    var escLabel = label.replace(/'/g, "\\'");
    html += '<button class="btn btn-primary btn-sm" style="margin-top:8px;" onclick="adoptSuggestion(\'' + escLabel + '\',\'' + effect + '\',' + pct + ')">采纳建议</button>';
  });
  return html;
}

function updateSimulationBanner() {
  var banner = $('#simulation-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'simulation-banner';
    // Add flex-wrap + overflow:visible to prevent clipping
    banner.style.cssText = 'background:#eff6ff;border:1px solid #3b82f6;border-radius:8px;padding:10px 16px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;font-size:13px;color:#1e40af;overflow:visible;min-height:40px;';
    var content = document.querySelector('.content');
    if (content) content.insertBefore(banner, content.firstChild);
  }
  // Each suggestion gets a visible × button with high-contrast dark border
  var labelsHtml = simulationParams.map(function(p) {
    return '<span style="display:inline-flex;align-items:center;gap:4px;margin-right:6px;white-space:nowrap;">' + p.label +
      '<button onclick="window.removeSuggestion(\'' + p.label.replace(/'/g, "\\'") + '\')" style="background:#fff;border:1.5px solid #1e40af;color:#1e40af;border-radius:50%;width:18px;height:18px;font-size:11px;font-weight:700;cursor:pointer;line-height:1;padding:0;flex-shrink:0;" title="取消此建议">&times;</button></span>';
  }).join('');
  banner.innerHTML = '<span style="display:flex;flex-wrap:wrap;align-items:center;gap:4px;"><strong>模拟模式</strong> · 已采纳 ' + simulationParams.length + ' 条: ' + labelsHtml + '</span><div style="display:flex;gap:8px;flex-shrink:0;"><button class="btn btn-secondary btn-sm" onclick="resetSimulation()">重置</button></div>';
}
function hideSimulationBanner() {
  var banner = $('#simulation-banner');
  if (banner) banner.remove();
}

function updateSimulationNotes(data) {
  document.querySelectorAll('.kpi-card-ai-note').forEach(function(el) { el.remove(); });
  if (!simulationMode || !data._original) return;

  var k = data.kpis || {};
  var ok = data._original.kpis || {};

  function changed(cur, orig) {
    if (!orig) return false;
    return Math.abs((cur - orig) / orig) > 0.005;
  }

  // Summary page 4 cards — meaningful business notes only if changed
  if (changed(k.roi, ok.roi)) {
    var roiPct = ((k.roi - ok.roi)/ok.roi*100).toFixed(1);
    var absChg = (k.roi - ok.roi).toFixed(1);
    addAiNote('#kpi-grid-summary .kpi-card:nth-child(1)',
      'ROI 提升 ' + roiPct + '%（从 ' + ok.roi + '% 升至 ' + k.roi + '%，增加约 ' + absChg + ' 个百分点），削减低效停车券后资源效率显著改善');
  }
  if (changed(k.total_sales, ok.total_sales)) {
    var salesPct = ((k.total_sales - ok.total_sales)/ok.total_sales*100).toFixed(1);
    addAiNote('#kpi-grid-summary .kpi-card:nth-child(2)',
      '销售额变化 ' + salesPct + '%（从 CNY ' + fmt(ok.total_sales) + ' 至 CNY ' + fmt(k.total_sales) + '），客群优化策略有效');
  }
  if (changed(k.conversion_rate, ok.conversion_rate)) {
    var convPct = ((k.conversion_rate - ok.conversion_rate)/(ok.conversion_rate||1)*100).toFixed(1);
    addAiNote('#kpi-grid-summary .kpi-card:nth-child(3)',
      '核销率提升 ' + convPct + '%，发券时机优化后转化效率改善');
  }
  if (changed(k.member_contribution, ok.member_contribution)) {
    addAiNote('#kpi-grid-summary .kpi-card:nth-child(4)',
      '会员贡献占比 ' + k.member_contribution + '%，高价值会员仍为核心消费群体');
  }

  // KPI page — only changed cards with business meaning
  if (changed(k.total_issued, ok.total_issued)) {
    addAiNote('#kpi-grid-page .kpi-card:nth-child(1)',
      '发券量从 ' + ok.total_issued + ' 调整为 ' + k.total_issued + '，精准投放减少无效发券');
  }
  if (changed(k.real_used, ok.real_used)) {
    addAiNote('#kpi-grid-page .kpi-card:nth-child(2)',
      '核销量变化反映券激励强度调整效果');
  }
  if (changed(k.total_orders, ok.total_orders)) {
    addAiNote('#kpi-grid-page .kpi-card:nth-child(3)',
      '交易笔数变化反映券种结构调整对消费频次的影响');
  }
  if (changed(k.aov, ok.aov)) {
    addAiNote('#kpi-grid-page .kpi-card:nth-child(4)',
      '客单价从 CNY ' + fmt(ok.aov) + ' 变为 CNY ' + fmt(k.aov) + '，客群策略调整有效');
  }
  if (changed(k.total_sales, ok.total_sales)) {
    addAiNote('#kpi2-sales', '总销售额变化反映整体策略调整效果');
  }
  if (changed(k.member_contribution, ok.member_contribution)) {
    addAiNote('#kpi2-member', '会员贡献变化反映会员体系优化效果');
  }
  if (changed(k.roi, ok.roi)) {
    var roiPct2 = ((k.roi - ok.roi)/ok.roi*100).toFixed(1);
    addAiNote('#kpi2-roi',
      k.roi > ok.roi ? 'ROI 提升 ' + roiPct2 + '%（从 ' + ok.roi + '% 至 ' + k.roi + '%），削减低效券种后资源使用效率显著改善' : 'ROI 变化');
  }
  if (changed(k.coupon_leverage, ok.coupon_leverage)) {
    addAiNote('#kpi2-leverage', '动销渗透率变化反映营销杠杆效应调整');
  }

  // Update banner — delegate to updateSimulationBanner to keep × buttons consistent
  if (simulationParams.length > 0) updateSimulationBanner();
}

function addAiNote(selector, note) {
  var el = document.querySelector(selector);
  if (!el) return;
  // If the selector matched an inner element (e.g. .kpi-card-value),
  // walk up to the outer .kpi-card container so the note sits at card level
  var card = el.classList.contains('kpi-card') ? el : el.closest('.kpi-card');
  if (!card) return;
  // Clean old AI note before adding new one
  var old = card.querySelector('.kpi-card-ai-note');
  if (old) old.remove();
  var div = document.createElement('div');
  div.className = 'kpi-card-ai-note';
  div.textContent = note;
  // Insert before footer for stable layout, fallback to appendChild
  var footer = card.querySelector('.kpi-card-footer');
  if (footer) {
    card.insertBefore(div, footer);
  } else {
    card.appendChild(div);
  }
}

// R3: Compute change marker (arrow + pct) for any numeric pair
function simChangeMark(cur, orig) {
  if (orig == null || orig === 0) return null;
  var diff = Number(cur) - Number(orig);
  var pct = (diff / Math.abs(Number(orig))) * 100;
  if (Math.abs(pct) < 0.1) return { arrow: '—', color: '#9ca3af', pct: 0, cls: 'flat', text: '持平' };
  if (pct > 0) return { arrow: '↑', color: '#10b981', pct: pct, cls: 'up', text: '+' + Math.abs(pct).toFixed(1) + '%' };
  return { arrow: '↓', color: '#ef4444', pct: pct, cls: 'down', text: Math.abs(pct).toFixed(1) + '%' };
}

// R3: Add simulation change badge to any DOM element
function addSimChangeBadge(el, cur, orig) {
  if (!el || orig == null) return;
  var mark = simChangeMark(cur, orig);
  if (!mark) return;
  var existing = el.querySelector('.sim-change-badge');
  if (existing) existing.remove();
  var badge = document.createElement('span');
  badge.className = 'sim-change-badge';
  badge.style.cssText = 'font-size:11px;font-weight:600;margin-left:6px;white-space:nowrap;color:' + mark.color + ';';
  badge.textContent = mark.arrow + ' ' + mark.text;
  el.appendChild(badge);
  el.classList.add('sim-changed');
}

// ===== autoShrink: shrink font until content fits =====
function autoShrink(el, minPx, startPx) {
  if (!el) return;
  var size = startPx;
  el.style.fontSize = size + 'px';
  while (size > minPx && el.scrollWidth > el.clientWidth + 1) {
    size -= 1;
    el.style.fontSize = size + 'px';
  }
}

// ===== fillKPI: block layout, delta inline after unit =====
function fillKPI(cardId, val, unit, sub, isSimulated, originalVal, tooltip) {
  var card = document.querySelector(cardId);
  if (!card) return;
  if (!card.classList.contains('kpi-card')) card = card.closest('.kpi-card');
  if (!card) return;
  // KPI tooltip — show data source
  if (tooltip) card.title = tooltip;

  var valueEl = card.querySelector('.kpi-card-value');
  var subEl = card.querySelector('.kpi-card-sub');

  if (valueEl) {
    valueEl.classList.remove('loading');
    // Clear inline loading-skeleton styles so value area expands naturally
    valueEl.style.width = '';
    valueEl.style.height = '';
    valueEl.style.borderRadius = '';

    // Build value line with inline styles — never depends on CSS classes
    var html = '<span class="val" style="font-size:24px;font-weight:700;color:#1f2937;flex-shrink:1;min-width:0;">' + fmt(val) + '</span>';

    if (unit && unit.length > 0) {
      html += '<span class="unit" style="font-size:13px;font-weight:500;color:#6b7280;flex-shrink:0;margin-left:2px;">' + unit + '</span>';
    }

    // Simulation change badge: show ▲▼ + percentage when data has changed (same style as cost structure bars)
    if (isSimulated && originalVal != null) {
      var mark = simChangeMark(val, originalVal);
      if (mark) {
        html += '<span class="sim-change-badge" style="font-size:11px;font-weight:600;margin-left:6px;white-space:nowrap;flex-shrink:0;color:' + mark.color + ';">' + mark.arrow + ' ' + mark.text + '</span>';
      }
    }

    valueEl.innerHTML = html;

    // Fix 1: Shrink .val only if entire valueEl overflows, allow down to 12px
    requestAnimationFrame(function() {
      var valEl = valueEl.querySelector('.val');
      if (!valEl) return;
      var size = 24;
      valEl.style.fontSize = size + 'px';
      while (size > 12 && valueEl.scrollWidth > valueEl.clientWidth + 1) {
        size -= 1;
        valEl.style.fontSize = size + 'px';
      }
    });
  }

  if (subEl) {
    subEl.classList.remove('loading');
    // Clear inline loading-skeleton styles so subtitle uses full card width
    subEl.style.width = '';
    subEl.style.height = '';
    subEl.style.borderRadius = '';
    subEl.textContent = sub || '';
    requestAnimationFrame(function() { autoShrink(subEl, 9, 11); });
  }

  // Fix 2: NEVER change card border/background color in simulation mode.
  // Simulation only affects value numbers and delta arrows (handled in updateSummary/updateSimulationNotes).
  // The .simulated class is kept for potential future use but has no visual effect now.
  if (card) {
    if (isSimulated) card.classList.add('simulated');
    else card.classList.remove('simulated');
  }
}

// ---- Date Range ----
function updateDateRange(s) {
  if (s && s.date_range) {
    var c = s.date_range.coupon;
    var el = $('#date-range-text');
    if (el) el.textContent = c.min + ' — ' + c.max;
  }
}

// ---- Summary KPI Cards (FIX 1: use fillKPI properly) ----
function updateSummary(data) {
  var k = data.kpis;
  if (!k || !k.total_issued) return;
  var sim = !!data._simulated;
  var orig = (data._original && data._original.kpis) ? data._original.kpis : null;

  // Summary page 4 KPI cards with tooltips
  fillKPI('#kpi-grid-summary .kpi-card:nth-child(1)', k.roi || 0, '%', '发券 ' + (k.total_issued || 0) + ' 张', sim, orig ? orig.roi : null, '估算值：按券种单张成本 × 发券量推算');
  fillKPI('#kpi-grid-summary .kpi-card:nth-child(2)', k.total_sales || 0, '', '交易 ' + (k.total_orders || 0).toLocaleString() + ' 笔', sim, orig ? orig.total_sales : null, '真实统计：销售表聚合');
  fillKPI('#kpi-grid-summary .kpi-card:nth-child(3)', k.conversion_rate || 0, '%', '真实核销 ' + (k.real_used || 0) + ' 张', sim, orig ? orig.conversion_rate : null, '真实统计：核销数 / 发券总数');
  fillKPI('#kpi-grid-summary .kpi-card:nth-child(4)', k.member_contribution || 0, '%', '会员消费 ' + fmt(k.member_sales || 0), sim, orig ? orig.member_contribution : null, '真实统计：会员销售额 / 总销售额');

  // KPI page row 1
  fillKPI('#kpi-grid-page .kpi-card:nth-child(1)', k.total_issued || 0, '张', '核销率 ' + fmtPct(k.redeem_rate || 0), sim, orig ? orig.total_issued : null, '真实统计：发券表聚合');
  fillKPI('#kpi-grid-page .kpi-card:nth-child(2)', k.real_used || 0, '张', '真实使用', sim, orig ? orig.real_used : null, '真实统计：发券表 status_code 聚合');
  fillKPI('#kpi-grid-page .kpi-card:nth-child(3)', k.total_orders || 0, '笔', '日均 ' + Math.round((k.total_orders || 0) / 180) + ' 笔', sim, orig ? orig.total_orders : null, '真实统计：销售表去重计数');
  fillKPI('#kpi-grid-page .kpi-card:nth-child(4)', k.aov || 0, '元', 'CNY ' + Number(k.aov || 0).toFixed(0), sim, orig ? orig.aov : null, '真实统计：销售额 / 交易笔数');
  // KPI page row 2
  fillKPI('#kpi2-sales', k.total_sales || 0, '', 'CNY ' + Number(k.total_sales || 0).toFixed(0), sim, orig ? orig.total_sales : null, '真实统计：销售表聚合');
  fillKPI('#kpi2-member', k.member_contribution || 0, '%', '会员销售 ' + fmt(k.member_sales || 0), sim, orig ? orig.member_contribution : null, '真实统计：会员销售额 / 总销售额');
  fillKPI('#kpi2-roi', k.roi || 0, '%', (k.roi || 0) < 10 ? '低于 10% 安全线' : '正常', sim, orig ? orig.roi : null, '估算值：按券种单张成本 × 发券量推算');
  fillKPI('#kpi2-leverage', k.coupon_leverage || 0, '%', (k.coupon_leverage || 0) < 0.5 ? '杠杆效应不足' : '正常', sim, orig ? orig.coupon_leverage : null, '真实统计：领券后消费人数 / 总领券人数');

  var rs = $('#record-summary'); if (rs) rs.textContent = (k.total_issued || 0).toLocaleString() + ' 条发券记录 · ' + (k.total_orders || 0).toLocaleString() + ' 条销售记录';
  // Alert cards now handled by updateAlertCards() below
}

// ===== Alert Cards (standalone, called from renderAll) =====
function updateAlertCards() {
  if (!globalData || !globalData.structure || !globalData.kpis) return;

  // Parking ratio: use pct from structure data (same as AI calculation)
  var parkingEntry = globalData.structure.find(function(s) { return s.name.indexOf('停车') >= 0; });
  var parkingRatio = parkingEntry ? (parkingEntry.pct || 0) : 0;

  // Parking thresholds: >75% severe, 50-75% warning, <50% healthy (lowered from >85% to actually trigger healthy)
  var structLevel, structLabel, structColor, structTitleColor;
  if (parkingRatio > 75)        { structLevel = 'severe'; structLabel = '结构性告警'; structColor = '#ef4444'; structTitleColor = '#b91c1c'; }
  else if (parkingRatio >= 50)  { structLevel = 'warning'; structLabel = '结构预警'; structColor = '#f59e0b'; structTitleColor = '#b45309'; }
  else                          { structLevel = 'healthy'; structLabel = '结构健康'; structColor = '#10b981'; structTitleColor = '#047857'; }

  var structDesc = '停车券占发券总量 ' + parkingRatio.toFixed(1) + '%' +
    (structLevel === 'severe' ? '，结构单一风险突出' : structLevel === 'warning' ? '，存在一定集中风险' : '，结构相对均衡') + '。';

  var bgColors = { severe: '#fef2f2', warning: '#fffbeb', healthy: '#f0fdf4' };
  var borderColors = { severe: '#fecaca', warning: '#fde68a', healthy: '#bbf7d0' };

  // Render both summary page and structure page alert cards (same data, same logic)
  ['alert-structure', 'alert-structure-struct'].forEach(function(sid) {
    var structCard = document.getElementById(sid);
    if (structCard) {
      var structBr = structLevel === 'severe' ? '999px' : '4px';
      structCard.style.cssText = 'display:flex;align-items:flex-start;gap:8px;background:' + bgColors[structLevel] + ';border:1px solid ' + borderColors[structLevel] + ';padding:8px 12px;box-shadow:none;';
      // Use setProperty with !important to defeat any cached CSS rules
      structCard.style.setProperty('border-radius', structBr, 'important');
      var st = structCard.querySelector('.alert-title');
      var sd = structCard.querySelector('.alert-desc');
      var iconSpan = structCard.querySelector('.alert-icon');
      if (st) { st.textContent = structLabel + ' · 停车券资源错配'; st.style.color = structTitleColor; }
      if (sd) sd.textContent = structDesc;
      if (iconSpan) {
        if (structLevel === 'healthy') {
          // Green outline circle with checkmark for healthy state
          iconSpan.outerHTML = '<svg class="alert-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;margin-top:1px;">' +
            '<circle cx="12" cy="12" r="10" fill="none" stroke="#10b981" stroke-width="1.5"/>' +
            '<path d="M7 12.5l3.5 3.5 6.5-7" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>' +
            '</svg>';
        } else if (structLevel === 'severe') {
          // Red outline circle with "!" for severe state
          iconSpan.outerHTML = '<svg class="alert-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;margin-top:1px;">' +
            '<circle cx="12" cy="12" r="10" fill="none" stroke="' + structColor + '" stroke-width="1.5"/>' +
            '<rect x="11" y="6" width="2" height="9" rx="1" fill="' + structColor + '"/>' +
            '<circle cx="12" cy="17.5" r="1.2" fill="' + structColor + '"/>' +
            '</svg>';
        } else {
          // Amber rounded triangle with "!" for warning state
          iconSpan.outerHTML = '<svg class="alert-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;margin-top:1px;">' +
            '<path d="M12 2.5 Q12.8 2.5 13.3 3.3 L21.8 18.8 Q22.3 19.8 21.3 20.7 Q20.8 21.2 20 21.2 L4 21.2 Q3.2 21.2 2.7 20.7 Q1.7 19.8 2.2 18.8 L10.7 3.3 Q11.2 2.5 12 2.5 Z" ' +
            'stroke="' + structColor + '" stroke-width="1.5" fill="none" stroke-linejoin="round" stroke-linecap="round"/>' +
            '<rect x="11" y="9" width="2" height="6" rx="1" fill="' + structColor + '"/>' +
            '<circle cx="12" cy="17.5" r="1.2" fill="' + structColor + '"/>' +
            '</svg>';
        }
      }
    }
  });

  // ROI alert card — same on both pages
  var roiVal = globalData.kpis.roi || 0;
  var roiLevel, roiLabel, roiColor, roiTitleColor;
  if (roiVal < 100)        { roiLevel = 'severe'; roiLabel = 'ROI 告警'; roiColor = '#ef4444'; roiTitleColor = '#b91c1c'; }
  else if (roiVal <= 300)  { roiLevel = 'warning'; roiLabel = 'ROI 预警'; roiColor = '#f59e0b'; roiTitleColor = '#b45309'; }
  else                     { roiLevel = 'healthy'; roiLabel = 'ROI 健康'; roiColor = '#10b981'; roiTitleColor = '#047857'; }
  var roiDesc = '综合 ROI ' + roiVal.toFixed(0) + '%，投入产出效率' +
    (roiLevel === 'severe' ? '偏低' : roiLevel === 'warning' ? '中等' : '良好') + '。';

  ['alert-roi', 'alert-roi-struct'].forEach(function(rid) {
    var roiCard = document.getElementById(rid);
    if (roiCard) {
      roiCard.style.display = 'flex';
      var roiBr = roiLevel === 'severe' ? '999px' : '4px';
      roiCard.style.cssText = 'display:flex;align-items:flex-start;gap:8px;background:' + bgColors[roiLevel] + ';border:1px solid ' + borderColors[roiLevel] + ';padding:8px 12px;box-shadow:none;';
      // Use setProperty with !important to defeat any cached CSS rules
      roiCard.style.setProperty('border-radius', roiBr, 'important');
      var rt = roiCard.querySelector('.alert-title');
      var rd = roiCard.querySelector('.alert-desc');
      if (rt) { rt.textContent = roiLabel + ' · 营销投资回报率'; rt.style.color = roiTitleColor; }
      if (rd) rd.textContent = roiDesc;
      // Fix 9: Update ROI alert icon based on level
      var roiIcon = roiCard.querySelector('.alert-icon');
      if (roiIcon) {
        if (roiLevel === 'healthy') {
          // Green outline circle with checkmark for healthy
          roiIcon.outerHTML = '<svg class="alert-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;margin-top:1px;">' +
            '<circle cx="12" cy="12" r="10" fill="none" stroke="#10b981" stroke-width="1.5"/>' +
            '<path d="M7 12.5l3.5 3.5 6.5-7" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>' +
            '</svg>';
        } else if (roiLevel === 'severe') {
          // Red outline circle with "!" for severe
          roiIcon.outerHTML = '<svg class="alert-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;margin-top:1px;">' +
            '<circle cx="12" cy="12" r="10" fill="none" stroke="' + roiColor + '" stroke-width="1.5"/>' +
            '<rect x="11" y="6" width="2" height="9" rx="1" fill="' + roiColor + '"/>' +
            '<circle cx="12" cy="17.5" r="1.2" fill="' + roiColor + '"/>' +
            '</svg>';
        } else {
          // Amber rounded triangle with "!" for warning
          roiIcon.outerHTML = '<svg class="alert-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;margin-top:1px;">' +
            '<path d="M12 2.5 Q12.8 2.5 13.3 3.3 L21.8 18.8 Q22.3 19.8 21.3 20.7 Q20.8 21.2 20 21.2 L4 21.2 Q3.2 21.2 2.7 20.7 Q1.7 19.8 2.2 18.8 L10.7 3.3 Q11.2 2.5 12 2.5 Z" ' +
            'stroke="' + roiColor + '" stroke-width="1.5" fill="none" stroke-linejoin="round" stroke-linecap="round"/>' +
            '<rect x="11" y="9" width="2" height="6" rx="1" fill="' + roiColor + '"/>' +
            '<circle cx="12" cy="17.5" r="1.2" fill="' + roiColor + '"/>' +
            '</svg>';
        }
      }
    }
  });
}

// ---- Trend Chart (FIX 2: closest for tab clicks) ----
var trendChartInstance;
function updateTrendChart(trend) {
  var el = $('#trendChart');
  if (!el) return;
  var ctx = el.getContext('2d');
  if (trendChartInstance) trendChartInstance.destroy();
  if (!trend || !trend.labels || trend.labels.length === 0) {
    var rl = $('#trend-r-label'); if (rl) rl.textContent = '暂无数据';
    return;
  }

  // R3: In simulation mode, overlay original trend data as dashed lines
  var datasets = [
    { label: '销售额 (CNY)', data: trend.sales, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', fill: true, tension: 0.4, yAxisID: 'y', borderWidth: 2.5, pointRadius: 2 },
    { label: '发券量 (张)', data: trend.coupon, borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.1)', fill: true, tension: 0.4, yAxisID: 'y1', borderWidth: 2.5, pointRadius: 2 },
  ];
  if (simulationMode && globalData._original && globalData._original.trend && globalData._original.trend.labels) {
    var origTrend = globalData._original.trend;
    datasets.push({ label: '原始销售额（模拟前）', data: origTrend.sales, borderColor: '#93c5fd', backgroundColor: 'transparent', fill: false, tension: 0.4, yAxisID: 'y', borderWidth: 1.5, borderDash: [6, 3], pointRadius: 1 });
    datasets.push({ label: '原始发券量（模拟前）', data: origTrend.coupon, borderColor: '#6ee7b7', backgroundColor: 'transparent', fill: false, tension: 0.4, yAxisID: 'y1', borderWidth: 1.5, borderDash: [6, 3], pointRadius: 1 });
  }

  trendChartInstance = new Chart(ctx, {
    type: 'line', data: { labels: trend.labels, datasets: datasets },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      plugins: { legend: { position: 'top', labels: { usePointStyle: true, padding: 20, font: { size: 11 } } } },
      scales: {
        y: { type: 'linear', position: 'left', title: { display: true, text: '销售额 (CNY)', font: { size: 11 } }, grid: { color: '#f3f4f6' }, ticks: { callback: function(v) { return fmt(v); } } },
        y1: { type: 'linear', position: 'right', title: { display: true, text: '发券量 (张)', font: { size: 11 } }, grid: { drawOnChartArea: false }, ticks: { callback: function(v) { return Math.round(v); } } },
      }
    }
  });
  var rl2 = $('#trend-r-label');
  if (rl2) {
    var predTag = simulationMode ? ' <span id="trend-prediction-label" style="font-size:11px;color:#1e40af;font-weight:500;background:#dbeafe;padding:1px 6px;border-radius:3px;margin-left:4px;">AI 预测值</span>' : '';
    rl2.innerHTML = '双轴时间序列 · 皮尔逊相关系数 r = ' + trend.correlation + '（' + (trend.correlation >= 0.5 ? '中等相关' : '弱相关') + '）<span style="font-size:10px;color:#9ca3af;margin-left:4px;">真实计算</span>' + predTag;
  }
}

// ---- Donut Charts ----
var donutChart, structDonutChart;
function renderDonut(canvasId, data) {
  var el = $(canvasId); if (!el) return null;
  var ctx = el.getContext('2d');
  return new Chart(ctx, { type: 'doughnut', data: { labels: data.map(function(d) { return d.name; }), datasets: [{ data: data.map(function(d) { return d.count; }), backgroundColor: data.map(function(d) { return d.color; }), borderWidth: 2, borderColor: '#fff' }] }, options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: { display: false }, tooltip: { callbacks: { label: function(ctx) { return ctx.label + ': ' + ctx.raw + ' 张 (' + ctx.parsed + '%)'; } } } } } });
}
function updateDonutLegends(legendId, data) {
  var el = $(legendId); if (!el) return;
  el.innerHTML = data.map(function(d) { return '<div style="display:flex;align-items:center;gap:8px;font-size:13px;"><span style="width:10px;height:10px;border-radius:3px;background:' + d.color + ';flex-shrink:0;"></span><span style="color:var(--gray-700);flex:1;">' + d.name + '</span><span style="font-weight:600;color:var(--gray-900);">' + d.pct + '%</span><span style="font-size:11px;color:var(--gray-400);width:50px;text-align:right;">' + d.count + ' 张</span><span class="sim-legend-badge" style="font-size:10px;font-weight:600;margin-left:2px;"></span></div>'; }).join('');
}
function updateDonutCharts(structure) {
  if (!structure || structure.length === 0) return;
  if (donutChart) donutChart.destroy();
  if (structDonutChart) structDonutChart.destroy();
  donutChart = renderDonut('#donutChart', structure);
  structDonutChart = renderDonut('#structDonutChart', structure);
  updateDonutLegends('#donut-legend', structure);
  updateDonutLegends('#struct-donut-legend', structure);

  // Alert cards now rendered by unified updateAlertCards() — consistent across all pages

  // R3: Add simulation change badges to donut legends
  if (simulationMode && globalData._original && globalData._original.structure) {
    var origStruct = globalData._original.structure || [];
    structure.forEach(function(cur, i) {
      var orig = origStruct.find(function(o) { return o.name === cur.name; });
      if (orig && orig.count !== cur.count) {
        // Update both legend sets
        ['#donut-legend', '#struct-donut-legend'].forEach(function(lid) {
          var legendEl = document.querySelector(lid);
          if (legendEl) {
            var rows = legendEl.querySelectorAll('div');
            if (rows[i]) {
              var badge = rows[i].querySelector('.sim-legend-badge');
              if (badge) {
                var mark = simChangeMark(cur.count, orig.count);
                if (mark) { badge.textContent = mark.arrow + ' ' + mark.text; badge.style.color = mark.color; }
              }
            }
          }
        });
      }
    });
  }
}

// ---- Cohort Matrix ----
function updateCohortMatrix(cohorts) {
  if (!cohorts || cohorts.length === 0) return;
  var tags = { GREEN: [], GOLD: [], RED: [], GRAY: [] };
  cohorts.forEach(function(c) { if (tags[c.tag]) tags[c.tag].push(c); });
  // Use issued_users as primary count (people who received coupons); fallback to consumers
  var total = cohorts.reduce(function(s, c) { return s + (c.issued_users || c.consumers || 0); }, 0);

  // R3: Compute original cohort counts for simulation comparison
  var origTags = null;
  if (simulationMode && globalData._original && globalData._original.cohorts) {
    origTags = { GREEN: [], GOLD: [], RED: [], GRAY: [] };
    globalData._original.cohorts.forEach(function(c) { if (origTags[c.tag]) origTags[c.tag].push(c); });
  }

  ['green','gold','red','gray'].forEach(function(tag) {
    var items = tags[tag.toUpperCase()];
    var count = items.reduce(function(s, c) { return s + (c.issued_users || c.consumers || 0); }, 0);
    var pct = total > 0 ? (count / total * 100).toFixed(1) : 0;
    var el = $('#matrix-' + tag);
    if (el) {
      el.querySelector('.matrix-cell-count').textContent = count.toLocaleString();
      var top = items[0];
      var extra = '';
      if (tag === 'red' && top && top.issued_users && !top.consumers) extra = ' · 领券未消费';
      el.querySelector('.matrix-cell-desc').innerHTML = '占 ' + pct + '% · ' + items.length + ' 个客群组' + (top ? '<br>' + top.name + ' · 客单价 ¥' + top.atv + extra : '');
      // R3: Add change marker for quadrant count
      if (origTags) {
        var origItems = origTags[tag.toUpperCase()];
        var origCount = origItems.reduce(function(s, c) { return s + (c.issued_users || c.consumers || 0); }, 0);
        addSimChangeBadge(el.querySelector('.matrix-cell-count'), count, origCount);
      }
    }
  });
}
function updateCohortMatrixPage(cohorts) {
  if (!cohorts || cohorts.length === 0) return;
  var tags = { GREEN: [], GOLD: [], RED: [], GRAY: [] };
  cohorts.forEach(function(c) { if (tags[c.tag]) tags[c.tag].push(c); });

  var tagColors = { GREEN: '#10b981', GOLD: '#c9a961', RED: '#ef4444', GRAY: '#9ca3af' };

  ['green','gold','red','gray'].forEach(function(tag) {
    var items = tags[tag.toUpperCase()];
    var count = items.reduce(function(s, c) { return s + (c.issued_users || c.consumers || 0); }, 0);
    var el = $('#cp-matrix-' + tag);
    if (el) {
      el.querySelector('.matrix-cell-count').textContent = count.toLocaleString();
      el.querySelector('.matrix-cell-desc').innerHTML = items.length + ' 个客群组' + (items[0] ? '<br>Top: ' + items[0].name : '');

      // Quadrant expand list
      var expandList = el.querySelector('.matrix-expand-list');
      if (expandList) {
        expandList.innerHTML = items.map(function(c) {
          return '<div style="display:flex;align-items:center;gap:4px;padding:2px 0;border-bottom:1px solid rgba(0,0,0,0.05);">' +
            '<span style="width:6px;height:6px;border-radius:50%;background:' + (tagColors[c.tag] || '#9ca3af') + ';flex-shrink:0;"></span>' +
            '<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + c.level + '/' + c.age_group + '</span>' +
            '<span style="font-size:10px;color:#9ca3af;">¥' + (c.atv || 0) + '</span>' +
            '<span style="font-size:10px;color:#6b7280;">' + (c.issued_users || c.consumers || 0) + '人</span>' +
            '</div>';
        }).join('');
      }
      // Toggle handler
      var toggleBtn = el.querySelector('.matrix-expand-toggle');
      if (toggleBtn) {
        toggleBtn.onclick = function(e) {
          e.stopPropagation();
          var list = el.querySelector('.matrix-expand-list');
          if (list.style.display === 'none' || !list.style.display) {
            list.style.display = 'block';
            toggleBtn.innerHTML = '收起 &#x25B2;';
          } else {
            list.style.display = 'none';
            toggleBtn.innerHTML = '查看全部组 &#x25BC;';
          }
        };
      }
    }
  });
  // Side list next to matrix
  renderCohortSideList(cohorts);
}

// Prompt 2b: Side list panel — right side of cohort matrix
var cohortSideExpanded = false;
function renderCohortSideList(cohorts) {
  var panelBody = document.querySelector('#page-cohort .panel:first-of-type .panel-body');
  if (!panelBody) return;
  // Convert panel-body to flex layout: matrix (60%) + side list (40%)
  panelBody.style.cssText = 'display:flex;gap:16px;align-items:flex-start;';

  // Ensure matrix wrapper
  var matrix = panelBody.querySelector('#cohort-page-matrix');
  if (!matrix) return;
  matrix.style.flex = '60%';

  // Create or get side list container
  var sideList = document.getElementById('cohort-side-list');
  if (!sideList) {
    sideList = document.createElement('div');
    sideList.id = 'cohort-side-list';
    sideList.style.cssText = 'flex:40%;min-width:0;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;';
    panelBody.appendChild(sideList);
  }

  var limit = cohortSideExpanded ? 0 : 5;
  var shown = limit ? cohorts.slice(0, limit) : cohorts;
  var tagColors = { GREEN: '#10b981', GOLD: '#c9a961', RED: '#ef4444', GRAY: '#9ca3af' };
  sideList.innerHTML =
    '<div style="padding:10px 14px;border-bottom:1px solid #e5e7eb;font-weight:600;font-size:13px;color:#374151;background:#f9fafb;">客群分组清单</div>' +
    '<div style="max-height:320px;overflow-y:auto;">' +
      shown.map(function(c) {
        var dotColor = tagColors[c.tag] || '#9ca3af';
        return '<div class="cohort-side-row" style="display:flex;align-items:center;gap:6px;padding:8px 14px;border-bottom:1px solid #f3f4f6;font-size:12px;cursor:pointer;transition:background 0.15s;" data-tag="' + c.tag + '" onmouseenter="this.style.background=\'#f0fdf4\'" onmouseleave="this.style.background=\'\'">' +
          '<span style="width:8px;height:8px;border-radius:50%;background:' + dotColor + ';flex-shrink:0;"></span>' +
          '<span style="flex:1;color:#374151;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + c.level + ' / ' + c.age_group + '</span>' +
          '<span style="color:#9ca3af;font-size:11px;">¥' + (c.atv || 0) + '</span>' +
          '<span style="color:#6b7280;font-variant-numeric:tabular-nums;width:50px;text-align:right;flex-shrink:0;">' + (c.issued_users || c.consumers || 0).toLocaleString() + ' 人</span>' +
        '</div>';
      }).join('') +
    '</div>' +
    '<div style="padding:8px 14px;border-top:1px solid #e5e7eb;text-align:right;">' +
      '<button id="cohort-side-expand-btn" class="btn btn-secondary btn-sm" style="font-size:11px;">展开全部（共 ' + cohorts.length + ' 组）</button>' +
    '</div>';

  // Click handler for side list rows — highlight corresponding matrix quadrant
  sideList.querySelectorAll('.cohort-side-row').forEach(function(row) {
    row.addEventListener('click', function() {
      var tag = this.getAttribute('data-tag').toLowerCase();
      var cell = document.getElementById('cp-matrix-' + tag);
      if (cell) {
        cell.style.transform = 'scale(1.05)';
        cell.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        setTimeout(function() { cell.style.transform = ''; cell.style.boxShadow = ''; }, 500);
      }
    });
  });

  // Expand button for side list
  var sideExpandBtn = document.getElementById('cohort-side-expand-btn');
  if (sideExpandBtn) {
    sideExpandBtn.textContent = cohortSideExpanded ? '收起' : '展开全部（共 ' + cohorts.length + ' 组）';
    sideExpandBtn.onclick = function() { cohortSideExpanded = !cohortSideExpanded; renderCohortSideList(cohorts); };
  }
}
// ---- Category Bars ----
function renderCategoryBars(containerId, data) {
  var el = $(containerId);
  if (!el || !data || data.length === 0) { if (el) el.innerHTML = '暂无数据'; return; }
  var maxVal = data[0] ? (data[0].sales || 1) : 1;

  // R3: Original category data for simulation comparison
  var origCat = null;
  if (simulationMode && globalData._original && globalData._original.category) {
    origCat = globalData._original.category;
  }

  el.innerHTML = data.map(function(d, i) {
    var changeHtml = '';
    if (origCat) {
      var orig = origCat.find(function(o) { return o.name === d.name; });
      if (orig && orig.sales !== d.sales) {
        var mark = simChangeMark(d.sales, orig.sales);
        if (mark) changeHtml = '<span class="sim-change-badge" style="font-size:11px;font-weight:600;margin-left:6px;color:' + mark.color + ';">' + mark.arrow + ' ' + mark.text + '</span>';
      }
    }
    return '<div class="progress-row"><div class="progress-label" style="display:flex;align-items:center;gap:6px;"><span class="badge-dot" style="background:' + d.color + ';"></span>' + d.name + '</div><div class="progress-track"><div class="progress-fill" style="width:' + (d.sales / maxVal * 95).toFixed(0) + '%;background:linear-gradient(90deg,' + d.color + ',' + d.color + '88);"></div></div><div class="progress-value">' + fmt(d.sales) + changeHtml + '</div></div>';
  }).join('');
}
function updateCategoryBars(cat, structure) {
  renderCategoryBars('#category-bars', cat);
  renderCategoryBars('#struct-category-bars', cat);
  if (!cat || cat.length === 0) return;
}

// ---- Lag Analysis ----
var lagChart, lagCorrChart;
function updateLagChart(lagData) {
  if (!lagData || lagData.length === 0) return;
  var sorted = [].concat(lagData).sort(function(a, b) { return a.lag - b.lag; });
  var best = sorted.reduce(function(a, b) { return (b.r > a.r ? b : a); }, sorted[0]);
  if (best) {
    var blt = $('#best-lag-title'); if (blt) blt.textContent = '发现最佳滞后窗口 · ' + best.lag + ' 天';
    var bld = $('#best-lag-desc'); if (bld) bld.textContent = '滞后 ' + best.lag + ' 天时皮尔逊相关系数达峰值 r = ' + best.r + '（' + (best.r >= 0.5 ? '强' : best.r >= 0.2 ? '中等' : '弱') + '相关）。建议据此调整发券时点策略。';
  }
  // Fix 12: Dynamic y-axis — collect all r values including original data for proper range
  var allR = sorted.map(function(d) { return d.r; });
  var allRValues = [].concat(allR);

  // R3: Original lag data for simulation comparison
  // Always show the original dashed line in sim mode (so user can see whether simulation changed this metric).
  // Use distinct colors to differentiate: green = current/simulated, gray dashed = original (pre-sim).
  var origLagMap = null;
  var lagChanged = false;
  if (simulationMode && globalData._original && globalData._original.lag) {
    origLagMap = {};
    globalData._original.lag.forEach(function(d) {
      origLagMap[d.lag] = d;
      if (d.r != null) allRValues.push(d.r);
    });
    // Detect if any lag value actually differs from original
    lagChanged = sorted.some(function(d) {
      var orig = origLagMap[d.lag];
      return orig && Math.abs((orig.r || 0) - (d.r || 0)) > 0.005;
    });
  }

  var rMin = Math.min.apply(null, allRValues);
  var rMax = Math.max.apply(null, allRValues);
  // Include 0 axis + 0.05 buffer on both sides
  var yMin = Math.min(0, rMin - 0.05);
  var yMax = Math.max(0, rMax + 0.05);
  // Ensure at least 0.3 range so chart isn't too flat
  if (yMax - yMin < 0.3) {
    var center = (yMax + yMin) / 2;
    yMin = center - 0.15;
    yMax = center + 0.15;
  }

  var lctx = $('#lagCorrChart');
  if (lctx) {
    var ctx = lctx.getContext('2d');
    if (lagCorrChart) lagCorrChart.destroy();
    // R3: If in simulation mode, overlay original data as dashed line
    // R2: All-green points — no yellow, best lag gets larger green dot
    var datasets = [{ label: '皮尔逊 r', data: allR, borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.1)', fill: true, tension: 0.4, borderWidth: 3, pointRadius: sorted.map(function(d) { return d.lag === best.lag ? 6 : 3; }), pointBackgroundColor: '#10b981' }];
    if (origLagMap) {
      var origR = sorted.map(function(d) { return origLagMap[d.lag] ? origLagMap[d.lag].r : null; });
      datasets.push({ label: '原始 r（模拟前）', data: origR, borderColor: '#9ca3af', backgroundColor: 'transparent', fill: false, tension: 0.4, borderWidth: 2, borderDash: [5, 5], pointRadius: 2, pointBackgroundColor: '#9ca3af', spanGaps: true });
    }
    lagCorrChart = new Chart(ctx, { type: 'line', data: { labels: sorted.map(function(d) { return d.lag + '天'; }), datasets: datasets }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: true, labels: { usePointStyle: true, padding: 16, font: { size: 11 } } } }, scales: { y: { min: yMin, max: yMax, grace: '5%', grid: { color: '#f3f4f6' }, ticks: { callback: function(v) { return v.toFixed(2); } } } } } });
  }

  // Show simulation status hint below the lag chart
  var lagPanel = lctx ? lctx.closest('.panel') : null;
  if (lagPanel) {
    var existingHint = lagPanel.querySelector('.sim-lag-unchanged-hint');
    if (existingHint) existingHint.remove();
    if (simulationMode) {
      var hint = document.createElement('div');
      hint.className = 'sim-lag-unchanged-hint';
      hint.style.cssText = 'margin-top:8px;padding:6px 10px;border-radius:4px;font-size:11px;line-height:1.5;';
      if (lagChanged) {
        hint.style.background = '#ecfdf5';
        hint.style.border = '1px solid #6ee7b7';
        hint.style.color = '#065f46';
        hint.innerHTML = '<span style="font-weight:600;">模拟已生效：</span>灰色虚线为原始 r 值，绿色实线为模拟后 r 值。本次采纳的建议中有「优化滞后窗口」类操作，滞后相关性已发生变化。';
      } else {
        hint.style.background = '#f3f4f6';
        hint.style.border = '1px dashed #9ca3af';
        hint.style.color = '#6b7280';
        hint.innerHTML = '<span style="font-weight:600;">注：</span>灰色虚线 = 原始 r 值（两线重合说明当前采纳的建议不影响滞后相关性）。如需改变滞后窗口，请采纳「优化滞后窗口」类建议。';
      }
      lagPanel.querySelector('.panel-body').appendChild(hint);
    }
  }
  var sctx = $('#lagChart');
  if (sctx) {
    var ctx2 = sctx.getContext('2d');
    if (lagChart) lagChart.destroy();
    // Issue 8: Best lag bar highlighted in light green, others default gray
    lagChart = new Chart(ctx2, { type: 'bar', data: { labels: sorted.map(function(d) { return d.lag + '天'; }), datasets: [{ data: allR, backgroundColor: sorted.map(function(d) { return d.lag === best.lag ? '#6ee7b7' : '#d1d5db'; }), borderRadius: 4, base: 0 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: function(ctx) { return 'r = ' + ctx.raw.toFixed(2) + (ctx.dataIndex === sorted.findIndex(function(d) { return d.lag === best.lag; }) ? ' (最佳窗口)' : ''); } } } }, scales: { y: { min: yMin, max: yMax, grace: '5%', grid: { color: '#f3f4f6' }, ticks: { callback: function(v) { return v.toFixed(1); } } } } } });
  }
  var li = $('#lag-insight');
  if (li) li.innerHTML = '<svg style="vertical-align:middle;margin-right:4px;" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg><strong>发现: 滞后 ' + best.lag + ' 天时相关系数达峰值 ' + best.r + '。</strong><br>建议提前 ' + best.lag + ' 天发券以最大化转化效果。';
  var tbody = $('#lag-table-body');
  if (tbody) {
    var tips = { strong: '最佳窗口 · 建议锁定此节奏', moderate: '有一定关联 · 可作为备选窗口', weak: '关联较弱 · 非优先窗口', none: '几乎无关联 · 不考虑' };
    var sl = { strong: '强相关', moderate: '中等相关', weak: '弱相关', none: '无相关' };
    var bc = { strong: 'badge-green', moderate: 'badge-gold', weak: 'badge-gray', none: 'badge-gray' };
    // Update table header for simulation mode
    var lagTable = tbody.closest('table');
    if (lagTable) {
      lagTable.style.tableLayout = 'fixed';
      lagTable.style.width = '100%';
      var thead = lagTable.querySelector('thead tr');
      if (thead) {
        // Reset header to default
        thead.innerHTML = '<th style="width:20%;text-align:left;">滞后天数</th><th style="width:20%;text-align:right;">皮尔逊 r</th>';
        if (origLagMap) {
          thead.innerHTML += '<th style="width:20%;text-align:right;" class="lag-orig-col">原始 r</th>';
        }
        thead.innerHTML += '<th style="width:20%;text-align:center;">强度</th><th style="width:40%;">说明</th>';
      }
    }
    tbody.innerHTML = sorted.map(function(d) {
      var origCell = '';
      if (origLagMap && origLagMap[d.lag]) {
        origCell = '<td class="num" style="text-align:right;color:#9ca3af;font-size:12px;">' + origLagMap[d.lag].r.toFixed(2) + '</td>';
      } else if (origLagMap) {
        origCell = '<td style="text-align:right;color:#9ca3af;">—</td>';
      }
      return '<tr' + (d.lag === best.lag ? ' style="background:var(--pv-green-50);"' : '') + '>' +
        '<td style="text-align:left;">' + (d.lag === best.lag ? '<strong>' + d.lag + ' 天</strong>' : d.lag + ' 天') + '</td>' +
        '<td class="num" style="text-align:right;' + (d.r >= 0.7 ? 'color:#10b981;font-weight:700;' : '') + '">' + d.r.toFixed(2) + '</td>' +
        origCell +
        '<td style="text-align:center;"><span class="badge ' + (bc[d.strength] || 'badge-gray') + '">' + (sl[d.strength] || d.strength) + '</span></td>' +
        '<td style="font-size:12px;color:var(--gray-500);">' + (tips[d.strength] || '') + '</td></tr>';
    }).join('');
  }
}

// ---- Cohort Tables (FIX 7: expand/collapse) ----
// R3: Single shared expand state for both summary page and cohort page

function renderCohortRows(containerId, cohorts, limit) {
  var el = $(containerId); if (!el) return;
  var top = limit ? cohorts.slice(0, limit) : cohorts;
  var tagBadges = { GREEN: 'badge-green', GOLD: 'badge-gold', RED: 'badge-red', GRAY: 'badge-gray' };
  el.innerHTML = top.map(function(c) {
    var dotColor = c.tag === 'GREEN' ? 'var(--success)' : c.tag === 'GOLD' ? 'var(--pv-gold-500)' : c.tag === 'RED' ? 'var(--error)' : 'var(--gray-400)';
    var rateClass = c.redeem_rate >= 3 ? 'text-success' : c.redeem_rate === 0 ? 'text-muted' : '';
    return '<tr><td><strong>' + c.level + ' / ' + c.age_group + '</strong></td><td>' + c.level + '</td><td>' + c.age_group + '</td><td class="num">' + c.issued + '</td><td class="num">' + c.redeemed + '</td><td class="num ' + rateClass + '">' + c.redeem_rate + '%</td><td class="num">' + c.atv + '</td><td class="num font-bold">' + fmt(c.sales) + '</td><td><span class="badge ' + (tagBadges[c.tag] || 'badge-gray') + '"><span class="badge-dot" style="background:' + dotColor + ';"></span>' + c.tag + '</span></td></tr>';
  }).join('');
}
function updateCohortTables(cohorts) {
  if (!cohorts || cohorts.length === 0) return;

  // === Summary page: fixed Top 5, no expand ===
  renderCohortRows('#cohort-table-body', cohorts, 5);

  // === Cohort page: single Top 5 table (with expand) ===
  var detailLimit = cohortExpanded ? 0 : 5;
  var shown = cohortExpanded ? cohorts : cohorts.slice(0, 5);
  renderCohortRows('#cohort-detail-table', cohorts, detailLimit);

  // Total row only for the expandable bottom table
  var detailTbody = document.querySelector('#cohort-detail-table');
  if (detailTbody) {
    var oldTotal = detailTbody.querySelector('.cohort-total-row');
    if (oldTotal) oldTotal.remove();
    var totalLabel = cohortExpanded ? '全部合计' : 'Top 5 合计';
    var tIssued = shown.reduce(function(s, c) { return s + (c.issued || 0); }, 0);
    var tRedeemed = shown.reduce(function(s, c) { return s + (c.redeemed || 0); }, 0);
    var tSales = shown.reduce(function(s, c) { return s + (c.sales || 0); }, 0);
    var tr = document.createElement('tr');
    tr.className = 'cohort-total-row';
    tr.style.cssText = 'background:#f9fafb;font-weight:600;';
    tr.innerHTML = '<td colspan="3" style="font-size:12px;color:#6b7280;">' + totalLabel + '</td>' +
      '<td class="num" style="font-weight:600;">' + fmt(tIssued) + '</td>' +
      '<td class="num" style="font-weight:600;">' + fmt(tRedeemed) + '</td>' +
      '<td class="num"></td><td class="num"></td>' +
      '<td class="num font-bold" style="font-weight:700;">' + fmt(tSales) + '</td><td></td>';
    detailTbody.appendChild(tr);
  }

  // Update summary table info
  var ti = $('#table-info');
  if (ti) ti.textContent = '显示 Top 5 / ' + cohorts.length + ' 条客群记录';

  // === Expand button: only for #cohort-detail-panel ===
  function toggleExpand() { cohortExpanded = !cohortExpanded; updateCohortTables(cohorts); }

  var cpPanelHeader = document.querySelector('#cohort-detail-panel .panel-header');
  var cpExpandBtn = $('#cohort-page-expand-btn');
  if (!cpExpandBtn && cpPanelHeader) {
    cpExpandBtn = document.createElement('button');
    cpExpandBtn.id = 'cohort-page-expand-btn';
    cpExpandBtn.className = 'btn btn-secondary btn-sm';
    cpExpandBtn.style.cssText = 'margin-left:auto;';
    cpPanelHeader.appendChild(cpExpandBtn);
  }
  if (cpExpandBtn) {
    cpExpandBtn.textContent = cohortExpanded ? '收起' : '展开全部（共 ' + cohorts.length + ' 组）';
    cpExpandBtn.onclick = toggleExpand;
  }

  // Update detail table title dynamically
  var cpPanelTitle = document.querySelector('#cohort-detail-panel .panel-title');
  if (cpPanelTitle) {
    var shownN = cohortExpanded ? cohorts.length : 5;
    cpPanelTitle.textContent = '客群明细 — Top ' + shownN + ' by 销售额';
  }

  // Remove summary expand button if it exists (no longer needed)
  var oldSummaryBtn = $('#cohort-expand-btn');
  if (oldSummaryBtn) oldSummaryBtn.remove();

  // === Quadrant expand lists ===
  var tags = { GREEN: [], GOLD: [], RED: [], GRAY: [] };
  cohorts.forEach(function(c) { if (tags[c.tag]) tags[c.tag].push(c); });
  // Use issued_users as primary population count
  var total = cohorts.reduce(function(s, c) { return s + (c.issued_users || c.consumers || 0); }, 0);
  var tagDefs = [
    { tag: 'GREEN', condition: '核销率 ≥ 0.5% & 客单价 ≥ ¥300', color: 'var(--success)', badge: 'badge-green' },
    { tag: 'GOLD', condition: '客单价 ≥ ¥800 & 核销率 < 1%', color: 'var(--pv-gold-500)', badge: 'badge-gold' },
    { tag: 'RED', condition: '人均领券 ≥ 2 & 客单价 < ¥500', color: 'var(--error)', badge: 'badge-red' },
    { tag: 'GRAY', condition: '未触发以上任何条件', color: 'var(--gray-400)', badge: 'badge-gray' },
  ];
  var tbody = $('#tag-table-body');
  if (tbody) { tbody.innerHTML = tagDefs.map(function(d) { var items = tags[d.tag]; var count = items.reduce(function(s, c) { return s + (c.issued_users || c.consumers || 0); }, 0); var pct = total > 0 ? (count / total * 100).toFixed(1) : 0; return '<tr><td><span class="badge ' + d.badge + '"><span class="badge-dot" style="background:' + d.color + ';"></span>' + d.tag + '</span></td><td style="font-size:12px;">' + d.condition + '</td><td class="num font-bold">' + count.toLocaleString() + '</td><td class="num">' + pct + '%</td></tr>'; }).join(''); }
  var distEl = $('#cohort-dist-stats');
  if (distEl) { var recs = { GREEN: '加大精准投放，提升发券频次', GOLD: '体验式营销，避免折扣侵蚀毛利', RED: '熔断止损，限制发券频率', GRAY: '常规运营覆盖，观察转化潜力' }; var names = { GREEN: '高ROI转化客群', GOLD: '自然高价值客群', RED: '耗损型客群', GRAY: '基础客群' }; distEl.innerHTML = tagDefs.map(function(d) { var items = tags[d.tag]; var count = items.reduce(function(s, c) { return s + (c.issued_users || c.consumers || 0); }, 0); return '<div class="stat-mini" style="margin-bottom:var(--space-3);"><div class="stat-mini-label">' + d.tag + ' · ' + (names[d.tag] || '') + '</div><div class="stat-mini-value" style="color:' + d.color + ';">' + count.toLocaleString() + ' 人</div><div style="font-size:11px;color:var(--gray-400);">建议: ' + (recs[d.tag] || '') + '</div></div>'; }).join(''); }
}

// ---- KPI Metrics Table ----
function updateKPITables(kpis) {
  if (!kpis) return;
  var rows = [
    { key: 'total_issued', name: '总发券量', formula: 'count(coupon_record_id)', value: kpis.total_issued, unit: '张', status: 'normal' },
    { key: 'real_used', name: '真实核销量', formula: 'sum(status_code == 1)', value: kpis.real_used, unit: '张', status: 'normal' },
    { key: 'conversion_rate', name: '核销转化率', formula: 'real_used / total_issued × 100', value: kpis.conversion_rate, unit: '%', status: kpis.conversion_rate >= 3 ? 'good' : 'normal' },
    { key: 'roi', name: '营销投资回报率', formula: '(est_sales - est_cost) / est_cost × 100', value: kpis.roi, unit: '%', status: kpis.roi < 10 ? 'critical' : 'good' },
    { key: 'coupon_leverage', name: '发券动销渗透率', formula: 'est_coupon_sales / total_sales × 100', value: kpis.coupon_leverage, unit: '%', status: kpis.coupon_leverage < 0.5 ? 'warning' : 'normal' },
    { key: 'aov', name: '平均客单价', formula: 'total_sales / total_orders', value: kpis.aov, unit: 'CNY', status: 'good' },
    { key: 'member_contribution', name: '会员贡献占比', formula: 'member_sales / total_sales × 100', value: kpis.member_contribution, unit: '%', status: kpis.member_contribution > 50 ? 'good' : 'normal' },
  ];
  var statusBadges = { good: 'badge-green', warning: 'badge-gold', critical: 'badge-red', normal: 'badge-gray' };
  var statusLabels = { good: '达标', warning: '预警', critical: '严重', normal: '正常' };
  var tbody = $('#metric-table-body');
  if (tbody) tbody.innerHTML = rows.map(function(r) { return '<tr><td class="font-mono" style="font-size:12px;">' + r.key + '</td><td>' + r.name + '</td><td class="font-mono" style="font-size:11px;color:var(--gray-500);">' + r.formula + '</td><td class="num font-bold ' + (r.status === 'critical' ? 'text-error' : '') + '">' + (typeof r.value === 'number' ? Number(r.value).toFixed(2) : r.value) + '</td><td class="num text-muted">' + r.unit + '</td><td><span class="badge ' + statusBadges[r.status] + '">' + statusLabels[r.status] + '</span></td></tr>'; }).join('');
}

// ---- Insights ----
function updateInsights(data) {
  // Local mode: don't render diagnostic cards, don't send AI requests
  if (window._aiEnabled === false) {
    var cardsContainer = document.getElementById('insight-cards');
    if (cardsContainer) cardsContainer.innerHTML = '<div class="panel" style="flex:1 1 100%;"><div class="panel-header"><div class="panel-title">智能诊室</div></div><div class="panel-body"><p style="color:#64748b;text-align:center;padding:20px 0;font-size:13px;line-height:1.8;">智能诊室为 LLM 模式专属功能<br><span style="font-size:12px;color:#94a3b8;">请点击左上角模式切换按钮后使用</span></p></div></div>';
    updateAiVisibility();
    return;
  }
  var k = data.kpis || {}, structure = data.structure || [], cohorts = data.cohorts || [];
  if (!k.total_issued && cohorts.length === 0) return;

  var parking = structure.find(function(s) { return s.name.indexOf('停车') >= 0; });
  var parkingPct = parking ? parking.pct : 0;
  var lagData = data.lag || [];
  var best = lagData.length > 0 ? [].concat(lagData).sort(function(a, b) { return b.r - a.r; })[0] : { lag: 3, r: 0.82 };
  var greenItems = cohorts.filter(function(c) { return c.tag === 'GREEN'; });

  // Cards are now fully data-driven via updateAIInsight() — no static slots.
  var ca = $('#chat-answer');
  if (ca) ca.innerHTML = '基于当前数据分析：<br>1. <strong>资源错配</strong>：' + parkingPct + '% 预算投入停车券但回报极低<br>2. <strong>滞后窗口</strong>：最佳发券时点为消费前 ' + best.lag + ' 天（r=' + best.r + '）<br>3. <strong>客群策略</strong>：GREEN 客群（' + greenItems.length + '组）应加大投放，GOLD 客群应走体验式营销路径<br>4. <strong>ROI 风险</strong>：当前 ROI ' + (k.roi || 0) + '%' + ((k.roi || 0) < 100 ? ' 低于安全线，需紧急调整' : '');

  // Local mode: hide AI chat module
  updateAiVisibility();
}

// ===== AI visibility toggle (local vs LLM mode) =====
function updateAiVisibility() {
  var chatModule = document.querySelector('#page-insight .panel:last-of-type');
  var chatAnswer = document.getElementById('chat-answer');
  if (window._aiEnabled === false) {
    if (chatModule) chatModule.style.display = 'none';
    if (chatAnswer) chatAnswer.style.display = 'none';
  } else {
    if (chatModule) chatModule.style.display = 'block';
    if (chatAnswer) chatAnswer.style.display = 'block';
  }
}

// ---- AI Insight Panel (data-driven dynamic card rendering) ----
// Each recommendation dict carries {text, action, effect, pct, title, severity_label, severity_color}
// Cards are generated dynamically — no fixed slots, no hardcoded titles.
function updateAIInsight(insight) {
  if (!insight) return;

  // Show engine source in page title
  var engineLabel = document.getElementById('insight-engine');
  if (!engineLabel) {
    var pageInsight = document.getElementById('page-insight');
    if (pageInsight) {
      var title = pageInsight.querySelector('.section-title');
      if (title) {
        var span = document.createElement('span');
        span.id = 'insight-engine';
        span.style.cssText = 'font-size:11px;color:var(--gray-400);font-weight:400;margin-left:8px;';
        title.appendChild(span);
        engineLabel = span;
      }
    }
  }
  if (engineLabel) {
    engineLabel.textContent = '引擎: ' + (insight.generated_by || '本地规则引擎');
  }

  var ca = document.getElementById('chat-answer');
  if (ca && insight.executive_summary) {
    var cleanSummary = cleanText(insight.executive_summary || '');
    ca.innerHTML = cleanSummary + '<br><small style="color:var(--gray-400);margin-top:4px;display:block;">引擎: ' + (insight.generated_by || '本地规则引擎') + '</small>';
  }

  // Defensive: page_overview format has {summary, findings, recommendation}, not {recommendations}.
  // Convert it to diagnostic recs on the fly so the cards still render.
  var recs = insight.recommendations || [];
  if (recs.length === 0 && insight.findings && Array.isArray(insight.findings) && insight.findings.length > 0) {
    recs = insight.findings.map(function(f, i) {
      return {
        text: f,
        action: f,
        effect: 'sales_efficiency',
        effect_label: '销售效率',
        pct: 0,
        title: '关键发现 ' + (i + 1),
        severity: 'info',
        how_to: ['按数据洞察调整相关策略', '2 周后复盘关键 KPI 变化', '与历史同期对比验证效果'],
      };
    });
    if (insight.recommendation) {
      recs.push({
        text: insight.recommendation,
        action: insight.recommendation,
        effect: 'sales_efficiency',
        effect_label: '销售效率',
        pct: 0,
        title: '最优先建议',
        severity: 'warning',
        how_to: ['立即落地最优先项的调整动作', '2 周后监控核心指标变化', '形成闭环经验沉淀到运营 SOP'],
      });
    }
  }
  var alerts = insight.alerts || [];
  // Also surface findings as alerts for the alerts panel (so they appear if recs branch was used)
  if (alerts.length === 0 && insight.findings && Array.isArray(insight.findings)) {
    alerts = insight.findings.map(function(f) { return { severity: 'info', message: f }; });
  }
  var engineTag = (insight.generated_by && insight.generated_by !== '本地规则引擎')
    ? '<div style="font-size:10px;color:#3b82f6;margin-top:8px;padding-top:8px;border-top:1px dashed var(--gray-100);">引擎: ' + insight.generated_by + '</div>'
    : '';

  // ---- Build dynamic cards from recommendations ----
  var cardsContainer = document.getElementById('insight-cards');
  if (!cardsContainer) return;

  if (recs.length === 0) {
    // Distinguish between "still loading" and "no scenarios triggered"
    if (!insight.generated_by) {
      cardsContainer.innerHTML = '<div class="panel" style="flex:1 1 100%;"><div class="panel-header"><div class="panel-title">加载中</div></div><div class="panel-body"><p style="font-size:14px;color:var(--gray-400);line-height:1.8;">正在分析数据...</p></div></div>';
    } else {
      cardsContainer.innerHTML = '<div class="panel" style="flex:1 1 100%;"><div class="panel-header"><div class="panel-title">当前数据健康</div></div><div class="panel-body"><p style="font-size:14px;color:var(--gray-400);line-height:1.8;">当前数据范围内未触发诊断场景，' + (insight.executive_summary || '各项指标处于正常区间。') + '</p></div></div>';
    }
    return;
  }

  // Severity → visual mapping
  var sevMap = {
    'critical': { dot: 'var(--error)', badge: 'badge-red', label: '严重' },
    'high':     { dot: 'var(--error)', badge: 'badge-red', label: '严重' },
    'warning':  { dot: '#f59e0b', badge: 'badge-gold', label: '预警' },
    'medium':   { dot: '#f59e0b', badge: 'badge-gold', label: '预警' },
    'info':     { dot: 'var(--info)', badge: 'badge-gray', label: '信息' },
    'low':      { dot: 'var(--info)', badge: 'badge-gray', label: '信息' },
    'opportunity': { dot: 'var(--success)', badge: 'badge-green', label: '机会' },
  };

  var cardsHtml = '';
  for (var i = 0; i < recs.length; i++) {
    var r = recs[i];
    if (typeof r !== 'object') continue;

    var text = r.text || '';
    var action = r.action || '';
    var effect = r.effect || 'sales_efficiency';
    var effectLabel = r.effect_label || ({coupon_volume: '发券量', sales_efficiency: '销售效率', lag_correlation: '滞后效应'})[effect] || '营销效能';
    var pct = (r.pct != null) ? r.pct : 0;
    var title = r.title || ('诊断 #' + (i + 1));
    var howTo = Array.isArray(r.how_to) ? r.how_to : [];
    var sev = r.severity || 'medium';
    var sevInfo = sevMap[sev] || sevMap['medium'];
    var escAction = (action || title).replace(/'/g, "\\'");

    // effect + pct badge (shows the "what dimension + how much")
    var pctArrow = pct > 0 ? '↑' : (pct < 0 ? '↓' : '—');
    var pctColor = pct > 0 ? '#10b981' : (pct < 0 ? '#ef4444' : '#9ca3af');
    var pctText = pct > 0 ? ('+' + pct + '%') : (pct < 0 ? (pct + '%') : '0%');
    var effectBadge =
      '<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 8px;background:#f3f4f6;border:1px solid #e5e7eb;border-radius:10px;font-size:11px;color:var(--gray-600);margin-right:6px;">' +
        '<span style="font-weight:600;">' + escapeHtml(effectLabel) + '</span>' +
      '</span>' +
      '<span style="display:inline-flex;align-items:center;gap:2px;padding:2px 8px;background:' + pctColor + '15;border:1px solid ' + pctColor + '40;border-radius:10px;font-size:11px;font-weight:600;color:' + pctColor + ';">' +
        pctArrow + ' ' + pctText +
      '</span>';

    // how_to list
    var howToHtml = '';
    if (howTo.length > 0) {
      howToHtml =
        '<p style="font-weight:600;margin:12px 0 6px 0;">具体怎么做</p>' +
        '<ol style="padding-left:20px;margin:0;font-size:12px;color:var(--gray-600);line-height:1.7;">' +
          howTo.map(function(step) { return '<li style="margin-bottom:4px;">' + escapeHtml(step) + '</li>'; }).join('') +
        '</ol>';
    }

    cardsHtml +=
      '<div class="panel" style="flex:1 1 48%;min-width:320px;">' +
        '<div class="panel-header">' +
          '<div class="panel-title" style="display:flex;align-items:center;gap:8px;">' +
            '<span style="width:8px;height:8px;border-radius:50%;background:' + sevInfo.dot + ';flex-shrink:0;"></span>' +
            '诊断 #' + (i + 1) + ' · ' + escapeHtml(title) +
          '</div>' +
          '<span class="badge ' + sevInfo.badge + '">' + sevInfo.label + '</span>' +
        '</div>' +
        '<div class="panel-body">' +
          '<div style="margin-bottom:10px;">' + effectBadge + '</div>' +
          '<p style="font-weight:600;margin-bottom:6px;">核心诊断</p>' +
          '<p style="font-size:13px;color:var(--gray-600);margin-bottom:6px;line-height:1.6;">' + escapeHtml(text) + '</p>' +
          '<p style="font-weight:600;margin-bottom:6px;">建议动作</p>' +
          '<div style="font-size:13px;color:var(--gray-600);line-height:1.6;margin-bottom:4px;">' +
            '<span style="display:inline-block;padding:2px 10px;background:' + sevInfo.dot + '15;border-left:3px solid ' + sevInfo.dot + ';border-radius:2px;">' + escapeHtml(action) + '</span>' +
          '</div>' +
          howToHtml +
          '<button class="btn btn-primary btn-sm" style="margin-top:12px;" onclick="adoptSuggestion(\'' + escAction + '\',\'' + effect + '\',' + pct + ')">采纳建议</button>' +
          engineTag +
        '</div>' +
      '</div>';
  }

  // ---- Alerts section (always present if there are alerts) ----
  if (alerts && alerts.length > 0) {
    cardsHtml +=
      '<div class="panel" style="flex:1 1 100%;">' +
        '<div class="panel-header">' +
          '<div class="panel-title" style="display:flex;align-items:center;gap:8px;">' +
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--error)" stroke-width="2" style="flex-shrink:0;"><path d="M12 3.5 L20.5 20 L3.5 20 Z" fill="#fff" stroke-linejoin="round"/><text x="12" y="15.5" text-anchor="middle" fill="var(--error)" font-size="11" font-weight="700">!</text></svg>' +
            '全量预警清单' +
          '</div>' +
          '<span style="font-size:12px;color:var(--gray-400);">共 ' + alerts.length + ' 条</span>' +
        '</div>' +
        '<div class="panel-body">' +
          '<ul style="padding-left:0;margin:0;list-style:none;">' +
            alerts.slice(0, 6).map(function(a) {
              var color = a.severity === 'critical' ? '#ef4444' : (a.severity === 'warning' ? '#f59e0b' : '#3b82f6');
              var label = a.severity === 'critical' ? '严重' : (a.severity === 'warning' ? '警告' : '提示');
              return '<li style="margin-bottom:8px;padding-left:0;display:flex;align-items:flex-start;gap:8px;font-size:13px;color:var(--gray-600);line-height:1.6;">' +
                '<span style="display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;color:#fff;background:' + color + ';flex-shrink:0;margin-top:2px;">' + label + '</span>' +
                '<span>' + escapeHtml(a.message || '') + '</span>' +
              '</li>';
            }).join('') +
          '</ul>' +
        '</div>' +
      '</div>';
  }

  cardsContainer.innerHTML = cardsHtml;
}

// Minimal HTML escape to prevent XSS in dynamic card content
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ---- FIX 6: Suggested Questions (enhanced) ----
function updateSuggestedQuestions(data) {
  var chatInput = document.getElementById('chat-input');
  if (!chatInput) return;
  var inputRow = chatInput.parentElement;
  if (!inputRow) return;

  var container = document.getElementById('suggested-questions');
  if (!container) {
    container = document.createElement('div');
    container.id = 'suggested-questions';
    inputRow.parentNode.insertBefore(container, inputRow);
  }

  var k = data.kpis || {};
  var structure = data.structure || [];
  var cohorts = data.cohorts || [];
  var lagData = data.lag || [];
  var pool = [];

  var parking = structure.find(function(s) { return s.name.indexOf('停车') >= 0; });
  var green = cohorts.filter(function(c) { return c.tag === 'GREEN'; });
  var bestLag = lagData.length > 0 ? [].concat(lagData).sort(function(a,b){return b.r-a.r;})[0] : null;

  if ((k.roi || 0) < 30) pool.push('如何提升营销 ROI？');
  if (parking && parking.pct > 60) pool.push('为什么停车券核销率这么低？');
  if (green.length > 0) pool.push('哪个客群的转化效率最高？');
  if (bestLag && bestLag.r > 0.2) pool.push('最佳发券时机是提前几天？');
  pool.push('当前最大的问题是什么？');
  pool.push('会员贡献占比多少？');
  pool.push('耗损型客群是什么意思？');
  pool.push('你能做什么？');

  // Random pick 4
  var questions = pool.sort(function() { return 0.5 - Math.random(); }).slice(0, 4);

  container.innerHTML =
    '<span style="font-size:12px;color:var(--gray-400);flex-shrink:0;">建议提问:</span>' +
    questions.map(function(q) {
      return '<span class="suggest-chip" data-q="' + q.replace(/"/g, '&quot;') + '">' + q + '</span>';
    }).join('') +
    '<span id="refresh-suggest" title="换一批">&#x21bb; 换一批</span>';

  // Click question -> fill input + send -> refresh suggestions
  container.querySelectorAll('.suggest-chip').forEach(function(chip) {
    chip.addEventListener('click', function() {
      var q = this.getAttribute('data-q');
      var input = document.getElementById('chat-input');
      var sendBtn = document.getElementById('chat-send');
      if (input && sendBtn) { input.value = q; sendBtn.click(); }
      setTimeout(function() { updateSuggestedQuestions(globalData); }, 300);
    });
  });

  // Refresh button
  var refreshBtn = document.getElementById('refresh-suggest');
  if (refreshBtn) refreshBtn.addEventListener('click', function() { updateSuggestedQuestions(globalData); });
}

// ---- FIX 8: Real Filter Selectors (custom dropdown) ----
function buildFilterSelectors(filterOpts) {
  if (!filterOpts || !filterOpts.levels) return;
  var bar = document.querySelector('#page-summary .filter-bar');
  if (!bar) return;
  // Remove old wrapper if exists
  var oldWrap = bar.querySelector('.filter-dropdown-wrap');
  if (oldWrap) oldWrap.remove();

  var wrapper = document.createElement('div');
  wrapper.className = 'filter-dropdown-wrap';
  wrapper.style.cssText = 'display:flex;align-items:center;gap:8px;';
  wrapper.innerHTML = '<span style="font-size:12px;color:var(--gray-500);white-space:nowrap;">筛选:</span>';

  // Build level dropdown
  wrapper.appendChild(_buildDropdown('level', '会员等级', filterOpts.levels, selectedLevels));
  // Build age dropdown
  wrapper.appendChild(_buildDropdown('age', '年龄段', filterOpts.ages || [], selectedAges));
  // Apply button
  var applyBtn = document.createElement('button');
  applyBtn.className = 'btn btn-secondary btn-sm';
  applyBtn.textContent = '应用';
  applyBtn.addEventListener('click', function() {
    loadAll({ levels: selectedLevels, ages: selectedAges, start_date: selectedStartDate, end_date: selectedEndDate }).then(renderAll);
  });
  wrapper.appendChild(applyBtn);

  bar.insertBefore(wrapper, bar.firstChild);
}

function _buildDropdown(type, label, options, selectedArr) {
  var container = document.createElement('div');
  container.className = 'multi-select';
  container.style.cssText = 'position:relative;';

  var trigger = document.createElement('div');
  trigger.className = 'multi-select-trigger';
  trigger.style.cssText = 'height:28px;padding:0 8px;border:1px solid var(--gray-200);border-radius:6px;font-size:12px;color:var(--gray-600);cursor:pointer;display:flex;align-items:center;gap:4px;white-space:nowrap;min-width:90px;background:white;';
  trigger.textContent = label + ' ' + (selectedArr.length ? '(' + selectedArr.length + ')' : '▼');
  trigger.setAttribute('data-type', type);

  var panel = document.createElement('div');
  panel.className = 'multi-select-dropdown';
  panel.style.cssText = 'display:none;position:absolute;top:100%;left:0;margin-top:4px;width:160px;background:white;border:1px solid var(--gray-200);border-radius:8px;box-shadow:var(--shadow-lg);z-index:100;max-height:220px;overflow-y:auto;';
  panel.setAttribute('data-type', type);

  options.forEach(function(opt) {
    var labelEl = document.createElement('label');
    labelEl.style.cssText = 'display:flex;align-items:center;gap:6px;padding:6px 12px;font-size:13px;color:var(--gray-700);cursor:pointer;';
    labelEl.addEventListener('mouseenter', function() { this.style.background = 'var(--gray-50)'; });
    labelEl.addEventListener('mouseleave', function() { this.style.background = ''; });
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.value = opt;
    cb.checked = selectedArr.indexOf(opt) >= 0;
    cb.addEventListener('change', function() {
      if (this.checked) { if (selectedArr.indexOf(opt) < 0) selectedArr.push(opt); }
      else { var idx = selectedArr.indexOf(opt); if (idx >= 0) selectedArr.splice(idx, 1); }
      trigger.textContent = label + ' ' + (selectedArr.length ? '(' + selectedArr.length + ')' : '▼');
    });
    labelEl.appendChild(cb);
    labelEl.appendChild(document.createTextNode(opt));
    panel.appendChild(labelEl);
  });

  trigger.addEventListener('click', function(e) {
    e.stopPropagation();
    var isOpen = panel.style.display === 'block';
    // Close all dropdowns first
    document.querySelectorAll('.multi-select-dropdown').forEach(function(p) { p.style.display = 'none'; });
    panel.style.display = isOpen ? 'none' : 'block';
  });

  // Close on outside click
  document.addEventListener('click', function(e) {
    if (!container.contains(e.target)) panel.style.display = 'none';
  });

  container.appendChild(trigger);
  container.appendChild(panel);
  return container;
}

// ---- Filter Bar ----
function updateFilterBar(filterOpts) {
  if (!filterOpts) return;
  var dateRange = $('#date-range-text');
  if (dateRange && filterOpts.date_min) dateRange.textContent = filterOpts.date_min + ' — ' + filterOpts.date_max;
}

// ---- Cohort Detail Table ----
function updateCohortDetailTable(detail) {
  // Only runs on summary page now — cohort page tables handled by updateCohortTables
  if (!detail || detail.length === 0) return;
  var tbody = $('#cohort-detail-table');
  if (!tbody) return;
  // Skip if cohort detail panel exists (its table is managed by updateCohortTables)
  if (document.getElementById('cohort-detail-panel')) return;
  var tagBadges = { GREEN: 'badge-green', GOLD: 'badge-gold', RED: 'badge-red', GRAY: 'badge-gray' };
  tbody.innerHTML = detail.slice(0, 5).map(function(c) {
    var tag = c['诊断标签'];
    var dotColor = tag === 'GREEN' ? 'var(--success)' : tag === 'GOLD' ? 'var(--pv-gold-500)' : tag === 'RED' ? 'var(--error)' : 'var(--gray-400)';
    return '<tr><td><strong>' + c['会员等级'] + ' / ' + c['世代人群'] + '</strong></td><td>' + c['会员等级'] + '</td><td>' + c['世代人群'] + '</td><td class="num">' + c['总发券量'] + '</td><td class="num">' + c['核销量'] + '</td><td class="num">' + c['核销率'] + '%</td><td class="num">' + c['客单价'] + '</td><td class="num font-bold">' + fmt(c['总销售额']) + '</td><td><span class="badge ' + (tagBadges[tag] || 'badge-gray') + '"><span class="badge-dot" style="background:' + dotColor + ';"></span>' + tag + '</span></td></tr>';
  }).join('');
  var ti = $('#table-info');
  if (ti) ti.textContent = '显示 Top 5 / ' + detail.length + ' 条客群记录';
}

// ---- AI Chat ----
function escapeHtml(text) { var div = document.createElement('div'); div.textContent = text; return div.innerHTML; }
function bindChatEvents() {
  var sendBtn = $('#chat-send'), inputEl = $('#chat-input');
  if (!sendBtn || !inputEl) return;
  sendBtn.addEventListener('click', async function() {
    var msg = inputEl.value.trim(); if (!msg) return;
    var msgs = $('#chat-messages'); if (!msgs) return;
    msgs.innerHTML += '<div style="align-self:flex-end;max-width:70%;padding:10px 16px;background:var(--pv-green-600);color:white;border-radius:12px 12px 4px 12px;font-size:13px;margin-top:8px;">' + escapeHtml(msg) + '</div>';
    inputEl.value = '';
    var answerEl = document.createElement('div');
    answerEl.style.cssText = 'align-self:flex-start;max-width:80%;padding:10px 16px;background:var(--gray-100);color:var(--gray-700);border-radius:12px 12px 12px 4px;font-size:13px;line-height:1.7;margin-top:8px;';
    answerEl.textContent = '正在分析...'; msgs.appendChild(answerEl); msgs.scrollTop = msgs.scrollHeight;
    try {
      var resp = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: msg }) });
      var result = await resp.json();
      var cleanAnswer = cleanText(result.answer);
      answerEl.innerHTML = cleanAnswer + '<br><small style="color:var(--gray-400);">引擎: ' + (result.engine || '未知') + '</small>';
    } catch (e) { answerEl.innerHTML = '抱歉，分析服务暂时不可用。请稍后重试。'; }
    msgs.scrollTop = msgs.scrollHeight;
  });
  inputEl.addEventListener('keydown', function(e) { if (e.key === 'Enter') sendBtn.click(); });
}

// ---- Page Routing ----
function bindPageRouting() {
  var navItems = $$('.nav-item[data-page]');
  var sections = $$('.page-section');
  var breadcrumb = $('#breadcrumb-current');
  if (!navItems.length || !sections.length) return;
  navItems.forEach(function(item) {
    item.addEventListener('click', function(e) {
      e.preventDefault();
      var page = this.getAttribute('data-page'), title = this.getAttribute('data-title');
      sections.forEach(function(s) { s.classList.remove('active'); });
      var target = $('#page-' + page); if (target) target.classList.add('active');
      navItems.forEach(function(n) { n.classList.remove('active'); });
      this.classList.add('active');
      if (breadcrumb) breadcrumb.textContent = title;
      // R4: Update current page + refresh AI panel
      currentPage = page;
      aiPanelForcePage = false;  // Reset force-page flag on navigation
      if (!aiPanelLocked) {
        aiPanelFocus = null;
        clearTimeout(aiPanelRestoreTimer);
      }
      updateSmartAnalysisPanel();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
}

// FIX 2: tab clicks use closest
function bindGlobalClicks() {
  document.addEventListener('click', function(e) {
    var tab = e.target.closest('.tab');
    if (tab) {
      var siblings = tab.parentElement.querySelectorAll('.tab');
      siblings.forEach(function(s) { s.classList.remove('active'); });
      tab.classList.add('active');
      var gran = tab.getAttribute('data-gran');
      if (gran && ['daily', 'weekly', 'monthly'].indexOf(gran) >= 0) {
        currentGranularity = gran;
        var old = tab.parentElement.querySelector('.tab-loading');
        if (old) old.remove();
        var loading = document.createElement('span'); loading.className = 'tab-loading'; loading.textContent = '...'; loading.style.cssText = 'font-size:11px;color:var(--gray-400);margin-left:4px;';
        tab.appendChild(loading);
        fetch('/api/trend?granularity=' + gran).then(function(r) { return r.json(); }).then(function(trend) {
          globalData.trend = trend; updateTrendChart(trend);
          var ld = document.querySelector('.tab-loading'); if (ld) ld.remove();
        });
      }
    }
    if (e.target.classList.contains('filter-chip-remove')) e.target.parentElement.style.display = 'none';
    if (e.target.closest('.matrix-cell')) { var cell = e.target.closest('.matrix-cell'); cell.style.transform = 'scale(0.98)'; setTimeout(function() { cell.style.transform = ''; }, 150); }
  });
}

// ---- Export Handlers ----
function bindExportHandlers() {
  document.addEventListener('click', async function(e) {
    if (e.target.matches('.btn-export-kpi') || e.target.closest('.btn-export-kpi')) { e.preventDefault(); window.open('/api/export-kpi-csv', '_blank'); }
    if (e.target.matches('.btn-export-cohort') || e.target.closest('.btn-export-cohort')) { e.preventDefault(); window.open('/api/export-cohort-csv', '_blank'); }
    if (e.target.matches('.btn-export-report') || e.target.closest('.btn-export-report')) {
      e.preventDefault();
      var insight = globalData.insight || {};
      try {
        var resp = await fetch('/api/export-report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ metrics: globalData.kpis, alerts: insight.alerts || [], insight_text: insight.executive_summary || '', recommendations: insight.recommendations || [] }) });
        var result = await resp.json();
        if (result.success) { alert('报告已生成: ' + result.filepath); var blob = new Blob([result.content], { type: 'text/markdown' }); var url = URL.createObjectURL(blob); var a = document.createElement('a'); a.href = url; a.download = '战情报告.md'; a.click(); URL.revokeObjectURL(url); }
        else alert('导出失败: ' + (result.message || '未知错误'));
      } catch (err) { alert('导出失败: ' + err.message); }
    }
  });
}

// ---- Date Picker ----
function bindDatePicker() {
  var trigger = $('#date-range-display');
  var panel = $('#date-picker-panel');
  var dpStart = $('#dp-start');
  var dpEnd = $('#dp-end');
  var dpHint = $('#dp-hint');
  var topbar = document.querySelector('.topbar-right');
  if (!trigger || !panel || !dpStart || !dpEnd || !dpHint) return;

  // Toggle panel
  trigger.addEventListener('click', function(e) {
    e.stopPropagation();
    var isOpen = panel.style.display === 'block';
    panel.style.display = isOpen ? 'none' : 'block';
    if (!isOpen && globalData.filterOpts) {
      var opts = globalData.filterOpts;
      dpStart.min = opts.date_min || '';
      dpStart.max = opts.date_max || '';
      dpEnd.min = opts.date_min || '';
      dpEnd.max = opts.date_max || '';
      dpHint.textContent = '数据范围：' + (opts.date_min || '—') + ' 至 ' + (opts.date_max || '—');
      dpStart.value = selectedStartDate;
      dpEnd.value = selectedEndDate;
    }
  });

  // Close on outside click
  document.addEventListener('click', function(e) {
    if (panel.style.display === 'block' && !panel.contains(e.target) && e.target !== trigger && !trigger.contains(e.target)) {
      panel.style.display = 'none';
    }
  });

  // Close on Escape
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && panel.style.display === 'block') { panel.style.display = 'none'; }
  });

  // Apply button
  var applyBtn = $('#dp-apply');
  if (applyBtn) applyBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    var start = dpStart.value;
    var end = dpEnd.value;
    if (start && end && start > end) { alert('开始日期不能晚于结束日期'); return; }
    selectedStartDate = start;
    selectedEndDate = end;
    panel.style.display = 'none';
    updateDateDisplay();
    loadAll({ levels: selectedLevels, ages: selectedAges, start_date: selectedStartDate, end_date: selectedEndDate }).then(renderAll);
  });

  // Reset button
  var resetBtn = $('#dp-reset');
  if (resetBtn) resetBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    selectedStartDate = '';
    selectedEndDate = '';
    dpStart.value = '';
    dpEnd.value = '';
    panel.style.display = 'none';
    updateDateDisplay();
    loadAll({ levels: selectedLevels, ages: selectedAges, start_date: selectedStartDate, end_date: selectedEndDate }).then(renderAll);
  });
}

function updateDateDisplay() {
  var el = $('#date-range-text');
  var topbar = document.querySelector('.topbar-right');
  if (!el) return;
  if (selectedStartDate || selectedEndDate) {
    el.textContent = (selectedStartDate || '最早') + ' — ' + (selectedEndDate || '最晚');
    if (topbar) topbar.classList.add('date-filter-active');
  } else {
    if (globalData.summary && globalData.summary.date_range) {
      var c = globalData.summary.date_range.coupon;
      el.textContent = c.min + ' — ' + c.max;
    }
    if (topbar) topbar.classList.remove('date-filter-active');
  }
}

// Also update filter-apply to pass date params
(function() {
  var origBuild = typeof buildFilterSelectors === 'function' ? buildFilterSelectors : null;
})();

// ---- Upload ----
function bindUpload() {
  var toggleBtn = document.getElementById('btn-upload-toggle');
  var panel = document.getElementById('upload-panel');
  var submitBtn = document.getElementById('btn-upload-submit');
  var statusEl = document.getElementById('upload-status');
  if (!toggleBtn || !panel || !submitBtn) return;

  toggleBtn.addEventListener('click', function() {
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
  });

  submitBtn.addEventListener('click', function() {
    var inputFile = document.getElementById('upload-input').files[0];
    var outputFile = document.getElementById('upload-output').files[0];
    if (!inputFile && !outputFile) {
      if (statusEl) statusEl.textContent = '请至少选择一个文件';
      return;
    }
    if (statusEl) statusEl.textContent = '上传中...';
    var formData = new FormData();
    if (inputFile) formData.append('input_file', inputFile);
    if (outputFile) formData.append('output_file', outputFile);

    fetch('/api/upload-data', { method: 'POST', body: formData })
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res.success) {
          if (statusEl) { statusEl.style.color = '#10b981'; statusEl.textContent = res.message; }
          loadAll().then(renderAll);
          setTimeout(function() { panel.style.display = 'none'; if (statusEl) statusEl.textContent = ''; }, 2000);
        } else {
          if (statusEl) { statusEl.style.color = '#ef4444'; statusEl.textContent = res.message; }
        }
      })
      .catch(function(err) {
        if (statusEl) { statusEl.style.color = '#ef4444'; statusEl.textContent = '上传失败: ' + err.message; }
      });
  });
}

// ---- Scheduler Config ----
function bindScheduler() {
  var toggleBtn = document.getElementById('btn-scheduler-toggle');
  var panel = document.getElementById('scheduler-panel');
  if (!toggleBtn || !panel) return;

  toggleBtn.addEventListener('click', function() {
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    if (panel.style.display === 'block') loadSchedulerConfig();
  });

  // Save config
  var saveBtn = document.getElementById('btn-scheduler-save');
  if (saveBtn) saveBtn.addEventListener('click', function() {
    var watchDir = document.getElementById('sched-watch-dir').value;
    var interval = parseFloat(document.getElementById('sched-interval').value) || 24;
    var enabled = document.getElementById('sched-enabled').checked;
    var statusEl = document.getElementById('scheduler-status');
    // R2: Email fields
    var emailEnabled = document.getElementById('sched-email-enabled').checked;
    var notifyEmail = document.getElementById('sched-notify-email').value;

    fetch('/api/scheduler-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        watch_dir: watchDir,
        interval_hours: interval,
        enabled: enabled,
        email_enabled: emailEnabled,
        notify_email: notifyEmail
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(res) {
      if (statusEl) {
        statusEl.style.color = '#10b981';
        var msg = res.running ? '运行中 · 每 ' + res.interval_hours + ' 小时' : '已停止';
        if (res.email_enabled && res.notify_email) msg += ' · 邮件通知: ' + res.notify_email;
        statusEl.textContent = msg;
      }
    })
    .catch(function(err) {
      if (statusEl) { statusEl.style.color = '#ef4444'; statusEl.textContent = '保存失败: ' + err.message; }
    });
  });

  // Trigger now
  var triggerBtn = document.getElementById('btn-scheduler-trigger');
  if (triggerBtn) triggerBtn.addEventListener('click', function() {
    var statusEl = document.getElementById('scheduler-status');
    if (statusEl) { statusEl.style.color = 'var(--gray-400)'; statusEl.textContent = '拉取中...'; }
    fetch('/api/scheduler-trigger', { method: 'POST' })
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res.success) {
          if (statusEl) { statusEl.style.color = '#10b981'; statusEl.textContent = '拉取完成: ' + res.result.files_pulled + ' 个文件，已刷新'; }
          loadAll().then(renderAll);
        }
      })
      .catch(function(err) {
        if (statusEl) { statusEl.style.color = '#ef4444'; statusEl.textContent = '拉取失败: ' + err.message; }
      });
  });
}

function loadSchedulerConfig() {
  fetch('/api/scheduler-config')
    .then(function(r) { return r.json(); })
    .then(function(cfg) {
      var watchEl = document.getElementById('sched-watch-dir');
      var intervalEl = document.getElementById('sched-interval');
      var enabledEl = document.getElementById('sched-enabled');
      var statusEl = document.getElementById('scheduler-status');
      if (watchEl) watchEl.value = cfg.watch_dir || '';
      if (intervalEl) intervalEl.value = cfg.interval_hours || 24;
      if (enabledEl) enabledEl.checked = !!cfg.enabled;
      // R2: Load email config
      var emailEnabledEl = document.getElementById('sched-email-enabled');
      var notifyEmailEl = document.getElementById('sched-notify-email');
      if (emailEnabledEl) emailEnabledEl.checked = !!cfg.email_enabled;
      if (notifyEmailEl) notifyEmailEl.value = cfg.notify_email || '';
      var msg = cfg.running ? '运行中 · 每 ' + cfg.interval_hours + ' 小时' : '已停止';
      if (cfg.email_enabled && cfg.notify_email) msg += ' · 邮件通知: ' + cfg.notify_email;
      if (statusEl) statusEl.textContent = msg;
    });
}

// R5/R6: Click-to-analyze — 鼠标滑取模块标题才触发分析（非悬停）
var hoverTimer = null;
function bindHoverAnalysis() {
  document.addEventListener('click', function(e) {
    // Only trigger on actual title text elements, not the whole panel header bar
    var target = e.target.closest('.section-title') || e.target.closest('.panel-title') || e.target.closest('.kpi-card-label');
    if (!target) return;

    // Ignore clicks on interactive elements within the title
    if (e.target.closest('.ask-btn, .badge, .section-actions, svg, button')) return;

    // Get clean text: use textContent, strip ask-btn/badge/section-title-bar text
    var clone = target.cloneNode(true);
    clone.querySelectorAll('.ask-btn, .badge, .section-title-bar, .section-actions, svg').forEach(function(el) { el.remove(); });
    var cleanText = clone.textContent
      .replace(/^诊断\s*#\d+\s*·\s*/, '')
      .replace(/\s*\(.*\)$/, '')
      .replace(/\s*问\s*$/, '')
      .trim();
    if (!cleanText || cleanText.length < 2) return;

    // Map KPI card labels to meaningful topic names
    var kpiNameMap = {
      '营销投资回报率': 'KPI指标', '总销售额': 'KPI指标', '核销转化率': 'KPI指标', '会员贡献占比': 'KPI指标',
      '发券总量': 'KPI指标', '真实核销量': 'KPI指标', '交易笔数': 'KPI指标', '客单价 (AOV)': 'KPI指标',
      '发券动销渗透率': 'KPI指标', '营销 ROI': 'KPI指标'
    };
    if (kpiNameMap[cleanText]) cleanText = kpiNameMap[cleanText];

    clearTimeout(hoverTimer);
    if (aiPanelLocked) return;
    // Toggle: clicking same title again clears the focus
    if (aiPanelFocus === cleanText) {
      aiPanelFocus = null;
    } else {
      aiPanelFocus = cleanText;
      aiPanelForcePage = false;  // Hover overrides page-view force
    }
    clearTimeout(aiPanelRestoreTimer);
    updateSmartAnalysisPanel();
  });
}

// ===== R7: Module-level "问一问" — floating windows (multi-open, minimize, fullscreen, drag) =====
var chatWindows = {}; // { moduleName: { messages: [], el: null, minimized: false, fullscreen: false } }
var chatWindowZ = 10000;

function openAskWindow(moduleName) {
  // If window already exists, just show it
  if (chatWindows[moduleName] && chatWindows[moduleName].el) {
    var w = chatWindows[moduleName];
    w.el.style.display = 'flex';
    w.el.style.zIndex = ++chatWindowZ;
    if (w.minimized) { restoreAskWindow(moduleName); }
    return;
  }

  // Init history
  if (!chatWindows[moduleName]) chatWindows[moduleName] = { messages: [] };
  var win = chatWindows[moduleName];

  var container = document.createElement('div');
  container.className = 'ask-window';
  container.setAttribute('data-module', moduleName);
  container.style.cssText = 'position:fixed;top:60px;left:300px;width:320px;height:480px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;box-shadow:none;display:flex;flex-direction:column;z-index:' + (++chatWindowZ) + ';overflow:hidden;resize:both;min-width:280px;min-height:380px;';

  // Title bar (flat, 36px)
  var titleBar = document.createElement('div');
  titleBar.style.cssText = 'height:36px;padding:0 12px;background:#f8fafc;border-bottom:1px solid #e2e8f0;display:flex;align-items:center;justify-content:space-between;cursor:move;user-select:none;flex-shrink:0;';
  titleBar.innerHTML = '<span style="font-weight:600;font-size:13px;color:#1e293b;">针对「' + moduleName + '」的问答</span>' +
    '<div style="display:flex;gap:2px;align-items:center;">' +
      '<button class="ask-win-btn" data-action="minimize" title="最小化" style="width:24px;height:24px;background:none;border:none;border-radius:4px;color:#64748b;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;">—</button>' +
      '<button class="ask-win-btn" data-action="fullscreen" title="全屏" style="width:24px;height:24px;background:none;border:none;border-radius:4px;color:#64748b;font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;">&#x26F6;</button>' +
      '<button class="ask-win-btn" data-action="close" title="关闭" style="width:24px;height:24px;background:none;border:none;border-radius:4px;color:#64748b;font-size:15px;cursor:pointer;display:flex;align-items:center;justify-content:center;">&times;</button>' +
    '</div>';

  // Messages area (flat green/blue-gray bubbles)
  var msgs = document.createElement('div');
  msgs.className = 'ask-win-messages';
  msgs.style.cssText = 'flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;';
  var history = win.messages || [];
  if (history.length === 0) {
    msgs.innerHTML = '<div style="color:#9ca3af;font-size:13px;text-align:center;padding:20px;">针对「' + moduleName + '」模块提问，AI 将基于数据给出针对性回答</div>';
  } else {
    msgs.innerHTML = history.map(function(m) {
      return '<div style="align-self:' + (m.role === 'user' ? 'flex-end;background:#dcfce7;color:#166534;' : 'flex-start;background:#f1f5f9;color:#334155;') + 'max-width:80%;padding:8px 12px;border-radius:' + (m.role === 'user' ? '12px 12px 4px 12px;' : '12px 12px 12px 4px;') + 'font-size:13px;line-height:1.6;">' + m.content + '</div>';
    }).join('');
    msgs.scrollTop = msgs.scrollHeight;
  }

  // Input row
  var inputRow = document.createElement('div');
  inputRow.style.cssText = 'padding:8px 12px;border-top:1px solid #e2e8f0;display:flex;gap:6px;flex-shrink:0;';
  inputRow.innerHTML = '<input type="text" class="ask-win-input" placeholder="输入问题..." style="flex:1;padding:6px 10px;border:1px solid #e2e8f0;border-radius:6px;font-size:13px;outline:none;" /><button class="ask-win-send" style="padding:6px 14px;background:#3b82f6;color:#fff;border:none;border-radius:6px;font-size:13px;cursor:pointer;">发送</button>';

  container.appendChild(titleBar);
  container.appendChild(msgs);
  container.appendChild(inputRow);
  document.body.appendChild(container);
  win.el = container;

  // === Drag logic ===
  var dragging = false, offsetX = 0, offsetY = 0;
  titleBar.addEventListener('mousedown', function(e) {
    if (e.target.closest('.ask-win-btn')) return;
    dragging = true;
    offsetX = e.clientX - container.offsetLeft;
    offsetY = e.clientY - container.offsetTop;
    container.style.cursor = 'grabbing';
    e.preventDefault();
  });
  document.addEventListener('mousemove', function(e) {
    if (!dragging) return;
    container.style.left = Math.max(0, e.clientX - offsetX) + 'px';
    container.style.top = Math.max(0, e.clientY - offsetY) + 'px';
  });
  document.addEventListener('mouseup', function() { dragging = false; container.style.cursor = ''; });

  // === Button handlers — use delegation so data-action swaps work repeatedly ===
  container.addEventListener('click', function(e) {
    var btn = e.target.closest('.ask-win-btn');
    if (!btn) return;
    e.stopPropagation();
    var action = btn.getAttribute('data-action');
    if (action === 'close') closeAskWindow(moduleName);
    else if (action === 'minimize') minimizeAskWindow(moduleName);
    else if (action === 'restore') restoreAskWindow(moduleName);
    else if (action === 'fullscreen') toggleFullscreenAskWindow(moduleName);
  });

  // === Send handler ===
  var sendFn = function() {
    var input = container.querySelector('.ask-win-input');
    var msgsEl = container.querySelector('.ask-win-messages');
    if (!input || !msgsEl) return;
    var q = input.value.trim();
    if (!q) return;
    input.value = '';
    win.messages.push({ role: 'user', content: q });
    msgsEl.innerHTML += '<div style="align-self:flex-end;background:#dcfce7;color:#166534;max-width:80%;padding:8px 12px;border-radius:12px 12px 4px 12px;font-size:13px;line-height:1.6;">' + q + '</div>';
    var loadingEl = document.createElement('div');
    loadingEl.style.cssText = 'align-self:flex-start;background:#f1f5f9;color:#9ca3af;max-width:80%;padding:8px 12px;border-radius:12px 12px 12px 4px;font-size:13px;';
    loadingEl.textContent = '分析中...';
    msgsEl.appendChild(loadingEl);
    msgsEl.scrollTop = msgsEl.scrollHeight;

    fetch('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, context_module: moduleName })
    })
    .then(function(r) { return r.json(); })
    .then(function(res) {
      loadingEl.remove();
      var answer = cleanText(res.answer || '暂无回答');
      var engineNote = res.engine ? '<div style="font-size:10px;color:#9ca3af;margin-top:4px;">引擎: ' + res.engine + '</div>' : '';
      win.messages.push({ role: 'assistant', content: answer });
      msgsEl.innerHTML += '<div style="align-self:flex-start;background:#f1f5f9;color:#334155;max-width:80%;padding:8px 12px;border-radius:12px 12px 12px 4px;font-size:13px;line-height:1.6;">' + answer + engineNote + '</div>';
      msgsEl.scrollTop = msgsEl.scrollHeight;
    })
    .catch(function() {
      loadingEl.remove();
      msgsEl.innerHTML += '<div style="align-self:flex-start;color:#ef4444;font-size:12px;">AI 服务暂不可用，请稍后重试</div>';
    });
  };
  container.querySelector('.ask-win-send').addEventListener('click', sendFn);
  container.querySelector('.ask-win-input').addEventListener('keydown', function(e) { if (e.key === 'Enter') sendFn(); });
  setTimeout(function() { var inp = container.querySelector('.ask-win-input'); if (inp) inp.focus(); }, 100);
}

function closeAskWindow(moduleName) {
  var win = chatWindows[moduleName];
  if (win && win.el) { win.el.remove(); win.el = null; }
  // Remove tab from tray when window is fully closed (x on tray tab or x on window title bar)
  removeTrayTab(moduleName);
  // If no more windows exist at all, remove the empty tray bar
  var hasAnyWindow = false;
  for (var k in chatWindows) {
    if (chatWindows[k] && chatWindows[k].el) { hasAnyWindow = true; break; }
  }
  if (!hasAnyWindow) {
    var tray = document.getElementById('ask-tray-bar');
    if (tray) tray.remove();
  }
}

// ===== Bottom tray bar — persistent, always visible, survives page switches =====
// Tray bar is created once on first minimize and NEVER removed (even when empty).
// It lives at document.body level (position:fixed), so page-section toggling cannot affect it.
function getTrayBar() {
  var tray = document.getElementById('ask-tray-bar');
  if (!tray) {
    tray = document.createElement('div');
    tray.id = 'ask-tray-bar';
    // Blue translucent — same style as AI analysis panel header
    tray.style.cssText = 'position:fixed;bottom:0;left:20px;display:flex;flex-direction:row;gap:4px;padding:4px 8px;background:rgba(219,234,254,0.95);backdrop-filter:blur(4px);border-top:1px solid #bfdbfe;border-right:1px solid #bfdbfe;border-radius:0 8px 0 0;z-index:99999;max-width:calc(100vw - 40px);overflow-x:auto;';
    document.body.appendChild(tray);
  }
  return tray;
}

function addTrayTab(moduleName) {
  var tray = getTrayBar();
  // If tab already exists, just update its state (don't duplicate)
  var existingTabId = 'ask-tray-' + moduleName.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, '_');
  var existingTab = document.getElementById(existingTabId);
  if (existingTab) {
    // Update indicator to show minimized state (white with blue border)
    existingTab.style.borderColor = '#60a5fa';
    existingTab.style.background = '#fff';
    existingTab.style.color = '#1e40af';
    return;
  }
  var tab = document.createElement('div');
  tab.id = existingTabId;
  // Minimized: white bg, blue border (matches AI panel theme)
  tab.style.cssText = 'display:flex;align-items:center;gap:6px;padding:4px 10px;background:#fff;border:1px solid #60a5fa;border-radius:6px;font-size:12px;color:#1e40af;cursor:pointer;white-space:nowrap;height:28px;transition:all 0.15s;';
  tab.innerHTML = '<span style="max-width:80px;overflow:hidden;text-overflow:ellipsis;">' + moduleName + '</span><button class="tray-close-btn" style="background:none;border:none;color:#93c5fd;font-size:14px;cursor:pointer;padding:0;line-height:1;" title="关闭窗口">&times;</button>';
  tab.addEventListener('click', function(e) {
    if (e.target.classList.contains('tray-close-btn')) return;
    restoreAskWindow(moduleName);
    // Update visual: show as active (blue bg)
    tab.style.borderColor = '#3b82f6';
    tab.style.background = '#dbeafe';
    tab.style.color = '#1e40af';
  });
  tab.querySelector('.tray-close-btn').addEventListener('click', function(e) {
    e.stopPropagation();
    closeAskWindow(moduleName);
  });
  tray.appendChild(tab);
}

function updateTrayTabActive(moduleName) {
  var tabId = 'ask-tray-' + moduleName.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, '_');
  var tab = document.getElementById(tabId);
  if (tab) {
    tab.style.borderColor = '#3b82f6';
    tab.style.background = '#dbeafe';
    tab.style.color = '#1e40af';
  }
}

function updateTrayTabMinimized(moduleName) {
  var tabId = 'ask-tray-' + moduleName.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, '_');
  var tab = document.getElementById(tabId);
  if (tab) {
    tab.style.borderColor = '#60a5fa';
    tab.style.background = '#fff';
    tab.style.color = '#1e40af';
  }
}

function removeTrayTab(moduleName) {
  var tabId = 'ask-tray-' + moduleName.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, '_');
  var tab = document.getElementById(tabId);
  if (tab) tab.remove();
  // Tray bar persists forever — never remove it even when empty.
  // This ensures minimized windows have a stable dock that survives page switches and scrolling.
}

function minimizeAskWindow(moduleName) {
  var win = chatWindows[moduleName];
  if (!win || !win.el) return;
  win.minimized = true;
  win.el.style.display = 'none';
  addTrayTab(moduleName);
  updateTrayTabMinimized(moduleName);
}

function restoreAskWindow(moduleName) {
  var win = chatWindows[moduleName];
  if (!win || !win.el) return;
  win.minimized = false;
  win.el.style.display = 'flex';
  win.el.style.zIndex = ++chatWindowZ;
  updateTrayTabActive(moduleName);
  // Keep tray tab visible — it acts as a persistent dock, user can close via the x on the tab.
}

function toggleFullscreenAskWindow(moduleName) {
  var win = chatWindows[moduleName];
  if (!win || !win.el) return;
  // If minimized, restore first then fullscreen
  if (win.minimized) restoreAskWindow(moduleName);
  win.fullscreen = !win.fullscreen;
  if (win.fullscreen) {
    win._savedRect = { top: win.el.style.top, left: win.el.style.left, width: win.el.style.width, height: win.el.style.height };
    win.el.style.top = '0';
    win.el.style.left = '0';
    win.el.style.width = '100vw';
    win.el.style.height = '100vh';
    win.el.style.borderRadius = '0';
    win.el.style.resize = 'none';
    win.el.style.zIndex = ++chatWindowZ;
  } else {
    var r = win._savedRect || { top: '60px', left: '300px', width: '420px', height: '520px' };
    win.el.style.top = r.top;
    win.el.style.left = r.left;
    win.el.style.width = r.width;
    win.el.style.height = r.height;
    win.el.style.borderRadius = '12px';
    win.el.style.resize = 'both';
  }
}

// R7: Bind "问" buttons to all panel titles
function bindAskButtons() {
  // In local mode, inject a style rule that hides ALL ask-btns permanently
  if (window._aiEnabled === false) {
    var styleId = 'ask-btn-hide-style';
    if (!document.getElementById(styleId)) {
      var style = document.createElement('style');
      style.id = styleId;
      style.textContent = '.ask-btn { display: none !important; }';
      document.head.appendChild(style);
    }
    // Also hide any already-existing buttons
    document.querySelectorAll('.ask-btn').forEach(function(b) { b.style.display = 'none'; });
    return;
  }
  // Fix 4: LLM mode — remove hide style and force-restore all ask buttons
  var hideStyle = document.getElementById('ask-btn-hide-style');
  if (hideStyle) hideStyle.remove();

  // Force restore display for any existing ask-btn that may have been hidden
  document.querySelectorAll('.ask-btn').forEach(function(b) {
    b.style.display = 'inline-flex';
  });

  function addAskButtons() {
    // Skip in local mode
    if (window._aiEnabled === false) return;
    document.querySelectorAll('.panel-title, .section-title').forEach(function(title) {
      if (title.querySelector('.ask-btn')) return;
      var text = title.textContent.trim();
      var cleanModule = text.replace(/^诊断\s*#\d+\s*·\s*/, '').replace(/^.*?·\s*/, '').trim();
      if (!cleanModule || cleanModule.length < 2) return;

      var btn = document.createElement('button');
      btn.className = 'ask-btn';
      btn.textContent = '问';
      btn.style.cssText = 'display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;border:1px solid #d1d5db;background:#fff;color:#6b7280;font-size:11px;font-weight:600;cursor:pointer;margin-left:6px;flex-shrink:0;transition:all 0.15s;';
      btn.title = '针对「' + cleanModule + '」提问';
      btn.addEventListener('mouseenter', function() { this.style.background = '#059669'; this.style.color = '#fff'; this.style.borderColor = '#059669'; });
      btn.addEventListener('mouseleave', function() { this.style.background = '#fff'; this.style.color = '#6b7280'; this.style.borderColor = '#d1d5db'; });
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        openAskWindow(cleanModule);
      });
      title.appendChild(btn);
    });
  }
  addAskButtons();
  // Fix 4: Retry once after a short delay to catch late-rendered DOM elements
  setTimeout(function() { addAskButtons(); }, 300);
  var observer = new MutationObserver(function() { addAskButtons(); });
  observer.observe(document.body, { childList: true, subtree: true });
}

// ---- INIT ----
document.addEventListener('DOMContentLoaded', function() {
  // Single mode toggle button in breadcrumb
  var modeBtn = document.getElementById('page-mode-toggle');
  if (modeBtn) {
    modeBtn.addEventListener('click', function() {
      var newState = window._aiEnabled === false;
      modeBtn.disabled = true;
      modeBtn.textContent = '切换中...';
      fetch('/api/ai-config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: newState }) })
        .then(function(r) { return r.json(); })
        .then(function(res) {
          window._aiEnabled = res.ai_enabled;
          updateModeToggleUI();
          loadAll().then(renderAll);
        })
        .catch(function() { updateModeToggleUI(); });
    });
  }

  // Fetch AI config first, then init UI
  fetch('/api/ai-config').then(function(r) { return r.json(); }).then(function(res) {
    window._aiEnabled = res.ai_enabled;
    updateModeToggleUI();
    bindPageRouting();
    bindGlobalClicks();
    bindExportHandlers();
    bindChatEvents();
    bindDatePicker();
    bindUpload();
    bindScheduler();
    bindHoverAnalysis();
    bindAskButtons();
    loadAll().then(renderAll);
  }).catch(function() {
    window._aiEnabled = false;
    bindPageRouting();
    bindGlobalClicks();
    bindExportHandlers();
    bindChatEvents();
    bindDatePicker();
    bindUpload();
    bindScheduler();
    bindHoverAnalysis();
    bindAskButtons();
    loadAll().then(renderAll);
  });
});

function updateModeToggleUI() {
  var btn = document.getElementById('btn-ai-mode-toggle');
  // Update single page-mode toggle button (next to breadcrumb)
  var btn = document.getElementById('page-mode-toggle');
  if (btn) {
    if (window._aiEnabled === false) {
      btn.textContent = '本地模式';
      btn.style.borderColor = '#9ca3af';
      btn.style.color = '#6b7280';
    } else {
      btn.textContent = 'LLM 模式';
      btn.style.borderColor = '#3b82f6';
      btn.style.color = '#1e40af';
    }
    btn.disabled = false;
  }
  updateAiVisibility();
  updateInsightPageLock();
  updateSmartAnalysisPanel(true);
  bindAskButtons();
  // Fix 4: Retry after DOM settles
  setTimeout(function() { bindAskButtons(); }, 500);
}

// Issue 2: Lock insight page in local mode
function updateInsightPageLock() {
  var page = document.getElementById('page-insight');
  if (!page) return;
  var lockOverlay = page.querySelector('.insight-lock-overlay');
  if (window._aiEnabled === false) {
    if (!lockOverlay) {
      page.style.position = 'relative';
      lockOverlay = document.createElement('div');
      lockOverlay.className = 'insight-lock-overlay';
      lockOverlay.style.cssText = 'position:absolute;inset:0;background:#ffffff;display:flex;align-items:center;justify-content:center;z-index:10;border-radius:8px;';
      lockOverlay.innerHTML = '<div style="text-align:center;color:#64748b;font-size:14px;line-height:1.8;">智能诊室为 LLM 模式专属功能<br><span style="font-size:12px;color:#94a3b8;">请点击左上角模式切换按钮后使用</span></div>';
      page.appendChild(lockOverlay);
    }
  } else {
    if (lockOverlay) lockOverlay.remove();
  }
}
