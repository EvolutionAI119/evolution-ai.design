// name 字段为 i18n 键（designer 域），渲染时通过 t('designer.' + name) 翻译
import { SIDE_GLASS_TILT, SIDE_GLASS_BARREL } from '../utils/carGlass.js'
import { FLIGHT_PRESETS } from '../utils/flightPhysics.js'

// 玻璃三参数（UI 可调）：倾角取 carGlass 车型表，保证 UI 默认与 3D 几何回退值不漂移
const glassParams = (type) => ({
  side_glass_angle: SIDE_GLASS_TILT[type],
  glass_barrel_angle: SIDE_GLASS_BARREL[type].angle,
  glass_barrel_radius: SIDE_GLASS_BARREL[type].radius
})

// 飞行参数（UI 可调，字段名与后端 飞行参数 组同名 → resolve_overrides 直通）：
// enable_vtol 为能力开关（默认开启=具备飞行功能），悬浮高度/暗能量/暗物质/风扇数
// 取 flightPhysics 车型表，保证 UI 默认与 3D 飞行动画回退值不漂移
const flightParams = (type) => ({
  enable_vtol: true,
  hover_altitude: FLIGHT_PRESETS[type].hoverAltitude,
  exotic_drive_ratio: FLIGHT_PRESETS[type].exoticRatio,
  dark_matter_ratio: FLIGHT_PRESETS[type].darkMatterRatio,
  lift_fan_count: FLIGHT_PRESETS[type].liftFans
})

// 轮拱扁平度（UI 可调，直通后端 车身部件.wheel_arch_flatten）：
// 0=圆拱（轿车/轿跑/跑车），>0 横轴放大成扁拱/方拱（SUV/皮卡越野风格）
const archFlatten = (type) => ({
  wheel_arch_flatten: { sedan: 0, suv: 0.25, coupe: 0, sport: 0, mpv: 0.05, pickup: 0.35 }[type] ?? 0.1
})

// 车门/B柱/把手布置（UI 可调，前后端同步）：默认值使 B柱宽≈22mm、把手落原硬编码位附近（零视觉回归）
const doorParams = () => ({
  b_pillar_width_ratio: 0.047,
  door_open_angle: 70,
  door_seam_width: 8,
  handle_drop_ratio: 0.12,
  handle_x_ratio: 0.45
})

export const carTypes = [
  { key: 'sedan', name: 'carSedan', desc: 'Classic sedan' },
  { key: 'suv', name: 'carSuv', desc: 'Sport utility' },
  { key: 'coupe', name: 'carCoupe', desc: 'Two-door' },
  { key: 'sport', name: 'carSport', desc: 'High performance' },
  { key: 'mpv', name: 'carMpv', desc: 'Multi-purpose' },
  { key: 'pickup', name: 'carPickup', desc: 'Pickup truck' }
]

export const defaultCarParams = {
  overall_length: 5770,
  overall_width: 2010,
  overall_height: 1648,
  wheel_base: 3552,
  track_width: 1680,
  ground_clearance: 150,
  hood_length: 1200,
  roof_height: 1000,
  wheel_diameter: 750,
  ...archFlatten('sedan'),
  windshield_angle: 30,
  rear_window_angle: 25,
  rear_slant_angle: 15,
  ...glassParams('sedan'),
  ...flightParams('sedan'),
  ...doorParams(),
  front_overhang: 1100,
  rear_overhang: 1118
}

export const carTypeParams = {
  sedan: {
    overall_length: 4950, overall_width: 1880, overall_height: 1460,
    wheel_base: 2890, track_width: 1600, ground_clearance: 140,
    hood_length: 1050, roof_height: 550, wheel_diameter: 680,
    windshield_angle: 35, rear_window_angle: 28, rear_slant_angle: 18,
    ...glassParams('sedan'),
    ...flightParams('sedan'),
    ...archFlatten('sedan'),
    front_overhang: 950, rear_overhang: 1110
  },
  suv: {
    overall_length: 5050, overall_width: 1980, overall_height: 1780,
    wheel_base: 2950, track_width: 1680, ground_clearance: 210,
    hood_length: 1150, roof_height: 850, wheel_diameter: 760,
    windshield_angle: 28, rear_window_angle: 22, rear_slant_angle: 12,
    ...glassParams('suv'),
    ...flightParams('suv'),
    ...archFlatten('suv'),
    front_overhang: 980, rear_overhang: 1120
  },
  coupe: {
    overall_length: 4800, overall_width: 1890, overall_height: 1380,
    wheel_base: 2780, track_width: 1620, ground_clearance: 120,
    hood_length: 1350, roof_height: 420, wheel_diameter: 700,
    windshield_angle: 40, rear_window_angle: 35, rear_slant_angle: 40,
    ...glassParams('coupe'),
    ...flightParams('coupe'),
    ...archFlatten('coupe'),
    front_overhang: 1020, rear_overhang: 1000
  },
  sport: {
    overall_length: 4600, overall_width: 1980, overall_height: 1250,
    wheel_base: 2700, track_width: 1700, ground_clearance: 100,
    hood_length: 1500, roof_height: 350, wheel_diameter: 720,
    windshield_angle: 45, rear_window_angle: 42, rear_slant_angle: 50,
    ...glassParams('sport'),
    ...flightParams('sport'),
    ...archFlatten('sport'),
    front_overhang: 950, rear_overhang: 950
  },
  mpv: {
    overall_length: 5200, overall_width: 1920, overall_height: 1830,
    wheel_base: 3100, track_width: 1640, ground_clearance: 160,
    hood_length: 850, roof_height: 950, wheel_diameter: 700,
    windshield_angle: 25, rear_window_angle: 15, rear_slant_angle: 8,
    ...glassParams('mpv'),
    ...flightParams('mpv'),
    ...archFlatten('mpv'),
    front_overhang: 880, rear_overhang: 1220
  },
  pickup: {
    overall_length: 5600, overall_width: 1980, overall_height: 1880,
    wheel_base: 3450, track_width: 1680, ground_clearance: 230,
    hood_length: 1350, roof_height: 750, wheel_diameter: 780,
    windshield_angle: 28, rear_window_angle: 20, rear_slant_angle: 15,
    ...glassParams('pickup'),
    ...flightParams('pickup'),
    ...archFlatten('pickup'),
    front_overhang: 1050, rear_overhang: 1100
  }
}

// 按车型注入可调参数默认值：接近/离去角 = atan(离地间隙/对应悬长)（与 deriveCarProfile 缺省逐位一致，零回归）
// + 车门/B柱/把手布置默认（doorParams）。defaultCarParams 亦补角度，保证滑块有初值。
for (const t of Object.keys(carTypeParams)) {
  const c = carTypeParams[t]
  const deg = (a, b) => (Math.atan2(a / 1000, b / 1000) * 180) / Math.PI
  c.approach_angle = deg(c.ground_clearance, c.front_overhang)
  c.departure_angle = deg(c.ground_clearance, c.rear_overhang)
  Object.assign(c, doorParams())
}
defaultCarParams.approach_angle = (Math.atan2(defaultCarParams.ground_clearance / 1000, defaultCarParams.front_overhang / 1000) * 180) / Math.PI
defaultCarParams.departure_angle = (Math.atan2(defaultCarParams.ground_clearance / 1000, defaultCarParams.rear_overhang / 1000) * 180) / Math.PI

// name 字段为 i18n 键（designer 域），渲染时通过 t('designer.' + name) 翻译
export const bodyColors = [
  { name: 'colorObsidianBlack', value: '#0a0a0f' },
  { name: 'colorCarbonGray', value: '#374151' },
  { name: 'colorSilverMetallic', value: '#9ca3af' },
  { name: 'colorPearlWhite', value: '#f3f4f6' },
  { name: 'colorCreamBeige', value: '#d4c5a9' },
  { name: 'colorChampagneGold', value: '#d4af37' },
  { name: 'colorRacingRed', value: '#dc2626' },
  { name: 'colorBurgundy', value: '#7f1d1d' },
  { name: 'colorSunsetOrange', value: '#ea580c' },
  { name: 'colorCanaryYellow', value: '#facc15' },
  { name: 'colorBritishGreen', value: '#166534' },
  { name: 'colorMintGreen', value: '#4ade80' },
  { name: 'colorOceanBlue', value: '#0369a1' },
  { name: 'colorRoyalBlue', value: '#1e40af' },
  { name: 'colorAmethystPurple', value: '#6b21a8' }
]

const IMG = 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image'
const ep = encodeURIComponent

const mk = (p, s) => IMG + '?prompt=' + ep(p) + '&image_size=' + s

export const imageLoaderConfig = {
  maxRetries: 3,
  baseRetryIntervalMs: 3000,
  retryIntervalMultiplier: 1,
  placeholderSizeThresholdBytes: 5000,
  preloadConcurrency: 3
}

// 静态真实照片路径：/brands/{brand}/{model}.jpg
// 19 款车型的真实照片（从 Bing 图片搜索下载），随项目打包部署，永远可用。
// 作为首选图片源，无需网络请求，彻底解决"照片丢失"问题。
export const getStaticBrandImagePath = (brandKey, modelKey) => {
  if (!brandKey || !modelKey) return null
  return `/brands/${encodeURIComponent(brandKey)}/${encodeURIComponent(modelKey)}.jpg`
}

const brandsRaw = [
  {
    key: 'rolls-royce',
    name: 'Rolls-Royce',
    color: '#4ade80',
    models: [
      { key: 'phantom', name: 'Phantom', params: { overall_length: 5770, overall_width: 2018, overall_height: 1648, wheel_base: 3552, track_width: 1680, ground_clearance: 150, hood_length: 1300, roof_height: 750, wheel_diameter: 750, windshield_angle: 28, rear_window_angle: 22, rear_slant_angle: 12, front_overhang: 1050, rear_overhang: 1168 }, image: mk('Rolls-Royce Phantom luxury sedan side view black', 'landscape_16_9') },
      { key: 'ghost', name: 'Ghost', params: { overall_length: 5546, overall_width: 1948, overall_height: 1550, wheel_base: 3295, track_width: 1640, ground_clearance: 145, hood_length: 1200, roof_height: 650, wheel_diameter: 720, windshield_angle: 30, rear_window_angle: 24, rear_slant_angle: 14, front_overhang: 1020, rear_overhang: 1231 }, image: mk('Rolls-Royce Ghost luxury sedan side view silver', 'landscape_16_9') },
      { key: 'cullinan', name: 'Cullinan', params: { overall_length: 5341, overall_width: 2000, overall_height: 1835, wheel_base: 3295, track_width: 1680, ground_clearance: 215, hood_length: 1200, roof_height: 900, wheel_diameter: 780, windshield_angle: 26, rear_window_angle: 20, rear_slant_angle: 10, front_overhang: 970, rear_overhang: 1076 }, image: mk('Rolls-Royce Cullinan luxury SUV side view white', 'landscape_16_9') },
      { key: 'wraith', name: 'Wraith', params: { overall_length: 5285, overall_width: 1947, overall_height: 1507, wheel_base: 3112, track_width: 1630, ground_clearance: 135, hood_length: 1400, roof_height: 550, wheel_diameter: 710, windshield_angle: 38, rear_window_angle: 32, rear_slant_angle: 35, front_overhang: 1090, rear_overhang: 1083 }, image: mk('Rolls-Royce Wraith luxury coupe side view blue', 'landscape_16_9') }
    ]
  },
  {
    key: 'bentley',
    name: 'Bentley',
    color: '#3b82f6',
    models: [
      { key: 'continental-gt', name: 'Continental GT', params: { overall_length: 4850, overall_width: 1954, overall_height: 1405, wheel_base: 2851, track_width: 1650, ground_clearance: 125, hood_length: 1450, roof_height: 480, wheel_diameter: 730, windshield_angle: 38, rear_window_angle: 33, rear_slant_angle: 38, front_overhang: 1000, rear_overhang: 999 }, image: mk('Bentley Continental GT coupe side view green', 'landscape_16_9') },
      { key: 'continental-gtc', name: 'Continental GTC', params: { overall_length: 4850, overall_width: 1954, overall_height: 1405, wheel_base: 2851, track_width: 1650, ground_clearance: 125, hood_length: 1450, roof_height: 480, wheel_diameter: 730, windshield_angle: 38, rear_window_angle: 33, rear_slant_angle: 38, front_overhang: 1000, rear_overhang: 999 }, image: mk('Bentley Continental GTC convertible side view blue', 'landscape_16_9') },
      { key: 'flying-spur', name: 'Flying Spur', params: { overall_length: 5316, overall_width: 1978, overall_height: 1484, wheel_base: 3194, track_width: 1660, ground_clearance: 140, hood_length: 1300, roof_height: 600, wheel_diameter: 730, windshield_angle: 32, rear_window_angle: 26, rear_slant_angle: 16, front_overhang: 1060, rear_overhang: 1062 }, image: mk('Bentley Flying Spur sedan side view black', 'landscape_16_9') },
      { key: 'bentayga', name: 'Bentayga', params: { overall_length: 5125, overall_width: 1998, overall_height: 1742, wheel_base: 2995, track_width: 1680, ground_clearance: 200, hood_length: 1200, roof_height: 850, wheel_diameter: 760, windshield_angle: 28, rear_window_angle: 22, rear_slant_angle: 12, front_overhang: 1030, rear_overhang: 1100 }, image: mk('Bentley Bentayga luxury SUV side view white', 'landscape_16_9') }
    ]
  },
  {
    key: 'bugatti',
    name: 'Bugatti',
    color: '#f59e0b',
    models: [
      { key: 'chiron', name: 'Chiron', params: { overall_length: 4544, overall_width: 2038, overall_height: 1212, wheel_base: 2711, track_width: 1720, ground_clearance: 95, hood_length: 1550, roof_height: 320, wheel_diameter: 740, windshield_angle: 48, rear_window_angle: 42, rear_slant_angle: 52, front_overhang: 920, rear_overhang: 913 }, image: mk('Bugatti Chiron hypercar side view blue', 'landscape_16_9') },
      { key: 'veyron', name: 'Veyron', params: { overall_length: 4462, overall_width: 1998, overall_height: 1159, wheel_base: 2710, track_width: 1710, ground_clearance: 90, hood_length: 1500, roof_height: 300, wheel_diameter: 720, windshield_angle: 46, rear_window_angle: 40, rear_slant_angle: 50, front_overhang: 900, rear_overhang: 852 }, image: mk('Bugatti Veyron supercar side view black', 'landscape_16_9') },
      { key: 'divo', name: 'Divo', params: { overall_length: 4579, overall_width: 2038, overall_height: 1212, wheel_base: 2711, track_width: 1730, ground_clearance: 90, hood_length: 1550, roof_height: 310, wheel_diameter: 740, windshield_angle: 50, rear_window_angle: 44, rear_slant_angle: 55, front_overhang: 930, rear_overhang: 938 }, image: mk('Bugatti Divo hypercar side view blue carbon', 'landscape_16_9') }
    ]
  },
  {
    key: 'porsche',
    name: 'Porsche',
    color: '#ef4444',
    models: [
      { key: '911', name: '911 Carrera', params: { overall_length: 4519, overall_width: 1852, overall_height: 1299, wheel_base: 2450, track_width: 1580, ground_clearance: 105, hood_length: 1100, roof_height: 400, wheel_diameter: 680, windshield_angle: 42, rear_window_angle: 35, rear_slant_angle: 45, front_overhang: 920, rear_overhang: 1149 }, image: mk('Porsche 911 sports car side view red', 'landscape_16_9') },
      { key: 'taycan', name: 'Taycan', params: { overall_length: 4963, overall_width: 1966, overall_height: 1381, wheel_base: 2900, track_width: 1660, ground_clearance: 125, hood_length: 1200, roof_height: 500, wheel_diameter: 710, windshield_angle: 38, rear_window_angle: 32, rear_slant_angle: 35, front_overhang: 980, rear_overhang: 1083 }, image: mk('Porsche Taycan electric sedan side view white', 'landscape_16_9') },
      { key: 'panamera', name: 'Panamera', params: { overall_length: 5049, overall_width: 1937, overall_height: 1423, wheel_base: 2950, track_width: 1650, ground_clearance: 130, hood_length: 1300, roof_height: 550, wheel_diameter: 710, windshield_angle: 35, rear_window_angle: 28, rear_slant_angle: 30, front_overhang: 1020, rear_overhang: 1079 }, image: mk('Porsche Panamera sedan side view gray', 'landscape_16_9') },
      { key: 'cayenne', name: 'Cayenne', params: { overall_length: 4926, overall_width: 1983, overall_height: 1673, wheel_base: 2895, track_width: 1680, ground_clearance: 190, hood_length: 1200, roof_height: 780, wheel_diameter: 760, windshield_angle: 28, rear_window_angle: 22, rear_slant_angle: 15, front_overhang: 950, rear_overhang: 1081 }, image: mk('Porsche Cayenne SUV side view white', 'landscape_16_9') },
      { key: 'macan', name: 'Macan', params: { overall_length: 4686, overall_width: 1923, overall_height: 1624, wheel_base: 2807, track_width: 1650, ground_clearance: 180, hood_length: 1150, roof_height: 720, wheel_diameter: 730, windshield_angle: 30, rear_window_angle: 24, rear_slant_angle: 18, front_overhang: 900, rear_overhang: 979 }, image: mk('Porsche Macan compact SUV side view black', 'landscape_16_9') }
    ]
  },
  {
    key: 'ferrari',
    name: 'Ferrari',
    color: '#dc2626',
    models: [
      { key: 'sf90', name: 'SF90 Stradale', params: { overall_length: 4710, overall_width: 1972, overall_height: 1186, wheel_base: 2650, track_width: 1700, ground_clearance: 90, hood_length: 1450, roof_height: 300, wheel_diameter: 730, windshield_angle: 50, rear_window_angle: 45, rear_slant_angle: 55, front_overhang: 980, rear_overhang: 1080 }, image: mk('Ferrari SF90 supercar side view red', 'landscape_16_9') },
      { key: 'f8-tributo', name: 'F8 Tributo', params: { overall_length: 4611, overall_width: 1979, overall_height: 1206, wheel_base: 2650, track_width: 1700, ground_clearance: 95, hood_length: 1400, roof_height: 320, wheel_diameter: 720, windshield_angle: 48, rear_window_angle: 42, rear_slant_angle: 52, front_overhang: 950, rear_overhang: 1011 }, image: mk('Ferrari F8 Tributo sports car side view red', 'landscape_16_9') },
      { key: 'roma', name: 'Roma', params: { overall_length: 4656, overall_width: 1974, overall_height: 1301, wheel_base: 2670, track_width: 1680, ground_clearance: 105, hood_length: 1350, roof_height: 420, wheel_diameter: 710, windshield_angle: 40, rear_window_angle: 34, rear_slant_angle: 40, front_overhang: 970, rear_overhang: 1016 }, image: mk('Ferrari Roma GT coupe side view silver', 'landscape_16_9') }
    ]
  }
]

// 车型 → CAR TYPE 映射：品牌认证车型与左侧车型宫格双向连动的数据源。
// 依据各车型官方定位与几何特征归类（GT 轿跑如 Roma/Wraith 归 coupe），
// mpv/pickup 品牌库暂无认证车型，选这两个类型时走通用参数兜底。
const MODEL_CAR_TYPE = {
  // Rolls-Royce
  'phantom': 'sedan', 'ghost': 'sedan', 'cullinan': 'suv', 'wraith': 'coupe',
  // Bentley
  'continental-gt': 'coupe', 'continental-gtc': 'coupe',
  'flying-spur': 'sedan', 'bentayga': 'suv',
  // Bugatti
  'chiron': 'sport', 'veyron': 'sport', 'divo': 'sport',
  // Porsche
  '911': 'sport', 'taycan': 'sedan', 'panamera': 'sedan',
  'cayenne': 'suv', 'macan': 'suv',
  // Ferrari
  'sf90': 'sport', 'f8-tributo': 'sport', 'roma': 'coupe',
}

// 为每个 model 预置稳定的本地静态照片路径（/brands/{brand}/{model}.jpg）
// 同时保留 image（远程 AI 生成图）作为可选。
// 说明：localImage = 静态 JPG 照片路径，由 Vite public 目录直接提供，
//       不受端口变更、HMR、网络抖动影响，彻底解决"照片丢失"老问题。
// 同时注入 car_type 连动标注（缺失时置 null，视为不参与连动）。
brandsRaw.forEach(brand => {
  brand.models.forEach(model => {
    model.localImage = getStaticBrandImagePath(brand.key, model.key)
    model.car_type = MODEL_CAR_TYPE[model.key] || null
    // 玻璃三参数按官方定位 car_type 从车型表补齐（模型自带显式玻璃参数时以模型为准），
    // 保证 setCarType/selectModel 双向连动应用 model.params 时玻璃滑块随车型联动
    if (model.car_type && glassParams(model.car_type)) {
      // 飞行参数同步按 car_type 注入（显式模型参数优先），保证车型切换时
      // 飞行滑块与 3D 飞行动画随官方定位联动（与玻璃三参数同模式）
      model.params = { ...glassParams(model.car_type), ...flightParams(model.car_type), ...model.params }
    }
  })
})

export const brands = brandsRaw

export default { carTypes, defaultCarParams, carTypeParams, brands, bodyColors, getStaticBrandImagePath, imageLoaderConfig }

