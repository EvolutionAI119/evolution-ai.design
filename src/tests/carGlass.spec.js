import { describe, it, expect } from 'vitest'
import { deriveCarProfile, filletCorner } from '../utils/carProfile.js'
import { bandGlassEndpoints, deriveCabinGlass, dloZAt, pillarPlacement, buildDloFrame, buildDloStrip, greenhouseInsetAt, filletXAtY, ROOF_FILLETS, SIDE_GLASS_TILT, SIDE_GLASS_BARREL } from '../utils/carGlass.js'
import { carTypeParams, defaultCarParams, brands } from '../config/carPresets.js'

const ALL_TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']

describe('bandGlassEndpoints 斜面玻璃带几何', () => {
  it('法线为单位向量且朝上（ny ≥ 0）', () => {
    const { normal } = bandGlassEndpoints(1, 0, 0, 1, 0, 0)
    const [nx, ny] = normal
    expect(Math.hypot(nx, ny)).toBeCloseTo(1, 10)
    expect(ny).toBeGreaterThanOrEqual(0)
  })

  it('下坡斜面法线自动翻转为朝上（外表面）', () => {
    // (0,1)→(1,0)：原始法线 ny<0，必须翻转为朝上
    const { normal } = bandGlassEndpoints(0, 1, 1, 0, 0, 0)
    expect(normal[1]).toBeGreaterThan(0)
    // 翻转后与手工计算一致：(-dy, dx)/len = (1, 1)/√2
    expect(normal[0]).toBeCloseTo(Math.SQRT1_2, 10)
    expect(normal[1]).toBeCloseTo(Math.SQRT1_2, 10)
  })

  it('topInset 使顶缘沿斜线下退，底缘不动', () => {
    const { a, b } = bandGlassEndpoints(0, 0, 0, 2, 0.5, 0)
    expect(a).toEqual([0, 0])
    expect(b[0]).toBeCloseTo(0, 10)
    expect(b[1]).toBeCloseTo(1.5, 10) // 2 - 0.5
  })

  it('topInset 超过段长 90% 时钳位，杜绝回折', () => {
    const { a, b } = bandGlassEndpoints(0, 0, 0, 2, 10, 0)
    expect(b[1]).toBeCloseTo(0.2, 10) // 2 × (1 - 0.9)
  })

  it('offset 沿法线平移两端点（贴合外扩后的车身侧壁）', () => {
    const { a, b } = bandGlassEndpoints(0, 0, 0, 2, 0, 0.031)
    // 竖直带法线 = (+1, 0)
    expect(a).toEqual([0.031, 0])
    expect(b).toEqual([0.031, 2])
  })

  it('零长度带不抛异常（len || 1 保护）', () => {
    expect(() => bandGlassEndpoints(0, 0, 0, 0, 0.09, 0.03)).not.toThrow()
  })
})

describe('deriveCabinGlass 与 2D Car2D windowPath/pillarX 逐点同源', () => {
  it('前风挡带锚点 = A 柱线（COWL → 车顶前缘），宽度 = W × 0.9', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P)
    expect(g.windshield.x1).toBeCloseTo(P.hoodEndX, 10)
    expect(g.windshield.y1).toBeCloseTo(P.beltLineY, 10)
    expect(g.windshield.x2).toBeCloseTo(P.windshieldTopX, 10)
    expect(g.windshield.y2).toBeCloseTo(P.roofTopY, 10)
    expect(g.windshield.width).toBeCloseTo(P.W * 0.9, 10)
    // 顶缘下退 = A 柱顶圆角半径；底缘下退避开 COWL 直角 bevel 外扩角
    expect(g.windshield.topInset).toBeCloseTo(ROOF_FILLETS.aPillarTop, 10)
    expect(g.windshield.bottomInset).toBeCloseTo(0.06, 10)
  })

  it('三厢车后风挡存在，锚点 = C 柱线，宽度 = W × 0.88', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P)
    expect(g.rearWindow).not.toBeNull()
    expect(g.rearWindow.x1).toBeCloseTo(P.rearWindowBottomX, 10)
    expect(g.rearWindow.y1).toBeCloseTo(P.beltLineY, 10)
    expect(g.rearWindow.x2).toBeCloseTo(P.rearWindowTopX, 10)
    expect(g.rearWindow.y2).toBeCloseTo(P.roofTopY, 10)
    expect(g.rearWindow.width).toBeCloseTo(P.W * 0.88, 10)
    expect(g.rearWindow.topInset).toBeCloseTo(ROOF_FILLETS.roofRear, 10)
  })

  it('DLO 四边形与轮廓 G1 圆角同源：底前角在 A 柱斜线上、顶后角由圆角贝塞尔求解、底后角沿 C 柱斜线上退', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P)
    const [p0, p1, p2, p3] = g.dlo
    const dloTopY = P.roofTopY - 0.035
    const dloBotY = P.beltLineY + 0.008
    // 底前角：A 柱斜线（COWL→车顶前缘）在 dloBotY 高度的 X，再向车尾内移 4mm
    const rakeAtBot = P.hoodEndX + (P.windshieldTopX - P.hoodEndX) * (0.008 / (P.roofTopY - P.beltLineY))
    expect(p0[0]).toBeCloseTo(rakeAtBot - 0.004, 12)
    expect(p0[1]).toBeCloseTo(dloBotY, 12)
    // 顶前角：车顶前缘内收 12mm（A 柱顶圆角切线区前为直线段，保持原修裁）
    expect(p1).toEqual([P.windshieldTopX + 0.012, dloTopY])
    // 顶后角：车顶后缘圆角贝塞尔在 dloTopY 高度的 X，再向座舱内移 6mm
    const f2 = filletCorner(P.windshieldTopX, P.roofTopY, P.rearWindowTopX, P.roofTopY,
      P.rearWindowBottomX, P.beltLineY, ROOF_FILLETS.roofRear)
    expect(p2[0]).toBeCloseTo(filletXAtY(f2, dloTopY) + 0.006, 10)
    expect(p2[1]).toBeCloseTo(dloTopY, 10)
    // 底后角：沿 C 柱斜线上退 min(r3+0.014, 45% 斜线长) 避开圆角切线区，再向车头内移 4mm
    const cdx = P.rearWindowTopX - P.rearWindowBottomX
    const cdy = P.roofTopY - P.beltLineY
    const clen = Math.hypot(cdx, cdy)
    const back = Math.min(ROOF_FILLETS.cPillarBottom + 0.014, clen * 0.45)
    expect(p3[0]).toBeCloseTo(P.rearWindowBottomX + (cdx / clen) * back + 0.004, 10)
    expect(p3[1]).toBeCloseTo(P.beltLineY + (cdy / clen) * back, 10)
  })

  it('B 柱 = DLO 顶跨 55% 分段（与 2D pillarX 同公式），顶端搭入 DLO 顶边消除悬浮', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P)
    expect(g.pillar.x).toBeCloseTo(
      P.windshieldTopX + (P.rearWindowTopX - P.windshieldTopX) * 0.55, 10
    )
    // 55% 插值朝车尾方向（dloTopRear < windshieldTopX，X+ 为车头）
    expect(g.pillar.x).toBeLessThan(P.windshieldTopX)
    expect(g.pillar.x).toBeGreaterThan(g.dloTopRear)
    // 顶端越过 DLO 顶边 2mm（搭接玻璃面，消除 15mm 悬浮缝隙），仍低于车顶线
    expect(g.pillar.topY).toBeCloseTo(P.roofTopY - 0.033, 10)
    expect(g.pillar.topY).toBeGreaterThanOrEqual(g.dlo[1][1])
    expect(g.pillar.topY).toBeLessThan(P.roofTopY)
    expect(g.pillar.botY).toBeCloseTo(P.beltLineY + 0.035, 10)
    expect(g.pillar.topY).toBeGreaterThan(g.pillar.botY)
    expect(g.pillar.botY).toBeGreaterThan(g.dlo[0][1])
  })

  it('皮卡专属拓扑：无后风挡，DLO 止于驾驶室后壁（顶后角按驾驶室圆角修裁）', () => {
    const P = deriveCarProfile(carTypeParams.pickup, 'pickup')
    const g = deriveCabinGlass(P)
    expect(g.rearWindow).toBeNull()
    expect(g.dloTopRear).toBeCloseTo(P.pickup.cabRearX, 10)
    expect(g.dloBotRear).toBeCloseTo(P.pickup.cabWindowBottomX, 10)
    const dloTopY = P.roofTopY - 0.035
    const f2p = filletCorner(P.windshieldTopX, P.roofTopY, P.pickup.cabRearX, P.roofTopY,
      P.pickup.cabWindowBottomX, P.pickup.bedWallY, ROOF_FILLETS.pickupCabTop)
    expect(g.dlo[2][0]).toBeCloseTo(filletXAtY(f2p, dloTopY) + 0.006, 10)
    expect(g.dlo[2][1]).toBeCloseTo(dloTopY, 10)
    expect(g.dlo[3]).toEqual([P.pickup.cabWindowBottomX, P.beltLineY + 0.008])
    expect(g.pillar.x).toBeCloseTo(
      P.windshieldTopX + (P.pickup.cabRearX - P.windshieldTopX) * 0.55, 10
    )
  })

  it.each(ALL_TYPES)('%s 玻璃面板拓扑合法（DLO 高于底边、风挡锚点有序）', (type) => {
    const P = deriveCarProfile(carTypeParams[type], type)
    const g = deriveCabinGlass(P)
    // 前风挡：底缘在车头侧、顶缘在车顶（X 向后收、Y 向上升）
    expect(g.windshield.x2).toBeLessThan(g.windshield.x1)
    expect(g.windshield.y2).toBeGreaterThan(g.windshield.y1)
    // DLO：顶边高于底边，顶前角在底前角之后（车头在 +X）
    expect(g.dlo[1][1]).toBeGreaterThan(g.dlo[0][1])
    expect(g.dlo[1][0]).toBeLessThan(g.dlo[0][0])
    // 顶后角与底后角关系（后窗斜面不回折）：
    // 常规车 C 柱向后倾 → 底后角更靠车尾；皮卡驾驶室后窗 → 底后角在顶后角车头侧
    if (type === 'pickup') {
      expect(g.dlo[3][0]).toBeGreaterThan(g.dlo[2][0])
    } else {
      expect(g.dlo[2][0]).toBeGreaterThanOrEqual(g.dlo[3][0])
    }
    // B 柱严格落在 DLO 水平跨度内（55% 插值朝车尾方向）
    expect(g.pillar.x).toBeLessThan(P.windshieldTopX)
    expect(g.pillar.x).toBeGreaterThan(g.dloTopRear)
  })
})

describe('侧玻璃倾角（tumblehome，前视车肩造型）', () => {
  it('SIDE_GLASS_TILT 六车型角度均在真车合理区间（5~30°）', () => {
    for (const type of ALL_TYPES) {
      expect(SIDE_GLASS_TILT[type]).toBeGreaterThan(5)
      expect(SIDE_GLASS_TILT[type]).toBeLessThan(30)
    }
  })

  it('运动/轿跑倾角大于 SUV/皮卡（前视车肩更窄）', () => {
    expect(SIDE_GLASS_TILT.sport).toBeGreaterThan(SIDE_GLASS_TILT.suv)
    expect(SIDE_GLASS_TILT.coupe).toBeGreaterThan(SIDE_GLASS_TILT.suv)
    expect(SIDE_GLASS_TILT.suv).toBeGreaterThan(SIDE_GLASS_TILT.pickup)
  })

  it.each(ALL_TYPES)('%s 输出 tiltDeg/barrelAngle=车型默认，dloTopInsetZ = 倾角内收 + 桶面内收', (type) => {
    const P = deriveCarProfile(carTypeParams[type], type)
    const g = deriveCabinGlass(P, { carType: type })
    expect(g.tiltDeg).toBeCloseTo(SIDE_GLASS_TILT[type], 10)
    expect(g.barrelAngle).toBeCloseTo(SIDE_GLASS_BARREL[type].angle, 10)
    expect(g.barrelRadius).toBeCloseTo(SIDE_GLASS_BARREL[type].radius / 1000, 10)
    const dloTopY = P.roofTopY - 0.035
    const dloBotY = P.beltLineY + 0.008
    const tiltInset = (dloTopY - dloBotY) * Math.tan((SIDE_GLASS_TILT[type] * Math.PI) / 180)
    const barrelInset = (SIDE_GLASS_BARREL[type].radius / 1000) * (1 - Math.cos((SIDE_GLASS_BARREL[type].angle * Math.PI) / 180))
    expect(g.tiltInsetZ).toBeCloseTo(tiltInset, 12)
    expect(g.dloTopInsetZ).toBeCloseTo(tiltInset + barrelInset, 12)
    expect(g.dloTopInsetZ).toBeGreaterThan(g.tiltInsetZ)   // 桶面使总内收大于纯倾角
    // 内收量为正且远小于半车宽（不越过车身中线）
    expect(g.dloTopInsetZ).toBeGreaterThan(0)
    expect(g.dloTopInsetZ).toBeLessThan(P.W / 2)
  })

  it('carParams.side_glass_angle 显式覆盖车型默认', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P, { carType: 'sedan', sideGlassAngle: 30 })
    expect(g.tiltDeg).toBeCloseTo(30, 10)
  })

  it('非法覆盖（NaN / 越界 / 负值）自动回退车型默认', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    for (const bad of [NaN, 0, -5, 45, 100]) {
      const g = deriveCabinGlass(P, { carType: 'sedan', sideGlassAngle: bad })
      expect(g.tiltDeg).toBeCloseTo(SIDE_GLASS_TILT.sedan, 10)
    }
  })

  it('carType 缺省时由 P.pickup 推断皮卡倾角', () => {
    const P = deriveCarProfile(carTypeParams.pickup, 'pickup')
    const g = deriveCabinGlass(P)
    expect(g.tiltDeg).toBeCloseTo(SIDE_GLASS_TILT.pickup, 10)
  })
})

describe('dloZAt DLO 倾斜面 Z 插值（tumblehome 消费端几何）', () => {
  // 简单框架：底边 z=1.05，跨 0.4m，内收 0.1m
  const F = { dloYBot: 0.8, dloYSpan: 0.4, dloTopInsetZ: 0.1, dloZBase: 1.05 }

  it('底边高度返回 dloZBase（不内收）', () => {
    expect(dloZAt(0.8, F, 1)).toBeCloseTo(1.05, 12)
  })

  it('顶边高度内收 dloTopInsetZ', () => {
    expect(dloZAt(1.2, F, 1)).toBeCloseTo(0.95, 12)
  })

  it('中点线性插值（半内收）', () => {
    expect(dloZAt(1.0, F, 1)).toBeCloseTo(1.0, 12)
  })

  it('超出 [底, 顶] 的高度按边界钳位（不外扩）', () => {
    expect(dloZAt(0.5, F, 1)).toBeCloseTo(1.05, 12)   // 低于底边 → 底边值
    expect(dloZAt(2.0, F, 1)).toBeCloseTo(0.95, 12)   // 高于顶边 → 顶边值
  })

  it('zSide=-1 严格镜像（|z| 相等、符号相反）', () => {
    for (const y of [0.8, 0.9, 1.0, 1.1, 1.2]) {
      expect(dloZAt(y, F, -1)).toBeCloseTo(-dloZAt(y, F, 1), 12)
    }
  })

  it('dloYSpan=0 不抛异常（|| 1 保护：底边→dloZBase，1m 后钳位到顶边）', () => {
    const F0 = { dloYBot: 0.8, dloYSpan: 0, dloTopInsetZ: 0.1, dloZBase: 1.05 }
    expect(dloZAt(0.8, F0, 1)).toBeCloseTo(1.05, 12)   // t=0（底边）
    expect(dloZAt(1.8, F0, 1)).toBeCloseTo(0.95, 12)   // t=clamp(1/1)=1（顶边值）
  })
})

describe('pillarPlacement B 柱定位（与 DLO 共面同倾角）', () => {
  const P = deriveCarProfile(carTypeParams.sport, 'sport')
  const cabin = deriveCabinGlass(P, { carType: 'sport' })
  const dloYBot = cabin.dlo[0][1]
  const dloYSpan = cabin.dlo[1][1] - dloYBot
  const dloZBase = 1.05

  // 与 pillarPlacement 内部一致的全参框架（倾角 + 桶面）
  const glassFrame = (c, yBot, ySpan, zBase) => ({
    dloYBot: yBot,
    dloYSpan: ySpan,
    dloZBase: zBase,
    tiltInsetZ: ySpan * Math.tan((c.tiltDeg * Math.PI) / 180),
    barrelRad: (c.barrelAngle * Math.PI) / 180,
    barrelRadius: c.barrelRadius
  })

  it('底部 Z 锚点与 dloZAt(botY) 完全一致（共面性）', () => {
    const pp = pillarPlacement(cabin, dloYBot, dloYSpan, dloZBase)
    const glassZ = Math.abs(dloZAt(cabin.pillar.botY, glassFrame(cabin, dloYBot, dloYSpan, dloZBase), 1))
    expect(pp.baseZ).toBeCloseTo(glassZ, 12)
  })

  it('底部锚点位于 DLO 底边与顶边之间（B 柱下端低于顶边内收量）', () => {
    const pp = pillarPlacement(cabin, dloYBot, dloYSpan, dloZBase)
    expect(pp.baseZ).toBeLessThan(dloZBase)
    expect(pp.baseZ).toBeGreaterThan(dloZBase - cabin.dloTopInsetZ)
  })

  it('tiltRad = tiltDeg 的弧度转换，立柱几何透传', () => {
    const pp = pillarPlacement(cabin, dloYBot, dloYSpan, dloZBase)
    expect(pp.tiltRad).toBeCloseTo((cabin.tiltDeg * Math.PI) / 180, 12)
    expect(pp.x).toBeCloseTo(cabin.pillar.x, 12)
    expect(pp.botY).toBeCloseTo(cabin.pillar.botY, 12)
    expect(pp.height).toBeCloseTo(cabin.pillar.topY - cabin.pillar.botY, 12)
    expect(pp.height).toBeGreaterThan(0)
  })

  it('皮卡同样满足共面性（专属拓扑下 B 柱锚定驾驶室玻璃面）', () => {
    const Pk = deriveCarProfile(carTypeParams.pickup, 'pickup')
    const ck = deriveCabinGlass(Pk, { carType: 'pickup' })
    const yBot = ck.dlo[0][1]
    const ySpan = ck.dlo[1][1] - yBot
    const pp = pillarPlacement(ck, yBot, ySpan, dloZBase)
    const glassZ = Math.abs(dloZAt(ck.pillar.botY, glassFrame(ck, yBot, ySpan, dloZBase), 1))
    expect(pp.baseZ).toBeCloseTo(glassZ, 12)
  })
})

describe('SIDE_GLASS_BARREL 玻璃桶面（前视玻璃鼓肚造型）', () => {
  it('六车型桶面参数均在真车合理区间（角 0~20°、半径 400~5000mm）', () => {
    for (const type of ALL_TYPES) {
      const b = SIDE_GLASS_BARREL[type]
      expect(b.angle).toBeGreaterThanOrEqual(0)
      expect(b.angle).toBeLessThanOrEqual(20)
      expect(b.radius).toBeGreaterThanOrEqual(400)
      expect(b.radius).toBeLessThanOrEqual(5000)
    }
  })

  it('运动/轿跑桶面角大于 SUV/皮卡（鼓肚更明显）', () => {
    expect(SIDE_GLASS_BARREL.sport.angle).toBeGreaterThan(SIDE_GLASS_BARREL.suv.angle)
    expect(SIDE_GLASS_BARREL.coupe.angle).toBeGreaterThan(SIDE_GLASS_BARREL.pickup.angle)
  })

  it('carPresets 契约：defaultCarParams 与六车型均携带三个玻璃字段且与车型表一致', () => {
    const keys = ['side_glass_angle', 'glass_barrel_angle', 'glass_barrel_radius']
    for (const k of keys) {
      expect(defaultCarParams).toHaveProperty(k)
    }
    expect(defaultCarParams.side_glass_angle).toBe(SIDE_GLASS_TILT.sedan)
    for (const type of ALL_TYPES) {
      const p = carTypeParams[type]
      expect(p.side_glass_angle).toBe(SIDE_GLASS_TILT[type])
      expect(p.glass_barrel_angle).toBe(SIDE_GLASS_BARREL[type].angle)
      expect(p.glass_barrel_radius).toBe(SIDE_GLASS_BARREL[type].radius)
    }
  })

  it('carPresets 契约：19 款品牌认证车型 params 均携带与其 car_type 一致的玻璃三参数', () => {
    // 回归保护：setCarType/selectModel 双向连动应用 model.params，
    // 若品牌车型缺玻璃字段，切换车型后滑块会停留在 sedan 默认值
    let count = 0
    for (const b of brands) {
      for (const m of b.models) {
        expect(m.car_type, `${b.key}/${m.key} 应标注 car_type`).toBeTruthy()
        expect(m.params.side_glass_angle).toBe(SIDE_GLASS_TILT[m.car_type])
        expect(m.params.glass_barrel_angle).toBe(SIDE_GLASS_BARREL[m.car_type].angle)
        expect(m.params.glass_barrel_radius).toBe(SIDE_GLASS_BARREL[m.car_type].radius)
        count++
      }
    }
    expect(count).toBe(19)
  })

  it('glassBarrelAngle / glassBarrelRadius 显式覆盖车型默认（radius 单位 mm → 内部米）', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P, { carType: 'sedan', glassBarrelAngle: 14, glassBarrelRadius: 800 })
    expect(g.barrelAngle).toBeCloseTo(14, 10)
    expect(g.barrelRadius).toBeCloseTo(0.8, 10)
  })

  it('非法桶面覆盖（NaN / 负值 / 超上限）自动回退车型默认', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    for (const bad of [NaN, -2, 21, 100]) {
      const g = deriveCabinGlass(P, { carType: 'sedan', glassBarrelAngle: bad })
      expect(g.barrelAngle).toBeCloseTo(SIDE_GLASS_BARREL.sedan.angle, 10)
    }
    for (const bad of [NaN, 100, 399, 6000]) {
      const g = deriveCabinGlass(P, { carType: 'sedan', glassBarrelRadius: bad })
      expect(g.barrelRadius).toBeCloseTo(SIDE_GLASS_BARREL.sedan.radius / 1000, 10)
    }
  })

  it('barrelAngle=0 时桶面内收为零，dloTopInsetZ 退化为纯倾角（向后兼容）', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P, { carType: 'sedan', glassBarrelAngle: 0 })
    expect(g.dloTopInsetZ).toBeCloseTo(g.tiltInsetZ, 12)
  })

  it('dloZAt 桶面轮廓：顶边总内收 = 倾角 + R(1−cos β)，中段相对端点连线外凸（鼓肚）', () => {
    const F = { dloYBot: 0.8, dloYSpan: 0.4, tiltInsetZ: 0.1, barrelRad: (10 * Math.PI) / 180, barrelRadius: 0.9, dloZBase: 1.05 }
    // 顶边（t=1）：0.1 + 0.9 × (1 − cos10°)
    const topExpected = 1.05 - 0.1 - 0.9 * (1 - Math.cos((10 * Math.PI) / 180))
    expect(dloZAt(1.2, F, 1)).toBeCloseTo(topExpected, 12)
    // 底边不内收
    expect(dloZAt(0.8, F, 1)).toBeCloseTo(1.05, 12)
    // 中段鼓肚：z(t=0.5) 高于端点连线（线性插值）在中点的值
    const chordMid = (1.05 + topExpected) / 2
    expect(dloZAt(1.0, F, 1)).toBeGreaterThan(chordMid)
    // 单调内收：高度越高 |Z| 越小
    for (const y of [0.85, 0.95, 1.05, 1.15]) {
      expect(dloZAt(y, F, 1)).toBeLessThan(dloZAt(y - 0.05, F, 1))
    }
  })

  it('dloZAt 无桶面字段时与旧线性公式逐点一致（向后兼容）', () => {
    const F = { dloYBot: 0.8, dloYSpan: 0.4, dloTopInsetZ: 0.1, dloZBase: 1.05 }
    for (const y of [0.8, 0.9, 1.0, 1.1, 1.2, 1.5]) {
      const t = Math.min(Math.max((y - 0.8) / 0.4, 0), 1)
      expect(dloZAt(y, F, 1)).toBeCloseTo(1.05 - t * 0.1, 12)
    }
  })

  it('桶面下 pillarPlacement 仍与玻璃面共面（barrel=0 与 barrel>0 两态）', () => {
    const P = deriveCarProfile(carTypeParams.coupe, 'coupe')
    for (const barrel of [0, 14]) {
      const c = deriveCabinGlass(P, { carType: 'coupe', glassBarrelAngle: barrel })
      const yBot = c.dlo[0][1]
      const ySpan = c.dlo[1][1] - yBot
      const pp = pillarPlacement(c, yBot, ySpan, 1.05)
      const glassZ = Math.abs(dloZAt(c.pillar.botY, {
        dloYBot: yBot, dloYSpan: ySpan, dloZBase: 1.05,
        tiltInsetZ: ySpan * Math.tan((c.tiltDeg * Math.PI) / 180),
        barrelRad: (c.barrelAngle * Math.PI) / 180,
        barrelRadius: c.barrelRadius
      }, 1))
      expect(pp.baseZ).toBeCloseTo(glassZ, 12)
    }
  })
})

describe('buildDloFrame / buildDloStrip DLO 条带网格（Car3D 消费端纯函数）', () => {
  const P = deriveCarProfile(carTypeParams.sport, 'sport')
  const cabin = deriveCabinGlass(P, { carType: 'sport' })

  it('buildDloFrame：字段派生正确（跨度/弧度换算/Z 基准透传）', () => {
    const f = buildDloFrame(cabin, 1.05)
    expect(f.dloYBot).toBeCloseTo(cabin.dlo[0][1], 12)
    expect(f.dloYSpan).toBeCloseTo(cabin.dlo[1][1] - cabin.dlo[0][1], 12)
    expect(f.tiltInsetZ).toBeCloseTo(cabin.tiltInsetZ, 12)
    expect(f.barrelRad).toBeCloseTo((cabin.barrelAngle * Math.PI) / 180, 12)
    expect(f.barrelRadius).toBeCloseTo(cabin.barrelRadius, 12)
    expect(f.dloZBase).toBe(1.05)
  })

  it('buildDloStrip：顶点数 = rows × 18，首顶点 = DLO 底前角（t=0）', () => {
    const rows = 8
    const f = buildDloFrame(cabin, 1.05)
    const pos = buildDloStrip(cabin.dlo, f, rows, 1)
    expect(pos.length).toBe(rows * 18)
    expect(pos[0]).toBeCloseTo(cabin.dlo[0][0], 12)
    expect(pos[1]).toBeCloseTo(f.dloYBot, 12)
    expect(pos[2]).toBeCloseTo(f.dloZBase, 12)
  })

  it('buildDloStrip：末行顶点落在 DLO 顶缘（t=1 处 x/y 与 dlo 顶角一致）', () => {
    const rows = 8
    const f = buildDloFrame(cabin, 1.05)
    const pos = buildDloStrip(cabin.dlo, f, rows, 1)
    const last = pos.slice(pos.length - 9)   // 行内最后 3 顶点：[rx0,y0,z0, rx1,y1,z1, fx1,y1,z1]
    expect(last[6]).toBeCloseTo(cabin.dlo[1][0], 12)         // 前上角 x（第 6 顶点）
    expect(last[7]).toBeCloseTo(f.dloYBot + f.dloYSpan, 12)  // 顶缘 y
    // 顶缘 Z = 全额内收（倾角 + 桶面），桶面使其低于纯线性内收
    const topZ = f.dloZBase - f.tiltInsetZ - f.barrelRadius * (1 - Math.cos(f.barrelRad))
    expect(last[8]).toBeCloseTo(topZ, 12)
    expect(last[8]).toBeLessThan(f.dloZBase - f.tiltInsetZ)
  })

  it('buildDloStrip：行边界 y 均匀递进，每行 Z 与 dloZAt 同公式', () => {
    const rows = 16
    const f = buildDloFrame(cabin, 1.05)
    const pos = buildDloStrip(cabin.dlo, f, rows, 1)
    for (let r = 0; r < rows; r++) {
      const y0 = f.dloYBot + (r / rows) * f.dloYSpan
      const b = r * 18
      expect(pos[b + 1]).toBeCloseTo(y0, 12)                       // 首顶点 y
      expect(pos[b + 2]).toBeCloseTo(dloZAt(y0, f, 1), 12)         // 首顶点 z
      expect(pos[b + 5]).toBeCloseTo(dloZAt(y0, f, 1), 12)         // 第二顶点 z（同行）
    }
  })

  it('buildDloStrip：zSide=-1 严格镜像（x/y 相同，z 逐点取反）', () => {
    const f = buildDloFrame(cabin, 1.05)
    const left = buildDloStrip(cabin.dlo, f, 6, 1)
    const right = buildDloStrip(cabin.dlo, f, 6, -1)
    expect(left.length).toBe(right.length)
    for (let i = 0; i < left.length; i += 3) {
      expect(right[i]).toBeCloseTo(left[i], 12)
      expect(right[i + 1]).toBeCloseTo(left[i + 1], 12)
      expect(right[i + 2]).toBeCloseTo(-left[i + 2], 12)
    }
  })

  it('dloZAt 桶面下越界高度同样钳位（底部桶面贡献为零、顶部全额内收）', () => {
    const F = { dloYBot: 0.8, dloYSpan: 0.4, tiltInsetZ: 0.1, barrelRad: (10 * Math.PI) / 180, barrelRadius: 0.9, dloZBase: 1.05 }
    const topZ = 1.05 - 0.1 - 0.9 * (1 - Math.cos((10 * Math.PI) / 180))
    expect(dloZAt(0.5, F, 1)).toBeCloseTo(1.05, 12)    // 低于底边 → 底边值（t=0）
    expect(dloZAt(2.0, F, 1)).toBeCloseTo(topZ, 12)    // 高于顶边 → 顶边值（t=1）
  })

  it('dloZAt 桶面下 zSide=-1 严格镜像', () => {
    const F = { dloYBot: 0.8, dloYSpan: 0.4, tiltInsetZ: 0.1, barrelRad: (10 * Math.PI) / 180, barrelRadius: 0.9, dloZBase: 1.05 }
    for (const y of [0.8, 0.9, 1.0, 1.1, 1.2, 1.5]) {
      expect(dloZAt(y, F, -1)).toBeCloseTo(-dloZAt(y, F, 1), 12)
    }
  })

  it('仅覆盖 glassBarrelRadius 时角度回退车型默认，反之亦然（两字段独立校验）', () => {
    const Ps = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const gR = deriveCabinGlass(Ps, { carType: 'sedan', glassBarrelRadius: 3000 })
    expect(gR.barrelAngle).toBeCloseTo(SIDE_GLASS_BARREL.sedan.angle, 10)
    expect(gR.barrelRadius).toBeCloseTo(3, 10)
    const gA = deriveCabinGlass(Ps, { carType: 'sedan', glassBarrelAngle: 15 })
    expect(gA.barrelAngle).toBeCloseTo(15, 10)
    expect(gA.barrelRadius).toBeCloseTo(SIDE_GLASS_BARREL.sedan.radius / 1000, 10)
  })
})

describe('greenhouseInsetAt 车身 greenhouse 收窄（A/B/C 柱与车顶随玻璃角度联动）', () => {
  const F = { dloYBot: 0.8, dloYSpan: 0.4, tiltInsetZ: 0.1, barrelRad: (10 * Math.PI) / 180, barrelRadius: 0.9, dloZBase: 1.05 }

  it('DLO 底边处内收为 0（车身侧壁与玻璃面同锚）', () => {
    expect(greenhouseInsetAt(0.8, F)).toBeCloseTo(0, 12)
  })

  it('DLO 顶边处内收 = 倾角 + 桶面全额', () => {
    const expected = 0.1 + 0.9 * (1 - Math.cos((10 * Math.PI) / 180))
    expect(greenhouseInsetAt(1.2, F)).toBeCloseTo(expected, 12)
  })

  it('恒等式：inset(y) = dloZBase − |dloZAt(y, f, 1)|（车身与玻璃面共享轮廓）', () => {
    for (const y of [0.8, 0.9, 1.0, 1.1, 1.2, 1.5]) {
      expect(greenhouseInsetAt(y, F)).toBeCloseTo(F.dloZBase - Math.abs(dloZAt(y, F, 1)), 12)
    }
  })

  it('barrel>0 时内收为凸函数：中段内收小于端点弦中点（对应玻璃 Z 鼓肚）', () => {
    const bottom = greenhouseInsetAt(0.8, F)
    const top = greenhouseInsetAt(1.2, F)
    const mid = greenhouseInsetAt(1.0, F)
    // 精确值：t=0.5 → 0.5×倾角分量 + R(1−cos(β/2))
    expect(mid).toBeCloseTo(0.05 + 0.9 * (1 - Math.cos((10 * Math.PI) / 180 * 0.5)), 12)
    // 凸性：内收先慢后快，中段低于端点连线中点
    expect(mid).toBeLessThan((bottom + top) / 2)
  })

  it('无 barrel 字段时严格线性（纯倾角，向后兼容）', () => {
    const Fs = { dloYBot: 0.8, dloYSpan: 0.4, dloTopInsetZ: 0.1, dloZBase: 1.05 }
    expect(greenhouseInsetAt(0.8, Fs)).toBeCloseTo(0, 12)
    expect(greenhouseInsetAt(1.0, Fs)).toBeCloseTo(0.05, 12)
    expect(greenhouseInsetAt(1.2, Fs)).toBeCloseTo(0.1, 12)
    expect(greenhouseInsetAt(1.5, Fs)).toBeCloseTo(0.1, 12)  // 越界钳位到全额
  })

  it('真实车型：DLO 顶边内收等于 cabin.dloTopInsetZ（buildDloFrame 衔接）', () => {
    for (const type of ALL_TYPES) {
      const P = deriveCarProfile(carTypeParams[type], type)
      const cabin = deriveCabinGlass(P, { carType: type })
      const f = buildDloFrame(cabin, 1.0)
      expect(greenhouseInsetAt(cabin.dlo[1][1], f)).toBeCloseTo(cabin.dloTopInsetZ, 12)
      expect(greenhouseInsetAt(cabin.dlo[0][1] - 0.5, f)).toBeCloseTo(0, 12)
    }
  })
})

describe('filletXAtY 圆角贝塞尔求值（DLO 顶后角修裁依据）', () => {
  // 手工圆角：a=(1,0)，ctrl=(0,0)（角点），b=(0,1) → y(t)=t²，x(t)=(1−t)²
  // y=0.25 → t=0.5 → x=0.25
  const F = { a: [1, 0], ctrl: [0, 0], b: [0, 1] }

  it('端点命中：y = a_y 返回 a_x，y = b_y 返回 b_x', () => {
    expect(filletXAtY(F, 0)).toBeCloseTo(1, 12)
    expect(filletXAtY(F, 1)).toBeCloseTo(0, 12)
  })

  it('中点：y=0.25 处返回贝塞尔 x=0.25（解析手工值）', () => {
    expect(filletXAtY(F, 0.25)).toBeCloseTo(0.25, 12)
  })

  it('圆角语义：曲线位于 ctrl=角点内侧（x+ + y+ ≤ a_x），与 filletCorner 拼接一致', () => {
    // 用真实 filletCorner 构建（车顶后缘构型：水平段→角点→下坡段）
    const f = filletCorner(2, 1.5, 1, 1.5, 0.6, 1.2, 0.09)
    const mid = filletXAtY(f, (f.a[1] + f.b[1]) / 2)
    // 同高度直线弦（切点连线）的 x：曲线在弦的车尾侧（更小 x = 轮廓内侧收）
    const chordX = f.a[0] + (f.b[0] - f.a[0]) * 0.5
    expect(mid).toBeLessThan(chordX)
  })

  it('y 超出 [b_y, a_y] 范围返回 null（无 [0,1] 内的根）', () => {
    expect(filletXAtY(F, -0.5)).toBeNull()
    expect(filletXAtY(F, 1.5)).toBeNull()
  })

  it('常值退化（全水平圆角）：y 命中曲线高度返回起点 x，未命中返回 null', () => {
    const flat = { a: [1, 0.5], ctrl: [0.5, 0.5], b: [0, 0.5] }
    expect(filletXAtY(flat, 0.5)).toBeCloseTo(1, 12)   // 整条曲线 y=0.5，取 t=0 → x=a_x
    expect(filletXAtY(flat, 0.4)).toBeNull()
    // 半线性：a_y=c_y=1.5，b_y=1.446（车顶后缘圆角实况，y(t) = a_y − (a_y−b_y)t²）
    // t=0.5 时 y = a_y + (b_y−a_y)×0.25，x = a_x·0.25 + c_x·0.5 + b_x·0.25
    const f = filletCorner(2, 1.5, 1, 1.5, 0.6, 1.2, 0.09)
    const x = filletXAtY(f, f.a[1] + (f.b[1] - f.a[1]) * 0.25)
    expect(x).toBeCloseTo(f.a[0] * 0.25 + f.ctrl[0] * 0.5 + f.b[0] * 0.25, 12)
  })
})

describe('bandGlassEndpoints bottomInset 底缘下退（COWL 角避让）', () => {
  it('bottomInset 使底缘沿斜线向顶缘方向退缩，顶缘不动', () => {
    const { a, b } = bandGlassEndpoints(0, 0, 0, 2, 0, 0, 0.5)
    expect(a).toEqual([0, 0.5])
    expect(b).toEqual([0, 2])
  })

  it('bottomInset 超过段长 90% 时钳位（与 topInset 同规则）', () => {
    const { a } = bandGlassEndpoints(0, 0, 0, 2, 0, 0, 10)
    expect(a[1]).toBeCloseTo(1.8, 10)
  })

  it('topInset 与 bottomInset 同时生效（两端各退，中段保留）', () => {
    const { a, b } = bandGlassEndpoints(0, 0, 0, 2, 0.5, 0, 0.5)
    expect(a).toEqual([0, 0.5])
    expect(b).toEqual([0, 1.5])
  })

  it('offset 与 bottomInset 叠加：先沿带退再沿法线抬', () => {
    const { a, normal } = bandGlassEndpoints(0, 0, 0, 2, 0, 0.031, 0.5)
    expect(normal[0]).toBeCloseTo(1, 12)
    expect(normal[1]).toBeCloseTo(0, 12)
    expect(a[0]).toBeCloseTo(0.031, 12)
    expect(a[1]).toBeCloseTo(0.5, 12)
  })
})

describe('六车型玻璃拓扑守卫（复刻 bodyShape 轮廓内点判定，与数值审计同判据）', () => {
  // 二次贝塞尔采样（filletCorner 的 ctrl = 角点，轮廓圆角实为二次贝塞尔）
  const quadTo = (pts, cx, cy, x, y, n = 12) => {
    const [x0, y0] = pts[pts.length - 1]
    for (let i = 1; i <= n; i++) {
      const t = i / n
      const omt = 1 - t
      pts.push([
        omt * omt * x0 + 2 * t * omt * cx + t * t * x,
        omt * omt * y0 + 2 * t * omt * cy + t * t * y
      ])
    }
  }

  // 复刻 Car3D.vue bodyShape 轮廓（与非 pickup / pickup 两分支逐行同参）
  const buildBodyOutline = (P) => {
    const {
      frontX, bodyBottomY, hoodLineY, cowlStartX, hoodEndX, beltLineY,
      windshieldTopX, roofTopY, rearWindowTopX, rearWindowBottomX,
      rearX, trunkLineY, pickup
    } = P
    const tailCtrlX = rearX + 0.02
    const tailCtrlY = trunkLineY - 0.016
    const tailEndY = trunkLineY - 0.056
    const pts = [[frontX, bodyBottomY]]
    if (pickup) {
      const f1 = filletCorner(hoodEndX, beltLineY, windshieldTopX, roofTopY, pickup.cabRearX, roofTopY, ROOF_FILLETS.aPillarTop)
      const f2 = filletCorner(windshieldTopX, roofTopY, pickup.cabRearX, roofTopY, pickup.cabWindowBottomX, pickup.bedWallY, ROOF_FILLETS.pickupCabTop)
      const f3 = filletCorner(pickup.cabRearX, roofTopY, pickup.cabWindowBottomX, pickup.bedWallY, rearX - 0.024, pickup.bedWallY, ROOF_FILLETS.pickupCabBottom)
      quadTo(pts, frontX + 0.09, hoodLineY - 0.04, frontX + 0.02, hoodLineY)
      pts.push([cowlStartX, hoodLineY], [hoodEndX, beltLineY])
      for (const f of [f1, f2, f3]) {
        pts.push([f.a[0], f.a[1]])
        quadTo(pts, f.ctrl[0], f.ctrl[1], f.b[0], f.b[1])
      }
      pts.push([rearX - 0.024, pickup.bedWallY])
      quadTo(pts, rearX, pickup.bedWallY - 0.008, rearX, pickup.bedWallY - 0.048)
      pts.push([rearX, bodyBottomY + 0.026])
      quadTo(pts, rearX, bodyBottomY, rearX - 0.036, bodyBottomY)
    } else {
      const f1 = filletCorner(hoodEndX, beltLineY, windshieldTopX, roofTopY, rearWindowTopX, roofTopY, ROOF_FILLETS.aPillarTop)
      const f2 = filletCorner(windshieldTopX, roofTopY, rearWindowTopX, roofTopY, rearWindowBottomX, beltLineY, ROOF_FILLETS.roofRear)
      const f3 = filletCorner(rearWindowTopX, roofTopY, rearWindowBottomX, beltLineY, tailCtrlX, tailCtrlY, ROOF_FILLETS.cPillarBottom)
      quadTo(pts, frontX + 0.09, hoodLineY - 0.04, frontX + 0.02, hoodLineY)
      pts.push([cowlStartX, hoodLineY], [hoodEndX, beltLineY])
      for (const f of [f1, f2, f3]) {
        pts.push([f.a[0], f.a[1]])
        quadTo(pts, f.ctrl[0], f.ctrl[1], f.b[0], f.b[1])
      }
      quadTo(pts, tailCtrlX, tailCtrlY, rearX, tailEndY)
      pts.push([rearX, bodyBottomY + 0.026])
      quadTo(pts, rearX, bodyBottomY, rearX - 0.036, bodyBottomY)
    }
    pts.push(pts[0])   // 闭合
    return pts
  }

  const pointInPoly = (x, y, poly) => {
    let inside = false
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const [xi, yi] = poly[i]
      const [xj, yj] = poly[j]
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside
    }
    return inside
  }

  const distToPolyEdge = (x, y, poly) => {
    let best = Infinity
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const [xj, yj] = poly[j]
      const dx = poly[i][0] - xj
      const dy = poly[i][1] - yj
      const L2 = dx * dx + dy * dy || 1e-12
      const t = Math.max(0, Math.min(1, ((x - xj) * dx + (y - yj) * dy) / L2))
      best = Math.min(best, Math.hypot(x - (xj + t * dx), y - (yj + t * dy)))
    }
    return best
  }

  // 内点判据：严格内点，或距边界 ≤ 2mm（贴边浮点容差）
  const insideOrOnEdge = (x, y, poly) => pointInPoly(x, y, poly) || distToPolyEdge(x, y, poly) <= 0.002

  it.each(ALL_TYPES)('%s：DLO 四角与四边采样点均落于车身轮廓内', (type) => {
    const P = deriveCarProfile(carTypeParams[type], type)
    const g = deriveCabinGlass(P, { carType: type })
    const poly = buildBodyOutline(P)
    const [p0, p1, p2, p3] = g.dlo
    const corners = [[p0, '底前'], [p1, '顶前'], [p2, '顶后'], [p3, '底后']]
    for (const [pt, name] of corners) {
      expect(insideOrOnEdge(pt[0], pt[1], poly), `${type} DLO ${name}角 (${pt}) 越出轮廓`).toBe(true)
    }
    // 四边中点采样（t=0.15/0.5/0.85，覆盖审计曾抓到的边缘 POKE 区）
    const edges = [[p0, p1], [p1, p2], [p2, p3], [p3, p0]]
    for (const [pa, pb] of edges) {
      for (const t of [0.15, 0.5, 0.85]) {
        const x = pa[0] + (pb[0] - pa[0]) * t
        const y = pa[1] + (pb[1] - pa[1]) * t
        expect(insideOrOnEdge(x, y, poly), `${type} DLO 边 t=${t} 点 (${x.toFixed(3)},${y.toFixed(3)}) 越出轮廓`).toBe(true)
      }
    }
  })

  it.each(ALL_TYPES)('%s：风挡带两端点贴壁（距轮廓 = bevel 外扩量 +1.5mm 容差，不戳出不内陷）', (type) => {
    const P = deriveCarProfile(carTypeParams[type], type)
    const g = deriveCabinGlass(P, { carType: type })
    const poly = buildBodyOutline(P)
    const ws = g.windshield
    const { a, b } = bandGlassEndpoints(ws.x1, ws.y1, ws.x2, ws.y2, ws.topInset, 0.031, ws.bottomInset)
    for (const [pt, name] of [[a, '底端'], [b, '顶端']]) {
      const d = distToPolyEdge(pt[0], pt[1], poly)
      expect(d, `${type} 风挡${name}距轮廓 ${d.toFixed(4)}m 超出贴壁带`).toBeLessThanOrEqual(0.0315)
      expect(d, `${type} 风挡${name}陷入车身内部 ${d.toFixed(4)}m`).toBeGreaterThanOrEqual(0.025)
    }
    // 非皮卡后窗带同样贴壁
    if (g.rearWindow) {
      const rw = g.rearWindow
      const rb = bandGlassEndpoints(rw.x1, rw.y1, rw.x2, rw.y2, rw.topInset, 0.031)
      for (const [pt, name] of [[rb.a, '底端'], [rb.b, '顶端']]) {
        const d = distToPolyEdge(pt[0], pt[1], poly)
        expect(d, `${type} 后窗${name}距轮廓 ${d.toFixed(4)}m 超出贴壁带`).toBeLessThanOrEqual(0.0315)
      }
    }
  })

  it.each(ALL_TYPES)('%s：B 柱顶端搭接 DLO 顶边、底端高于 DLO 底边（无悬浮无越界）', (type) => {
    const P = deriveCarProfile(carTypeParams[type], type)
    const g = deriveCabinGlass(P, { carType: type })
    expect(g.pillar.topY).toBeGreaterThanOrEqual(g.dlo[1][1])   // 顶端越过顶边 2mm 搭接
    expect(g.pillar.topY).toBeLessThan(P.roofTopY)              // 不越过车顶线
    expect(g.pillar.botY).toBeGreaterThan(g.dlo[0][1])          // 底端在 DLO 底边之上
    expect(g.pillar.x).toBeLessThan(P.windshieldTopX)           // 55% 分段在 DLO 跨度内
    expect(g.pillar.x).toBeGreaterThan(g.dloTopRear)
  })
})
