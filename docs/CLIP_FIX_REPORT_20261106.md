# EVOLUTION-AI.DESIGN｜穿模根治与 SISA 提案落地报告（2026-11-06）

## 一、执行摘要

本轮针对「物体穿模未彻底解决」的反馈，先在平台侧定位到**同构根因**，再按 SISA 提案
`PROPOSAL_TO_PLATFORM_PANEL_TOPOLOGY.md` 的修法 2 完成等价改造，并一并处理了提案附带的
两个数据缺陷。

| 项目 | 结论 |
| --- | --- |
| 穿模根因 | 车身壳「洞壁内饰化」原用 bbox 判定 + 多条判据链各自命中，同一面片可被两条链重复命中；斜面玻璃带分支把整宽斜面墙染黑 |
| 平台侧修法 | 面片归属（互斥 + 穷尽）：每个三角形在一次遍历中拿到**恰好一个** owner；判据改为真实洞口多边形等距带 |
| 前风挡黑带 + 锯齿 | 已消除（斜面不再改判车身面片，舱影改为独立几何，与玻璃逐点同源） |
| 后侧窗下沿锯齿 | 已消除（bbox → 真实多边形等距带，覆盖面积从 ~10 倍降到 ~1.1 倍） |
| 数据缺陷一（皮卡后窗角） | 已修：`rear_window_angle` 统一为「与竖直方向夹角」，六车型声明角 == 隐含角（偏差 0°，门禁 ≤1.5°） |
| 数据缺陷二（roof_height 三口径） | 已在契约层显式定义并纳入校验，标注为合同占位（几何未消费） |
| 前端测试 | 981 passed / 0 failed（29 个测试文件） |
| 后端契约测试 | 21 passed（含新增 2 条语义门禁） |
| 视觉回归 | 六车型 × 透视 + 皮卡侧视 + SUV/皮卡开门，共 9 张，无黑带/锯齿/互穿 |

## 二、根因与修法（平台侧等价）

### 2.1 根因 R2 的平台同构：判定式改判 ≠ 面片归属

原实现用「三角形重心落在口径矩形 bbox 内」判定是否改判内饰，问题是：

- bbox 是洞口的粗近似（实测 `fixedFront` 多边形外占比 53%、`door-lower` 45%）→ 洞口下沿锯齿；
- 判定式是「命中即改判」，同一面片可被两条判据链重复命中 → 与提案 R2「同一批面片被两个分件各取一次」同构；
- 斜面玻璃带分支按重心判「是否落在玻璃半宽内」，而斜面墙几何是**整宽大三角形**（重心 `cz ≈ 0`）→ 整片染黑 → 前风挡黑带 + 齿状边。

### 2.2 修法：面片归属（互斥 + 穷尽）

新增 [panelOwnership.js](file:///d:/API/Evolution-Ai.Design/src/three/geometry/panelOwnership.js)：

- `assignShellOwners(geom, { apertures, zCapAt, isBodyMaterial, band })`：一次遍历为每个三角形赋**唯一** owner（`PAINT` / `APERTURE_LINER`）；
- `groupShellByOwner(geom, owners)`：按归属把面片重排成两个材质组，重排后每个面片**恰好出现一次**；
- `auditShellOwners(geom)`：审计 `exhaustive / exclusive / clean`，即提案 A1/A2 的平台等价判据。

判据口径（米制，X+ 车头 / Y+ 向上 / Z+ 副驾侧）：

- 洞壁带 = 三角重心到**最近洞口多边形边界**的距离 ≤ `APERTURE_BAND = BODY_BEVEL_SIZE + 0.002`；
- 端盖（`|nz| > 0.6`）与水平壁（`|ny| > 0.8`）必为车漆（车外可见面不被吞）；
- 外蒙皮（`isBodyMaterial === false`）必为车漆；
- 归属在**装配期一次性**求解，渲染帧循环零开销。

## 三、提案 A1–A5 逐条回执

| 提案判据 | 平台落地 | 验证 |
| --- | --- | --- |
| A1 穷尽 | 每个三角形必有 owner；两组面片数之和 == 总数 | `panelOwnership.spec.js` 六车型 `exhaustive === true` |
| A2 互斥 | 顶点区间首尾相接，无重叠/空隙；内饰组不含端盖/水平壁 | 六车型 `exclusive === true`、`clean === true`；`paint×3 == group.count` |
| A3 同壳 | 归属判据与挖洞使用**同一份**真实洞口多边形（非 bbox） | 六车型内饰面片重心到洞口边界最大值 ≤ `APERTURE_BAND` |
| A4 车型正确 | 四门（sedan/suv/mpv）走 `rearSeamX`；两门（coupe/sport/pickup）走 `midSeamX` 回落 | 门洞后缘逐点等于 `(rearSeamX ?? midSeamX) − 4mm` |
| A5 区间派生 | 洞口 X 区间由该车型 `carProfile/doorLayout` 推出，非写死轿车比例 | 六车型门洞跨度互不相同（≥4 种），且全部落在车身 X 包络内 |

## 四、数据缺陷处置

### 4.1 缺陷一：皮卡后窗角 implied 90° vs 声明 29°

**权威语义取证**：`rear_window_angle` = 后风挡面与**竖直方向**的夹角（越大越躺）；
`windshield_angle` 仍为与**水平面**夹角。旧实现全部按水平夹角消费（`dx = dy / tan(a)`），
导致同参数进深被放大约 2~3 倍；皮卡分支更因后壁以「腰带线交点」为圆角第三点而出现方向反转。

**修正**：

- [carProfile.js](file:///d:/API/Evolution-Ai.Design/src/utils/carProfile.js)：`dx = dy · tan(a)`，`dy = roofTopY − beltLineY`（真实玻璃带高）；新增 `rearWindowAngleDeg / rearWindowImpliedAngleDeg / rearWindowAngleClamped` 三字段供门禁；
- 皮卡驾驶室后壁统一为「自上而下向后倾」，圆角一律以**壁底** `cabBaseX` 为第三点；
- [carImageManager.js](file:///d:/API/Evolution-Ai.Design/src/utils/carImageManager.js)（2D SVG 第二实现）、`scripts/generate_brand_svgs.py`、`backend/rhino_plugin/evolution_ai_rhino.py`、`backend/tools/render_brand_gallery.py` 同步为竖直语义；
- `backend/app/cad_importer.py`：`rear_window_angle = ws_angle − 8` 改为 `90 − ws_angle`（两者基准不同，不可相减）。

**六车型实测（declared == implied，无钳制）**：

| 车型 | 声明角 | 隐含角 | 玻璃带高 dy | 水平进深 dx |
| --- | --- | --- | --- | --- |
| sedan | 28° | 28.0000° | 0.4672 | 0.2484 |
| suv | 22° | 22.0000° | 0.5696 | 0.2301 |
| coupe | 35° | 35.0000° | 0.4692 | 0.3285 |
| sport | 42° | 42.0000° | 0.4250 | 0.3827 |
| mpv | 15° | 15.0000° | 0.6460 | 0.1731 |
| pickup | 20° | 20.0000°（后壁角） | 0.6528 / 壁高 0.8064 | 0.2376 / 壁进深 0.2935 |

### 4.2 缺陷二：roof_height 三口径未定义

三个口径并存且互不重叠：

| 口径 | 字段 | 含义 | 区间 |
| --- | --- | --- | --- |
| 前端 | `frontend.roof_height` | 车顶纵向跨度 | 1200~2000（映射到 `roof_length`） |
| 后端 | `车身部件.roof_height` | 车顶板厚 | 30~100 |
| 知识库 | `brand_design_knowledge.roof_height` | 车顶纵向高度/跨度 | 550~900 |

**修正**：[param_contract.py](file:///d:/API/Evolution-Ai.Design/backend/app/param_contract.py) 的
`parameter_schema()["semantics"]` 新增 `roof_height_calibers` 三口径表与 `rear_window_angle`
语义项（`basis: vertical`、公式、`not_interchangeable_with: windshield_angle`），并显式标注
`consumed_by_geometry: false`（`deriveCarProfile` 从未读取该字段 ⟹ 属合同占位，不是几何输入）。

校验仍由既有 `PARAM_ALIASES` / `FORCE_ALIAS` / 区间表强制：前端跨度只能落到 `roof_length`，
绝不可能被当成板厚接收（`roof_height: 850` 直接判越界）。

## 五、测试与验证

### 5.1 新增专项测试

[panelOwnership.spec.js](file:///d:/API/Evolution-Ai.Design/src/tests/panelOwnership.spec.js)：88 条

- A1/A2/A3/A4/A5 六车型全覆盖；
- 边界/极限：后窗角 10°/60°、轮径 520/780mm、车顶跨度 1200/2000mm × 六车型，归属仍穷尽互斥；
- 角度门禁：声明角 vs 隐含角 ≤1.5°（六车型实测偏差 0°）；极端角明确区分「钳制」与「一致」；
- 性能基准：六车型全量装配 + 审计 < 8s；审计纯遍历无副作用（重复调用结果一致）。

### 5.2 断言更新（旧语义 → 新语义）

| 文件 | 变更 |
| --- | --- |
| `src/tests/carProfile.spec.js` | MPV/SUV 后窗从「钳制到 trunkStartX」改为「按竖直夹角派生 + 未越甲板起点」；皮卡后壁锚点从 `rearWheelX+0.5` 常量改为「门后缝 −50mm」 |
| `src/tests/carGlass.spec.js` | 皮卡圆角第三点改用 `cabBaseX`；DLO 顶/底后角关系取消皮卡特例（后壁与 C 柱同向）；轮廓复刻同步 `cabBaseX` |
| `tests/car2d.test.js` | 后窗下沿约束方向反转（2D X 增大指向车尾）；皮卡后壁锚点改为与 3D 同源推导；`EXPECTED_CAR_MESHES` 198 → **197**（基线 193 + 地毯分段 +2 + 舱影 +2） |

### 5.3 执行结果

- 前端全量：`981 passed / 0 failed`，29 个测试文件（基线 893 + 新增专项 88）；
- 受影响三文件：`284 passed`（carProfile 114 / carGlass 143 / car2d 27）；
- 新增专项：`88 passed`；
- 后端契约：`21 passed`。

### 5.4 视觉回归（harness 截图）

采集用例：六车型透视 + 皮卡侧视 + SUV 开门 + 皮卡开门，共 9 张。

| 观察点 | 结果 |
| --- | --- |
| 前风挡区黑带 + 锯齿 | 无（玻璃外 A/C 柱区保持车漆色） |
| 后侧窗下沿锯齿 | 无（洞口边界平滑贴合） |
| 皮卡驾驶室后壁 / 货箱衔接 | 无互穿，后壁自上而下向后倾 |
| 开门工况（门洞 / 内饰 / 门板） | 无重叠、无遮挡黑块，门洞内读作深色内饰 |
| MPV 15° 近竖直后风挡 | 与车顶/尾门衔接自然，无折叠 |

## 六、当前状态与遗留

**已完成**：面片归属（A1/A2/A3）、真实多边形洞口判据（修锯齿）、舱影独立几何（修黑带）、
A4/A5 车型区间派生验证、两个数据缺陷处置、2D 与后端消费者语义同步、专项测试与视觉回归。

**遗留 / 需决策**：

1. `docs/preview/ip-luggage-3d.js` 为生成产物，本轮未重新生成（其内联旧公式不影响生产构建，但下次生成前建议先确认脚本已同步）；
2. `panelOwnership` 的 `clean` 判据只覆盖端盖/水平壁两类法向门控，若后续新增洞口类型需同步扩判据；
3. `coupe` / `sport` 为两门车型，其后门缝回落 `midSeamX` 属既有设计，本轮仅验证未改动；
4. 全部改动**未提交**，临时脚本已清理，等待复核后再决定是否入库。
