// 平稳垂直起降（VTOL）分支 —— 零依赖纯函数
//
// 设计目标：让所有车型具备飞行能力，在算法、物理、数学与体验间取得最优平衡：
//  - 物理：推重比 T/W ≥ 1（悬浮充要）；暗能量负压类比（状态方程 w≈−1）降低
//    有效重力，工程化上限 0.35·η（η∈[0,0.3]，科幻但受界）
//  - 数学：起升曲线用五次 smoothstep s(t)=6t⁵−15t⁴+10t³（C² 连续：
//    端点速度/加速度均为 0，无加速度突变 → 体感无冲击）
//  - 无眩晕三重保证：①阻尼比 ζ=1+0.6·η_cdm ≥ 1（临界/过阻尼，零超调振荡）；
//    ②悬浮呼吸振幅 < 0.2% 车长（感知阈以下）、频率 < 0.2Hz（远离 0.5~1Hz
//    人体晕动敏感频段）；③全程纯垂直运动、相机零滚转（无角速度刺激前庭）

// 车型飞行预设（hoverAltitude 悬浮高度 mm；liftDuration 起升时长 s；
// exoticRatio 暗能量驱动占比；darkMatterRatio 暗物质惯性配比；
// liftFans 升力风扇数；hoverBobAmp 悬浮呼吸振幅 mm；hoverBobFreq 呼吸频率 Hz）
export const FLIGHT_PRESETS = {
  sedan:  { hoverAltitude: 1600, liftDuration: 3.2, exoticRatio: 0.15, darkMatterRatio: 0.20, liftFans: 6, hoverBobAmp: 6, hoverBobFreq: 0.14 },
  suv:    { hoverAltitude: 1900, liftDuration: 3.6, exoticRatio: 0.18, darkMatterRatio: 0.24, liftFans: 6, hoverBobAmp: 7, hoverBobFreq: 0.12 },
  coupe:  { hoverAltitude: 1700, liftDuration: 3.0, exoticRatio: 0.16, darkMatterRatio: 0.20, liftFans: 6, hoverBobAmp: 6, hoverBobFreq: 0.15 },
  sport:  { hoverAltitude: 1650, liftDuration: 2.8, exoticRatio: 0.14, darkMatterRatio: 0.18, liftFans: 6, hoverBobAmp: 5, hoverBobFreq: 0.16 },
  mpv:    { hoverAltitude: 2000, liftDuration: 3.8, exoticRatio: 0.20, darkMatterRatio: 0.28, liftFans: 8, hoverBobAmp: 8, hoverBobFreq: 0.11 },
  pickup: { hoverAltitude: 1800, liftDuration: 3.4, exoticRatio: 0.22, darkMatterRatio: 0.26, liftFans: 8, hoverBobAmp: 8, hoverBobFreq: 0.12 }
}

const SEDAN = FLIGHT_PRESETS.sedan

const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi)

/** 飞行参数解析：非法车型回退 sedan，越界值钳位（与玻璃参数同一防御模式） */
export function resolveFlightParams(carType, overrides = {}) {
  const base = FLIGHT_PRESETS[carType] || SEDAN
  const num = (v, lo, hi, fb) => {
    const n = Number(v)
    return Number.isFinite(n) ? clamp(n, lo, hi) : fb
  }
  return {
    hoverAltitude: num(overrides.hover_altitude, 400, 3000, base.hoverAltitude),
    liftDuration: num(overrides.lift_duration, 2.0, 5.0, base.liftDuration),
    exoticRatio: num(overrides.exotic_drive_ratio, 0, 0.3, base.exoticRatio),
    darkMatterRatio: num(overrides.dark_matter_ratio, 0, 0.3, base.darkMatterRatio),
    liftFans: Math.round(num(overrides.lift_fan_count, 2, 8, base.liftFans)),
    hoverBobAmp: num(overrides.hover_bob_amp, 0, 9.6, base.hoverBobAmp),
    hoverBobFreq: num(overrides.hover_bob_freq, 0.05, 0.2, base.hoverBobFreq)
  }
}

// ============ 反重力飞控系统 ============
// 技术目标：悬停姿态偏差 ≤±2°；360° 无限制原地转向；续航 ≥3× 同量级传统动力；
// 全工况无明显能耗峰值（峰值因子 ≤1.25）；动作切换响应 ≤100ms。
//
// 能耗模型物理叙事：
//  - 暗能量负压场是「度规效应」（几何曲率）而非推进做功：场维持功率仅为
//    相干性保持耗散（12 W/kg 量级），远低于风扇动量推进
//  - 场升力份额 s = 2.6·η_e + 1.8·η_cdm（引力透镜/惯性屏蔽贡献），上限 0.75：
//    风扇必须保留 ≥25% 推力做姿态差动与阵风抑制（±2° 包络的物理前提）
//  - 传统动力基准 P_base = 55 kW/t^1.2（同量级高效大盘面升力风扇，盘载荷模型）
//  - 风扇诱导功率随推力 1.5 次方：P_fan = P_base·(1−s)^1.5
//  - 续航倍数（同电量）E = P_base / (P_fan + P_field) ≥ 3（六车型预设全部达标）

export const FLIGHT_CONTROL = {
  attitudeLimitDeg: 2.0,       // 悬停姿态偏差设计包络 ±2°
  attitudeBandwidthHz: 2.5,    // 姿态控制回路带宽（远低于车身结构模态）
  fieldLiftCoefE: 2.6,         // 暗能量场升力份额系数
  fieldLiftCoefC: 1.8,         // 暗物质惯性屏蔽贡献系数
  fieldLiftShareMax: 0.75,     // 场份额上限：风扇保留 ≥25% 做姿态差动
  fieldPowerWPerKg: 12,        // 场维持比功率（度规效应非做功过程）
  basePowerKwPerTon: 55,       // 传统动力基准功率系数（kW/t^1.2）
  powerMassExponent: 1.2,
  takeoffSafetyFactor: 1.2,    // 起飞垂直爬升推力余量
  turnPeakRateDps: 45,         // 转向峰值角速度舒适限（视场旋转晕动阈内）
  turnMinSec: 2.5,             // 最短转向时长（任意小角度也有过渡带）
  quinticPeakSlope: 1.875,     // quintic 中点最大斜率 → T = 1.875·|Δ|/rate
  turnPowerMargin: 1.05,       // 原地转向差动功率增量 ≤5%
  peakFactorLimit: 1.25,       // 全工况能耗峰值因子上限（无明显峰值）
  enduranceTarget: 3.0,        // 续航倍数目标（vs 传统动力）
  batteryKwh: 100,             // 同量级纯电平台基准电量（续航对比基准）
  latencyBaseMs: 30,           // 指令链路基延迟（感知+解算+场建立）
  latencyPerFanMs: 6,          // 每风扇差动通道附加延迟
  latencyLimitMs: 100,         // 响应延迟上限
  gustRecoveryFromDeg: 8       // 阵风扰动注入幅值（恢复时间评估起点）
}

const r2 = v => Math.round(v * 100) / 100
const r3 = v => Math.round(v * 1000) / 1000

/** 场升力份额 s：暗能量负压 + 暗物质惯性屏蔽，钳位 [0, 0.75] */
export function fieldLiftShare(exoticRatio, darkMatterRatio) {
  const s = FLIGHT_CONTROL.fieldLiftCoefE * clamp(exoticRatio, 0, 0.3) +
    FLIGHT_CONTROL.fieldLiftCoefC * clamp(darkMatterRatio, 0, 0.3)
  return clamp(s, 0, FLIGHT_CONTROL.fieldLiftShareMax)
}

/** 传统动力基准悬停功率（kW）：P = 55·(m/t)^1.2（盘载荷模型，全推力悬停） */
export function baseHoverPowerKw(curbMassKg) {
  return FLIGHT_CONTROL.basePowerKwPerTon *
    Math.pow(Math.max(curbMassKg, 1) / 1000, FLIGHT_CONTROL.powerMassExponent)
}

/** 反重力悬停功率（kW）：P = P_base·(1−s)^1.5 + k_field·m·s/1000 */
export function antigravityHoverPowerKw(curbMassKg, exoticRatio, darkMatterRatio) {
  const s = fieldLiftShare(exoticRatio, darkMatterRatio)
  const fan = baseHoverPowerKw(curbMassKg) * Math.pow(1 - s, 1.5)
  const field = FLIGHT_CONTROL.fieldPowerWPerKg * curbMassKg * s / 1000
  return { fan: fan, field: field, total: fan + field, share: s }
}

/** 续航倍数（同电量）：E = P_base / P_antigravity ≥ 3（预设达标） */
export function enduranceMultiple(curbMassKg, exoticRatio, darkMatterRatio) {
  const pAg = antigravityHoverPowerKw(curbMassKg, exoticRatio, darkMatterRatio).total
  return baseHoverPowerKw(curbMassKg) / Math.max(pAg, 1e-9)
}

/** 全工况能耗剖面（kW）：悬停/起飞峰值/原地转向，附峰值因子 */
export function energyProfile(curbMassKg, exoticRatio, darkMatterRatio) {
  const ag = antigravityHoverPowerKw(curbMassKg, exoticRatio, darkMatterRatio)
  const base = baseHoverPowerKw(curbMassKg)
  // 起飞瞬间：风扇推力 ×1.2 爬升余量（场份额不变）→ 峰值出现在起飞而非悬停
  const fanTakeoff = base * Math.pow(FLIGHT_CONTROL.takeoffSafetyFactor * (1 - ag.share), 1.5)
  const takeoffPeak = fanTakeoff + ag.field
  const turn = ag.total * FLIGHT_CONTROL.turnPowerMargin
  const peak = Math.max(takeoffPeak, turn)
  return {
    baseHoverKw: r2(base),
    fanHoverKw: r2(ag.fan),
    fieldKw: r2(ag.field),
    hoverKw: r2(ag.total),
    takeoffPeakKw: r2(takeoffPeak),
    turnKw: r2(turn),
    share: r3(ag.share),
    peakFactor: r2(peak / Math.max(ag.total, 1e-9))
  }
}

/** 360° 原地转向时长（s）：T = 1.875·|Δ|/45°/s（峰值角速度舒适限内），最短 2.5s */
export function turnDurationSec(deltaDeg) {
  const t = FLIGHT_CONTROL.quinticPeakSlope * Math.abs(deltaDeg) / FLIGHT_CONTROL.turnPeakRateDps
  return Math.max(t, FLIGHT_CONTROL.turnMinSec)
}

/** 偏航角剖面（deg）：Δ·quintic(t/T) —— C² 端点归零（无卡顿、无姿态失稳），
 *  累计角无 wrap：连续指令多圈累加（全自由度无限制） */
export function yawAt(tSec, deltaDeg, durationSec) {
  return deltaDeg * quinticSmoothstep(tSec / Math.max(durationSec, 1e-6))
}

/** 悬停姿态残余微摆（deg，车体局部 roll/pitch 共用谱）：
 *  双低频正弦（0.07/0.11Hz，远离 0.5~1Hz 晕动频段），峰值 ≤0.85°/ζ < ±2° 包络 */
export function attitudeSample(tSec, darkMatterRatio) {
  const zeta = dampingRatio(darkMatterRatio)
  const a = 0.85 / zeta
  return a * 0.588 * Math.sin(2 * Math.PI * 0.07 * tSec) +
    a * 0.412 * Math.sin(2 * Math.PI * 0.11 * tSec + 1.3)
}

/** 姿态控制指标：过阻尼二阶回路，τ = 1/(ζ·2πf_n)，无超调 → 峰值即扰动注入值 */
export function attitudeControl(darkMatterRatio) {
  const zeta = dampingRatio(darkMatterRatio)
  const tauMs = 1000 / (zeta * 2 * Math.PI * FLIGHT_CONTROL.attitudeBandwidthHz)
  // 8° 大阵风注入后回落至 ±2° 带内的单调恢复时间（ζ≥1 无超调，指数衰减）
  const recoveryMs = tauMs * Math.log(
    FLIGHT_CONTROL.gustRecoveryFromDeg / FLIGHT_CONTROL.attitudeLimitDeg)
  return {
    limitDeg: FLIGHT_CONTROL.attitudeLimitDeg,
    bandwidthHz: FLIGHT_CONTROL.attitudeBandwidthHz,
    dampingRatio: r3(zeta),
    timeConstantMs: r2(tauMs),
    settlingMs: Math.round(tauMs * 3),          // 2% 带内调节时间
    recoveryMs: r2(recoveryMs),
    peakDeg: r3(0.85 / zeta)                    // 稳态残余扰动峰值
  }
}

/** 飞控响应延迟（ms）：指令链路延迟 vs 大扰动恢复时间取大者，≤100ms */
export function controlLatencyMs(liftFans, darkMatterRatio) {
  const chain = FLIGHT_CONTROL.latencyBaseMs +
    FLIGHT_CONTROL.latencyPerFanMs * clamp(Math.round(liftFans), 2, 8)
  const ac = attitudeControl(darkMatterRatio)
  return Math.round(Math.max(chain, ac.recoveryMs))
}

/** 反重力飞控总包线（UI 指标卡数据源；与后端 flight_envelope.flight_control 同公式） */
export function flightControlEnvelope(dimsMm, p) {
  const { curbMassKg } = flightEnvelope(dimsMm, p)
  const ep = energyProfile(curbMassKg, p.exoticRatio, p.darkMatterRatio)
  const ac = attitudeControl(p.darkMatterRatio)
  const latency = controlLatencyMs(p.liftFans, p.darkMatterRatio)
  const mult = enduranceMultiple(curbMassKg, p.exoticRatio, p.darkMatterRatio)
  return {
    curbMassKg,
    fieldLiftShare: ep.share,
    basePowerKw: ep.baseHoverKw,
    hoverPowerKw: ep.hoverKw,
    fieldPowerKw: ep.fieldKw,
    takeoffPeakKw: ep.takeoffPeakKw,
    peakFactor: ep.peakFactor,
    enduranceMultiple: r2(mult),
    enduranceBaseH: r2(FLIGHT_CONTROL.batteryKwh / Math.max(ep.baseHoverKw, 1e-9)),
    enduranceAgH: r2(FLIGHT_CONTROL.batteryKwh / Math.max(ep.hoverKw, 1e-9)),
    attitudeLimitDeg: FLIGHT_CONTROL.attitudeLimitDeg,
    attitudePeakDeg: ac.peakDeg,
    settlingMs: ac.settlingMs,
    latencyMs: latency,
    fullTurnSec: r2(turnDurationSec(360)),
    attitudeOk: ac.peakDeg <= FLIGHT_CONTROL.attitudeLimitDeg,
    peakOk: ep.peakFactor <= FLIGHT_CONTROL.peakFactorLimit,
    enduranceOk: mult >= FLIGHT_CONTROL.enduranceTarget,
    latencyOk: latency <= FLIGHT_CONTROL.latencyLimitMs
  }
}

/** 五次 smoothstep（C² 连续）：t∈ℝ → [0,1]，端点 s/s′/s″ 全为零 */
export function quinticSmoothstep(t) {
  const x = clamp(t, 0, 1)
  return x * x * x * (10 - 15 * x + 6 * x * x)
}

/** 高度剖面（mm）：t 秒时刻的悬浮高度，t > liftDuration 进入稳态悬浮 */
export function altitudeAt(tSec, p) {
  return p.hoverAltitude * quinticSmoothstep(tSec / Math.max(p.liftDuration, 1e-6))
}

/** 悬浮呼吸偏移（mm）：低频微幅正弦，振幅与频率均在无眩晕阈内 */
export function hoverBobOffset(tSec, p) {
  return p.hoverBobAmp * Math.sin(2 * Math.PI * p.hoverBobFreq * tSec)
}

/** VTOL 相位机：ground → lift → hover（t 为自起飞起累计秒） */
export function vtolPhase(tSec, p) {
  if (tSec <= 0) return 'ground'
  return tSec < p.liftDuration ? 'lift' : 'hover'
}

/** 有效重力（m/s²）：暗能量负压类比，g_eff = g·(1−0.35η)，η∈[0,0.3] → g_eff ∈ [0.895g, g] */
export function effectiveGravity(exoticRatio) {
  return 9.81 * (1 - 0.35 * clamp(exoticRatio, 0, 0.3))
}

/** 暗物质惯性配比下的阻尼比：ζ = 1 + 0.6·η_cdm ≥ 1（过阻尼 → 无超调 → 无眩晕） */
export function dampingRatio(darkMatterRatio) {
  return 1 + 0.6 * clamp(darkMatterRatio, 0, 0.3)
}

/** 悬浮推重比：T/W = g/g_eff = 1/(1−0.35η) ≥ 1（η=0 时恰为 1.0） */
export function thrustToWeight(exoticRatio) {
  return 1 / (1 - 0.35 * clamp(exoticRatio, 0, 0.3))
}

/** 整车飞行包线（工程估算，全部公式可复现）：
 *  curbMass ≈ 120 kg/m³ × 包络体积（L×W×H，mm→m³）——紧凑级整车密度线性外推；
 *  起飞推力含 1.2 安全系数（垂直爬升余量） */
export function flightEnvelope(dimsMm, p) {
  const L = dimsMm.overall_length, W = dimsMm.overall_width, H = dimsMm.overall_height
  const mass = (L * W * H) / 1e9 * 120.0
  const gEff = effectiveGravity(p.exoticRatio)
  const zeta = dampingRatio(p.darkMatterRatio)
  const thrust = (mass * gEff) / 1000.0
  return {
    curbMassKg: Math.round(mass * 10) / 10,
    effectiveGravity: Math.round(gEff * 1000) / 1000,
    thrustRequiredKn: Math.round(thrust * 100) / 100,
    thrustTakeoffKn: Math.round(thrust * 1.2 * 100) / 100,
    dampingRatio: Math.round(zeta * 1000) / 1000,
    hoverAltitudeM: Math.round((p.hoverAltitude / 1000) * 100) / 100,
    liftFans: p.liftFans,
    vertigoFree: zeta >= 1.0
  }
}
