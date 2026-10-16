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
  sedan:  { hoverAltitude: 1600, liftDuration: 3.2, exoticRatio: 0.15, darkMatterRatio: 0.20, liftFans: 4, hoverBobAmp: 6, hoverBobFreq: 0.14 },
  suv:    { hoverAltitude: 1900, liftDuration: 3.6, exoticRatio: 0.18, darkMatterRatio: 0.24, liftFans: 6, hoverBobAmp: 7, hoverBobFreq: 0.12 },
  coupe:  { hoverAltitude: 1700, liftDuration: 3.0, exoticRatio: 0.16, darkMatterRatio: 0.20, liftFans: 4, hoverBobAmp: 6, hoverBobFreq: 0.15 },
  sport:  { hoverAltitude: 1650, liftDuration: 2.8, exoticRatio: 0.14, darkMatterRatio: 0.18, liftFans: 4, hoverBobAmp: 5, hoverBobFreq: 0.16 },
  mpv:    { hoverAltitude: 2000, liftDuration: 3.8, exoticRatio: 0.20, darkMatterRatio: 0.28, liftFans: 6, hoverBobAmp: 8, hoverBobFreq: 0.11 },
  pickup: { hoverAltitude: 1800, liftDuration: 3.4, exoticRatio: 0.22, darkMatterRatio: 0.26, liftFans: 6, hoverBobAmp: 8, hoverBobFreq: 0.12 }
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
