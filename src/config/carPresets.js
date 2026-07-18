export const carTypes = [
  { key: 'sedan', name: 'Sedan', desc: 'Classic sedan' },
  { key: 'suv', name: 'SUV', desc: 'Sport utility' },
  { key: 'coupe', name: 'Coupe', desc: 'Two-door' },
  { key: 'sport', name: 'Sports', desc: 'High performance' },
  { key: 'mpv', name: 'MPV', desc: 'Multi-purpose' },
  { key: 'pickup', name: 'Pickup', desc: 'Pickup truck' }
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
  windshield_angle: 30,
  rear_window_angle: 25,
  rear_slant_angle: 15,
  front_overhang: 1100,
  rear_overhang: 1118
}

export const carTypeParams = {
  sedan: {
    overall_length: 4950, overall_width: 1880, overall_height: 1460,
    wheel_base: 2890, track_width: 1600, ground_clearance: 140,
    hood_length: 1050, roof_height: 550, wheel_diameter: 680,
    windshield_angle: 35, rear_window_angle: 28, rear_slant_angle: 18,
    front_overhang: 950, rear_overhang: 1110
  },
  suv: {
    overall_length: 5050, overall_width: 1980, overall_height: 1780,
    wheel_base: 2950, track_width: 1680, ground_clearance: 210,
    hood_length: 1150, roof_height: 850, wheel_diameter: 760,
    windshield_angle: 28, rear_window_angle: 22, rear_slant_angle: 12,
    front_overhang: 980, rear_overhang: 1120
  },
  coupe: {
    overall_length: 4800, overall_width: 1890, overall_height: 1380,
    wheel_base: 2780, track_width: 1620, ground_clearance: 120,
    hood_length: 1350, roof_height: 420, wheel_diameter: 700,
    windshield_angle: 40, rear_window_angle: 35, rear_slant_angle: 40,
    front_overhang: 1020, rear_overhang: 1000
  },
  sport: {
    overall_length: 4600, overall_width: 1980, overall_height: 1250,
    wheel_base: 2700, track_width: 1700, ground_clearance: 100,
    hood_length: 1500, roof_height: 350, wheel_diameter: 720,
    windshield_angle: 45, rear_window_angle: 38, rear_slant_angle: 48,
    front_overhang: 950, rear_overhang: 950
  },
  mpv: {
    overall_length: 5200, overall_width: 1920, overall_height: 1830,
    wheel_base: 3100, track_width: 1640, ground_clearance: 160,
    hood_length: 850, roof_height: 950, wheel_diameter: 700,
    windshield_angle: 25, rear_window_angle: 18, rear_slant_angle: 10,
    front_overhang: 880, rear_overhang: 1220
  },
  pickup: {
    overall_length: 5600, overall_width: 1980, overall_height: 1880,
    wheel_base: 3450, track_width: 1680, ground_clearance: 230,
    hood_length: 1350, roof_height: 750, wheel_diameter: 780,
    windshield_angle: 28, rear_window_angle: 20, rear_slant_angle: 15,
    front_overhang: 1050, rear_overhang: 1100
  }
}

export const bodyColors = [
  { name: 'Obsidian Black', value: '#0a0a0f' },
  { name: 'Carbon Gray', value: '#374151' },
  { name: 'Silver Metallic', value: '#9ca3af' },
  { name: 'Pearl White', value: '#f3f4f6' },
  { name: 'Cream Beige', value: '#d4c5a9' },
  { name: 'Champagne Gold', value: '#d4af37' },
  { name: 'Racing Red', value: '#dc2626' },
  { name: 'Burgundy', value: '#7f1d1d' },
  { name: 'Sunset Orange', value: '#ea580c' },
  { name: 'Canary Yellow', value: '#facc15' },
  { name: 'British Green', value: '#166534' },
  { name: 'Mint Green', value: '#4ade80' },
  { name: 'Ocean Blue', value: '#0369a1' },
  { name: 'Royal Blue', value: '#1e40af' },
  { name: 'Amethyst Purple', value: '#6b21a8' }
]

const IMG = '/api/ide/v1/text_to_image'
const ep = encodeURIComponent

const mk = (p, s) => IMG + '?prompt=' + ep(p) + '&image_size=' + s

export const imageLoaderConfig = {
  maxRetries: 5,
  baseRetryIntervalMs: 3000,
  retryIntervalMultiplier: 1,
  placeholderSizeThresholdBytes: 5000,
  preloadConcurrency: 3
}

export const brands = [
  {
    key: 'rolls-royce',
    name: 'Rolls-Royce',
    color: '#4ade80',
    models: [
      { key: 'phantom', name: 'Phantom', params: { overall_length: 5770, overall_width: 2018, overall_height: 1648, wheel_base: 3552, track_width: 1680, ground_clearance: 150, hood_length: 1300, roof_height: 750, wheel_diameter: 750, windshield_angle: 28, rear_window_angle: 22, rear_slant_angle: 12 }, image: mk('Rolls-Royce Phantom luxury sedan side view black', 'landscape_16_9') },
      { key: 'ghost', name: 'Ghost', params: { overall_length: 5546, overall_width: 1948, overall_height: 1550, wheel_base: 3295, track_width: 1640, ground_clearance: 145, hood_length: 1200, roof_height: 650, wheel_diameter: 720, windshield_angle: 30, rear_window_angle: 24, rear_slant_angle: 14 }, image: mk('Rolls-Royce Ghost luxury sedan side view silver', 'landscape_16_9') },
      { key: 'cullinan', name: 'Cullinan', params: { overall_length: 5341, overall_width: 2000, overall_height: 1835, wheel_base: 3295, track_width: 1680, ground_clearance: 215, hood_length: 1200, roof_height: 900, wheel_diameter: 780, windshield_angle: 26, rear_window_angle: 20, rear_slant_angle: 10 }, image: mk('Rolls-Royce Cullinan luxury SUV side view white', 'landscape_16_9') },
      { key: 'wraith', name: 'Wraith', params: { overall_length: 5285, overall_width: 1947, overall_height: 1507, wheel_base: 3112, track_width: 1630, ground_clearance: 135, hood_length: 1400, roof_height: 550, wheel_diameter: 710, windshield_angle: 38, rear_window_angle: 32, rear_slant_angle: 35 }, image: mk('Rolls-Royce Wraith luxury coupe side view blue', 'landscape_16_9') }
    ]
  },
  {
    key: 'bentley',
    name: 'Bentley',
    color: '#3b82f6',
    models: [
      { key: 'continental-gt', name: 'Continental GT', params: { overall_length: 4850, overall_width: 1954, overall_height: 1405, wheel_base: 2851, track_width: 1650, ground_clearance: 125, hood_length: 1450, roof_height: 480, wheel_diameter: 730, windshield_angle: 38, rear_window_angle: 33, rear_slant_angle: 38 }, image: mk('Bentley Continental GT coupe side view green', 'landscape_16_9') },
      { key: 'continental-gtc', name: 'Continental GTC', params: { overall_length: 4850, overall_width: 1954, overall_height: 1405, wheel_base: 2851, track_width: 1650, ground_clearance: 125, hood_length: 1450, roof_height: 480, wheel_diameter: 730, windshield_angle: 38, rear_window_angle: 33, rear_slant_angle: 38 }, image: mk('Bentley Continental GTC convertible side view blue', 'landscape_16_9') },
      { key: 'flying-spur', name: 'Flying Spur', params: { overall_length: 5316, overall_width: 1978, overall_height: 1484, wheel_base: 3194, track_width: 1660, ground_clearance: 140, hood_length: 1300, roof_height: 600, wheel_diameter: 730, windshield_angle: 32, rear_window_angle: 26, rear_slant_angle: 16 }, image: mk('Bentley Flying Spur sedan side view black', 'landscape_16_9') },
      { key: 'bentayga', name: 'Bentayga', params: { overall_length: 5125, overall_width: 1998, overall_height: 1742, wheel_base: 2995, track_width: 1680, ground_clearance: 200, hood_length: 1200, roof_height: 850, wheel_diameter: 760, windshield_angle: 28, rear_window_angle: 22, rear_slant_angle: 12 }, image: mk('Bentley Bentayga luxury SUV side view white', 'landscape_16_9') }
    ]
  },
  {
    key: 'bugatti',
    name: 'Bugatti',
    color: '#f59e0b',
    models: [
      { key: 'chiron', name: 'Chiron', params: { overall_length: 4544, overall_width: 2038, overall_height: 1212, wheel_base: 2711, track_width: 1720, ground_clearance: 95, hood_length: 1550, roof_height: 320, wheel_diameter: 740, windshield_angle: 48, rear_window_angle: 42, rear_slant_angle: 52 }, image: mk('Bugatti Chiron hypercar side view blue', 'landscape_16_9') },
      { key: 'veyron', name: 'Veyron', params: { overall_length: 4462, overall_width: 1998, overall_height: 1159, wheel_base: 2710, track_width: 1710, ground_clearance: 90, hood_length: 1500, roof_height: 300, wheel_diameter: 720, windshield_angle: 46, rear_window_angle: 40, rear_slant_angle: 50 }, image: mk('Bugatti Veyron supercar side view black', 'landscape_16_9') },
      { key: 'divo', name: 'Divo', params: { overall_length: 4579, overall_width: 2038, overall_height: 1212, wheel_base: 2711, track_width: 1730, ground_clearance: 90, hood_length: 1550, roof_height: 310, wheel_diameter: 740, windshield_angle: 50, rear_window_angle: 44, rear_slant_angle: 55 }, image: mk('Bugatti Divo hypercar side view blue carbon', 'landscape_16_9') }
    ]
  },
  {
    key: 'porsche',
    name: 'Porsche',
    color: '#ef4444',
    models: [
      { key: '911', name: '911 Carrera', params: { overall_length: 4519, overall_width: 1852, overall_height: 1299, wheel_base: 2450, track_width: 1580, ground_clearance: 105, hood_length: 1100, roof_height: 400, wheel_diameter: 680, windshield_angle: 42, rear_window_angle: 35, rear_slant_angle: 45 }, image: mk('Porsche 911 sports car side view red', 'landscape_16_9') },
      { key: 'taycan', name: 'Taycan', params: { overall_length: 4963, overall_width: 1966, overall_height: 1381, wheel_base: 2900, track_width: 1660, ground_clearance: 125, hood_length: 1200, roof_height: 500, wheel_diameter: 710, windshield_angle: 38, rear_window_angle: 32, rear_slant_angle: 35 }, image: mk('Porsche Taycan electric sedan side view white', 'landscape_16_9') },
      { key: 'panamera', name: 'Panamera', params: { overall_length: 5049, overall_width: 1937, overall_height: 1423, wheel_base: 2950, track_width: 1650, ground_clearance: 130, hood_length: 1300, roof_height: 550, wheel_diameter: 710, windshield_angle: 35, rear_window_angle: 28, rear_slant_angle: 30 }, image: mk('Porsche Panamera sedan side view gray', 'landscape_16_9') },
      { key: 'cayenne', name: 'Cayenne', params: { overall_length: 4926, overall_width: 1983, overall_height: 1673, wheel_base: 2895, track_width: 1680, ground_clearance: 190, hood_length: 1200, roof_height: 780, wheel_diameter: 760, windshield_angle: 28, rear_window_angle: 22, rear_slant_angle: 15 }, image: mk('Porsche Cayenne SUV side view white', 'landscape_16_9') },
      { key: 'macan', name: 'Macan', params: { overall_length: 4686, overall_width: 1923, overall_height: 1624, wheel_base: 2807, track_width: 1650, ground_clearance: 180, hood_length: 1150, roof_height: 720, wheel_diameter: 730, windshield_angle: 30, rear_window_angle: 24, rear_slant_angle: 18 }, image: mk('Porsche Macan compact SUV side view black', 'landscape_16_9') }
    ]
  },
  {
    key: 'ferrari',
    name: 'Ferrari',
    color: '#dc2626',
    models: [
      { key: 'sf90', name: 'SF90 Stradale', params: { overall_length: 4710, overall_width: 1972, overall_height: 1186, wheel_base: 2650, track_width: 1700, ground_clearance: 90, hood_length: 1450, roof_height: 300, wheel_diameter: 730, windshield_angle: 50, rear_window_angle: 45, rear_slant_angle: 55 }, image: mk('Ferrari SF90 supercar side view red', 'landscape_16_9') },
      { key: 'f8-tributo', name: 'F8 Tributo', params: { overall_length: 4611, overall_width: 1979, overall_height: 1206, wheel_base: 2650, track_width: 1700, ground_clearance: 95, hood_length: 1400, roof_height: 320, wheel_diameter: 720, windshield_angle: 48, rear_window_angle: 42, rear_slant_angle: 52 }, image: mk('Ferrari F8 Tributo sports car side view red', 'landscape_16_9') },
      { key: 'roma', name: 'Roma', params: { overall_length: 4656, overall_width: 1974, overall_height: 1301, wheel_base: 2670, track_width: 1680, ground_clearance: 105, hood_length: 1350, roof_height: 420, wheel_diameter: 710, windshield_angle: 40, rear_window_angle: 34, rear_slant_angle: 40 }, image: mk('Ferrari Roma GT coupe side view silver', 'landscape_16_9') }
    ]
  }
]

export default { carTypes, defaultCarParams, carTypeParams, brands, bodyColors }
