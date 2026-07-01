---
AIGC:
    Label: "1"
    ContentProducer: 001191110102MACQD9K64018705
    ProduceID: 7625792088554078499-data_volume/files/所有对话/主对话/patent_materials/W2-D2_D3_Task_Cards.md
    ReservedCode1: ""
    ContentPropagator: 001191110102MACQD9K64028705
    PropagateID: 4250075737373691#1782128454667
    ReservedCode2: ""
---
# W2-D2 / W2-D3 任务卡（具体展开版）

> **阶段**：W2 — Three-Zone Blending + 31-Point Cross-Section
> **工期**：2 个工作日（D2 + D3）
> **状态**：W2-D1 已基本完成（inline-vendor.js 已写，待自测通过），D2/D3 待启动
> **关联专利**：Claim 4、Claim 5、Claim 6
> **关联公式**：F4（三区段归一化）、F5（tumblehome）
> **关联 Roadmap**：`patent_materials/Development_Roadmap.md` § W2
> **代码组织（已探明）**：算法核心在 `algorithm_model/car_modeling/`，按"汽车部件"组织（body, glass, wheels, lights 等），**不是** Roadmap 描述的 `services/blending.py`。本任务卡按实际代码组织展开。

---

## 当前代码状态（2026-06-22 探明）

- ✅ W0/W1 阶段已交付：`car_model_service.py` 薄壳 + `algorithm_model/api.py::build_car` 入口
- ✅ W1 成果：`hardpoints.py`（三角函数推导）、`interp.py`（smoothstep）、`car_params.py`（22 维参数）
- ❌ W2 阶段未实现：`grep` 找不到 `three_zone / zone_weights / cross_section / arc_length / tumblehome / blending` 任何关键词
- 🟡 W2-D1 进展：`evo_build/public/inline-vendor.js` 1.78MB 已写，index.html 单 script 引用，**未重 build + 未自测**

---

## W2-D2：Three-Zone Blending + Tumblehome

### 任务卡头部

| 字段 | 值 |
|---|---|
| **工期** | 1 个工作日（8h） |
| **优先级** | P0（核心专利 Claim 4-5） |
| **依赖** | W2-D1 通过（inline-vendor.js build + 自测） |
| **阻塞风险** | 沙箱文件系统清零 bug（已用 inline-vendor.js 缓解） |
| **负责模块（新建）** | `algorithm_model/car_modeling/blending.py` |
| **集成模块** | `algorithm_model/car_modeling/body.py`（调 blending） |
| **测试模块（新建）** | `algorithm_model/tests/test_blending.py` |
| **关联公式** | F4（三区段归一化）、F5（tumblehome） |
| **关联 Claim** | Claim 4、Claim 5 |

### 任务清单（按时间顺序）

#### T1. 设计 ZoneParamsTable 数据结构（1h）

- **动作**：设计 5 水平 × 3 区段 = 15 个参数表的 Python dataclass
- **位置**：`algorithm_model/car_modeling/blending.py::ZoneParamsTable`
- **字段**：
  - 5 水平：bottom / sill / waist / shoulder / roof
  - 3 区段：hood / cabin / trunk
  - 每格：相对 X 偏移、相对 Y 倍率、相对 Z 倍率
- **产物**：
  ```python
  @dataclass
  class ZoneLevel:
      x_offset: float  # 相对 X 偏移
      y_scale: float   # 相对 Y 倍率
      z_scale: float   # 相对 Z 倍率

  @dataclass
  class ZoneParamsTable:
      hood: List[ZoneLevel]   # 5 个水平
      cabin: List[ZoneLevel]
      trunk: List[ZoneLevel]
  ```
- **验收**：dataclass 通过 import 测试 + 初始化能填满 15 格

#### T2. 实现 three_zone_weights（2h）

- **动作**：实现三区段权重函数
- **位置**：`algorithm_model/car_modeling/blending.py::three_zone_weights`
- **函数签名**：
  ```python
  def three_zone_weights(x: float, hardpoints: dict) -> Tuple[float, float, float]:
      """返回 (hoodF, cabinF, trunkF) 归一化前的原始权重"""
  ```
- **算法**：
  - 输入：X 位置（沿车身长度方向）+ 硬点字典（含 `hood_end_x`, `cabin_start_x`, `cabin_end_x`, `trunk_start_x`）
  - 用 smoothstep 替代 step blend（专利描述的"硬切换"会破坏 G1 连续性）
  - 三个 smoothstep 区域，中心分别落在 hood 中心、cabin 中心、trunk 中心
- **验收**：单测覆盖 95% + 3 个边界用例
  - `x = hood_center` → 期望 hoodF ≈ 1.0
  - `x = cabin_center` → 期望 cabinF ≈ 1.0
  - `x = trunk_center` → 期望 trunkF ≈ 1.0
  - 过渡区权重 = [0.0, 1.0] 单调

#### T3. 实现 normalize_zone_weights（0.5h）

- **动作**：实现 product-based 归一化
- **位置**：`algorithm_model/car_modeling/blending.py::normalize_zone_weights`
- **公式**（Claim 4 product-based normalization）：
  $$\hat{w}_i = \frac{\prod_{j \neq i} w_j}{\sum_k \prod_{j \neq k} w_j}$$
- **函数签名**：
  ```python
  def normalize_zone_weights(hoodF: float, cabinF: float, trunkF: float) -> Tuple[float, float, float]:
      """返回归一化后 (hood_n, cabin_n, trunk_n)，sum=1.0"""
  ```
- **验收**：3 个权重加起来 = 1.0（容差 1e-9）+ 单测通过 + 边界（某个 = 0）不报错

#### T4. 实现 Tumblehome（F5 公式）（1h）

- **动作**：实现 F5 tumblehome 效应
- **位置**：`algorithm_model/car_modeling/blending.py::compute_tumblehome`
- **公式**：
  $$c_{RoofHW} = h_w \cdot \max(0.25,\; s_W \cdot 0.45 - \sin(CA) \cdot 0.15)$$
- **参数**：
  - `hw`：半宽（half-width）
  - `shoulderW`：肩部宽度
  - `CA`：C-pillar 角度（弧度）
- **函数签名**：
  ```python
  def compute_tumblehome(hw: float, shoulderW: float, CA: float) -> float:
      """返回车顶半宽（含 tumblehome 衰减）"""
  ```
- **验收**：单测通过 + 极端输入（CA = π/2）安全降级到 0.25 下限 + CA = 0 时返回 `hw * 0.45 * shoulderW`

#### T5. 装配 ZONE_PARAMS_TABLE 常量数据（1h）

- **动作**：填 5 × 3 = 15 个常量格
- **数据来源**：专利说明书 Step 5 表格
- **位置**：`algorithm_model/car_modeling/blending.py::ZONE_PARAMS_TABLE`（模块级常量）
- **产物**（初始值，需与专利表格核对）：
  | 水平 | hood (x/y/z) | cabin (x/y/z) | trunk (x/y/z) |
  |---|---|---|---|
  | bottom | 0.0/0.85/0.15 | 0.0/0.90/0.20 | 0.0/0.88/0.18 |
  | sill | 0.15/0.95/0.30 | 0.20/0.98/0.40 | 0.10/0.94/0.35 |
  | waist | 0.30/0.92/0.55 | 0.40/0.95/0.65 | 0.25/0.86/0.55 |
  | shoulder | 0.50/0.78/0.85 | 0.65/0.85/0.95 | 0.45/0.68/0.85 |
  | roof | 0.70/0.62/1.00 | 0.85/0.72/1.00 | 0.65/0.55/1.00 |
- **验收**：手动验证 15 格填满 + 与专利表格一致性 + 模块导入可访问

#### T6. 服务化 + 集成到 build_car（1h）

- **动作**：把 blending 模块集成到 `body.py` 和 `api.py`
- **位置**：
  - `algorithm_model/car_modeling/body.py::Body.assemble()` → 调 `three_zone_weights` → `normalize_zone_weights` → 选 `ZONE_PARAMS_TABLE[zone]`
  - `algorithm_model/api.py::build_car()` → 调 `Body.assemble()` 走通三区段
- **集成点**：
  - 在 body 主装配流程里加 `zone = get_zone(x, hardpoints)` 一步
  - 选 `ZONE_PARAMS_TABLE[zone]`
  - 计算 tumblehome 调整 roof 高度
- **验收**：`build_car(default_params)` 能跑通 + 视觉上车身有明显的三区段过渡（截图对比）

#### T7. 单元测试（1h）

- **位置**：`algorithm_model/tests/test_blending.py`（新建）
- **测试用例**：
  - F4 公式：3 个归一化用例（边界 1.0、中心 0.5/0.5、混合）
  - F5 公式：3 个 tumblehome 用例（CA = 0、CA = π/6、CA = π/2）
  - 集成：`build_car(default_params)` 不报错 + 视觉回归（截图 SSIM ≥ 99%）
- **覆盖目标**：≥ 95%
- **命令**：`pytest algorithm_model/tests/test_blending.py -v --cov=algorithm_model.car_modeling.blending --cov-report=term-missing`

#### T8. 前端联调 + 自测（0.5h）

- **动作**：跑 `vite build`，验证前端 3D 渲染
- **位置**：`/app/data/所有对话/主对话/evo_build/`
- **步骤**：
  1. `cd /app/data/所有对话/主对话/evo_build/`
  2. `npx vite build`（inline-vendor.js + main.js 一起写进 dist/index.html）
  3. 跑 `test_evo.py`（端口 8094/8095+）访问 `evo_build/dist/`
  4. 验证：console error 是否解决 / `#app innerHTML` 长度 > 0 / 3D canvas 是否渲染 / 三区段视觉可见
- **验收**：build 成功 + http 200 + 3D canvas 渲染车身 + 三区段视觉可见

### W2-D2 交付清单

- [ ] `blending.py` 实现完整（含 4 个函数 + 1 个常量表）
- [ ] `ZONE_PARAMS_TABLE` 15 格填好
- [ ] `test_blending.py` 95% 覆盖
- [ ] `build_car()` 集成三区段 + 端到端跑通
- [ ] 前端 build + 自测通过 + 三区段视觉可见
- [ ] 截图归档到 `patent_materials/w2_screenshots/D2_*.png`

---

## W2-D3：31-Point Cross-Section + Arc-Length Parameterization

### 任务卡头部

| 字段 | 值 |
|---|---|
| **工期** | 1 个工作日（8h） |
| **优先级** | P0（核心专利 Claim 6） |
| **依赖** | W2-D2 通过 |
| **阻塞风险** | 31 点闭合误差累积、G0 连续性失败 |
| **负责模块（新建）** | `algorithm_model/car_modeling/parametrize.py` |
| **集成模块** | `algorithm_model/car_modeling/body.py`（调 parametrize） |
| **测试模块（新建）** | `algorithm_model/tests/test_parametrize.py` |
| **关联公式** | F6（特征线插值，关联） |
| **关联 Claim** | Claim 6 |

### 任务清单（按时间顺序）

#### T1. 设计 CrossSection 数据模型（1h）

- **动作**：设计 31 个截面点的数据模型
- **位置**：`algorithm_model/car_modeling/parametrize.py::CrossSection`
- **字段**：
  - 31 个 (x, y) 坐标 + 闭合标志
  - 索引分段：
    - 0-5：底部（bottom，6 点）
    - 6-11：腰线（waist，**特征线**，6 点）
    - 12-18：肩部（shoulder，7 点）
    - 19-24：车顶（roof，**特征线**，6 点）
    - 25-30：反向（closing，6 点，回到起点）
- **产物**：
  ```python
  @dataclass
  class CrossSection:
      points: np.ndarray  # shape (31, 2)，每行 (y, z)
      closed: bool = True
      feature_lines: List[Tuple[int, int]] = field(default_factory=lambda: [(6, 11), (19, 24)])
  ```
- **验收**：dataclass 通过 import 测试 + 索引分段验证

#### T2. 实现 generate_cross_section（3h）

- **动作**：实现 31 点闭合截面生成
- **位置**：`algorithm_model/car_modeling/parametrize.py::generate_cross_section`
- **函数签名**：
  ```python
  def generate_cross_section(x: float, zone_params: ZoneParamsTable, hardpoints: dict) -> CrossSection:
      """根据 X 位置、当前区段参数、硬点生成 31 点闭合截面"""
  ```
- **算法**：
  - 根据 `x` 选 `zone_params`（5 水平 × 3 区段 → 选对应行）
  - 应用 tumblehome 调整（调 `compute_tumblehome`）
  - 生成 31 个点的 Y/Z 坐标
  - 强制最后一点 = 第一点（闭合）
- **验收**：3 个典型位置的截面形状正确
  - `x = hood_center` → 截面细长（hood 区段）
  - `x = cabin_center` → 截面饱满（cabin 区段 + tumblehome）
  - `x = trunk_center` → 截面中等（trunk 区段）
  - 每个截面 points[30] ≈ points[0]（容差 1e-6）

#### T3. 实现 arc_length_parameterize（2h）

- **动作**：实现弧长参数化
- **位置**：`algorithm_model/car_modeling/parametrize.py::arc_length_parameterize`
- **函数签名**：
  ```python
  def arc_length_parameterize(cross_section: CrossSection) -> np.ndarray:
      """返回 31 个归一化弧长参数 t ∈ [0, 1]，单调递增"""
  ```
- **算法**：
  - 累加欧氏距离：`arc_len[i] = sum_{k=1..i} ||p_k - p_{k-1}||`
  - 归一化：`t[i] = arc_len[i] / arc_len[30]`
- **验收**：
  - `t[0] = 0`, `t[30] = 1`
  - `t` 单调递增
  - 单测覆盖 95%

#### T4. 实现 feature_line_interp（2h）

- **动作**：实现特征线感知插值（Claim 6 核心）
- **位置**：`algorithm_model/car_modeling/parametrize.py::feature_line_interp`
- **规则**：
  - 段索引 6-11（腰线，特征线）：**线性**插值（`frac`）
  - 段索引 19-24（车顶，特征线）：**线性**插值（`frac`）
  - 其他段（0-5、12-18、25-30）：**smoothstep** 插值（`3*frac^2 - 2*frac^3`）
- **函数签名**：
  ```python
  def feature_line_interp(seg_idx: int, frac: float) -> float:
      """根据段索引返回插值后的参数值"""
  ```
- **验收**：
  - 单测通过
  - 段 6-11 的二阶导数 = 0（线性特征）
  - 段 0-5 的二阶导数 ≠ 0（smoothstep 特征）

#### T5. 网格装配（0.5h）

- **动作**：80 longitudinal stations × 64 cross-section stations = 5,184 vertices, 10,240 triangles
- **位置**：`algorithm_model/car_modeling/body.py::Body.assemble_mesh()`
- **步骤**：
  1. 在 80 个 X 位置调用 `generate_cross_section`
  2. 顶点拼接 → 5,184 个
  3. 三角形索引拼接 → 10,240 个
- **验收**：
  - trimesh 能导出 GLB
  - 无 NaN/Inf 顶点
  - 顶点数量 = 5,184 ± 1
  - 三角形数量 = 10,240 ± 1

#### T6. 单元测试（0.5h）

- **位置**：`algorithm_model/tests/test_parametrize.py`（新建）
- **测试用例**：
  - `generate_cross_section`：3 个典型位置 + 闭合验证
  - `arc_length_parameterize`：t 范围 + 单调
  - `feature_line_interp`：6-11 线性、其余 smoothstep
- **覆盖目标**：≥ 95%
- **命令**：`pytest algorithm_model/tests/test_parametrize.py -v --cov=algorithm_model.car_modeling.parametrize --cov-report=term-missing`

#### T7. G0 连续性自测（0.5h）

- **动作**：在合成的 profile 上跑 G0 检查
- **位置**：`algorithm_model/surface_quality/continuity.py::check_g0_continuity()`
- **验证**：
  - 相邻截面共享边数 = 总边数 ✅
  - 无 NaN 边
  - 边界框合理
- **验收**：
  - G0 = 100%
  - 报告输出到 `patent_materials/w2_quality/D3_g0_report.json`

#### T8. 端到端 + 前端联调 + 性能（0.5h）

- **动作**：
  1. `build_car()` 端到端跑通（80 stations × 31 points）
  2. 重新 build 前端
  3. 性能测试：单次 build < 20ms（Claim 12 目标）
  4. FPS 测试：50+ FPS 持续 5 秒
- **验收**：
  - 3D 车身流畅渲染
  - 性能 baseline 输出到 `patent_materials/w2_perf/D3_benchmark.json`

### W2-D3 交付清单

- [ ] `parametrize.py` 实现完整（4 个函数 + 1 个数据类）
- [ ] `generate_cross_section` 跑通（3 个典型位置 + 闭合）
- [ ] `arc_length_parameterize` 跑通
- [ ] `feature_line_interp` 跑通
- [ ] 完整 mesh 组装（80 × 31 = 2,480 stations，包含 64 cross-section stations）
- [ ] `test_parametrize.py` 95% 覆盖
- [ ] G0 连续性 = 100%
- [ ] 端到端 < 20ms
- [ ] 前端 50+ FPS
- [ ] 截图 + 性能报告归档

---

## W2 总验收标准（D2+D3 都完成后）

- [ ] 12 个专利 Claim 中 1-6 全部有对应代码模块
- [ ] F1-F5 公式单测 95% 覆盖
- [ ] G0 连续性 = 100%
- [ ] 单次 build < 20ms
- [ ] 前端 50+ FPS
- [ ] `build_car()` 返回完整车身 GLB
- [ ] 三区段过渡视觉可见
- [ ] 31 点截面闭合（容差 1e-6）
- [ ] 弧长参数化正确（t 单调）
- [ ] 特征线插值符合专利规则（段 6-11 / 19-24 线性，其余 smoothstep）
- [ ] 所有产物归档到 `patent_materials/w2_*/` 子目录

## 风险点

| 风险 | 等级 | 缓解 |
|---|---|---|
| 沙箱文件系统清零导致 vendor 丢失 | 高 | inline-vendor.js 兜底（已写） |
| 三区段权重选择不平滑 | 中 | 用 smoothstep 替代 step blend |
| Tumblehome 极端 CA 角度溢出 | 中 | `max(0.25, ...)` 下限保护 |
| 31 点截面闭合误差累积 | 中 | 强制 `points[30] = points[0]` |
| 性能不达标（> 20ms） | 中 | numpy 向量化 + 预计算常量表 |
| G0 连续性失败 | 低 | 共享边强制对齐 + 单测验证 |
| W2-D1 inline-vendor.js 自身被清零 | 中 | 重生成 inline-vendor.js（base64 内联 6 个 vendor） |
| 前端 build 因中文路径失败 | 中 | 用 `evo_build/` 子目录 |

## 关联资产

- 专利 PDF：`/app/data/所有对话/主对话/用户上传/patent_1782045990915_0_5srb.pdf`
- 专利 TXT：`/tmp/patent.txt`（28KB）
- Roadmap：`/app/data/所有对话/主对话/patent_materials/Development_Roadmap.md`（13KB）
- v3 PPTX：`/app/data/所有对话/主对话/A-Class-Surface-Patent-EN-v2.pptx`（5.97MB）
- v3 升级脚本：`/app/data/所有对话/主对话/patent_materials/v2_enhance.py`（22KB）
- v3 预览图：`/app/data/所有对话/主对话/patent_materials/v2_preview/v3_preview-{01-10}.png`
- 后端项目：`/app/data/所有对话/主对话/EVOLUTION_AI_DEMO/`
- 算法核心：`/app/data/所有对话/主对话/EVOLUTION_AI_DEMO/algorithm_model/`
- 前端项目：`/app/data/所有对话/主对话/evo_build/`
- inline-vendor.js：`/app/data/所有对话/主对话/evo_build/public/inline-vendor.js`（1.78MB）
- EMBODY AI 报告：`/app/data/所有对话/主对话/patent_materials/EMBODY_AI_Technology_Framework.md`（44KB）

## 派发建议

| D | 适合派发 | 说明 |
|---|---|---|
| W2-D2 | ✅ sessions_spawn（lead agent） | 8h 工作量，独立闭环，含明确验收 |
| W2-D3 | ✅ sessions_spawn（lead agent） | 8h 工作量，独立闭环，含明确验收 |
| 或 D2+D3 一起 | ✅ sessions_spawn（lead agent） | 16h 大任务，但流程同构，可一并派 |

派发时 task 字段直接引用本文件路径（`/app/data/所有对话/主对话/patent_materials/W2-D2_D3_Task_Cards.md`）+ 标注"按 W2-D2 任务卡执行"或"按 W2-D3 任务卡执行"。

---

> 本内容由 Coze AI 生成，请遵循相关法律法规及《人工智能生成合成内容标识办法》使用与传播。
