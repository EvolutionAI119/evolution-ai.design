import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDesignerStore } from '../stores/designer.js'
import { brands, carTypes } from '../config/carPresets'

// CAR TYPE ↔ 品牌认证车型双向实时连动
describe('designer store：CAR TYPE 与品牌模型双向连动', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('数据完整性：19 款品牌车型全部带 car_type 标注且值合法', () => {
    const keys = new Set(carTypes.map(ct => ct.key))
    const total = brands.reduce((n, b) => n + b.models.length, 0)
    expect(total).toBe(19)
    for (const b of brands) {
      for (const m of b.models) {
        expect(m.car_type, `${b.key}/${m.key}`).toBeTruthy()
        expect(keys.has(m.car_type), `${b.key}/${m.key} → ${m.car_type}`).toBe(true)
      }
    }
  })

  it('→ 连动：选 Sport 自动跳到含该类型的品牌并选中代表车型', () => {
    const d = useDesignerStore()
    d.setCarType('sport')
    expect(d.carType).toBe('sport')
    // 初始品牌 rolls-royce 无 sport → 跳到第一个含 sport 的品牌
    const target = brands.find(b => b.models.some(m => m.car_type === 'sport'))
    expect(d.brand).toBe(target.key)
    expect(d.selectedModel).toBe(target.models.find(m => m.car_type === 'sport').key)
    // 参数来自认证车型而非通用模板
    const model = target.models.find(m => m.car_type === 'sport')
    expect(d.params.overall_length).toBe(model.params.overall_length)
  })

  it('→ 连动：当前品牌含该类型时留在当前品牌（品牌优先）', () => {
    const d = useDesignerStore()
    d.setBrand('porsche')
    d.setCarType('suv')
    expect(d.brand).toBe('porsche')
    expect(d.selectedModel).toBe('cayenne')
  })

  it('→ 兜底：mpv/pickup 无认证车型时回退通用类型参数', () => {
    const d = useDesignerStore()
    d.setCarType('mpv')
    expect(d.selectedModel).toBeNull()
    // 参数回落到通用 mpv 模板（不炸、有合理值）
    expect(d.params.overall_length).toBeGreaterThan(0)
    expect(d.params.overall_height).toBeGreaterThan(0)
    d.setCarType('pickup')
    expect(d.selectedModel).toBeNull()
  })

  it('← 连动：选 Ferrari Roma 时 CAR TYPE 同步切到 Coupe', () => {
    const d = useDesignerStore()
    d.setBrand('ferrari')
    const roma = brands.find(b => b.key === 'ferrari').models.find(m => m.key === 'roma')
    d.selectModel(roma)
    expect(d.selectedModel).toBe('roma')
    expect(d.carType).toBe('coupe')
    expect(d.params.overall_length).toBe(roma.params.overall_length)
  })

  it('← 连动：从 Coupe 车型切到 Cayenne 时类型跟随到 SUV', () => {
    const d = useDesignerStore()
    d.setBrand('ferrari')
    d.selectModel(brands.find(b => b.key === 'ferrari').models.find(m => m.key === 'roma'))
    expect(d.carType).toBe('coupe')
    d.setBrand('porsche')
    d.selectModel(brands.find(b => b.key === 'porsche').models.find(m => m.key === 'cayenne'))
    expect(d.carType).toBe('suv')
  })

  it('往返闭环：Sport → 选 Ferrari SF90 → 类型仍为 Sport，品牌留在 Ferrari', () => {
    const d = useDesignerStore()
    d.setCarType('sport')
    d.setBrand('ferrari')
    d.selectModel(brands.find(b => b.key === 'ferrari').models.find(m => m.key === 'sf90'))
    expect(d.carType).toBe('sport')
    expect(d.brand).toBe('ferrari')
    expect(d.selectedModel).toBe('sf90')
  })

  it('exportToProject 契约：连动后导出的 carType 与 brand 一致', () => {
    const d = useDesignerStore()
    d.setCarType('coupe')
    const exported = d.exportToProject()
    expect(exported.carType).toBe('coupe')
    expect(exported.brand).toBe(d.brand)
    expect(exported.params.overall_length).toBe(d.params.overall_length)
  })
})
