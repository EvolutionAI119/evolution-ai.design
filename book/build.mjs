// 《AI 原生软件开发方法论》单文件 HTML 构建脚本
// 用法：node build.mjs
// 输出：ai-native-software-development.zh.html / .en.html（离线可开、含侧边目录、打印样式）

import { readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import MarkdownIt from 'markdown-it'

const __dirname = dirname(fileURLToPath(import.meta.url))

const CHAPTERS = [
  ['00-framework-map',             { zh: '框架地图',                              en: 'Framework Map' }],
  ['01-ai-native-software',        { zh: '第 1 章 · AI 原生软件的定义与边界',      en: 'Ch.1 · Defining AI-Native Software' }],
  ['02-complex-giant-systems',     { zh: '第 2 章 · 开放的复杂巨系统',              en: 'Ch.2 · Open Complex Giant Systems' }],
  ['03-metasynthesis',             { zh: '第 3 章 · 从定性到定量：综合集成方法',     en: 'Ch.3 · Qualitative-to-Quantitative Metasynthesis' }],
  ['04-five-layer-architecture',   { zh: '第 4 章 · 五层架构与薄壳编排',            en: 'Ch.4 · Five-Layer Architecture & Thin Orchestration' }],
  ['05-dual-geometry-core',        { zh: '第 5 章 · 一个向量，四种表达',            en: 'Ch.5 · One Vector, Four Expressions' }],
  ['06-contract-first-interfaces', { zh: '第 6 章 · 契约优先的接口设计',            en: 'Ch.6 · Contract-First Interface Design' }],
  ['07-unified-workbench-frontend',{ zh: '第 7 章 · 统一工作台：12 个页面的信息架构', en: 'Ch.7 · Unified Workbench: 12 Pages' }],
  ['08-bayesian-optimization',     { zh: '第 8 章 · 代理模型与贝叶斯优化',          en: 'Ch.8 · Surrogate Models & Bayesian Optimization' }],
  ['09-dl-llm-fusion',             { zh: '第 9 章 · 深度学习与 LLM 融合层',         en: 'Ch.9 · DL & LLM Fusion Layer' }],
  ['10-semantic-interfaces',       { zh: '第 10 章 · 语义接口：从纹理到品牌 DNA',   en: 'Ch.10 · Semantic Interfaces: Texture to Brand DNA' }],
  ['11-testing-pyramid',           { zh: '第 11 章 · 测试金字塔与 1000+ 例基线',     en: 'Ch.11 · Testing Pyramid & the 1000+ Baseline' }],
  ['12-observability-audit',       { zh: '第 12 章 · 可观测性与全链路审计',         en: 'Ch.12 · Observability & Full-Chain Audit' }],
  ['13-security-guardrails',       { zh: '第 13 章 · 安全围栏与游客模式',           en: 'Ch.13 · Security Guardrails & Guest Mode' }],
  ['14-build-deploy-release',      { zh: '第 14 章 · 构建、部署与发布',             en: 'Ch.14 · Build, Deploy & Release' }],
  ['15-general-design-department', { zh: '第 15 章 · 总体设计部：人机结合的研讨厅', en: 'Ch.15 · The General Design Department' }],
  ['16-knowledge-document-system', { zh: '第 16 章 · 文档即产品：知识底座与一致性审计', en: 'Ch.16 · Docs as Product: Knowledge Base & Consistency Audit' }],
  ['17-team-roles-rhythm',         { zh: '第 17 章 · AI 原生团队的角色与节奏',      en: 'Ch.17 · Roles & Rhythm of AI-Native Teams' }],
  ['18-fast-slow-variables',       { zh: '第 18 章 · 快变量与序参量：深度演化七项纲领', en: 'Ch.18 · Fast/Slow Variables: Seven Guidelines' }],
  ['appendix-a-glossary',          { zh: '附录 A · 术语表',                         en: 'Appendix A · Glossary' }],
  ['appendix-b-checklists',        { zh: '附录 B · 检查清单',                       en: 'Appendix B · Checklists' }],
  ['appendix-c-baseline-facts',    { zh: '附录 C · 本平台事实基线',                 en: 'Appendix C · Baseline Facts' }],
  ['appendix-d-references',        { zh: '附录 D · 参考文献',                       en: 'Appendix D · References' }],
]

const md = new MarkdownIt({ html: true, linkify: true, breaks: false })

function inlineImages (html, lang) {
  // 把相对 SVG 路径内联为 data URI，实现单文件离线阅读
  return html.replace(/<img([^>]*?)src="([^"]+\.svg)"([^>]*)>/g, (m, pre, src, post) => {
    try {
      const p = join(__dirname, src) // 章节中的 ../docs/images/... 以 book/ 为基准解析
      const svg = readFileSync(p)
      const b64 = svg.toString('base64')
      return `<img${pre}src="data:image/svg+xml;base64,${b64}"${post}>`
    } catch {
      console.warn('  ⚠ 缺失图片: ' + src)
      return m
    }
  })
}

function render (lang) {
  const isZh = lang === 'zh'
  const parts = []
  const toc = []
  for (const [slug, title] of CHAPTERS) {
    const file = join(__dirname, lang, slug + '.md')
    let raw
    try { raw = readFileSync(file, 'utf-8') } catch { console.warn(`  ⚠ 缺章：${lang}/${slug}.md`); continue }
    const body = inlineImages(md.render(raw), lang)
    const t = title[lang]
    toc.push(`<li><a href="#${slug}">${t}</a></li>`)
    parts.push(`<section class="chapter" id="${slug}"><div class="chapter-body">${body}</div></section>`)
  }
  const bookTitle = isZh ? 'AI 原生软件开发方法论' : 'AI-Native Software Development Methodology'
  const subTitle  = isZh ? '从复杂巨系统到可验证交付' : 'From Complex Giant Systems to Verifiable Delivery'
  const author    = isZh ? '量子剑客' : 'Quantum Swordsman'
  const tocHead   = isZh ? '目录' : 'Contents'
  const html = `<!doctype html>
<html lang="${isZh ? 'zh-CN' : 'en'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${bookTitle} · ${subTitle}</title>
<style>
:root { --ink:#0F1622; --line:#1E2A3A; --fg:#E2E8F0; --mut:#94A3B8; --dim:#64748B; --acc:#34D399; --acc2:#38BDF8; }
* { box-sizing: border-box; }
body { margin:0; background:var(--ink); color:var(--fg); font-family:-apple-system,"Segoe UI","Microsoft YaHei",Roboto,sans-serif; line-height:1.75; }
.layout { display:grid; grid-template-columns:280px 1fr; max-width:1280px; margin:0 auto; }
aside.toc { position:sticky; top:0; height:100vh; overflow:auto; padding:32px 20px; border-right:1px solid var(--line); }
aside.toc h2 { font-size:14px; color:var(--acc); letter-spacing:.08em; margin:0 0 12px; }
aside.toc ol { list-style:none; padding:0; margin:0; }
aside.toc li { margin:6px 0; }
aside.toc a { color:var(--mut); text-decoration:none; font-size:13px; }
aside.toc a:hover { color:var(--acc2); }
main { padding:48px 56px; max-width:880px; }
header.cover { margin-bottom:48px; padding-bottom:32px; border-bottom:1px solid var(--line); }
header.cover h1 { font-size:34px; margin:0 0 8px; color:var(--fg); }
header.cover .sub { color:var(--acc); font-size:16px; margin:0 0 4px; }
header.cover .author { color:var(--dim); font-size:13px; }
section.chapter { margin-bottom:64px; }
section.chapter h1 { font-size:26px; color:var(--acc2); border-left:4px solid var(--acc); padding-left:14px; margin-top:0; }
section.chapter h2 { font-size:20px; color:var(--fg); margin-top:36px; }
section.chapter h3 { font-size:16px; color:var(--acc2); margin-top:24px; }
section.chapter p, section.chapter li { font-size:14.5px; color:var(--fg); }
section.chapter blockquote { border-left:3px solid var(--acc); padding:4px 16px; margin:16px 0; color:var(--mut); background:#0c1220; }
section.chapter code { background:#0c1220; padding:2px 6px; border-radius:4px; font-size:13px; color:var(--acc2); }
section.chapter pre { background:#0c1220; padding:16px; border-radius:8px; overflow:auto; border:1px solid var(--line); }
section.chapter pre code { background:none; padding:0; color:var(--fg); }
section.chapter table { border-collapse:collapse; width:100%; margin:16px 0; font-size:13.5px; }
section.chapter th, section.chapter td { border:1px solid var(--line); padding:8px 12px; text-align:left; }
section.chapter th { background:#0c1220; color:var(--acc); }
section.chapter figure.doc-figure { margin:24px 0; padding:16px; background:#0c1220; border:1px solid var(--line); border-radius:8px; }
section.chapter figure.doc-figure img { max-width:100%; height:auto; display:block; margin:0 auto; }
section.chapter figcaption { margin-top:12px; font-size:13px; color:var(--mut); }
section.chapter figcaption strong { color:var(--acc); }
@media print {
  body { background:#fff !important; color:#000 !important; }
  aside.toc { display:none !important; }
  .layout { grid-template-columns:1fr !important; }
  main { max-width:none !important; padding:24px !important; }
  /* 白底强制可读：正文区内一切文字转纯黑，底色转浅灰 */
  main, main * { color:#000 !important; background-color:transparent !important; border-color:#888 !important; text-shadow:none !important; }
  main th { background:#e8e8e8 !important; }
  main pre, main code, main blockquote { background:#f2f2f2 !important; }
  main figure.doc-figure { background:#fff !important; border:1px solid #888 !important; }
  /* 字号与行距：打印可读性优先 */
  main p, main li, main td, main th, main blockquote { font-size:12pt !important; line-height:1.8 !important; }
  main h1 { font-size:22pt !important; }
  main h2 { font-size:16pt !important; }
  main h3 { font-size:13pt !important; }
  header.cover h1 { font-size:30pt !important; }
  header.cover .sub { font-size:14pt !important; }
  section.chapter { page-break-before:always; }
}
@media (max-width:960px) { .layout { grid-template-columns:1fr; } aside.toc { position:static; height:auto; border-right:none; border-bottom:1px solid var(--line); } main { padding:24px; } }
</style>
</head>
<body>
<div class="layout">
<aside class="toc"><h2>${tocHead}</h2><ol>${toc.join('\n')}</ol></aside>
<main>
<header class="cover">
  <h1>${bookTitle}</h1>
  <p class="sub">${subTitle}</p>
  <p class="author">${isZh ? '著者' : 'by'} ${author} · v1.0 · 2026-10</p>
</header>
${parts.join('\n<hr style="border:none;border-top:1px dashed var(--line);margin:48px 0;">\n')}
</main>
</div>
</body>
</html>`
  const out = join(__dirname, `ai-native-software-development.${lang}.html`)
  writeFileSync(out, html)
  const kb = (html.length / 1024).toFixed(1)
  console.log(`✓ ${isZh ? '中文' : 'English'} → ${out.split(/[\\/]/).pop()} (${kb} KB, ${parts.length} 章)`)
}

console.log('构建《AI 原生软件开发方法论》单文件 HTML…')
render('zh')
render('en')
console.log('完成。')
