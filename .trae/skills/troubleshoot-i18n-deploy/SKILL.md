---
name: "troubleshoot-i18n-deploy"
description: "培训素材：诊断并修复「帮助中心文档语言与界面语言不一致」及「部署后公网黑屏」两类问题。当用户反馈中文界面显示英文内容、文档数字过期、或公网白屏/黑屏时使用，指导独立定位到具体故障层并完成修复验证。"
---

# 双语内容错位与部署黑屏：标准化排查训练手册

> 本素材提炼自真实案例：用户反馈"学术论文中文界面显示英文"→ 修复后又出现"公网黑屏"。全程共经历 **3 次用户反馈** 才闭环，根本原因是排查停在了错误的层。学完本手册后应能一轮定位。

## 一、问题场景

本项目的文档与站点有 **三层独立的事实源**，症状相同但根因在不同层：

| 层 | 位置 | 服务对象 |
|---|---|---|
| L1 源文件 | `docs/<name>.md`（中文）、`docs/en/<name>.md`（英文） | 磁盘事实 |
| L2 构建产物 | `dist/docs/**`（npm run build 时由 docsPlugin 复制） | 本地 dist / 预览 |
| L3 部署产物 | 远端 `gh-pages` 分支（工作树 `D:\ghp-deploy-tmp`） | 公网 https://evolution-ai.design |

语言路由规则（Help.vue）：中文界面取 `docs/<file>`，英文界面取 `docs/en/<file>`。

两类典型症状：
- **A. 语言错位**：中文界面点了文档节点，正文却是英文（或数字是旧口径）
- **B. 部署黑屏**：公网页面全黑，控制台 JS/CSS 404

## 二、判断标准（分层定位法）

**核心原则：不要假设根因，从 L1 到 L3 逐层探测，每层 30 秒内可证伪。**

```powershell
# L1 磁盘源文件：语言对不对？数字新不新？
Get-Content docs/EVOLUTION_AI_paper.md -TotalCount 2     # 中文应含"贝叶斯"
Select-String docs/EVOLUTION_AI_paper.md -Pattern '153|955'   # 应无旧数字

# L2 本地构建产物（若用户看的是 dist/预览）
Get-Content dist/docs/EVOLUTION_AI_paper.md -TotalCount 2

# L3 部署分支：gh-pages 上的内容才是公网真相
git show origin/gh-pages:docs/EVOLUTION_AI_paper.md | Select-Object -First 2

# L3 公网实测（必须加 ?_cb= 缓存破坏参数，否则测的是 CDN 缓存！）
$cb = Get-Date -UFormat %s
Invoke-WebRequest "https://evolution-ai.design/docs/EVOLUTION_AI_paper.md?_cb=$cb" -UseBasicParsing
```

**判定矩阵**：

| L1 源文件 | L3 gh-pages | 公网实测 | 结论 |
|---|---|---|---|
| 错 | — | — | 源内容问题，修文档 |
| 对 | 错/旧 | 错/旧 | **部署过期**，需同步 gh-pages（最常见） |
| 对 | 对 | 错 | CDN 缓存，加 `?_cb=` 重测即可排除 |
| 对 | 对 | 对 | 用户浏览器缓存，让其 Ctrl+Shift+R |

黑屏专属判定：抓公网 `index.html` 里引用的所有 `assets/*.js|css`，逐一 HEAD：
- 任一 **404** → gh-pages 的 assets 与 index.html 不同步（漏同步）
- 全部 200 → 前端运行时报错，转浏览器控制台排查

## 三、操作流程

### 症状 A：语言错位 / 数字过期

1. 按判定矩阵定位故障层。
2. 源文件错 → 修正内容（双语文件要**成对修改**：`docs/` 与 `docs/en/` 同步改），内嵌 SVG 图表另算（`docs/images/` 中英两份）。
3. 改完跑 `npm run build` 刷新 dist。
4. 部署：见「deploy-gh-pages」skill——**全量同步 dist/*，不许只挑目录**。
5. 验证（见第四节）。

### 症状 B：部署黑屏

1. 抓公网 index.html 资产引用 → 找 404 文件。
2. 对比本地 `dist/assets/` 与 `git -C D:\ghp-deploy-tmp ls-files assets/` 的文件名清单。
3. 缺失即同步：`Copy-Item dist\* D:\ghp-deploy-tmp -Recurse -Force`，然后 `git -C D:\ghp-deploy-tmp add -A`（必须 `-A`，否则旧哈希资产残留、新资产可能漏）。
4. 提交推送：`deploy: <说明> (main <sha>)` → `git push origin gh-pages`。
5. 等 30–60 秒（GitHub Pages 发布延迟），带 `?_cb=` 复验全部资产 200。

## 四、验证方法（验收标准，缺一不可）

```powershell
$cb = Get-Date -UFormat %s
# 1. index.html 引用的所有哈希资产必须全部 200
$h = (Invoke-WebRequest "https://evolution-ai.design/?_cb=$cb" -UseBasicParsing).Content
[regex]::Matches($h, 'assets/[^"'']+\.(js|css)') | ForEach-Object { $_.Value } | Select-Object -Unique | ForEach-Object {
  try { (Invoke-WebRequest "https://evolution-ai.design/$_?_cb=$cb" -Method Head -UseBasicParsing).StatusCode } catch { "$_ 404 ← 不合格" }
}
# 2. 中英路径语言断言
#    docs/EVOLUTION_AI_paper.md      首行含"贝叶斯"、不含 153/955
#    docs/en/EVOLUTION_AI_paper.md   首行含"Bayesian"、不含 153/955
# 3. 首页整体 200
```

全部通过后告知用户：**若仍见旧版，Ctrl+Shift+R 强刷**（CDN/浏览器缓存非故障）。

## 五、注意事项（反模式清单）

1. **禁止无缓存破坏参数测公网**——测到的是 CDN 缓存，会误判"没修好"或"已修好"。
2. **禁止部分目录同步**——每次 build 入口哈希名都变，只同步 `docs/`+`index.html` 而不同步 `assets/` = 必然黑屏（本项目真实事故）。
3. **禁止只推 main 不推 gh-pages**——公网由 gh-pages 驱动，main 推送不影响站点。
4. **双语修改必须成对**——只改中文版会让英文版带着旧数字继续传播；图表 SVG 也有中英两份。
5. **事实数字以 `docs/VALIDATION_REPORT_20261025.md` 为唯一口径**——154 端点（152 路由+2 系统）、1000+ 测试（200 算法/411 后端含 1 skip+2 xfail/416 前端）。
6. **先探测再下结论**——本案第一次回复误判为"浏览器缓存"，实际故障在 gh-pages 层；逐层探测可在首轮就定位。
