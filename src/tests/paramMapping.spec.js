import { describe, it, expect } from 'vitest'
import {
  FRONTEND_TO_BACKEND,
  toBackendKey,
  toBackendParams,
  toBackendGroups
} from '../config/paramMapping.js'

describe('paramMapping：前端 → 后端参数语义映射', () => {
  it('roof_height 必须映射到 roof_length（车顶跨度），绝不落到板厚 roof_height', () => {
    expect(toBackendKey('roof_height')).toBe('roof_length')
    expect(FRONTEND_TO_BACKEND.roof_height).toBe('roof_length')
    const flat = toBackendParams({ roof_height: 1400 })
    expect(flat.roof_length).toBe(1400)
    expect(flat.roof_height).toBeUndefined()
  })

  it('rear_slant_angle 保持独立，不得映射到 c_pillar_angle', () => {
    expect(toBackendKey('rear_slant_angle')).toBe('rear_slant_angle')
    expect(FRONTEND_TO_BACKEND.rear_slant_angle).toBeUndefined()
    expect(toBackendParams({ rear_slant_angle: 18 }).rear_slant_angle).toBe(18)
    expect(toBackendParams({ rear_slant_angle: 18 }).c_pillar_angle).toBeUndefined()
  })

  it('纯命名差异字段映射：wheel_base / front_overhang / rear_overhang', () => {
    const flat = toBackendParams({
      wheel_base: 2890, front_overhang: 950, rear_overhang: 1110
    })
    expect(flat.wheelbase).toBe(2890)
    expect(flat.overhang_front).toBe(950)
    expect(flat.overhang_rear).toBe(1110)
    expect(flat.wheel_base).toBeUndefined()
    expect(flat.front_overhang).toBeUndefined()
    expect(flat.rear_overhang).toBeUndefined()
  })

  it('分组载荷使用后端英文稳定键与规范参数名', () => {
    const groups = toBackendGroups({
      roof_height: 1400,
      rear_slant_angle: 18,
      wheel_base: 2890,
      front_overhang: 950
    })
    expect(groups.overall_dimensions.wheelbase).toBe(2890)
    expect(groups.body_components.roof_length).toBe(1400)
    expect(groups.proportions.overhang_front).toBe(950)
    expect(groups.styling_angles.rear_slant_angle).toBe(18)
    expect(groups.body_components.roof_height).toBeUndefined()
    expect(groups.styling_angles.c_pillar_angle).toBeUndefined()
  })

  it('undefined/null 不进入载荷', () => {
    expect(toBackendParams({ roof_height: undefined, wheel_base: null })).toEqual({})
    expect(toBackendGroups({ roof_height: undefined, rear_slant_angle: null })).toEqual({})
  })
})
