---
name: project-intro-deck
description: 为 EVOLUTION-AI.DESIGN 平台生成中英文项目介绍 PPT，最大可视化且无字符重叠。用于用户要求生成PPT、项目介绍演示文稿、更新介绍幻灯片时。不用于生成其他文档。
---

# 项目介绍 PPT 生成

为 EVOLUTION-AI.DESIGN 生成 16:9 项目介绍 PPT（中文 + 英文两个独立文件，每版 12 页）。目标：最大化图像可视化、图片完整不裁剪、零字符重叠、每页含 evolution-ai.design。

## 环境（本机 Windows，已验证可用）

- Python 包：`python-pptx`、`Pillow`（已装）；Node 包 `sharp` 装在 `%TEMP%\svgconv`（已装，丢失则 `npm install sharp`）
- Git 不在 PATH，需要时用 `"C:\Program Files\Git\bin\git.exe"`
- PowerPoint 可能占用旧版 pptx：覆盖报 `PermissionError` 时改用带版本号的新文件名，不要重试

## 素材清单（只允许使用仓库自有资产）

| 类型 | 路径 |
|------|------|
| 算法渲染 PNG（整车 NURBS/车身/四视图/连续性） | `data/step/*.png`（如 full_car_nurbs.png、body_nurbs_visual.png、continuity_attached_four_view.png） |
| 19 车型正侧视图 | `public/brands/<brand>/<model>.jpg` |
| 架构/流程 SVG（中文版） | `docs/images/*.svg` |
| 架构/流程 SVG（英文版，CN 版禁止混用） | `docs/images/en/*.svg` |
| 网页实拍截图 | 用浏览器代理截 `https://evolution-ai.design/#/` 与 `/#/help`，存 `%TEMP%\evo_ppt_shots\` |

已验证的关键 SVG：whitepaper-arch、paper-nurbs-pipeline、arch-dataflow、product-journey、method-pipeline、integration-flow、validation-metrics、api-lifecycle、meta-10dims。

## 执行流程

### 1. 素材准备

- 盘点素材是否存在；截图缺失时启动 browser_use 代理：游客态、不登录、1920×1080 视口，等待 3D 区渲染稳定后截全页
- 用 sharp 将 SVG 批量转 PNG（density 200）：`node scripts/svg_to_png.cjs`（按需修改其中的文件列表与输出目录；仓库 package.json 为 ESM，脚本必须用 .cjs）

### 2. 图片预处理：fit-contain（严禁裁剪）

每张原图等比缩放到目标区域（缩放比 = min(区宽/图宽, 区高/图高)），居中合成到 BG 底色画布（RGB 8,12,22），输出 PNG 再嵌入。参考 v4 实现的 `zone()` 函数，缓存在 `%TEMP%\evo_zones\`。

### 3. 构建幻灯片（规则不可破）

几何与版式细则见 `references/layout-spec.md`，硬规则：

1. **添加顺序即 z 序**：背景 → 图片 → 遮罩/装饰 → 文字。严禁 send_to_back / 调整 XML 层级（曾导致图片被压到背景下整片消失）
2. **坐标全部落在安全区**：body y∈[1.50, 6.92]；页脚 y≥7.06；任何元素不得越界
3. **文字框高度按内容反推**：高度 ≥ 行数 × 字号 × 1.22/72 + 内边距；描述文案先按卡片宽度估算是否换行，两行必须预留两行高度
4. **图片间距优先压缩，不压图片**：卡片行距 0.08–0.2，通过缩小间距填满区域，而不是放大图片或裁掉内容
5. 半透明遮罩用 XML `a:alpha`（封底约 58%），不要用不透明实色（会盖死全幅图）
6. 每页底部页脚：左 `evolution-ai.design`，右 `参数化 × AI 驱动` / `Parametric × AI-Driven`

标准 12 页结构：封面 / 六层架构 / 曲面引擎 / 品牌知识库（2×3 车网格）/ AI 创意四路径 / LLM 服务 / HELP 知识地图 / Dashboard 体验 / 数据与安全 / 部署架构 / 能力总览（底部 URL 横幅）/ 封底。

### 4. 验证（必须通过才能交付）

```
python scripts/check_collisions.py <pptx路径>
```

要求输出 `issues: 0`：检测全部形状越界、文本框两两相交、图片两两碰撞。发现问题先修坐标/文案再重新生成，禁止盲调。

### 5. 拆分中英版并交付

从合集删除 slideId（前 12 页=中文，后 12 页=英文），分别保存。默认输出到仓库根目录，带版本号文件名；文件为 untracked，是否入库由用户决定。完成后列出三个文件（合集+中+英）及大小，并提醒可清理的旧版本。

## 历史教训（勿重犯）

- 截图 1864×1376（≈1.355 比例）直接塞进 16:9 框会拉伸变形 → fit-contain
- 旧版 P7/P8 说明卡片 y=7.195 完全滑出幻灯片 → 安全区约束
- 封面英文 42pt 大标题溢出与网址重叠 → 英文标题用 27–30pt，多行排
- 用户会反复要求优化：每次先用可计算的碰撞检测定位问题，只对冲突点做局部修正，不要整体重排导致版式漂移
