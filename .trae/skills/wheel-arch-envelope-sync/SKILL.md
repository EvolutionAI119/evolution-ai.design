---
name: "wheel-arch-envelope-sync"
description: "处理轮拱包络模型在 EVO→SISA 跨平台同步中的拱轮错位、车轮穿壳、拱顶不足问题。Invoke when 轮拱造型异常、车轮与车身干涉、拱心与轮心不对齐、或需将上游平台参数化成果同步到 SISA 内核时。"
---

# 轮拱包络同步与拱轮对齐问题处理

## 问题场景

SISA 3D 整车建模中，轮拱区域出现以下任一症状时适用本 SKILL：

| 症状 | 典型表现 | 根因 |
|------|----------|------|
| 车轮穿壳 | 车轮上半部分陷入车身，无轮拱开口 | 旧「gc + 1.16×轮径」高斯拱幅值不足，拱顶 < 胎顶 |
| 拱轮错位 | 轮拱开口与车轮不同心，前后偏移 | 拱心用「车长中点 ± 轴距/2」，与车轮「前悬/后悬」定位口径不一致 |
| 车型无差异 | 六款车型轮拱形态雷同 | 缺少 WHEEL_ENVELOPE 分车型参数表，未接入 car_type |
| 2D/3D 不一致 | 侧视图纸轮拱与 3D 模型开口不重合 | 2D/3D 未共享同一包络计算真源 |

## 判断标准

### 1. 拱顶高度判据

真车物理约束：拱顶必须高于胎顶，且预留悬架跳动与装配间隙。

```
拱顶 apex_z = 轮心高 + 轮半径 + 跳动量 jounce + 顶隙 gap_top
```

**红线**：拱顶 < 胎顶（即 2×轮半径）→ 必然穿壳，必须修复。

### 2. 拱心对齐判据

拱心 x 坐标必须与轮心 x 坐标一致，偏差容差 < 1mm。

| 车型 | 前悬 FO | 后悬 RO | 中点口径错位量 |
|------|---------|---------|----------------|
| moyu-s | 1020 | 1080 | 0 |
| moyu-l | 1020 | 1080 | 15 |
| moyu-g | 1020 | 1080 | 30 |
| moyu-r | 1020 | 1080 | 30 |
| moyu-x | 1020 | 1080 | 40 |
| moyu-t | 1040 | 1150 | **110** |

**结论**：中点口径在前后悬不等时必然错位，必须改用「前轴 = 前悬、后轴 = 全长 − 后悬」。

### 3. 包络参数一致性判据

SISA `feature_lines.WHEEL_ENVELOPE` 必须与 EVO `src/utils/carProfile.js` 的 `WHEEL_ENVELOPE` 逐值一致：

| 车型 | jounce | gap_top | gap_side | steer_deg | flatten |
|------|--------|---------|----------|-----------|---------|
| sedan | 45.0 | 35.0 | 25.0 | 33.0 | 0.00 |
| suv | 80.0 | 60.0 | 40.0 | 34.0 | 0.25 |
| coupe | 35.0 | 30.0 | 22.0 | 32.0 | 0.00 |
| sport | 30.0 | 25.0 | 18.0 | 30.0 | 0.00 |
| mpv | 45.0 | 35.0 | 25.0 | 32.0 | 0.05 |
| pickup | 90.0 | 75.0 | 50.0 | 34.0 | 0.35 |

## 操作流程

### Step 1：确认同步基线

```bash
cd D:\API\SISA
python -m harness.backend._upstream_sync --check
```

- 输出「无欠账」→ 继续排查内核实现
- 输出「有欠账」→ 先执行 `--sync` 吸收上游变更，再评估是否仍需内核修复

### Step 2：定位缺口层级

按以下顺序排查，定位问题落在哪一层：

1. **harness 白名单层**：`harness/backend/` 是否已吸收上游算法文件？
2. **常量表层**：`sisa/feature_lines.py` 是否已有 `WHEEL_ENVELOPE` 六型表？
3. **公式层**：`sisa/feature_lines.py` 是否已有 `derive_wheel_arch` 纯函数？
4. **应用层**：`sisa/master_panel.py` 的母曲面拱抬升与特征引导是否调用同一 helper？
5. **参数化层**：`build()` 是否支持 `car_type` 六型传入？

### Step 3：实施修复

#### 3.1 落地包络常量表（feature_lines.py）

```python
WHEEL_ENVELOPE: Dict[str, Dict[str, float]] = {
    "sedan":  {"jounce": 45.0, "gap_top": 35.0, "gap_side": 25.0,
               "steer_deg": 33.0, "flatten": 0.00},
    "suv":    {"jounce": 80.0, "gap_top": 60.0, "gap_side": 40.0,
               "steer_deg": 34.0, "flatten": 0.25},
    "coupe":  {"jounce": 35.0, "gap_top": 30.0, "gap_side": 22.0,
               "steer_deg": 32.0, "flatten": 0.00},
    "sport":  {"jounce": 30.0, "gap_top": 25.0, "gap_side": 18.0,
               "steer_deg": 30.0, "flatten": 0.00},
    "mpv":    {"jounce": 45.0, "gap_top": 35.0, "gap_side": 25.0,
               "steer_deg": 32.0, "flatten": 0.05},
    "pickup": {"jounce": 90.0, "gap_top": 75.0, "gap_side": 50.0,
               "steer_deg": 34.0, "flatten": 0.35},
}
```

#### 3.2 落地包络公式纯函数（feature_lines.py）

```python
def derive_wheel_arch(wheel_r_mm: float, belt_line_mm: float,
                      car_type: str = "sedan", axle: str = "front"
                      ) -> Dict[str, Any]:
    env = WHEEL_ENVELOPE.get(str(car_type or "").strip().lower()) \
        or WHEEL_ENVELOPE["sedan"]
    r = float(wheel_r_mm)
    tire_w = 2.0 * r * 0.36
    front = str(axle or "front").strip().lower() != "rear"
    gs = float(env["gap_side"]) * (1.0 if front else 0.8)
    c_steer = ((tire_w / 2.0) * math.sin(math.radians(float(env["steer_deg"])))
               if front else 0.0)
    cy = r
    ry = r + float(env["jounce"]) + float(env["gap_top"])
    clamped = False
    cap = max(float(belt_line_mm) - 40.0 - cy, r * 0.04)
    if ry > cap:
        ry, clamped = cap, True
    denom = math.sqrt(max(1.0 - (float(env["jounce"]) / ry) ** 2, 0.25))
    rx = (r + c_steer + gs) / denom * (1.0 + 0.5 * float(env["flatten"]))
    return {"ry": ry, "rx": rx, "c_steer": c_steer,
            "flatten": float(env["flatten"]), "cy": cy,
            "apex_z": cy + ry, "clamped": clamped,
            "car_type": str(car_type or "sedan").strip().lower(),
            "axle": "front" if front else "rear"}
```

**关键公式**：
- `ry = r + jounce + gap_top`（拱顶 = 轮顶 + 跳动 + 顶隙）
- `rx = (r + c_steer + gap_side) / √(1 − (jounce/ry)²) · (1 + 0.5·flatten)`
- `c_steer = (胎宽/2) · sin(steer_deg)` 仅前轴，后轴 `gap_side × 0.8` 收紧
- `胎宽 ≈ 0.36 × 轮径`

#### 3.3 统一拱心来源（master_panel.py）

```python
def _arch_axles(p: Dict[str, Any]) -> List[Tuple[float, str]]:
    L = float(p["length"])
    fo, ro = p.get("front_overhang"), p.get("rear_overhang")
    if fo and ro and (L - float(fo) - float(ro)) > 0:
        return [(float(fo) / L, "front"), ((L - float(ro)) / L, "rear")]
    half = float(p["wheelbase"]) / 2.0 / L
    return [(0.5 - half, "front"), (0.5 + half, "rear")]
```

#### 3.4 唯一同源拱剖面（master_panel.py）

母曲面 `master_surface` 与特征引导 `feature_guides` 必须共用 `_arch_profile`：

```python
def _arch_profile(p: Dict[str, Any]) -> List[Dict[str, Any]]:
    from .dimension_plan import LINE_RATIOS, MODEL_TYPE
    from .feature_lines import derive_wheel_arch
    wheel_r = float(p["wheel_diameter"]) / 2.0
    L = float(p["length"])
    ct = str(p.get("car_type") or "sedan").strip().lower()
    ct = MODEL_TYPE.get(ct, ct)
    if ct not in LINE_RATIOS:
        ct = "sedan"
    belt_z = float(p["height"]) * float(LINE_RATIOS[ct]["belt"])
    out: List[Dict[str, Any]] = []
    for tc, axle in _arch_axles(p):
        env = derive_wheel_arch(wheel_r, belt_z, ct, axle)
        out.append({"t": tc, "axle": axle, "car_type": ct,
                    "apex_z": env["apex_z"], "ry": env["ry"], "rx": env["rx"],
                    "sigma_t": max(env["rx"], 1.0) / (2.0 * L),
                    "clamped": env["clamped"]})
    return out
```

**原则**：`zthr ≡ z_bot`，母曲面与特征引导按构造镜像，不得各自独立计算。

#### 3.5 六型参数化接入（master_panel.py）

```python
def build(..., car_type: str = "sedan"):
    p = master_params(dna)
    p.setdefault("car_type", car_type)
    ...
```

### Step 4：价值对齐测试

新建 `tests/test_wheel_envelope.py`，必须包含以下 6 项：

| 测试项 | 验证内容 | 通过标准 |
|--------|----------|----------|
| 表逐值对齐 | 直读上游 carProfile.js，与 WHEEL_ENVELOPE 逐值比对 | 全部相等 |
| 公式独立复算 | 测试内独立实现公式，与内核交叉验证 | 前/后轴 × 六型全部一致 |
| 包络净空 | 母曲面拱心行最低点 vs 胎顶 | 最低点 > 胎顶 + 12mm |
| 拱轮对齐 | `_arch_axles` 输出 vs make_wheels 轮位 | 偏差 < 1e-9 |
| 母曲面实测 | 生产网格拱心行采样 | 与包络公式预测一致 |
| 分档差异化 | sport / sedan / suv 拱顶与 rx 排序 | sport < sedan < suv |

### Step 5：全量回归

```bash
cd D:\API\SISA
$env:SISA_SECRETS_ROOT='D:\API\_sisa_private'
$env:SISA_DNA_RELPATH='brand_dna.json'
$env:SISA_UPSTREAM_ROOT='D:\API\Evolution-Ai.Design'
python -m pytest tests/ -q
```

**通过标准**：827 passed, 1 skipped，零失败。

## 注意事项

### 1. 测试解析上游 JS 常量的陷阱

`carProfile.js` 中 `LINE_RATIOS` 与 `WHEEL_ENVELOPE` 有同名车型键（如 `sedan:`），正则直接匹配会命中错误块。

**正确做法**：先 `js.split("export const WHEEL_ENVELOPE", 1)[1]` 切块，再在块内正则匹配。

### 2. 几何 helper 同源纪律

母曲面与特征引导的拱抬升必须调用**同一函数**，禁止各自复制公式。任何后续修改只需改 `_arch_profile` 一处，两端自动同步。

### 3. 遗留同步清单

以下三项与本轮修复同源，但涉及级联几何基线与并行会话，需协调后另批执行：

1. `car_body.build_closed_shell`（cad_bridge STEP 导出链）同口径升级——联动 arch_narrow 与 test_feature_lines contact 断言
2. `feature_lines.build_wheel_arch` 圆弧 → 包络椭圆——联动 fender_arch 判据
3. `dimension_plan` L4 drawing_formulas 拱半径——与 SISA web `drawing.js` 同源锁定，须同批更新

### 4. 并行会话纪律

- 进行时几何修正与测试基线归进行线所有，其他会话不抢改
- 提交时只提交本会话交付文件
- PowerShell 无 heredoc，git commit 多行信息用临时文件 + `git commit -F`

### 5. 关键数值速查

| 参数 | 含义 | 典型值（sedan） |
|------|------|----------------|
| 轮心离地 | 轮胎半径 | r |
| 胎宽 | 0.36 × 轮径 | 0.36 × 2r |
| 拱顶 apex_z | cy + ry | 840 mm（r=380） |
| 前轴 rx | 含转向扫掠 | 482 mm |
| 后轴 rx | 收紧 0.8× | 402 mm |
| σ_t | rx / (2L) | 拱形宽度系数 |
