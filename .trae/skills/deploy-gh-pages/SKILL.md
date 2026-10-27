---
name: "deploy-gh-pages"
description: "把本地 dist/ 完整同步到 gh-pages 工作树并提交推送，部署 https://evolution-ai.design。当需要发布公网、更新站点内容、修复公网黑屏/404、或用户说部署/推送线上时使用。严禁只同步部分目录——漏同步 assets/ 会导致黑屏。"
---

# deploy-gh-pages：dist/ → gh-pages 完整同步部署

公网站点 `https://evolution-ai.design` 由 **GitHub Pages 的 `gh-pages` 分支**驱动（不是 main）。部署 = 把 `dist/` 全量同步到工作树并推送。

## 路径约定

| 项 | 值 |
|---|---|
| 项目根 | `d:\API\Evolution-Ai.Design` |
| gh-pages 工作树 | `D:\ghp-deploy-tmp`（分支 `gh-pages`） |
| 公网 | `https://evolution-ai.design` |

## 关键教训（血泪）

> **`index.html` 引用的哈希资产必须与 gh-pages 上的 `assets/` 完全一致，缺一个就黑屏。**
> 每次 `npm run build` 都会改变入口哈希名（如 `index-Ca78XK9Y.js`）。只同步 `docs/` + `index.html` 而不同步 `assets/` 是已发生过的黑屏事故根因。

## 执行步骤

### 1. 构建

```powershell
cd d:\API\Evolution-Ai.Design
npm run build
```

### 2. 全量同步（不是挑目录）

```powershell
# 同步整个 dist/* 到工作树——assets/ docs/ images/ brands/ gallery/ index.html favicon 等全部
Copy-Item -Path "d:\API\Evolution-Ai.Design\dist\*" -Destination "D:\ghp-deploy-tmp" -Recurse -Force
```

### 3. 暂存（含被删除的旧哈希资产）

```powershell
# -A 才能捕获旧哈希资产被新构建删除的情况；否则会残留旧文件、新文件缺失
git -C D:\ghp-deploy-tmp add -A
git -C D:\ghp-deploy-tmp status --short | Where-Object { $_ -match '^[MADR]' }
```

若只想加白名单顶层项（保留工作树里的草稿），至少必须包含：`assets index.html docs images brands gallery favicon.svg favicon.ico`——**`assets` 绝不可省略**。

### 4. 提交（信息格式）

```powershell
$sha = git -C d:\API\Evolution-Ai.Design rev-parse --short HEAD
git -C D:\ghp-deploy-tmp commit -m "deploy: <本次改动说明> (main $sha)"
```

### 5. 推送（会过专利守卫）

```powershell
git -C D:\ghp-deploy-tmp push origin gh-pages
```

### 6. 发布后验证（必须做）

GitHub Pages 发布有延迟（约 15–60 秒），用 `?_cb=` 缓存破坏参数绕过 CDN 校验：

```powershell
Start-Sleep -Seconds 30
$cb = Get-Date -UFormat %s

# a. 取 index.html 引用的全部资产并逐一 HEAD 校验
$h = (Invoke-WebRequest "https://evolution-ai.design/?_cb=$cb" -UseBasicParsing).Content
[regex]::Matches($h, 'assets/[^"'']+\.(js|css)') | ForEach-Object { $_.Value } | Select-Object -Unique | ForEach-Object {
  try { $r = Invoke-WebRequest "https://evolution-ai.design/$_?_cb=$cb" -Method Head -UseBasicParsing -TimeoutSec 15; "$_ -> $($r.StatusCode)" }
  catch { "$_ -> 404  ← 黑屏风险，立即排查" }
}

# b. 抽查双语文档语言正确
"https://evolution-ai.design/docs/EVOLUTION_AI_paper.md?_cb=$cb"      # 首行应为中文（贝叶斯）
"https://evolution-ai.design/docs/en/EVOLUTION_AI_paper.md?_cb=$cb"   # 首行应为英文（Bayesian）
```

**验收标准**：index.html 引用的所有 `assets/*.js` 和 `assets/*.css` 全部 200；中英路径各自返回对应语言。

## 故障速查

| 现象 | 根因 | 处置 |
|---|---|---|
| 公网黑屏、控制台 JS 404 | `assets/` 未同步或哈希不一致 | 重新执行步骤 2–6（全量同步） |
| 文档语言错乱 | 只推了 main 没推 gh-pages | 同上 |
| 推送被专利守卫拦 | 提交内容含受保护关键词 | 改写敏感词后 amend 重推 |
| HEAD 校验 404 但 `git ls-files` 有 | GitHub Pages 发布延迟 | 等 30–60s 用 `?_cb=` 重试 |
