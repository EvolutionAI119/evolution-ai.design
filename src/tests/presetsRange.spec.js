import { describe, it, expect } from 'vitest'
import schema from '../../backend/config/automotive_parameters.json'
import { carTypeParams, defaultCarParams, brands } from '../config/carPresets.js'
import { toBackendKey, resolveRange } from '../config/paramMapping.js'

const groups = schema.automotive_parameters
const index = {}
for (const items of Object.values(groups)) {
  for (const [key, meta] of Object.entries(items)) index[key] = meta
}

function outOfRange (name, params) {
  const bad = []
  for (const [key, value] of Object.entries(params)) {
    if (typeof value !== 'number') continue
    const meta = index[toBackendKey(key)]
    if (!meta) continue
    const { min_value: lo, max_value: hi } = meta
    if (typeof lo === 'number' && typeof hi === 'number' && (value < lo || value > hi)) {
      bad.push(`${name}.${key}=${value} ∉ [${lo}, ${hi}]`)
    }
  }
  return bad
}

describe('前端品牌/车型默认值必须落在后端物理区间内', () => {
  it('defaultCarParams', () => {
    expect(outOfRange('default', defaultCarParams)).toEqual([])
  })

  it.each(Object.entries(carTypeParams))('carTypeParams.%s', (type, params) => {
    expect(outOfRange(type, params)).toEqual([])
  })

  it.each(brands.flatMap((b) => b.models.map((m) => [m.key, { ...defaultCarParams, ...m.params }])))(
    'brand.%s',
    (key, params) => {
      expect(outOfRange(key, params)).toEqual([])
    }
  )

  it('resolveRange 通过映射表取到后端区间（roof_height → roof_length）', () => {
    const flat = {}
    for (const [key, meta] of Object.entries(index)) {
      flat[key] = { min: meta.min_value, max: meta.max_value }
    }
    expect(resolveRange(flat, 'roof_height')).toEqual({ min: 1200, max: 2000 })
    expect(resolveRange(flat, 'roof_height_thickness_missing')).toBeNull()
  })
})
