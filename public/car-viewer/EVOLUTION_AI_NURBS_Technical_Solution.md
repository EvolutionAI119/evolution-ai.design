# EVOLUTION AI — 3D NURBS曲面模型导入导出生成编辑 综合技术方案

## v2.0 — SOLO架构重构版

> 基于"单任务聚焦"(SOLO)理念，将原有17+按钮、8个浮动面板、4个标签页简化为**2个核心标签页 + 5个核心操作**的极简工作流。

---

## 一、现状问题诊断

### 1.1 当前UI组件清单（过度复杂）

| 层级 | 组件 | 数量 | 问题 |
|------|------|------|------|
| Topbar | 工具栏按钮 | **17个** | 信息过载，功能重叠 |
| 右面板 | 标签页 | **4个** | "关系"/"活动"与NURBS无关 |
| 左侧板 | 对象浏览器 + 动作 | **7+7=14个元素** | 与Topbar重复 |
| 浮动面板 | 独立弹窗 | **8个** | 遮挡3D视口，交互混乱 |
| 模态框 | 导入/导出对话框 | **1个** | 脱离主流程 |

### 1.2 核心矛盾

```
用户目标: 定义参数 → 构建NURBS → 分析曲率 → 导出文件
当前路径: 在17个按钮中找 → 切换到正确标签 → 打开某个浮动面板
         → 关闭遮挡视口的弹窗 → 找到导出格式 → 完成
期望路径: 参数页调参 → 点击"构建" → NURBS页看曲面 → 导出
```

---

## 二、SOLO重构方案

### 2.1 设计哲学

借鉴 **SOLO (Simple Online & Realtime tracking of Objects)** 的核心理念：

| SOLO原则 | 本项目应用 |
|----------|-----------|
| **单一职责** | 每个标签页只做一件事 |
| **即时反馈** | 调参→实时预览，无需额外确认 |
| **零遮挡** | 取消所有浮动面板，全部内嵌 |
| **渐进披露** | 基础功能默认可见，高级功能按需展开 |

### 2.2 新UI布局效果图

![SOLO重构后新UI布局](./assets/solo_ui_layout.png)

*图：SOLO重构后的极简UI布局 — 左侧参数面板 + 中央3D视窗(最大化) + 右侧NURBS分析面板*

```
┌─────────────────────────────────────────────────────────┐
│  [Topbar]  EVOLUTION AI  │ [▶生成] [📥导入] [📤导出] [⚙️]  │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  [参数]   │              3D 视窗区                        │
│ ┌──────┐ │          (Three.js WebGL)                   │
│ │尺寸  │ │                                              │
│ │硬点  │ │                                              │
│ │造型  │ │        ○── NURBS 曲面预览                    │
│ │高级  │ │       ╱    ╲                                 │
│ ├──────┤ │      ╱      ╲                                │
│ │显示  │ │     ╱________╲                               │
│ │重置  │ │                                              │
│ └──────┘ │                                              │
│          │                                              │
│  [NURBS]  │                                              │
│ ┌──────┐ │                                              │
│ │信息  │ │                                              │
│ │控制点│ │                                              │
│ │曲率图│ │                                              │
│ └──────┘ │                                              │
├──────────┴──────────────────────────────────────────────┤
│  [状态栏] L:4880 W:1860 H:1450 | NURBS: 6×4 有理 | FPS:60│
└─────────────────────────────────────────────────────────┘
```

### 2.3 SOLO精简对比

![UI精简前后对比](./assets/solo_before_after.png)

*图：左=BEFORE（17按钮+8浮动面板+4标签），右=AFTER SOLO（5按钮+2标签+零浮动面板）*

### 2.4 标签页精简

| 原4标签 | 新2标签 | 说明 |
|---------|---------|------|
| **参数** | **参数** (保留) | 21硬点滑块 + 显示选项 + 重置 |
| **关系** | ~~删除~~ | 合并到参数页底部"参数关系图" |
| **活动** | ~~删除~~ | 合并到状态栏时间线 |
| **NURBS** | **NURBS** (保留) | 控制点网格 + 曲率热力图 + 节点向量 |

### 2.5 操作按钮精简

| 原Topbar (17按钮) | 新Topbar (5按钮) | 归属 |
|-------------------|-----------------|------|
| 旋转/驾驶/颠簸 | ~~合并到~~ **[⚙️]** | 设置下拉 |
| 线框/斑马纹 | **[⚙️]显示模式** | 设置下拉 |
| 加载STL | **[📥导入]** | 导入按钮下拉(支持STL/IGES/STEP) |
| 导入模型 | 合并到**[📥导入]** | 同上 |
| 导出 | **[📤导出]** | 导出按钮下拉(6格式) |
| 标杆 | **[标杆]** | 移至状态栏 |
| 方法论/AI辅助/自主学习 | ~~删除~~ | 移至独立文档页面 |
| 参考/多视角/自进化 | ~~删除~~ | 移至设置面板 |
| 深度学习/多模态 | ~~删除~~ | 后台运行，不占UI |

### 2.6 浮动面板清零

原8个浮动的处理方式：

| 原浮动画板 | 处理方式 |
|-----------|---------|
| 标杆参考(refpanel) | 移入NURBS标签页"对标分析"折叠区 |
| 方法论(methpanel) | 移至独立`/docs`路由或帮助菜单 |
| AI辅助(aipanel) | 合并到NURBS标签页"AI优化"按钮 |
| 多视角(mvpanel) | 移入3D视口内嵌控制条 |
| 自进化(godelpanel) | 合并到NURBS标签页"自进化"折叠区 |
| 深度学习(dlpanel) | 后台自动运行，结果在状态栏展示 |
| 多模态(multipanel) | 合并到导入面板的多格式选项 |
| 自学习(learnelpanel) | 移入NURBS标签页"质量评分"区域 |

---

## 三、核心技术架构

### 3.1 数据流

![核心数据流架构](./assets/data_flow_architecture.png)

*图：21硬点参数 → deriveHardpoints()推导 → buildNURBSSurface()构建 → Three.js渲染/IGES-STEP导出*

```
┌─────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│ 21硬点  │ ──► │ deriveHardpoints│ ──► │buildNURBSSurface│ ──► │ Three.js  │
│ HP对象  │     │ (22二级硬点)   │     │ (8U×5V CP网)   │     │ BufferGeo │
└─────────┘     └──────────────┘     └─────────────┘     └──────────┘
                     │                      │                    │
                     ▼                      ▼                    ▼
              ┌──────────────┐     ┌─────────────┐     ┌──────────┐
              │ 双包络轮廓    │     │nurbsToBuffer│     │  渲染     │
              │ 三区截面混合  │     │ Geometry镶嵌 │     │  交互     │
              └──────────────┘     └─────────────┘     └──────────┘
                     │                      │
                     ▼                      ▼
              ┌──────────────────────────────────────┐
              │           导出层                       │
              │  IGES(Entity128) / STEP(AP214)        │
              │  STL(ASCII/Bin) / OBJ                  │
              └──────────────────────────────────────┘
```

### 3.2 NURBS数学引擎7模块

| 模块 | 函数 | 功能 |
|------|------|------|
| M1 数学引擎 | findKnotSpan / nurbsBasisFunctions / nurbsSurfacePoint / nurbsSurfaceDerivatives / nurbsSurfaceNormal | Cox-deBoor递归、Piegl&Tiller基函数、张量积求值、偏导数 |
| M2 曲面构建器 | buildNURBSSurface / clampedKnotVector / openUniformKnotVector | 从21硬点→8U×5V双三次有理B样条控制网格 |
| M3 自适应镶嵌 | nurbsToBufferGeometry / surfaceCurvature | 曲率>0.5区域2级细分→Y轴镜像→THREE.BufferGeometry |
| M4 曲率分析 | computeCurvatureMap / curvatureCombData | 高斯K/平均H/主曲率k1k2/曲率梳可视化数据 |
| M5 IGES导出 | generateIGESNURBS / padIgesField / formatIgesNumber | Entity 128(S/G/D/P/T五节)，roundtrip CP diff=0 |
| M6 STEP导出 | generateSTEPNURBS / computeKnotMultiplicities | AP214 B_SPLINE_SURFACE_WITH_KNOTS + RATIONAL + CLOSED_SHELL |
| M7 IGES导入 | parseIGESDESection / parseIGESPDSection / parseIGESNURBS | Entity 128完整解析，验证6×4 CP/3×3度/10+8节点 |

### 3.3 NURBS曲面渲染效果

![NURBS车身曲面渲染](./assets/nurbs_surface_render.png)

*图：基于21硬点参数构建的8U×5V双三次有理B样条NURBS车身曲面 — 青蓝色线框模式，控制点以洋红色标记*

### 3.4 21参数硬点体系

```
HP (Primary Hardpoints, 21维)
├── 尺寸 (9): L车长/W车宽/H车高/WB轴距/FO前悬/RO后悬/GC离地/WR轮径/TW轮距
├── 造型 (12):
│   ├── 角度 (3): AA A柱角 / RA Raked角 / CA C柱角
│   ├── 比值 (3): WL腰线高 / SW肩部宽比 / Bulge轮拱隆起
│   └── 高级 (6): HS引擎盖斜率 / DR行李箱高比 / TH tumblehome
│                / FF翼子板外扩 / SP风斗位置 / RT后部收缩

deriveHardpoints() 推导链:
21主参数 → 22二级硬点(h.aBaseX/h.aTopX/h.roofPeakX/h.cTopX/h.cBaseX
            h.fwx/h.fwz/h.rwx/topWidthProfile/sideUpperProfile)
    → 双包络轮廓(上包络/下包络)
    → 三区截面混合(A柱/C柱/D柱截面)
    → BufferGeometry
```

### 3.5 曲率分析可视化

![曲率热力图](./assets/curvature_heatmap.png)

*图：NURBS曲面平均曲率热力图 — 蓝(低曲率平坦区) → 绿 → 黄 → 红(高曲率尖锐边)，含色条图例与统计摘要*

---

## 四、实施步骤

### Phase 1: UI骨架重组 ✅ 已完成

- [x] NURBS标签页移入右侧面板(#rptNurbs)
- [x] 控制点表格优化(分行XYZ+权重高亮+交替行+图例)
- [x] 曲率热力图优化(4色渐变+色条图例+统计摘要+交替行)
- [x] "生成模型"按钮(延迟构建，初始无3D模型)
- [x] showNURBSPanel自动切换标签

### Phase 2: SOLO精简 🔄 进行中

- [ ] Topbar从17按钮精简为5个核心操作
- [ ] 删除"关系""活动"标签，内容归并
- [ ] 清除8个浮动面板，功能内嵌到对应标签页
- [ ] 左侧板精简或隐藏(移动端适配时折叠)
- [ ] 状态栏增加NURBS实时信息(度数/CP数/节点/有理性)

### Phase 3: 后端API对齐 ⏳ 待实施

- [ ] `POST /api/v1/nurbs/build` — 从硬点构建NURBS曲面
- [ ] `POST /api/v1/nurbs/export/{format}` — IGES/STEP/OBJ导出
- [ ] `GET /api/v1/nurbs/curvature` — 曲率分析数据
- [ ] `GET /api/v1/nurbs/control-points` — 控制点网格JSON
- [ ] `POST /api/v1/nurbs/import` — 上传IGES/STEP解析Entity128

### Phase 4: 文档闭环 ✅ 本任务完成

- [x] 技术方案文档 ✅ (本文档)
- [x] 架构示意图 (SOLO UI布局效果图)
- [x] 数据流图 (核心数据流架构图)
- [x] NURBS渲染效果图 (车身曲面预览)
- [x] 曲率分析效果图 (热力图可视化)
- [x] SOLO对比图 (精简前后对照)

---

## 五、关键修复记录 (已解决)

| # | 问题 | 修复 | 验证 |
|---|------|------|------|
| F1 | extractHPFromGeometry只反推9参数 | 扩展到21参数+mkDiff函数 | Node.js PASS |
| F2 | displayImportedParams角度×1000错误 | 角度显示°后缀，比值显示3位小数 | Browser OK |
| F3 | impBtnApply只应用13参数且>0限制 | 扩展21参数移除限制 | Browser OK |
| F4 | showImpImportTab innerHTML重建后onclick丢失 | 重建后立即重新绑定onclick | Browser OK |
| F5 | STEP CARTESIAN_POINT缺坐标括号 | 添加(x,y,z)括号包裹 | Node.js PASS |
| F6 | STEP引号嵌套语法错误 | 外层单引号改双引号 | Node.js PASS |
| F7 | IGES K/K2值错误(K=节点数-1而非CP数-1) | K=numU-1/K2=numV-1 | Node.js PASS |
| F8 | IGES P节格式pl+' '+chk(73字符被截断) | 改为pl+chk(72字符刚好) | Roundtrip diff=0 |
| F9 | NURBS面板在importPanel中不可见 | 提升到rpanel一级标签页#rptNurbs | Browser OK |
| F10 | 页面初始化自动构建3D模型 | 添加modelGenerated标志+生成按钮 | Browser OK |

---

## 六、文件清单

| 文件 | 行数/大小 | 说明 |
|------|----------|------|
| `index.html` | ~6592行 | 单文件应用(HTML+CSS+JS全部内联)，含NURBS引擎7模块 |
| `sample_nurbs.igs` | 20行/1539字节 | IGES v5.3 Entity 128测试文件(6×4 CP, K=5/K2=3) |
| `EVOLUTION_AI_NURBS_Technical_Solution.md` | ~280行 | 本技术方案文档(含5张配图) |

---

## 七、附录：图片索引

| # | 图片 | 用途 | 链接 |
|---|------|------|------|
| P1 | SOLO UI布局 | 新版极简界面效果图 | ![P1](./assets/solo_ui_layout.png) |
| P2 | 精简前后对比 | BEFORE vs AFTER SOLO | ![P2](./assets/solo_before_after.png) |
| P3 | 数据流架构 | 21HP→推导→NURBS→渲染/导出 | ![P3](./assets/data_flow_architecture.png) |
| P4 | NURBS曲面渲染 | 车身线框+控制点预览 | ![P4](./assets/nurbs_surface_render.png) |
| P5 | 曲率热力图 | 4色渐变曲率分析可视化 | ![P5](./assets/curvature_heatmap.png) |

---

*文档版本: v2.0-SOLO*
*最后更新: 2026-06-27*
*作者: EVOLUTION AI Team*
