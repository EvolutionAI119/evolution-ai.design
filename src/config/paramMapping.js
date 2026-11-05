// 前端参数（品牌预设/滑杆）→ 后端 carTypeParams 语义的显式映射表。
// 唯一真源：后端 backend/config/automotive_parameters.json；本文件只负责把前端
// 字段名翻译成后端规范参数名，不做区间校验（区间由后端契约与 /car/parameters/schema 提供）。
//
// 关键语义差异（不得省成“同名直通”）：
//   roof_height：前端=车顶纵向跨度（mm），后端 roof_length=车顶跨度 [1200,2000]，
//                而后端 roof_height=车顶板厚 [30,100]，两者同名不同义，必须映射到 roof_length；
//   rear_slant_angle：后端已有独立同名参数，保持独立，禁止再映射到 c_pillar_angle；
//   wheel_base / front_overhang / rear_overhang 仅命名差异。
export const FRONTEND_TO_BACKEND = Object.freeze({
  wheel_base: 'wheelbase',
  front_overhang: 'overhang_front',
  rear_overhang: 'overhang_rear',
  roof_height: 'roof_length'
})

export const BACKEND_TO_FRONTEND = Object.freeze(
  Object.fromEntries(Object.entries(FRONTEND_TO_BACKEND).map(([f, b]) => [b, f]))
)

// 前端字段所属的后端参数分组（用于 /import-export/import 的分组载荷）
export const FRONTEND_GROUP = Object.freeze({
  overall_length: 'overall_dimensions',
  overall_width: 'overall_dimensions',
  overall_height: 'overall_dimensions',
  wheel_base: 'overall_dimensions',
  track_width: 'overall_dimensions',
  ground_clearance: 'overall_dimensions',
  hood_length: 'body_components',
  roof_height: 'body_components',
  wheel_diameter: 'body_components',
  wheel_arch_flatten: 'body_components',
  b_pillar_width_ratio: 'body_components',
  door_open_angle: 'body_components',
  door_seam_width: 'body_components',
  handle_drop_ratio: 'body_components',
  handle_x_ratio: 'body_components',
  glass_barrel_radius: 'body_components',
  front_overhang: 'proportions',
  rear_overhang: 'proportions',
  windshield_angle: 'styling_angles',
  rear_window_angle: 'styling_angles',
  rear_slant_angle: 'styling_angles',
  approach_angle: 'styling_angles',
  departure_angle: 'styling_angles',
  side_glass_angle: 'styling_angles',
  glass_barrel_angle: 'styling_angles',
  enable_vtol: 'flight_parameters',
  hover_altitude: 'flight_parameters',
  exotic_drive_ratio: 'flight_parameters',
  dark_matter_ratio: 'flight_parameters',
  lift_fan_count: 'flight_parameters'
})

/** 前端字段名 → 后端规范参数名 */
export function toBackendKey (frontendKey) {
  return FRONTEND_TO_BACKEND[frontendKey] || frontendKey
}

/** 前端扁平参数 → 后端扁平规范参数（只做重命名，不增删业务字段） */
export function toBackendParams (frontendParams = {}) {
  const out = {}
  for (const [key, value] of Object.entries(frontendParams)) {
    if (value === undefined || value === null) continue
    out[toBackendKey(key)] = value
  }
  return out
}

/** 前端扁平参数 → 后端分组规范参数（未登记分组的字段忽略） */
export function toBackendGroups (frontendParams = {}) {
  const groups = {}
  for (const [key, value] of Object.entries(frontendParams)) {
    const group = FRONTEND_GROUP[key]
    if (!group || value === undefined || value === null) continue
    if (!groups[group]) groups[group] = {}
    groups[group][toBackendKey(key)] = value
  }
  return groups
}

/** 从后端 schema.flat 取某前端字段的 [min,max]；缺失时返回 null（调用方用本地回退） */
export function resolveRange (schemaFlat, frontendKey) {
  const meta = schemaFlat?.[toBackendKey(frontendKey)]
  if (!meta || typeof meta.min !== 'number' || typeof meta.max !== 'number') return null
  return { min: meta.min, max: meta.max }
}
