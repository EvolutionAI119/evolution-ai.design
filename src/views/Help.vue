<template>
  <div class="help-page">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div>
        <h2>{{ pick(ui.title) }}</h2>
        <p class="subtitle">{{ pick(ui.subtitle) }}</p>
      </div>
      <div class="header-stats">
        <div class="stat"><b>{{ docs.length }}</b><span>{{ pick(ui.documents) }}</span></div>
        <div class="stat"><b>{{ categories.length }}</b><span>{{ pick(ui.layers) }}</span></div>
        <div class="stat"><b>{{ manualModules.length }}</b><span>{{ pick(ui.modules) }}</span></div>
      </div>
    </div>

    <!-- 标签切换 -->
    <div class="tabs">
      <div
        v-for="tab in tabs"
        :key="tab.key"
        class="tab"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >{{ pick(tab.label) }}</div>
    </div>

    <!-- ============ 3D 知识图谱 ============ -->
    <div v-show="activeTab === 'graph'" class="tab-panel graph-panel">
      <div class="graph-stage">
        <div ref="canvasRef" class="three-canvas"></div>
        <div class="graph-hint">
          <button v-if="graphMode === 'chapters'" class="mini-btn back-btn" @click="exitChapters">
            ← {{ pick(ui.backToOverview) }}
          </button>
          <span v-if="drillDoc" class="drill-chip" :style="{ color: drillDoc._color, borderColor: drillDoc._color + '88' }">
            {{ pick(drillDoc.title) }}
          </span>
          <span>{{ graphMode === 'chapters' ? pick(ui.hintChapters) : pick(ui.hint) }}</span>
          <button class="mini-btn" @click="resetCamera">{{ pick(ui.resetView) }}</button>
          <button v-if="graphMode === 'overview'" class="mini-btn" @click="toggleAutoRotate" :class="{ active: autoRotate }">
            {{ autoRotate ? pick(ui.stopRotate) : pick(ui.autoRotate) }}
          </button>
        </div>
        <div v-show="graphMode === 'overview'" class="legend">
          <div class="legend-title">{{ pick(ui.legend) }}</div>
          <div class="legend-item" v-for="c in categories" :key="c.id">
            <span class="dot" :style="{ background: c.color }"></span>
            <span>{{ pick(c.label) }}</span>
          </div>
        </div>
      </div>

      <!-- 节点详情面板 -->
      <aside class="detail-panel" v-if="selectedDoc">
        <div class="detail-header">
          <h3>{{ pick(selectedDoc.title) }}</h3>
          <button class="close-btn" @click="selectedDoc = null">✕</button>
        </div>
        <div class="detail-meta">
          <span class="badge" :style="{ background: selectedDoc._color + '22', color: selectedDoc._color }">
            {{ pick(categories.find(c => c.id === selectedDoc._categoryId).label) }}
          </span>
          <span class="meta-item">{{ selectedDoc.date || '—' }}</span>
        </div>
        <p class="detail-summary">{{ pick(selectedDoc.summary) }}</p>
        <!-- 文档始终以 HTML 内联呈现，不提供文件类型选择 -->
        <div class="detail-content">
          <div v-if="loadingContent" class="loading">{{ pick(ui.loading) }}</div>
          <div v-else class="markdown-body" v-html="renderedContent"></div>
        </div>
      </aside>
      <aside class="detail-panel empty-panel" v-else>
        <h3>{{ pick(ui.selectHint) }}</h3>
        <p>{{ pick(ui.selectHintDesc) }}</p>
        <ul class="doc-list">
          <li v-for="d in docs" :key="d.id" @click="selectDoc(d)">
            <span class="dot" :style="{ background: d._color }"></span>
            {{ pick(d.title) }}
          </li>
        </ul>
      </aside>
    </div>

    <!-- ============ 使用手册 ============ -->
    <div v-show="activeTab === 'manual'" class="tab-panel manual-panel">
      <div class="manual-intro">
        <h3>{{ pick(ui.manualTitle) }}</h3>
        <p>{{ pick(ui.manualIntro) }}</p>
      </div>

      <!-- 上区：理论闭环 | 实践指南 并排各占 50%；下区：模块手册 5 列 × 2 行 -->
      <div class="manual-body">
        <div class="manual-top">
          <div class="cycle-section">
            <div class="cycle-title">{{ pick(ui.cycleTitle) }}</div>
            <div class="cycle-desc">{{ pick(ui.cycleDesc) }}</div>
            <div class="cycle-diagram">
              <svg class="cycle-svg" viewBox="0 0 520 330" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <defs>
              <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#64748b" />
              </marker>
            </defs>
            <!-- 中心平台 -->
            <circle cx="260" cy="165" r="42" fill="url(#centerGrad)" opacity="0.15" />
            <defs>
              <radialGradient id="centerGrad">
                <stop offset="0%" stop-color="#4ade80" />
                <stop offset="100%" stop-color="#0ea5e9" />
              </radialGradient>
            </defs>
            <!-- 5 个节点：按顺时针排列于椭圆 -->
            <g v-for="(s, i) in cycleSteps" :key="s.id">
              <circle :cx="cyclePos(i).x" :cy="cyclePos(i).y" r="34" :fill="s.color" opacity="0.18" />
              <circle :cx="cyclePos(i).x" :cy="cyclePos(i).y" r="28" :fill="s.color" opacity="0.9" />
              <text :x="cyclePos(i).x" :y="cyclePos(i).y + 6" text-anchor="middle" font-size="20">{{ s.icon }}</text>
              <text :x="cyclePos(i).x" :y="cyclePos(i).y - 42" text-anchor="middle" font-size="12" font-weight="700" fill="var(--text-primary)">{{ pick(s.title) }}</text>
              <text :x="cyclePos(i).x" :y="cyclePos(i).y + 50" text-anchor="middle" font-size="9.5" fill="var(--text-muted)">{{ pick(s.desc) }}</text>
            </g>
            <!-- 连线箭头 -->
            <g v-for="(s, i) in cycleSteps" :key="'e'+s.id">
              <line
                :x1="cyclePos(i).x" :y1="cyclePos(i).y"
                :x2="cyclePos((i+1)%cycleSteps.length).x" :y2="cyclePos((i+1)%cycleSteps.length).y"
                stroke="#64748b" stroke-width="1.5" stroke-dasharray="4 3"
                marker-end="url(#arrowhead)" opacity="0.5" />
            </g>
          </svg>
            </div>
          </div>

          <!-- 实践指南：理论→行动映射 -->
          <div class="practice-guide">
            <h3 class="pg-title">{{ pick(ui.practiceTitle) }}</h3>
            <p class="pg-sub">{{ pick(ui.practiceSub) }}</p>
            <div class="pg-grid">
              <div class="pg-card" v-for="pg in practiceGuide" :key="pg.id">
                <div class="pg-icon">{{ pg.icon }}</div>
                <div class="pg-body">
                  <b class="pg-theory">{{ pick(pg.theory) }}</b>
                  <span class="pg-arrow">→</span>
                  <span class="pg-action">{{ pick(pg.action) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 下区：模块手册网格（点击卡片跳转到对应模块页面） -->
        <div class="module-grid">
        <div class="module-card" v-for="m in manualModules" :key="m.id" :style="{ '--accent': m.accent }"
             @click="goModule(m)" :title="pick(ui.openModule)">
          <div class="module-head">
            <span class="module-icon">{{ m.icon }}</span>
            <h4>{{ pick(m.name) }}</h4>
            <span class="module-path">{{ m.path }}</span>
            <span class="module-enter">→</span>
          </div>
          <p class="module-desc">{{ pick(m.description) }}</p>
          <!-- 模块迷你流程图 -->
          <div class="module-flow" v-if="m.flow && m.flow.length">
            <div class="flow-steps">
              <template v-for="(step, i) in m.flow" :key="i">
                <div class="flow-step" :style="{ background: 'var(--accent)' }">
                  <span class="flow-idx">{{ i + 1 }}</span>
                  <span class="flow-label">{{ pick(step) }}</span>
                </div>
                <div class="flow-arrow" v-if="i < m.flow.length - 1">→</div>
              </template>
            </div>
          </div>
          <div class="module-features">
            <div class="feature" v-for="(f, i) in pick(m.features)" :key="i">
              <span class="feat-bullet">▸</span>
              <span>{{ f }}</span>
            </div>
          </div>
          <div class="module-tip" v-if="m.tip">
            <b>💡 {{ pick(ui.tip) }}:</b> {{ pick(m.tip) }}
          </div>
        </div>
      </div>
      </div>
    </div>

    <!-- ============ 文档体系 ============ -->
    <div v-show="activeTab === 'system'" class="tab-panel system-panel">
      <div class="system-intro">
        <h3>{{ pick(ui.systemTitle) }}</h3>
        <p>{{ pick(ui.systemIntro) }}</p>
      </div>
      <div class="layer-flow">
        <div class="layer-arrow" v-for="(c, i) in categories" :key="c.id" :style="{ '--c': c.color }">
          <div class="layer-num">L{{ i + 1 }}</div>
          <div class="layer-body">
            <div class="layer-name">{{ pick(c.label) }}</div>
            <div class="layer-desc">{{ pick(c.desc) }}</div>
            <div class="layer-docs">
              <span class="chip" v-for="d in docs.filter(x => x.category === c.id)" :key="d.id"
                    @click="activeTab='graph'; selectDoc(d)">
                {{ pick(d.title) }}
              </span>
            </div>
          </div>
        </div>
      </div>
      <div class="principle-row">
        <div class="principle" v-for="p in principles" :key="p.title.en">
          <b>{{ pick(p.title) }}</b>
          <span>{{ pick(p.desc) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import MarkdownIt from 'markdown-it'
import * as markdownItEmoji from 'markdown-it-emoji'

const { locale } = useI18n({ useScope: 'global' })

// 根据平台整体语言选择文本（英文为基础，中文为对应翻译）
const pick = (obj) => {
  if (!obj || typeof obj !== 'object') return obj
  const l = locale.value === 'zh' ? 'zh' : 'en'
  return obj[l] != null ? obj[l] : obj.en
}

// ---------------- Data: knowledge categories ----------------
const categories = [
  { id: 'philosophy', color: '#a78bfa',
    label: { en: 'Philosophy & Methodology', zh: '哲学与方法论' },
    desc: { en: 'Answers "why": design philosophy, meta-theory, and methodology form the root of the knowledge base.',
            zh: '回答"为什么"：设计哲学、元理论与方法论，构成知识底座的根脉。' } },
  { id: 'strategy', color: '#f472b6',
    label: { en: 'Strategy & Academic', zh: '战略与学术' },
    desc: { en: 'Answers "what": the technical whitepaper positions platform value; the English paper captures methodological contributions.',
            zh: '回答"是什么"：技术白皮书定位平台价值，英文学术论文沉淀方法学贡献。' } },
  { id: 'arch', color: '#38bdf8',
    label: { en: 'Architecture & API', zh: '架构与接口' },
    desc: { en: 'Answers "how": five-layer architecture, 118 endpoints, product spec, and the Bayesian optimization module.',
            zh: '回答"怎么搭"：五层架构、118 端点 API、产品规格与贝叶斯优化模块。' } },
  { id: 'quality', color: '#34d399',
    label: { en: 'Quality & Validation', zh: '质量与验证' },
    desc: { en: 'Answers "is it reliable": 489-case test baseline, Class-A grading, audit and platform test records.',
            zh: '回答"可不可靠"：489 测试基线、A 级分级、审计与平台测试记录。' } }
]

// ---------------- Data: knowledge documents ----------------
const docs = [
  { id: 'design_philosophy', category: 'philosophy', file: 'design_philosophy.md', date: 'v4.0 · 2026-09-27',
    title: { en: 'Design Philosophy', zh: '设计哲学' },
    summary: { en: 'The Form–Logic–Mathematics framework and the cross-civilization roots of Observe–Constrain–Generate–Evolve, defining the ontological stance of AI-era automotive design.',
               zh: '形·理·数技术框架与"观象·法地·成器·制变"跨文明哲学根基，定义 AI 时代造型设计的本体立场。' } },
  { id: 'design_meta_theory', category: 'philosophy', file: 'design_meta_theory.md', date: '2026-09-27',
    title: { en: 'Design Meta-Theory', zh: '设计元理论' },
    summary: { en: "Love's nine-layer framework and the ten-dimension autonomous knowledge system — an extended meta-theory for Chinese automotive styling design.",
               zh: 'Love 九层框架与十维度自主知识体系，中国汽车造型设计的元理论扩展。' } },
  { id: 'methodology', category: 'philosophy', file: 'methodology.md', date: 'v1.2 · 2026-09-27',
    title: { en: 'Development Methodology', zh: '开发方法论' },
    summary: { en: 'A five-dimension methodology, four SOPs, and a maturity checklist that turn platform capabilities into executable workflows.',
               zh: '五维度方法论、四套 SOP 与成熟度自检，把平台能力转化为可执行流程。' } },
  { id: 'whitepaper', category: 'strategy', file: 'whitepaper.md', date: 'v1.2 · 2026-09-27',
    title: { en: 'Technical Whitepaper', zh: '技术白皮书' },
    summary: { en: 'Platform positioning, core capabilities, architecture & deployment, trust baseline, and evolution roadmap — for R&D decision-makers.',
               zh: '平台定位、核心能力、架构部署、可信基线与演进路线，面向研发管理者。' } },
  { id: 'paper', category: 'strategy', file: 'EVOLUTION_AI_paper.md', date: '2026',
    title: { en: 'Academic Paper (EN)', zh: '英文学术论文' },
    summary: { en: 'An academic treatment of Bayesian optimization + NURBS Class-A surfaces + DL/LLM fusion + end-to-end integration.',
               zh: '贝叶斯优化 + NURBS A 级曲面 + DL/LLM 融合 + 端到端集成的学术化论述。' } },
  { id: 'arch', category: 'arch', file: 'ARCHITECTURE_DESIGN.md', date: '2026',
    title: { en: 'Architecture Design', zh: '架构设计' },
    summary: { en: 'Five-layer architecture, 16 route modules, 11 ORM tables, four key data flows, and deployment topology.',
               zh: '五层分层架构、16 路由模块、11 张 ORM 表、四条关键数据流与部署。' } },
  { id: 'api', category: 'arch', file: 'api_reference.md', date: '2026',
    title: { en: 'API Reference', zh: 'API 参考' },
    summary: { en: 'All 118 endpoints listed with method, path, function, and authentication markers.',
               zh: '全部 118 端点逐端明细表，含方法、路径、功能与认证标记。' } },
  { id: 'product', category: 'arch', file: 'PRODUCT_SPEC.md', date: '2026',
    title: { en: 'Product Specification', zh: '产品功能定义' },
    summary: { en: 'User roles, the 11-page feature set, and the capability matrix — aligned with real API calls.',
               zh: '用户角色、11 页面功能与能力矩阵，对齐真实接口调用。' } },
  { id: 'bayes', category: 'arch', file: 'bayes_optimization.md', date: '2026',
    title: { en: 'Bayesian Optimization', zh: '贝叶斯优化模块' },
    summary: { en: 'RBF-GP + EI/UCB surrogate optimization container, and the bridge from observations to training samples.',
               zh: 'RBF-GP + EI/UCB 代理寻优容器，观测样本与训练模块的桥接机制。' } },
  { id: 'integration_flow', category: 'arch', file: 'MODULE_INTEGRATION_FLOW.md', date: 'v1.0 · 2026-09-27',
    title: { en: 'Module Integration Flow', zh: '模块集成流程' },
    summary: { en: 'Login auth → Token-based training → workflow review: cross-module data contracts, API specs, and the ownership-checked review state machine.',
               zh: '登录认证 → Token 训练 → 工作流审核：跨模块数据契约、接口规范与归属校验的审核状态机。' } },
  { id: 'validation', category: 'quality', file: 'VALIDATION_REPORT_20260927.md', date: '2026-09-27',
    title: { en: 'Validation Report', zh: '验证报告' },
    summary: { en: '489 cases all green, 15-round Bayesian convergence, Class-A quality measurements, and fact-baseline reconciliation.',
               zh: '489 用例全绿、贝叶斯 15 轮收敛、A 级质量测量与事实基线核对。' } },
  { id: 'audit', category: 'quality', file: 'AUDIT_REPORT_20260810.md', date: '2026-08-10',
    title: { en: 'Audit Report', zh: '审计报告' },
    summary: { en: 'Historical audit baseline — the starting point of the platform consistency and quality evidence chain.',
               zh: '历史审计基线，平台一致性与质量证据链的起点。' } },
  { id: 'platform_test', category: 'quality', file: 'PLATFORM_TEST_REPORT_20260811.md', date: '2026-08-11',
    title: { en: 'Platform Test Report', zh: '平台测试报告' },
    summary: { en: 'Historical platform test records that, together with the latest validation report, form the quality evidence chain.',
               zh: '历史平台测试记录，与最新验证报告衔接构成质量证据链。' } }
]

// 为每个文档注入颜色
docs.forEach(d => {
  const c = categories.find(x => x.id === d.category)
  d._color = c.color
  d._categoryId = c.id
})

// ---------------- 数据：知识底座关系（四类语义连接） ----------------
// core     = 平台核心 → 各层锚点（中枢神经）
// intra    = 同层文档协同（层内连接）
// flow     = 层间知识推演（L1→L2→L3→L4 主干）
// feedback = 质量证据 → 哲学根基（持续进化的闭环回路）
const graphEdges = [
  // 中枢 → 四层锚点
  { a: 'core', b: 'design_philosophy', type: 'core' },
  { a: 'core', b: 'whitepaper', type: 'core' },
  { a: 'core', b: 'arch', type: 'core' },
  { a: 'core', b: 'validation', type: 'core' },
  // L1 哲学层：设计哲学为根，元理论与开发方法论皆由此生发（三角结构）
  { a: 'design_philosophy', b: 'design_meta_theory', type: 'intra' },
  { a: 'design_philosophy', b: 'methodology', type: 'intra' },
  { a: 'design_meta_theory', b: 'methodology', type: 'intra' },
  // L2 战略层：白皮书与学术论文互证
  { a: 'whitepaper', b: 'paper', type: 'intra' },
  // L3 架构层：架构设计为枢纽，API 逐端承接产品功能定义，贝叶斯为内置能力
  { a: 'arch', b: 'api', type: 'intra' },
  { a: 'arch', b: 'product', type: 'intra' },
  { a: 'arch', b: 'bayes', type: 'intra' },
  { a: 'api', b: 'product', type: 'intra' },
  // 集成流程报告承接架构设计与 API 参考（跨模块链路落地文档）
  { a: 'arch', b: 'integration_flow', type: 'intra' },
  { a: 'api', b: 'integration_flow', type: 'intra' },
  // L4 质量层：验证报告总摄，审计基线与平台测试构成完整证据链
  { a: 'validation', b: 'audit', type: 'intra' },
  { a: 'validation', b: 'platform_test', type: 'intra' },
  { a: 'audit', b: 'platform_test', type: 'intra' },
  // 层间推演主干：方法论 → 白皮书 → 架构；学术方法 → 贝叶斯；贝叶斯/产品 → 验证
  { a: 'methodology', b: 'whitepaper', type: 'flow' },
  { a: 'whitepaper', b: 'arch', type: 'flow' },
  { a: 'paper', b: 'bayes', type: 'flow' },
  { a: 'bayes', b: 'validation', type: 'flow' },
  { a: 'product', b: 'validation', type: 'flow' },
  // 闭环：质量证据回流哲学根基，理论在验证中持续进化
  { a: 'validation', b: 'design_philosophy', type: 'feedback' }
]

// ---------------- 数据：四层知识底座布局 ----------------
// 哲学为底座（最下层大环），逐层收敛上升，质量证据居顶——知识金字塔；
// 各层 angleOff 统一（锚点方位一致），四层锚点连成贯穿金字塔的知识脊柱
const LAYER_CFG = {
  philosophy: { y: -4.2, r: 12.5, angleOff: Math.PI / 2 },
  strategy:   { y: -1.4, r: 10.5, angleOff: Math.PI / 2 },
  arch:       { y:  1.4, r: 8.5,  angleOff: Math.PI / 2 },
  quality:    { y:  4.2, r: 6.5,  angleOff: Math.PI / 2 }
}

// ---------------- Data: 理论→实践→机器学习→反馈→改进 闭环 ----------------
const cycleSteps = [
  { id: 'theory', icon: '📖', color: '#a78bfa',
    title: { en: 'Theory', zh: '理论' },
    desc: { en: 'Philosophy & methodology', zh: '哲学与方法论' } },
  { id: 'practice', icon: '🛠️', color: '#38bdf8',
    title: { en: 'Practice', zh: '实践' },
    desc: { en: 'Parametric design', zh: '参数化设计' } },
  { id: 'ml', icon: '🧠', color: '#f472b6',
    title: { en: 'ML Training', zh: '机器学习' },
    desc: { en: 'Train on observations', zh: '观测样本训练' } },
  { id: 'feedback', icon: '🔄', color: '#fbbf24',
    title: { en: 'Feedback', zh: '反馈' },
    desc: { en: 'Quality → Bayesian', zh: '质量回流贝叶斯' } },
  { id: 'improve', icon: '🚀', color: '#34d399',
    title: { en: 'Improve', zh: '改进理论' },
    desc: { en: 'Practice refines theory', zh: '实践反哺理论' } }
]
// 在椭圆上均匀分布 5 个节点（顺时针）
const cyclePos = (i) => {
  const cx = 260, cy = 165, rx = 190, ry = 100
  // 从顶部开始，顺时针
  const angle = -Math.PI / 2 + (i * 2 * Math.PI / cycleSteps.length)
  return { x: cx + rx * Math.cos(angle), y: cy + ry * Math.sin(angle) }
}

// ---------------- Data: platform module user manual ----------------
const manualModules = [
  { id: 'dashboard', icon: '📊', path: '/', accent: '#38bdf8',
    name: { en: 'Dashboard', zh: '仪表盘' },
    description: { en: 'Platform overview entry, showing core stats and trends for projects, models, and reports.',
                   zh: '平台总览入口，展示项目、模型、报告等核心统计与趋势。' },
    flow: [{ en: 'Open page', zh: '打开页面' }, { en: 'Scan KPIs', zh: '浏览指标' }, { en: 'Spot anomaly', zh: '发现异常' }, { en: 'Drill in', zh: '下钻详情' }],
    features: { en: ['View total projects, model count, check reports, pass rate', 'Project status distribution and quality-score trend charts', 'Recent project shortcuts and system status'],
                zh: ['查看项目总数、模型数量、检查报告数、合格率', '项目状态分布与质量评分趋势图', '最近项目快捷入口与系统状态'] },
    tip: { en: 'The dashboard is the first view of global state; abnormal metrics are highlighted here.',
           zh: '仪表盘是全局状态的第一视角，异常指标会在此突出显示。' } },
  { id: 'designer', icon: '🎨', path: '/designer', accent: '#a78bfa',
    name: { en: 'AI Designer', zh: 'AI 设计器' },
    description: { en: 'The core parametric styling workbench — from parameters to a 3D full vehicle.',
                   zh: '参数化造型设计核心工作台，从参数到 3D 整车。' },
    flow: [{ en: 'Set params', zh: '设定参数' }, { en: '3D preview', zh: '3D 预览' }, { en: 'Optimize', zh: '优化' }, { en: 'Save variant', zh: '保存变体' }],
    features: { en: ['22-dimension CarParams panel with boundary validation', 'Real-time 3D vehicle preview and part switching', 'Cloud batch generation, evaluation, optimization, and variant saving'],
                zh: ['22 维 CarParams 参数面板，支持边界校验', '实时 3D 整车预览与部件切换', '云端批次生成、评估、优化与变体保存'] },
    tip: { en: 'Freeze hard points (size/proportion) first, then adjust local styling — optimization is far more effective.',
           zh: '先冻结硬点（尺寸/比例），再做局部造型调整，优化效果更显著。' } },
  { id: 'projects', icon: '📁', path: '/projects', accent: '#34d399',
    name: { en: 'Projects', zh: '项目管理' },
    description: { en: 'Create, query, and manage project status (with mock fallback).',
                   zh: '项目的创建、查询与状态管理（含 mock 兜底）。' },
    flow: [{ en: 'Create', zh: '创建' }, { en: 'Filter', zh: '筛选' }, { en: 'Open detail', zh: '进入详情' }],
    features: { en: ['Project CRUD and status filtering', 'Search by name or status', 'Enter project detail to manage models and workflows'],
                zh: ['项目 CRUD 与状态过滤', '按名称/状态搜索', '进入项目详情管理模型与工作流'] } },
  { id: 'project_detail', icon: '🗂️', path: '/projects/:id', accent: '#22d3ee',
    name: { en: 'Project Detail', zh: '项目详情' },
    description: { en: 'Manage model files, workflow steps, and model variants for a single project.',
                   zh: '单个项目的模型文件、工作流步骤与模型变体管理。' },
    flow: [{ en: 'Upload model', zh: '上传模型' }, { en: 'Track steps', zh: '跟踪步骤' }, { en: 'Compare variants', zh: '对比变体' }],
    features: { en: ['Model file upload and version management', 'Workflow step tracking and execution', 'Model variant comparison and parameter traceability'],
                zh: ['模型文件上传与版本管理', '工作流步骤跟踪与执行', '模型变体对比与参数回溯'] } },
  { id: 'deep_learning', icon: '🧠', path: '/deep-learning', accent: '#f472b6',
    name: { en: 'Deep Learning', zh: '深度学习设计器' },
    description: { en: 'Generative design, training tasks, and Bayesian optimization linkage.',
                   zh: '生成式设计、训练任务与贝叶斯优化联动。' },
    flow: [{ en: 'Train model', zh: '训练模型' }, { en: 'Generate', zh: '生成' }, { en: 'Bayesian opt', zh: '贝叶斯优化' }, { en: 'Export data', zh: '导出数据' }],
    features: { en: ['Create and poll PyTorch training tasks', 'Generative design sample batches', 'Bayesian optimization sessions and sample export'],
                zh: ['创建/轮询 PyTorch 训练任务', '生成式设计样本批次', '贝叶斯优化会话与样本导出'] },
    tip: { en: 'Bayesian observations can be exported in training format, letting real data gradually replace synthetic samples.',
           zh: '贝叶斯观测样本可导出为训练格式，让真实数据逐步替代合成样本。' } },
  { id: 'quality', icon: '✅', path: '/quality', accent: '#4ade80',
    name: { en: 'Quality', zh: '质量检查' },
    description: { en: 'Class-A surface quality assessment and historical report lookup.',
                   zh: 'A 级曲面质量评估与历史报告查询。' },
    flow: [{ en: 'Select model', zh: '选择模型' }, { en: 'Run check', zh: '执行检查' }, { en: 'View grade', zh: '查看等级' }],
    features: { en: ['G0/G1/G2 continuity grading (5°/2° thresholds)', 'Reflection-line score and A/B/C/D overall grade', 'Historical quality report search and comparison'],
                zh: ['G0/G1/G2 连续性分级（5°/2° 阈值）', '反射线评分与 A/B/C/D 综合等级', '历史质量报告检索与对比'] } },
  { id: 'deliver', icon: '📦', path: '/deliver', accent: '#fbbf24',
    name: { en: 'Deliver', zh: '数据交付' },
    description: { en: 'CAD import, parameter editing, and multi-format engineering export.',
                   zh: 'CAD 导入改参与多格式工程导出。' },
    flow: [{ en: 'Import CAD', zh: '导入 CAD' }, { en: 'Edit params', zh: '改参' }, { en: 'Export', zh: '导出' }],
    features: { en: ['STEP/IGES/GLB and other format import', 'Parameter parsing and edit-preview', 'Multi-format export download and archiving'],
                zh: ['STEP/IGES/GLB 等格式导入', '参数解析与改参预览', '多格式导出下载与归档'] } },
  { id: 'demo', icon: '🎬', path: '/demo', accent: '#fb923c',
    name: { en: 'DEMO', zh: 'DEMO 演示' },
    description: { en: 'Vehicle showcase and animated demonstration of the NURBS surface generation process.',
                   zh: '车型展示与 NURBS 曲面生成过程的动效演示。' },
    flow: [{ en: 'Pick model', zh: '选择车型' }, { en: 'Play seq', zh: '播放序列' }, { en: 'Record', zh: '录制' }],
    features: { en: ['Full-vehicle styling and surface generation sequence visualization', 'Automated demo and manual control', 'Demo video recording and download'],
                zh: ['整车造型与曲面生成序列可视化', '自动演示与手动控制', '演示视频录制与下载'] } },
  { id: 'account', icon: '👤', path: '/account', accent: '#94a3b8',
    name: { en: 'Account', zh: '账户设置' },
    description: { en: 'Personal info and API Key management for each LLM provider.',
                   zh: '个人信息与各 LLM 提供商 API Key 管理。' },
    flow: [{ en: 'Edit profile', zh: '编辑资料' }, { en: 'Set keys', zh: '配置 Key' }, { en: 'Check status', zh: '检查状态' }],
    features: { en: ['View and edit user information', 'Configure keys for 7 LLM providers (Fernet-encrypted)', 'Check provider availability status'],
                zh: ['用户信息查看与修改', '7 个 LLM 提供商 Key 配置（Fernet 加密）', '提供商可用性状态查看'] } },
  { id: 'help', icon: '❓', path: '/help', accent: '#60a5fa',
    name: { en: 'Help Center', zh: '帮助中心' },
    description: { en: '3D knowledge graph, module usage manual, and documentation system overview (this page).',
                   zh: '知识库 3D 图谱、模块使用手册与文档体系总览（本页）。' },
    flow: [{ en: 'Browse graph', zh: '浏览图谱' }, { en: 'Read manual', zh: '阅读手册' }, { en: 'Practice', zh: '动手实践' }],
    features: { en: ['Interactive 3D knowledge graph browsing', 'Feature usage guide for each module', 'Documentation system layering and principles'],
                zh: ['3D 知识图谱交互浏览', '各模块功能使用介绍', '文档体系分层与原则说明'] } }
]

// ---------------- Data: engineering principles ----------------
const principles = [
  { title: { en: 'Signal First', zh: '信号优先' },
    desc: { en: 'When a dependency is missing, report unavailable explicitly — never fabricate metrics.',
            zh: '依赖缺失显式报不可用，绝不返回编造指标。' } },
  { title: { en: 'Thin Orchestration', zh: '薄壳编排' },
    desc: { en: 'The web layer only orchestrates and persists; capabilities live in the algorithm package.',
            zh: 'Web 层只做编排与持久化，能力沉淀在算法包。' } },
  { title: { en: 'Full Auditability', zh: '全链路可审计' },
    desc: { en: 'Parameters, samples, scores, variants, and tasks are all traceable and rollbackable.',
            zh: '参数、样本、评分、变体、任务均可追溯可回滚。' } }
]

// ---------------- Data: 实践指南（理论→行动映射） ----------------
const practiceGuide = [
  { id: 'pg1', icon: '🎯',
    theory: { en: '"Freeze hard points first"', zh: '"先冻结硬点"' },
    action: { en: 'In AI Designer, lock size/proportion params before local styling tweaks',
              zh: '在 AI 设计器中先锁定尺寸/比例参数，再调整局部造型' } },
  { id: 'pg2', icon: '📐',
    theory: { en: '"Form–Logic–Mathematics"', zh: '"形·理·数"' },
    action: { en: 'For each design: set aesthetic form → verify engineering logic → confirm mathematical continuity',
              zh: '每次设计：定美学形态 → 验工程约束 → 确认数学连续性' } },
  { id: 'pg3', icon: '🔬',
    theory: { en: '"Signal, never simulate"', zh: '"有信号，不模拟"' },
    action: { en: 'If a module shows unavailable, do not force it — switch to an available path or report it',
              zh: '模块显示不可用时不要强用，切换到可用路径或反馈问题' } },
  { id: 'pg4', icon: '🔄',
    theory: { en: '"Feedback closes the loop"', zh: '"反馈闭环"' },
    action: { en: 'After quality check, export observations to Deep Learning for the next training round',
              zh: '质量检查后，将观测样本导出到深度学习用于下一轮训练' } },
  { id: 'pg5', icon: '🧬',
    theory: { en: '"Brand genes grow, not stack"', zh: '"基因生长，非堆砌"' },
    action: { en: 'Reference brand benchmark models in the designer instead of copying surface elements',
              zh: '在设计器中参考品牌基准车型，而非直接复制表面元素' } },
  { id: 'pg6', icon: '🛡️',
    theory: { en: '"Full auditability"', zh: '"全链路可审计"' },
    action: { en: 'Always save variants with parameter traces so any result can be reproduced',
              zh: '始终保存带参数回溯的变体，确保任何结果可复现' } }
]

const tabs = [
  { key: 'graph', label: { en: '3D Knowledge Graph', zh: '3D 知识图谱' } },
  { key: 'manual', label: { en: 'Module Manual', zh: '模块使用手册' } },
  { key: 'system', label: { en: 'Doc System', zh: '文档体系' } }
]

// ---------------- UI 静态文案（跟随平台整体语言切换） ----------------
const ui = {
  title: { en: 'Help Center · Knowledge Base', zh: '帮助中心 · 知识库' },
  subtitle: { en: '3D knowledge graph · module manual · documentation system',
              zh: '3D 知识图谱 · 模块手册 · 文档体系' },
  documents: { en: 'Documents', zh: '文档' },
  layers: { en: 'Layers', zh: '层级' },
  modules: { en: 'Modules', zh: '模块' },
  hint: { en: '🖱️ Drag to rotate · Scroll to zoom · Click to read · Double-click for chapters',
          zh: '🖱️ 拖拽旋转 · 滚轮缩放 · 单击阅读 · 双击展开章节' },
  hintChapters: { en: '🧬 Chapter chain top→bottom · Click a chapter to jump · Double-click to go back',
                  zh: '🧬 章节链自上而下 · 点击章节跳转 · 双击返回总览' },
  backToOverview: { en: 'Back to graph', zh: '返回总览' },
  resetView: { en: 'Reset View', zh: '重置视角' },
  stopRotate: { en: 'Stop Rotate', zh: '停止旋转' },
  autoRotate: { en: 'Auto Rotate', zh: '自动旋转' },
  legend: { en: 'Legend', zh: '图例' },
  loading: { en: 'Loading…', zh: '加载中…' },
  selectHint: { en: 'Select a document', zh: '选择文档' },
  selectHintDesc: { en: 'Click any node in the 3D graph or pick from the list below to read the full document.',
                    zh: '点击 3D 图谱中的任意节点，或从下方列表选择以阅读全文。' },
  manualTitle: { en: 'Platform Module User Manual', zh: '平台模块使用手册' },
  manualIntro: { en: 'Usage guide for each platform module — features, entry paths, and practical tips.',
                 zh: '平台各模块的功能说明、入口路径与实用提示。' },
  cycleTitle: { en: 'Theory → Practice → ML Training → Feedback → Improve', zh: '理论 → 实践 → 机器学习 → 反馈 → 改进理论' },
  cycleDesc: { en: 'Knowledge is not static: read theory, practice in the designer, train models on observations, feed quality results back, and let practice refine the theory — continuously.',
               zh: '知识不是静止的：读理论、在设计器中实践、用观测样本训练模型、将质量结果回流反馈，让实践反哺理论——持续进化。' },
  practiceTitle: { en: 'From Theory to Action — Practice Guide', zh: '从理论到行动 — 实践指南' },
  practiceSub: { en: 'Each principle maps to a concrete action you can take today.',
                 zh: '每一条原则都对应一个今天就能执行的具体动作。' },
  openModule: { en: 'Open this module', zh: '进入该模块' },
  tip: { en: 'Tip', zh: '提示' },
  systemTitle: { en: 'Documentation System', zh: '文档体系' },
  systemIntro: { en: 'The knowledge base is organized into four logical layers, flowing from philosophical roots to verifiable quality evidence.',
                 zh: '知识库按四个逻辑层组织，从哲学根基到可验证的质量证据逐层递进。' }
}

const activeTab = ref('graph')
const router = useRouter()
// 点击模块卡片跳转到对应模块页面（Help Center 自身除外，留在当前页）
const goModule = (m) => {
  if (m.path && m.path !== '/help') router.push(m.path)
}
const selectedDoc = ref(null)
const docContent = ref('')
const contentLocale = ref('')
const loadingContent = ref(false)
const autoRotate = ref(true)

// ---------------- Three.js 场景 ----------------
const canvasRef = ref(null)
let scene, camera, renderer, controls, raycaster, mouse

// ---------------- 取景参数：让图谱在画布中放大并居中 ----------------
const FOV_DEG = 50                                   // 相机垂直视场角
const TARGET_Y = -2.5                                // 注视点（金字塔视觉重心，非几何原点）
const CAM_POLAR = THREE.MathUtils.degToRad(21.8)     // 相机俯角（温和俯视）
const MIN_DIST = 28.5                                // 最小距离：保证哲学环前侧标签在俯视方向上不出框
const HORIZ_FACTOR = 38                              // 水平包围：窄画布时按 aspect 拉远距离防裁切
// 依据画布宽高比计算取景距离：前侧方向约束 与 水平包围约束 取大者
const framingDistance = (aspect) => Math.max(MIN_DIST, HORIZ_FACTOR / aspect)

// 章节钻取视图：DNA 螺旋布局
const CH_RADIUS = 4.2                                // 螺旋半径
const CH_STEP_Y = 1.35                               // 每章垂直步距（体现阅读顺序）
const CH_LABEL_REACH = 5.6                           // 水平取景余量（外推1.6+长标签半宽约4.0）
const CH_TOP_PAD = 2.8                               // 垂直取景余量（近端球+前侧标签+呼吸）
// 将相机定位到默认方位（正对 +Z、固定俯角），图谱在当前尺寸画布下完整居中
const placeCamera = () => {
  const d = framingDistance(camera.aspect)
  camera.position.set(0, TARGET_Y + d * Math.sin(CAM_POLAR), d * Math.cos(CAM_POLAR))
  controls.target.set(0, TARGET_Y, 0)
  controls.update()
}
let nodeMeshes = [], edgeLines = [], labelSprites = [], animId

// ---------------- 两级图谱：总览（知识底座） ↔ 钻取（文档章节链） ----------------
const graphMode = ref('overview')        // overview | chapters
const drillDoc = ref(null)               // 当前钻取的文档对象
const chapterSections = ref([])          // 当前文档章节（h2）标题列表
const chapterCache = new Map()           // key: `${lang}:${docId}` → 章节数组
let pendingChapterScroll = -1            // 打开文档后待滚动定位的章节序号

const initThree = () => {
  const container = canvasRef.value
  const w = container.clientWidth, h = container.clientHeight
  scene = new THREE.Scene()
  scene.background = null

  camera = new THREE.PerspectiveCamera(FOV_DEG, w / h, 0.1, 1000)
  // 机位在 controls 建立后由 placeCamera() 依据画布宽高比统一计算（放大并居中）

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.setSize(w, h)
  container.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  // 按当前画布宽高比计算机位：图谱放大并在画面中居中
  placeCamera()
  controls.autoRotate = autoRotate.value
  controls.autoRotateSpeed = 0.8
  controls.minDistance = 10
  controls.maxDistance = 80

  raycaster = new THREE.Raycaster()
  mouse = new THREE.Vector2()

  // 环境光 + 平行光
  scene.add(new THREE.AmbientLight(0xffffff, 0.7))
  const dir = new THREE.DirectionalLight(0xffffff, 0.8)
  dir.position.set(10, 20, 10)
  scene.add(dir)

  // 中心核心（平台中枢）
  const coreGeo = new THREE.IcosahedronGeometry(1.15, 1)
  const coreMat = new THREE.MeshStandardMaterial({ color: 0x4ade80, emissive: 0x166534, emissiveIntensity: 0.4, roughness: 0.4 })
  const core = new THREE.Mesh(coreGeo, coreMat)
  core.userData.baseScale = 1
  scene.add(core)

  // 中枢名称标签（位于核心下方）
  const coreLabel = makePillSprite(
    pick({ en: 'EVOLUTION AI · Core', zh: 'EVOLUTION AI · 中枢' }), '#4ade80', 0.7)
  coreLabel.position.set(0, -1.35, 0)
  scene.add(coreLabel)

  // 四层环带（知识底座的层级可视化）
  categories.forEach(cat => {
    const cfg = LAYER_CFG[cat.id]
    const pts = []
    for (let k = 0; k <= 72; k++) {
      const a = (k / 72) * Math.PI * 2
      pts.push(new THREE.Vector3(Math.cos(a) * cfg.r, cfg.y, Math.sin(a) * cfg.r))
    }
    const ringGeo = new THREE.BufferGeometry().setFromPoints(pts)
    const ringMat = new THREE.LineBasicMaterial({ color: new THREE.Color(cat.color), transparent: true, opacity: 0.22 })
    scene.add(new THREE.Line(ringGeo, ringMat))
  })

  // 层名标签：位于每层环带轴心下方，标注 L1~L4 与层含义（语言跟随平台）
  categories.forEach((cat, i) => {
    const cfg = LAYER_CFG[cat.id]
    const sp = makePillSprite(`L${i + 1} · ${pick(cat.label)}`, cat.color, 0.68)
    sp.position.set(0, cfg.y - 1.0, 0)
    scene.add(sp)
  })

  // 文档节点：按层均匀分布在环带上
  const map = new Map()
  docs.forEach(d => {
    const c = categories.find(x => x.id === d.category)
    const cfg = LAYER_CFG[d.category]
    const sameCat = docs.filter(x => x.category === d.category)
    const idx = sameCat.indexOf(d)
    const angle = cfg.angleOff + idx * 2 * Math.PI / sameCat.length
    const x = Math.cos(angle) * cfg.r
    const z = Math.sin(angle) * cfg.r
    const y = cfg.y
    d._pos = new THREE.Vector3(x, y, z)

    // 各层首个文档为锚点（与核心直连），略大
    const isAnchor = idx === 0
    const radius = isAnchor ? 0.88 : 0.68
    const geo = new THREE.SphereGeometry(radius, 24, 24)
    const mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(c.color), emissive: new THREE.Color(c.color),
      emissiveIntensity: isAnchor ? 0.4 : 0.25, roughness: 0.45, metalness: 0.1
    })
    const mesh = new THREE.Mesh(geo, mat)
    mesh.position.copy(d._pos)
    mesh.userData.docId = d.id
    mesh.userData.baseScale = isAnchor ? 1.15 : 1
    scene.add(mesh)
    nodeMeshes.push(mesh)
    map.set(d.id, mesh)

    // 文档名标签：节点径向外侧略上方，避开同层球体，也不侵入相邻层环带
    const sprite = makeLabelSprite(d)
    sprite.position.set(x * 1.12, y + 0.5, z * 1.12)
    scene.add(sprite)
    labelSprites.push(sprite)
  })

  // 四类语义连接：颜色/透明度/线型按类型区分；布线规则按类型分离，避免蛛网
  //   intra → 环带径向外侧外凸弧线（不穿金字塔内部）
  //   其余  → 三次贝塞尔，端点切线竖直，如神经网络层间连接
  const EDGE_STYLE = {
    core:     { color: 0x4ade80, opacity: 0.6,  gapFactor: 0.5,  dashed: false },
    flow:     { color: 0x9db8d8, opacity: 0.45, gapFactor: 0.5,  dashed: false },
    intra:    { color: 0x7c8aa5, opacity: 0.28, bow: 1.6, dashed: false },
    feedback: { color: 0xfbbf24, opacity: 0.7,  gapFactor: 0.3,  dashed: true }
  }
  graphEdges.forEach(e => {
    const pa = e.a === 'core' ? new THREE.Vector3(0, 0, 0) : map.get(e.a)?.position
    const pb = map.get(e.b)?.position
    if (!pa || !pb) return
    const st = EDGE_STYLE[e.type]

    let curve
    if (e.type === 'intra') {
      // 同层弧线：弦中点沿环径向外侧推出，弧线在环外展开，保持金字塔内部整洁
      const mid = pa.clone().add(pb).multiplyScalar(0.5)
      const radial = Math.hypot(mid.x, mid.z) || 1
      mid.x += (mid.x / radial) * st.bow
      mid.z += (mid.z / radial) * st.bow
      curve = new THREE.QuadraticBezierCurve3(pa, mid, pb)
    } else {
      // 跨层弧线：两控制点分别在端点竖直方向，出入环带均为垂直切线
      const gap = Math.max(0.6, Math.abs(pb.y - pa.y) * st.gapFactor)
      const c1 = pa.clone(); c1.y += gap
      const c2 = pb.clone(); c2.y -= gap
      curve = new THREE.CubicBezierCurve3(pa, c1, c2, pb)
    }

    const geo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(32))
    const mat = st.dashed
      ? new THREE.LineDashedMaterial({ color: st.color, transparent: true, opacity: st.opacity,
                                       dashSize: 0.35, gapSize: 0.22 })
      : new THREE.LineBasicMaterial({ color: st.color, transparent: true, opacity: st.opacity })
    const line = new THREE.Line(geo, mat)
    if (st.dashed) line.computeLineDistances()
    scene.add(line)
    edgeLines.push(line)
  })

  // 点击
  renderer.domElement.addEventListener('click', onCanvasClick)
  // hover
  renderer.domElement.addEventListener('mousemove', onCanvasMove)
  // 双击：钻取该文档的章节链
  renderer.domElement.addEventListener('dblclick', onCanvasDblClick)

  animate()
}

// ============ 章节钻取视图：文档核心 + 章节 DNA 螺旋链 ============
// 依据章节数与画布宽高比取景：螺旋上下端与外侧标签均不被裁切
const chaptersFramingDistance = (aspect) => {
  const n = chapterSections.value.length
  const halfH = (n * CH_STEP_Y) / 2
  const t = Math.tan(THREE.MathUtils.degToRad(FOV_DEG / 2))
  const dV = (halfH + CH_TOP_PAD) / t                   // 垂直包围（含标签余量）
  const dH = (CH_RADIUS + CH_LABEL_REACH) / (t * aspect) // 水平包围
  return Math.max(dV, dH, 11)
}
const placeChaptersCamera = () => {
  const d = chaptersFramingDistance(camera.aspect)
  const polar = THREE.MathUtils.degToRad(8)             // 章节视图接近正视，仅 8° 俯角
  camera.position.set(0, d * Math.sin(polar), d * Math.cos(polar))
  controls.target.set(0, 0, 0)
  controls.update()
}

const initChaptersThree = () => {
  const container = canvasRef.value
  const w = container.clientWidth, h = container.clientHeight
  scene = new THREE.Scene()
  scene.background = null

  camera = new THREE.PerspectiveCamera(FOV_DEG, w / h, 0.1, 1000)

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.setSize(w, h)
  container.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  placeChaptersCamera()
  controls.autoRotate = false
  controls.minDistance = 8
  controls.maxDistance = 60

  raycaster = new THREE.Raycaster()
  mouse = new THREE.Vector2()

  scene.add(new THREE.AmbientLight(0xffffff, 0.7))
  const dl = new THREE.DirectionalLight(0xffffff, 0.8)
  dl.position.set(10, 20, 10)
  scene.add(dl)

  const doc = drillDoc.value
  const baseColor = new THREE.Color(doc._color)
  const sections = chapterSections.value
  const N = sections.length

  // 文档核心（中轴）：点击在右侧打开全文；文档名显示在顶部工具条，避免与章节标签重叠
  const core = new THREE.Mesh(
    new THREE.IcosahedronGeometry(0.92, 1),
    new THREE.MeshStandardMaterial({ color: baseColor, emissive: baseColor, emissiveIntensity: 0.25, roughness: 0.4 })
  )
  core.userData = { kind: 'doc-root', baseScale: 1 }
  scene.add(core)
  nodeMeshes.push(core)

  // 章节螺旋：第 1 章在顶部，沿中轴螺旋下行——阅读顺序即逻辑链
  const totalH = N * CH_STEP_Y
  const turns = Math.max(1, N / 7.5)             // 圈数略收：末端章节分散左右，避免底部拥挤
  const positions = []
  sections.forEach((title, i) => {
    const y = totalH / 2 - (i + 0.5) * CH_STEP_Y
    const a = Math.PI / 2 - i * (Math.PI * 2 * turns) / N
    const radial = new THREE.Vector3(Math.cos(a), 0, Math.sin(a))
    const pos = new THREE.Vector3(radial.x * CH_RADIUS, y, radial.z * CH_RADIUS)
    positions.push(pos)

    const ch = new THREE.Mesh(
      new THREE.SphereGeometry(0.5, 24, 24),
      new THREE.MeshStandardMaterial({ color: baseColor, emissive: baseColor, emissiveIntensity: 0.35, roughness: 0.35 })
    )
    ch.position.copy(pos)
    ch.userData = { kind: 'chapter', idx: i, baseScale: 1 }
    scene.add(ch)
    nodeMeshes.push(ch)

    // 章节标签：沿螺旋径向外侧排布
    const sp = makePillSprite(title, doc._color, 0.62)
    sp.position.copy(pos).add(radial.multiplyScalar(1.6))
    scene.add(sp)
    labelSprites.push(sp)
  })

  // 章节顺序链：穿过全部章节点的平滑螺旋管（文档逻辑主线）
  if (N >= 2) {
    const curve = new THREE.CatmullRomCurve3(positions)
    const tube = new THREE.Mesh(
      new THREE.TubeGeometry(curve, Math.max(64, N * 16), 0.045, 8, false),
      new THREE.MeshBasicMaterial({ color: baseColor, transparent: true, opacity: 0.55 })
    )
    scene.add(tube)
  }

  // 核心 → 章节 辐条：文档与其各章节的归属关系
  const spokeVerts = []
  positions.forEach(p => spokeVerts.push(0, 0, 0, p.x, p.y, p.z))
  const spokeGeo = new THREE.BufferGeometry()
  spokeGeo.setAttribute('position', new THREE.Float32BufferAttribute(spokeVerts, 3))
  scene.add(new THREE.LineSegments(
    spokeGeo,
    new THREE.LineBasicMaterial({ color: baseColor, transparent: true, opacity: 0.2 })
  ))

  // 交互：单击章节定位/核心开文；双击回总览
  renderer.domElement.addEventListener('click', onCanvasClick)
  renderer.domElement.addEventListener('mousemove', onCanvasMove)
  renderer.domElement.addEventListener('dblclick', onCanvasDblClick)

  animate()
}

// 胶囊文字精灵：动态宽度，文字必须为已 pick 的字符串（禁止直接传 bilingual 对象，
// 否则 canvas 会把 {en,zh} 渲染成 [object Object]）
const makePillSprite = (label, color, worldH = 0.95) => {
  const fs = 30, padX = 20, h = fs + 16

  // 先测量文字宽度
  const mc = document.createElement('canvas').getContext('2d')
  mc.font = `600 ${fs}px "Segoe UI", "Microsoft YaHei", sans-serif`
  const w = Math.ceil(mc.measureText(label).width) + padX * 2

  // 2 倍分辨率保证清晰
  const canvas = document.createElement('canvas')
  canvas.width = w * 2; canvas.height = h * 2
  const ctx = canvas.getContext('2d')
  ctx.scale(2, 2)
  ctx.font = `600 ${fs}px "Segoe UI", "Microsoft YaHei", sans-serif`
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'

  // 胶囊底色：分类色半透明；描边同色
  const r = h / 2
  ctx.beginPath()
  ctx.moveTo(r, 2)
  ctx.arcTo(w - 1, 2, w - 1, h - 2, r - 2)
  ctx.arcTo(w - 1, h - 2, 1, h - 2, r - 2)
  ctx.arcTo(1, h - 2, 1, 2, r - 2)
  ctx.arcTo(1, 2, w - 1, 2, r - 2)
  ctx.closePath()
  ctx.fillStyle = color + '2e'
  ctx.fill()
  ctx.lineWidth = 1.5
  ctx.strokeStyle = color + '99'
  ctx.stroke()

  // 文字颜色跟随当前主题（深色模式近白，浅色模式近黑）
  const isLight = document.documentElement.classList.contains('light-theme')
  ctx.shadowColor = isLight ? 'rgba(0,0,0,0.25)' : 'rgba(0,0,0,0.7)'
  ctx.shadowBlur = 4
  ctx.fillStyle = isLight ? '#1a1a2e' : '#f8fafc'
  ctx.fillText(label, w / 2, h / 2 + 1)

  const tex = new THREE.CanvasTexture(canvas)
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false })
  const sprite = new THREE.Sprite(mat)
  sprite.scale.set(worldH * (w / h), worldH, 1)
  return sprite
}

// 文档名标签：文字为当前语言下的文档真实名称
const makeLabelSprite = (doc) => makePillSprite(pick(doc.title), doc._color)

const animate = () => {
  animId = requestAnimationFrame(animate)
  controls.autoRotate = autoRotate.value
  controls.update()
  // 节点呼吸（在各自基础尺寸上波动）
  const t = Date.now() * 0.001
  nodeMeshes.forEach((m, i) => {
    const base = m.userData.baseScale || 1
    m.scale.setScalar(base * (1 + Math.sin(t * 1.5 + i * 0.5) * 0.05))
  })
  renderer.render(scene, camera)
}

// 将鼠标事件换算为 NDC 并返回命中节点（总览/章节两视图共用）
const pickMeshAtEvent = (e) => {
  const rect = renderer.domElement.getBoundingClientRect()
  mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(mouse, camera)
  return raycaster.intersectObjects(nodeMeshes)
}

const onCanvasClick = (e) => {
  const hits = pickMeshAtEvent(e)
  if (!hits.length) return
  const ud = hits[0].object.userData
  if (graphMode.value === 'chapters') {
    // 章节节点：右侧打开文档并定位该章节；核心：打开全文
    if (ud.kind === 'chapter') openChapter(ud.idx)
    else if (ud.kind === 'doc-root') selectDoc(drillDoc.value)
    return
  }
  const doc = docs.find(d => d.id === ud.docId)
  if (doc) selectDoc(doc)
}

// 双击：总览中钻取该文档章节；章节视图中返回总览
const onCanvasDblClick = (e) => {
  if (graphMode.value === 'chapters') { exitChapters(); return }
  const hits = pickMeshAtEvent(e)
  if (!hits.length) return
  const doc = docs.find(d => d.id === hits[0].object.userData.docId)
  if (doc) enterChapters(doc)
}

let hoveredMesh = null
const onCanvasMove = (e) => {
  const hits = pickMeshAtEvent(e)
  if (hoveredMesh) { hoveredMesh.scale.setScalar(hoveredMesh.userData.baseScale || 1); hoveredMesh = null }
  renderer.domElement.style.cursor = hits.length ? 'pointer' : 'default'
  if (hits.length) { hoveredMesh = hits[0].object; hoveredMesh.scale.setScalar((hoveredMesh.userData.baseScale || 1) * 1.35) }
}

// 重置视角：回到默认方位并按当前画布尺寸重新居中取景（按当前视图取取景器）
const resetCamera = () => {
  if (graphMode.value === 'chapters') placeChaptersCamera()
  else placeCamera()
}

const toggleAutoRotate = () => { autoRotate.value = !autoRotate.value }

const onResize = () => {
  if (!renderer || !canvasRef.value) return
  const w = canvasRef.value.clientWidth, h = canvasRef.value.clientHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
  // 保留用户当前旋转方位，仅按新宽高比重算距离，图谱在新尺寸下仍完整居中
  const distFn = graphMode.value === 'chapters' ? chaptersFramingDistance : framingDistance
  const dir = camera.position.clone().sub(controls.target).normalize()
  camera.position.copy(controls.target).add(dir.multiplyScalar(distFn(camera.aspect)))
  controls.update()
}

// ---------------- 文档内容渲染 ----------------
const md = new MarkdownIt({ html: true, breaks: true, linkify: true }).use(markdownItEmoji.full)
const stripFrontmatter = (text) => text.replace(/^---\s*\n[\s\S]*?\n---\s*\n/, '')

// 抓取失败时，用元数据按当前语言构建兜底页（确保无空白页、无串语言）
const fallbackPage = (d) => {
  const wantEn = locale.value !== 'zh'
  const head = wantEn
    ? ['> The full English edition of this document is being prepared.',
       '> The structured overview below is available now.']
    : ['> 文档全文暂不可用，以下为结构化概要。']
  return [
    `# ${pick(d.title)}`,
    pick(d.summary),
    '',
    ...head,
    '',
    `**${wantEn ? 'Category' : '分类'}**: ${pick(categories.find(c => c.id === d._categoryId).label)}`,
    `**${wantEn ? 'Edition' : '版本'}**: ${d.date || '—'}`,
    `**${wantEn ? 'Source file' : '源文件'}**: \`docs/${d.file}\``
  ].join('\n')
}

// 始终按"当前平台语言"渲染：抓取文本只在语言匹配时采用，否则用元数据兜底
const renderedContent = computed(() => {
  if (!selectedDoc.value) return ''
  const want = locale.value === 'zh' ? 'zh' : 'en'
  const src = (docContent.value && contentLocale.value === want)
    ? docContent.value
    : fallbackPage(selectedDoc.value)
  return md.render(stripFrontmatter(src))
})

const selectDoc = async (d) => {
  selectedDoc.value = d
  docContent.value = ''
  contentLocale.value = ''
  loadingContent.value = true
  const want = locale.value === 'zh' ? 'zh' : 'en'
  const base = import.meta.env.BASE_URL || './'
  // 英文模式优先取 docs/en/<file> 英文伴生版；中文模式取中文源文件
  const candidates = want === 'en'
    ? [{ path: `en/${d.file}`, lang: 'en' }]
    : [{ path: d.file, lang: 'zh' }]
  for (const c of candidates) {
    try {
      const res = await fetch(`${base}docs/${c.path}`, { cache: 'no-store' })
      if (res.ok) {
        docContent.value = await res.text()
        contentLocale.value = c.lang
        break
      }
    } catch (e) { /* 继续兜底 */ }
  }
  loadingContent.value = false
}

// ---------------- 章节提取与钻取 ----------------
// 从 Markdown 提取 h2 章节标题（跳过代码围栏，避免注释里的 # 被误判）
const extractH2 = (mdText) => {
  const out = []
  let inFence = false
  stripFrontmatter(mdText).split('\n').forEach((ln) => {
    if (/^\s*```/.test(ln)) { inFence = !inFence; return }
    if (inFence) return
    const m = /^##\s+(.+?)\s*$/.exec(ln)
    if (m) out.push(m[1].replace(/[*_`]/g, '').trim())
  })
  return out
}

// 双击文档节点：抓取当前语言版本（带缓存）→ 进入章节视图；阅读时停止自动旋转
const enterChapters = async (doc) => {
  const lang = locale.value === 'zh' ? 'zh' : 'en'
  const key = `${lang}:${doc.id}`
  graphMode.value = 'chapters'
  drillDoc.value = doc
  autoRotate.value = false
  if (!chapterCache.has(key)) {
    const base = import.meta.env.BASE_URL || './'
    const path = lang === 'en' ? `en/${doc.file}` : doc.file
    let sections = []
    try {
      const res = await fetch(`${base}docs/${path}`, { cache: 'no-store' })
      if (res.ok) sections = extractH2(await res.text())
    } catch (e) { /* 失败缓存空数组，视图仍可返回 */ }
    chapterCache.set(key, sections)
  }
  chapterSections.value = chapterCache.get(key)
  await nextTick()
  rebuildThree()
}

// 返回知识底座总览
const exitChapters = () => {
  graphMode.value = 'overview'
  drillDoc.value = null
  chapterSections.value = []
  rebuildThree()
}

// 在右侧文档面板内滚动到第 idx 个 h2（滚动容器是 .detail-panel，只滚面板自身）
const scrollToChapter = (idx) => {
  nextTick(() => {
    const host = document.querySelector('.detail-panel')
    const h2 = host?.querySelectorAll('.detail-content h2')[idx]
    if (host && h2) {
      host.scrollTo({
        top: host.scrollTop + h2.getBoundingClientRect().top - host.getBoundingClientRect().top - 8,
        behavior: 'smooth'
      })
    }
  })
}

// 单击章节节点：打开文档并定位章节；文档已打开则直接滚动
const openChapter = async (idx) => {
  if (selectedDoc.value?.id !== drillDoc.value.id) {
    pendingChapterScroll = idx       // renderedContent 更新后由 watcher 执行滚动
    await selectDoc(drillDoc.value)
  } else {
    scrollToChapter(idx)
  }
}

// 文档渲染完成后执行挂起的章节定位（首次打开/语言切换后）
watch(renderedContent, () => {
  if (pendingChapterScroll < 0) return
  const want = locale.value === 'zh' ? 'zh' : 'en'
  // 抓取期间会先渲染兜底页（contentLocale 为空），此时不消费，等真实内容就绪
  if (contentLocale.value !== want) return
  const idx = pendingChapterScroll
  pendingChapterScroll = -1
  scrollToChapter(idx)
})

// ---------------- 3D 场景重建（语言/主题切换时，标签为一次性画布纹理） ----------------
let themeObserver = null
const teardownThree = () => {
  if (animId) cancelAnimationFrame(animId)
  animId = null
  if (renderer) {
    renderer.domElement.removeEventListener('click', onCanvasClick)
    renderer.domElement.removeEventListener('mousemove', onCanvasMove)
    renderer.domElement.removeEventListener('dblclick', onCanvasDblClick)
  }
  scene?.traverse(obj => {
    if (obj.geometry) obj.geometry.dispose()
    if (obj.material) {
      const mats = Array.isArray(obj.material) ? obj.material : [obj.material]
      mats.forEach(m => { m.map?.dispose(); m.dispose() })
    }
  })
  if (renderer) {
    renderer.dispose()
    renderer.domElement.parentNode?.removeChild(renderer.domElement)
  }
  scene = null; renderer = null; controls = null
  nodeMeshes = []; edgeLines = []; labelSprites = []
  hoveredMesh = null
}

const rebuildThree = () => {
  teardownThree()
  if (graphMode.value === 'chapters' && drillDoc.value) initChaptersThree()
  else initThree()
}

// ---------------- 生命周期 ----------------
onMounted(async () => {
  await nextTick()
  // 容器可能尚未完成布局（0×0），用 rAF 重试避免空白画布
  const boot = (tries) => {
    const el = canvasRef.value
    if (el && el.clientWidth > 0 && el.clientHeight > 0) initThree()
    else if (tries > 0) requestAnimationFrame(() => boot(tries - 1))
    else initThree()
  }
  boot(10)
  window.addEventListener('resize', onResize)

  // 主题切换（class 变化）→ 重建标签配色
  themeObserver = new MutationObserver(() => rebuildThree())
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
})

// 平台语言切换 → 已选文档按新语言重新抓取；图谱标签按新语言重建
watch(locale, () => {
  if (selectedDoc.value) selectDoc(selectedDoc.value)
  // 章节视图下按新语言重新抓取章节并重建；总览直接重建
  if (graphMode.value === 'chapters' && drillDoc.value) enterChapters(drillDoc.value)
  else rebuildThree()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  themeObserver?.disconnect()
  teardownThree()
})
</script>

<style scoped>
.help-page { padding: 4px; color: var(--text-primary); }

.page-header {
  display: flex; justify-content: space-between; align-items: flex-end;
  padding: 12px 18px; background: var(--bg-card); border: 1px solid var(--border-color);
  border-radius: 12px; margin-bottom: 14px;
}
.page-header h2 { font-size: 18px; margin: 0; }
.subtitle { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.header-stats { display: flex; gap: 18px; }
.stat { text-align: center; }
.stat b { display: block; font-size: 22px; color: var(--accent); font-weight: 800; }
.stat span { font-size: 11px; color: var(--text-muted); }

.tabs { display: flex; gap: 6px; margin-bottom: 14px; }
.tab {
  padding: 8px 18px; border-radius: 8px; cursor: pointer; font-size: 13px;
  background: var(--bg-card); border: 1px solid var(--border-color);
  color: var(--text-secondary); transition: all .2s;
}
.tab:hover { color: var(--text-primary); }
.tab.active { background: var(--accent-bg); color: var(--accent); border-color: var(--accent); }

.tab-panel { min-height: 560px; }

/* ===== 图谱 ===== */
/* 左图（3D 图谱）/ 右文（文档内容）各占 50%，以内容为重 */
.graph-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
/* 画布高度视口感知：矮窗口（如嵌入 webview）自动收缩，保证底部章节不落到视口外 */
.graph-stage { position: relative; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; }
.three-canvas { width: 100%; height: min(580px, calc(100vh - 220px)); }
.graph-hint {
  position: absolute; top: 10px; left: 12px; font-size: 11px; color: var(--text-muted);
  display: flex; gap: 10px; align-items: center;
}
.mini-btn {
  background: var(--bg-secondary); border: 1px solid var(--border-color); color: var(--text-secondary);
  font-size: 11px; padding: 3px 10px; border-radius: 6px; cursor: pointer;
}
.mini-btn.active { color: var(--accent); border-color: var(--accent); }
.drill-chip {
  font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 999px;
  border: 1px solid; background: var(--bg-secondary); white-space: nowrap;
}
.legend {
  position: absolute; bottom: 12px; left: 12px;
  background: var(--bg-card-elevated, rgba(20, 20, 30, 0.72));
  border: 1px solid var(--border-color);
  backdrop-filter: blur(4px);
  padding: 8px 12px; border-radius: 8px; font-size: 11px;
}
.legend-title { font-weight: 700; margin-bottom: 5px; color: var(--text-primary); }
.legend-item { display: flex; align-items: center; gap: 6px; margin: 3px 0; color: var(--text-secondary); }
.legend-item .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }

.detail-panel {
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px;
  padding: 16px; overflow-y: auto; max-height: min(580px, calc(100vh - 220px));
}
.detail-header { display: flex; justify-content: space-between; align-items: center; }
.detail-header h3 { font-size: 15px; margin: 0; }
.close-btn { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 16px; }
.detail-meta { display: flex; gap: 8px; margin: 8px 0; flex-wrap: wrap; }
.badge { padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.meta-item { font-size: 11px; color: var(--text-muted); align-self: center; }
.detail-summary { font-size: 12.5px; color: var(--text-secondary); line-height: 1.7; }
.detail-links { display: flex; gap: 10px; margin: 10px 0; }
.detail-links a {
  font-size: 12px; color: var(--accent); text-decoration: none;
  padding: 4px 12px; border: 1px solid var(--accent); border-radius: 6px;
}
.detail-links a:hover { background: var(--accent-bg); }
.detail-content { margin-top: 10px; font-size: 12px; }
.loading, .empty { color: var(--text-muted); font-size: 12px; padding: 12px; }
.empty-panel h3 { font-size: 14px; margin-bottom: 6px; }
.empty-panel p { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }
.doc-list { list-style: none; padding: 0; max-height: 480px; overflow-y: auto; }
.doc-list li {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 6px;
  cursor: pointer; font-size: 12.5px;
}
.doc-list li:hover { background: var(--hover-bg); }
.doc-list .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

/* markdown 渲染样式（v-html 内容无 scoped 属性，子元素必须用 :deep 穿透） */
.markdown-body { line-height: 1.7; font-size: 12px; }
.markdown-body :deep(h1) { font-size: 16px; border-bottom: 2px solid var(--accent); padding-bottom: 4px; margin: 14px 0 8px; }
.markdown-body :deep(h2) { font-size: 14px; border-bottom: 1px solid var(--border-color); padding-bottom: 3px; margin: 12px 0 6px; }
.markdown-body :deep(h3) { font-size: 13px; margin: 10px 0 5px; }
.markdown-body :deep(p) { margin: 6px 0; }
.markdown-body :deep(code) { background: var(--hover-bg); padding: 1px 5px; border-radius: 3px; font-size: 11px; color: var(--accent); }
.markdown-body :deep(pre) { background: var(--bg-secondary); padding: 8px; border-radius: 6px; overflow-x: auto; }
.markdown-body :deep(pre code) { background: none; color: inherit; }
.markdown-body :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 11px; }
.markdown-body :deep(th), .markdown-body :deep(td) { border: 1px solid var(--border-color); padding: 4px 7px; }
.markdown-body :deep(th) { background: var(--hover-bg); }
/* 链接：主题强调色 + 悬停增亮，保证深/浅主题下均有足够对比度 */
.markdown-body :deep(a) { color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }
.markdown-body :deep(a:hover) { filter: brightness(1.2); }
.markdown-body :deep(blockquote) { border-left: 3px solid var(--accent); padding-left: 10px; color: var(--text-muted); margin: 8px 0; }

/* ===== 手册 ===== */
.manual-panel { }
.manual-intro { margin-bottom: 16px; }
.manual-intro h3 { font-size: 15px; margin-bottom: 4px; }
.manual-intro p { font-size: 12.5px; color: var(--text-muted); }
.module-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.module-card {
  background: var(--bg-card); border: 1px solid var(--border-color); border-left: 4px solid var(--accent);
  border-radius: 10px; padding: 14px;
  transition: border-color .2s, transform .2s, box-shadow .2s;
  cursor: pointer; position: relative;
}
.module-card:hover { border-color: var(--accent); transform: translateY(-2px); box-shadow: 0 4px 14px rgba(0,0,0,0.12); }
.module-enter {
  margin-left: auto; font-size: 16px; color: var(--text-muted); opacity: 0;
  transition: opacity .2s, color .2s;
}
.module-card:hover .module-enter { opacity: 1; color: var(--accent); }
.module-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.module-icon { font-size: 20px; }
.module-head h4 { font-size: 14px; margin: 0; }
.module-path { font-size: 10.5px; color: var(--text-muted); font-family: Consolas, monospace; background: var(--hover-bg); padding: 1px 6px; border-radius: 4px; }
.module-desc { font-size: 12px; color: var(--text-secondary); margin: 8px 0; line-height: 1.6; }
.module-features { margin: 8px 0; }
.feature { display: flex; gap: 6px; font-size: 11.5px; color: var(--text-secondary); margin: 3px 0; }
.feat-bullet { color: var(--accent); }
.module-tip { font-size: 11px; color: var(--text-muted); background: var(--accent-bg); padding: 6px 9px; border-radius: 6px; margin-top: 8px; line-height: 1.5; }

/* ===== Module Manual：上区 理论闭环|实践指南 并排各 50%，下区 模块手册 5列×2行 ===== */
.manual-body { display: flex; flex-direction: column; gap: 16px; }
.manual-top { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: stretch; }
.manual-top .cycle-section { margin-bottom: 0; height: 100%; }
/* 实践指南补面板底，使左右两模块边界清晰、视觉成对 */
.manual-top .practice-guide {
  margin-top: 0; height: 100%;
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px;
  padding: 16px 18px;
}
.manual-body .module-grid { grid-template-columns: repeat(5, 1fr); }

/* ===== 闭环图 ===== */
.cycle-section {
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px;
  padding: 16px 18px; margin-bottom: 16px; text-align: center;
}
.cycle-title { font-size: 15px; font-weight: 700; margin-bottom: 4px; color: var(--text-primary); }
.cycle-desc { font-size: 12px; color: var(--text-muted); max-width: 720px; margin: 0 auto 10px; line-height: 1.6; }
.cycle-diagram { display: flex; justify-content: center; align-items: center; flex: 1; }
.cycle-svg { width: 100%; max-width: 560px; height: auto; }

/* ===== 模块迷你流程图 ===== */
.module-flow { margin: 10px 0; }
.flow-steps { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.flow-step {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--accent); color: #fff; font-size: 10.5px; font-weight: 600;
  padding: 3px 9px; border-radius: 999px; white-space: nowrap;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.flow-idx {
  background: rgba(255,255,255,0.3); border-radius: 50%;
  width: 16px; height: 16px; display: inline-flex; align-items: center; justify-content: center;
  font-size: 10px;
}
.flow-arrow { color: var(--text-muted); font-size: 12px; }

/* ===== 实践指南 ===== */
.practice-guide { margin-top: 20px; }
.pg-title { font-size: 15px; margin-bottom: 4px; }
.pg-sub { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }
.pg-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 10px; }
.pg-card {
  display: flex; align-items: center; gap: 10px;
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 10px 12px;
  transition: border-color .2s, transform .2s;
}
.pg-card:hover { border-color: var(--accent); transform: translateY(-1px); }
.pg-icon { font-size: 22px; flex-shrink: 0; }
.pg-body { font-size: 12px; line-height: 1.6; }
.pg-theory { color: var(--accent); font-weight: 700; }
.pg-arrow { margin: 0 5px; color: var(--text-muted); }
.pg-action { color: var(--text-secondary); }

/* 响应式：中屏模块 3 列、上区保持并排；窄屏全部单列/两列 */
@media (max-width: 1500px) {
  .manual-body .module-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 1100px) {
  .graph-panel { grid-template-columns: 1fr; }
  .principle-row { grid-template-columns: 1fr; }
  .pg-grid { grid-template-columns: 1fr; }
  /* 窄屏回退：上区两模块改上下堆叠，模块卡 2 列 */
  .manual-top { grid-template-columns: 1fr; }
  .manual-body .module-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .manual-body .module-grid { grid-template-columns: 1fr; }
}

/* ===== 文档体系 ===== */
.system-panel { }
.system-intro { margin-bottom: 16px; }
.system-intro h3 { font-size: 15px; margin-bottom: 4px; }
.system-intro p { font-size: 12.5px; color: var(--text-muted); }
.layer-flow { display: flex; flex-direction: column; gap: 10px; }
.layer-arrow { display: flex; gap: 12px; align-items: stretch; }
.layer-num {
  width: 44px; flex-shrink: 0; background: var(--c); color: #fff; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 16px;
}
.layer-body {
  flex: 1; background: var(--bg-card); border: 1px solid var(--border-color); border-left: 4px solid var(--c);
  border-radius: 8px; padding: 10px 14px;
}
.layer-name { font-size: 14px; font-weight: 700; color: var(--c); }
.layer-desc { font-size: 12px; color: var(--text-secondary); margin: 3px 0 8px; }
.layer-docs { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  background: var(--c); color: #fff; font-size: 11px; padding: 3px 10px; border-radius: 999px;
  cursor: pointer; opacity: 0.85; transition: opacity .2s;
}
.chip:hover { opacity: 1; }
.principle-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px; }
.principle {
  background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px;
}
.principle b { display: block; font-size: 13px; color: var(--accent); margin-bottom: 4px; }
.principle span { font-size: 11.5px; color: var(--text-secondary); line-height: 1.6; }

@media (max-width: 1100px) {
  .graph-panel { grid-template-columns: 1fr; }
  .principle-row { grid-template-columns: 1fr; }
}
</style>
