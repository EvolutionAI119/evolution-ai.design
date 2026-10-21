import { describe, it, expect } from 'vitest'
import { deriveCarProfile, deriveWheelFitment, archLinerProfile, LINE_RATIOS, filletCorner } from '../utils/carProfile.js'
import { carTypeParams, defaultCarParams } from '../config/carPresets.js'

const ALL_TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']

// 全部车型必须满足的物理/拓扑约束（回归保护）
const assertUniversalConstraints = (p, type) => {
  // 前风挡：顶端在发动机舱端点之后、车顶在风挡之后
  expect(p.windshieldTopX).toBeLessThan(p.hoodEndX)
  expect(p.rearWindowTopX).toBeLessThan(p.windshieldTopX)

  // 后窗：下缘不得越过甲板/后围起点，更不得超出后保险杠平面
  expect(p.rearWindowBottomX).toBeGreaterThanOrEqual(p.trunkStartX)
  expect(p.rearWindowBottomX).toBeGreaterThanOrEqual(p.rearX - 0.01)

  // 高度关系：底边 < 发动机舱线 < 甲板线 < 车顶
  expect(p.bodyBottomY).toBeLessThan(p.hoodLineY)
  expect(p.trunkLineY).toBeLessThan(p.roofTopY)

  // 车轮在车身前后边界之内
  expect(p.frontWheelX).toBeLessThan(p.frontX)
  expect(p.rearWheelX).toBeGreaterThan(p.rearX)

  // 轮拱半径必须大于车轮半径（装配间隙）
  expect(p.wheelArchRadius).toBeGreaterThan(p.wheelR)
}

describe('轮拱开口 = 转向+跳动包络椭圆（真实轮拱几何）', () => {
  it.each(ALL_TYPES)('%s 拱心=静置接地轮心，拱顶让开跳动+顶隙，前拱含满舵扫掠', (type) => {
    const p = deriveCarProfile(carTypeParams[type], type)
    const a = p.wheelArch
    // 拱心 = 轮心（接地：胎底触地，轮心绝对高度 = 轮半径）
    expect(a.cy).toBeCloseTo(p.wheelR, 5)
    // 拱顶 ≥ 轮顶 + 跳动 + 顶隙（WHEEL_ENVELOPE 最小配置：jounce 30 + gapTop 25）
    expect(a.cy + a.front.ry).toBeGreaterThanOrEqual(p.wheelR * 2 + 0.054)
    // 前拱宽于后拱（满舵扫掠外扩），且两者均包住轮胎
    expect(a.front.rx).toBeGreaterThan(a.rear.rx)
    expect(a.front.rx).toBeGreaterThan(p.wheelR)
    expect(a.rear.rx).toBeGreaterThan(p.wheelR)
    // 兼容字段同源
    expect(p.wheelArchRadius).toBeCloseTo(a.front.rx, 5)
    expect(p.archY).toBeCloseTo(p.wheelR, 5)
  })

  it('开口随车轮增大而增大（同车型换大轮）', () => {
    const base = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const big = deriveCarProfile({ ...carTypeParams.sedan, wheel_diameter: 780 }, 'sedan')
    expect(big.wheelArch.front.rx).toBeGreaterThan(base.wheelArch.front.rx)
    expect(big.wheelArch.front.ry).toBeGreaterThan(base.wheelArch.front.ry)
  })

  it('车型风格差异：suv/pickup 扁拱（flatten）且越野间隙大于轿车', () => {
    const sedan = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const suv = deriveCarProfile(carTypeParams.suv, 'suv')
    const pickup = deriveCarProfile(carTypeParams.pickup, 'pickup')
    expect(suv.wheelArch.style).toBe('square')
    expect(pickup.wheelArch.style).toBe('square')
    expect(sedan.wheelArch.style).toBe('round')
    // 越野车型的跳动包络更大 → 拱顶相对轮顶的间隙更大
    const topGap = (p) => p.wheelArch.cy + p.wheelArch.front.ry - p.wheelR * 2
    expect(topGap(suv)).toBeGreaterThan(topGap(sedan))
    expect(topGap(pickup)).toBeGreaterThan(topGap(suv))
  })
})

describe('接近角 / 离去角布置设计基准（2D/3D 同源）', () => {
  it.each(ALL_TYPES)('%s 角度 = atan(离地间隙 / 对应悬长)，落在真车合理区间', (type) => {
    const p = deriveCarProfile(carTypeParams[type], type)
    expect(p.approachAngleDeg).toBeCloseTo((Math.atan2(p.gc, p.FO) * 180) / Math.PI, 9)
    expect(p.departureAngleDeg).toBeCloseTo((Math.atan2(p.gc, p.RO) * 180) / Math.PI, 9)
    expect(p.approachAngleDeg).toBeGreaterThan(3)
    expect(p.approachAngleDeg).toBeLessThan(30)
    expect(p.departureAngleDeg).toBeGreaterThan(3)
    expect(p.departureAngleDeg).toBeLessThan(30)
  })

  it('越野取向（suv/pickup）角度大于低趴取向（sport/coupe）', () => {
    const suv = deriveCarProfile(carTypeParams.suv, 'suv')
    const pickup = deriveCarProfile(carTypeParams.pickup, 'pickup')
    const sport = deriveCarProfile(carTypeParams.sport, 'sport')
    const coupe = deriveCarProfile(carTypeParams.coupe, 'coupe')
    expect(suv.approachAngleDeg).toBeGreaterThan(sport.approachAngleDeg)
    expect(pickup.approachAngleDeg).toBeGreaterThan(coupe.approachAngleDeg)
    expect(suv.departureAngleDeg).toBeGreaterThan(sport.departureAngleDeg)
    expect(pickup.departureAngleDeg).toBeGreaterThan(coupe.departureAngleDeg)
  })
})

describe('deriveWheelFitment 车轮装配配合（胎藏于侧壁、内衬包住拱口）', () => {
  it('轮胎名义断面宽与包络椭圆 c_steer 同源（0.36 × 轮径）', () => {
    for (const type of ALL_TYPES) {
      const p = deriveCarProfile(carTypeParams[type], type)
      expect(p.tireWidth).toBeCloseTo(p.wheelR * 2 * 0.36, 9)
    }
  })

  it.each(ALL_TYPES)('%s 胎外侧面收进车身侧壁内（0~50mm 浅藏）', (type) => {
    const p = deriveCarProfile(carTypeParams[type], type)
    const f = deriveWheelFitment(p)
    expect(f.tireOuter).toBeLessThan(f.wall)
    expect(f.tireOuter).toBeGreaterThan(f.wall - 0.05)
    // 轮心 Z 对称布置：两侧胎外侧面不交叉（2·wheelZ > tireW）
    expect(f.wheelZ * 2).toBeGreaterThan(f.tireW)
  })
})

describe('archLinerProfile 轮腔内衬轮廓（与拱口同形、内缩不互穿）', () => {
  it.each(ALL_TYPES)('%s 内衬每一点严格位于拱口空腔内（前后壁/顶部/底部均不戳出）', (type) => {
    const p = deriveCarProfile(carTypeParams[type], type)
    for (const side of ['front', 'rear']) {
      const a = p.wheelArch[side]
      const ax = side === 'front' ? p.frontWheelX : p.rearWheelX
      const inset = 0.012
      const prof = archLinerProfile(p, side, inset)
      expect(prof.length).toBeGreaterThan(8)
      for (const [x, y] of prof) {
        // X 不越出拱口半宽（内缩后）
        expect(Math.abs(x - ax)).toBeLessThanOrEqual(a.rx - inset + 1e-9)
        // 顶部不越出拱口顶（archY+ry），底部不越出车身底板
        expect(y).toBeLessThanOrEqual(p.archY + a.ry - inset + 1e-9)
        expect(y).toBeGreaterThanOrEqual(p.bodyBottomY - 1e-9)
      }
    }
  })

  it('inset 越大内衬越窄（顶/宽同比收缩），杜绝零内缩量贴壁', () => {
    const p = deriveCarProfile(carTypeParams.sport, 'sport')
    const wide = archLinerProfile(p, 'front', 0.002)
    const narrow = archLinerProfile(p, 'front', 0.04)
    const halfW = (prof) => Math.max(...prof.map(([x]) => x)) - Math.min(...prof.map(([x]) => x))
    expect(halfW(narrow)).toBeLessThan(halfW(wide))
  })
})

describe('deriveCarProfile 全车型物理约束', () => {
  it('默认参数（无车型分支）也能合法推导', () => {
    const p = deriveCarProfile(defaultCarParams, 'sedan')
    assertUniversalConstraints(p, 'sedan')
    // 官方语义：overall_height = 离地总高（含离地间隙），车顶 Y = H
    expect(p.roofTopY).toBeCloseTo(defaultCarParams.overall_height / 1000, 5)
  })

  it.each(ALL_TYPES)('%s 特征线高度 = H × LINE_RATIOS（离地语义，与 2D 同源）', (type) => {
    const params = carTypeParams[type]
    const p = deriveCarProfile(params, type)
    const H = params.overall_height / 1000
    const r = LINE_RATIOS[type]
    expect(p.roofTopY).toBeCloseTo(H, 5)
    expect(p.beltLineY).toBeCloseTo(H * r.belt, 5)
    expect(p.hoodLineY).toBeCloseTo(H * r.hood, 5)
    expect(p.trunkLineY).toBeCloseTo(H * (r.trunk ?? r.bed), 5)
    // 特征线必须高于车身底边（侧裙），且低于车顶
    expect(p.hoodLineY).toBeGreaterThan(p.bodyBottomY)
    expect(p.beltLineY).toBeLessThan(p.roofTopY)
  })

  it.each(ALL_TYPES)('%s 满足全部通用拓扑约束', (type) => {
    const p = deriveCarProfile(carTypeParams[type], type)
    assertUniversalConstraints(p, type)
  })

  it('空参数 / 缺字段时回退默认值，不抛异常', () => {
    expect(() => deriveCarProfile(undefined, 'sedan')).not.toThrow()
    expect(() => deriveCarProfile({}, 'suv')).not.toThrow()
    const p = deriveCarProfile({}, 'sedan')
    expect(p.W).toBeGreaterThan(0)
    expect(p.rearX).toBeLessThan(0)
  })
})

describe('MPV / SUV：后窗与行李架（原缺陷回归）', () => {
  it('MPV 后窗被约束在甲板起点，不突出车身', () => {
    const p = deriveCarProfile(carTypeParams.mpv, 'mpv')
    // 15° 后窗按角度会落到 -3.00m（超出后保险杠），必须被钳制到 trunkStartX
    expect(p.rearWindowBottomX).toBe(p.trunkStartX)
    expect(p.rearWindowBottomX).toBeGreaterThan(p.rearX)
  })

  it('MPV 行李架长边沿车长方向、位于车身宽度之内、半嵌车顶', () => {
    const p = deriveCarProfile(carTypeParams.mpv, 'mpv')
    expect(p.rails).not.toBeNull()
    expect(p.rails.length).toBeGreaterThan(0.5)
    // 两侧架体加半宽不得超出车身
    expect(Math.abs(p.rails.z) + 0.023).toBeLessThan(p.W / 2)
    // 半嵌：架体 Y 不高于车顶 0.02m
    expect(p.rails.y).toBeLessThan(p.roofTopY + 0.02)
  })

  it('SUV 同样钳制后窗、行李架合规', () => {
    const p = deriveCarProfile(carTypeParams.suv, 'suv')
    expect(p.rearWindowBottomX).toBe(p.trunkStartX)
    expect(p.rails).not.toBeNull()
  })

  it('轿车 / 跑车 / 轿跑 / 皮卡不生成行李架', () => {
    for (const type of ['sedan', 'sport', 'coupe', 'pickup']) {
      expect(deriveCarProfile(carTypeParams[type], type).rails).toBeNull()
    }
  })
})

describe('sport：GT 尾翼落在后甲板上', () => {
  it('尾翼支柱 X 位于甲板区间，支柱高度为正', () => {
    const p = deriveCarProfile(carTypeParams.sport, 'sport')
    expect(p.wing).not.toBeNull()
    expect(p.wing.x).toBeGreaterThanOrEqual(p.trunkStartX)
    expect(p.wing.x).toBeLessThan(p.rearWindowBottomX)
    expect(p.wing.supportH).toBeGreaterThan(0.1)
    expect(p.wing.span).toBeLessThanOrEqual(p.W)
  })

  it('非 sport 车型不生成尾翼', () => {
    for (const type of ['sedan', 'suv', 'mpv', 'coupe', 'pickup']) {
      expect(deriveCarProfile(carTypeParams[type], type).wing).toBeNull()
    }
  })
})

describe('pickup：专属拓扑（短驾驶室 + 开放货箱）', () => {
  it('驾驶室后壁位于后轮中心朝车头 0.5m（F-150 基准），车顶不贯通', () => {
    const p = deriveCarProfile(carTypeParams.pickup, 'pickup')
    expect(p.pickup).not.toBeNull()
    const { cabRearX } = p.pickup
    expect(cabRearX).toBeCloseTo(p.rearWheelX + 0.5, 5)
    expect(cabRearX).toBeGreaterThan(p.rearX)
  })

  it('货箱栏板上沿 = H × 0.58（≈F-150 栏板 1.09m），高于轮拱、低于腰带线', () => {
    const p = deriveCarProfile(carTypeParams.pickup, 'pickup')
    expect(p.pickup.bedWallY).toBeCloseTo(p.H * LINE_RATIOS.pickup.bed, 5)
    expect(p.pickup.bedWallY).toBeGreaterThan(p.archY)
    expect(p.pickup.bedWallY).toBeLessThan(p.beltLineY)
  })

  it('货箱栏板上沿高于轮拱，货箱完全落在车长范围内', () => {
    const p = deriveCarProfile(carTypeParams.pickup, 'pickup')
    const bed = p.pickup
    expect(bed.bedWallY).toBeGreaterThan(p.archY)
    expect(bed.bedFrontX).toBeLessThan(bed.cabRearX + 0.5)
    expect(bed.bedRearX).toBeGreaterThanOrEqual(p.rearX - 0.15)
    expect(bed.bedFrontX - bed.bedRearX).toBeGreaterThan(1.0)
    // 内舱宽度在车身之内
    expect(bed.bedInteriorHalfZ).toBeLessThan(p.W / 2)
  })

  it('非 pickup 车型不产生货箱结构', () => {
    for (const type of ['sedan', 'suv', 'mpv', 'coupe', 'sport']) {
      expect(deriveCarProfile(carTypeParams[type], type).pickup).toBeNull()
    }
  })
})

describe('极端参数：约束仍保证拓扑合法', () => {
  it('Cowl 斜坡锚点位于 hoodEnd 与前保险杠之间（全车型）', () => {
    for (const type of ALL_TYPES) {
      const p = deriveCarProfile(carTypeParams[type], type)
      expect(p.cowlStartX).toBeGreaterThan(p.hoodEndX)     // 3D X+ 朝车头：cowl 在 hoodEnd 之前
      expect(p.cowlStartX).toBeLessThanOrEqual(p.frontX - 0.03 + 1e-9)
    }
  })

  it('filletCorner 圆角：切点在段内、G1 切线方向与原直线一致', () => {
    // L 形角点：A(0,0) → P(1,0) → B(1,1)，r=0.2
    const f = filletCorner(0, 0, 1, 0, 1, 1, 0.2)
    expect(f.a[0]).toBeCloseTo(0.8, 9)                    // a 在 PA 段上距 P 为 r
    expect(f.a[1]).toBeCloseTo(0, 9)
    expect(f.ctrl).toEqual([1, 0])                        // 控制点 = 角点
    expect(f.b[0]).toBeCloseTo(1, 9)                      // b 在 PB 段上距 P 为 r
    expect(f.b[1]).toBeCloseTo(0.2, 9)
    // G1：曲线 t=0 切线（ctrl-a）∥ 原入线方向；t=1 切线（b-ctrl）∥ 原出线方向
    const inDot = (f.ctrl[0] - f.a[0]) * (1 - 0) + (f.ctrl[1] - f.a[1]) * 0
    const outDot = (f.b[0] - f.ctrl[0]) * 0 + (f.b[1] - f.ctrl[1]) * 1
    expect(inDot).toBeGreaterThan(0)
    expect(outDot).toBeGreaterThan(0)
  })

  it('filletCorner 短段保护：r 超过段长 45% 时钳位，不产生回折', () => {
    const f = filletCorner(0, 0, 0.1, 0, 0.1, 0.1, 5)
    expect(f.a[0]).toBeGreaterThanOrEqual(0.055 - 1e-9)   // t = 0.45 → a = 0.1 - 0.045
    expect(f.b[1]).toBeLessThanOrEqual(0.045 + 1e-9)
  })

  it('后窗角度极小（5°）时后窗仍不越出车身', () => {
    const params = { ...carTypeParams.sedan, rear_window_angle: 5 }
    const p = deriveCarProfile(params, 'sedan')
    expect(p.rearWindowBottomX).toBeGreaterThanOrEqual(p.trunkStartX)
  })

  it('后窗角度极大（80°）时后窗仍位于车顶后缘之前', () => {
    const params = { ...carTypeParams.sedan, rear_window_angle: 80 }
    const p = deriveCarProfile(params, 'sedan')
    expect(p.rearWindowBottomX).toBeLessThan(p.rearWindowTopX)
  })

  it('皮卡即使后窗角度很小，货箱拓扑仍由专属规则生成', () => {
    const params = { ...carTypeParams.pickup, rear_window_angle: 5 }
    const p = deriveCarProfile(params, 'pickup')
    expect(p.pickup).not.toBeNull()
    expect(p.rearWindowBottomX).toBe(p.pickup.cabWindowBottomX)
  })
})
