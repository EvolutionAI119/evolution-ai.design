export const generateCarSvg = (model, carType = 'sedan') => {
  const { overall_length = 5000, overall_height = 1500, overall_width = 1900 } = model.params || {}
  
  const normalizedLength = Math.min(300, Math.max(150, overall_length / 20))
  const normalizedHeight = Math.min(80, Math.max(40, overall_height / 25))
  
  const carColors = {
    'rolls-royce': '#4ade80',
    'bentley': '#3b82f6',
    'bugatti': '#f59e0b',
    'porsche': '#ef4444',
    'ferrari': '#dc2626',
    'lamborghini': '#f97316',
    'aston-martin': '#22c55e',
    'mclaren': '#facc15'
  }
  
  const brandColor = carColors[model.brandKey] || '#4ade80'
  
  const bodyPath = getBodyPath(carType, normalizedLength, normalizedHeight)
  const windowPath = getWindowPath(carType, normalizedLength, normalizedHeight)
  
  return `<svg viewBox="0 0 320 160" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="${brandColor}" stop-opacity="0.9"/>
        <stop offset="50%" stop-color="${brandColor}" stop-opacity="0.7"/>
        <stop offset="100%" stop-color="${brandColor}" stop-opacity="0.5"/>
      </linearGradient>
      <linearGradient id="glassGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#1e293b" stop-opacity="0.8"/>
        <stop offset="100%" stop-color="#0f172a" stop-opacity="0.9"/>
      </linearGradient>
      <filter id="shadow">
        <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="black" flood-opacity="0.3"/>
      </filter>
    </defs>
    
    <rect width="320" height="160" fill="#0f172a" rx="8"/>
    
    <ellipse cx="160" cy="140" rx="${normalizedLength * 0.45}" ry="8" fill="black" opacity="0.3"/>
    
    <path d="${bodyPath}" fill="url(#bodyGrad)" stroke="${brandColor}" stroke-width="1.5" filter="url(#shadow)"/>
    
    <path d="${windowPath}" fill="url(#glassGrad)" stroke="${brandColor}" stroke-width="0.5" opacity="0.9"/>
    
    <circle cx="${160 - normalizedLength * 0.3}" cy="${140}" r="15" fill="#1e293b" stroke="#475569" stroke-width="2"/>
    <circle cx="${160 - normalizedLength * 0.3}" cy="${140}" r="8" fill="#334155"/>
    <circle cx="${160 + normalizedLength * 0.3}" cy="${140}" r="15" fill="#1e293b" stroke="#475569" stroke-width="2"/>
    <circle cx="${160 + normalizedLength * 0.3}" cy="${140}" r="8" fill="#334155"/>
    
    <line x1="20" y1="150" x2="300" y2="150" stroke="${brandColor}" stroke-width="1" opacity="0.3"/>
    
    <text x="160" y="155" text-anchor="middle" fill="${brandColor}" font-size="8" font-family="monospace" opacity="0.7">${model.name || 'Unknown'}</text>
  </svg>`
}

const getBodyPath = (carType, length, height) => {
  const cx = 160
  const cy = 100
  const halfLen = length / 2
  
  switch (carType) {
    case 'sport':
    case 'coupe':
      return `M${cx - halfLen},${cy + height * 0.6} 
              L${cx - halfLen + 20},${cy + height * 0.2} 
              Q${cx - halfLen + 40},${cy - height * 0.4} ${cx - 20},${cy - height * 0.5}
              Q${cx},${cy - height * 0.6} ${cx + 30},${cy - height * 0.4}
              Q${cx + halfLen - 30},${cy + height * 0.1} ${cx + halfLen},${cy + height * 0.5}
              L${cx + halfLen},${cy + height * 0.6}
              Z`
    case 'suv':
    case 'mpv':
      return `M${cx - halfLen},${cy + height * 0.5} 
              L${cx - halfLen + 15},${cy - height * 0.1} 
              L${cx - halfLen + 25},${cy - height * 0.5}
              L${cx + halfLen - 25},${cy - height * 0.5}
              L${cx + halfLen - 15},${cy - height * 0.1}
              L${cx + halfLen},${cy + height * 0.5}
              Z`
    case 'pickup':
      return `M${cx - halfLen},${cy + height * 0.5} 
              L${cx - halfLen + 15},${cy - height * 0.2} 
              L${cx - halfLen + 25},${cy - height * 0.45}
              L${cx - 20},${cy - height * 0.45}
              L${cx - 20},${cy + height * 0.3}
              L${cx + halfLen},${cy + height * 0.3}
              L${cx + halfLen},${cy + height * 0.5}
              Z`
    case 'sedan':
    default:
      return `M${cx - halfLen},${cy + height * 0.5} 
              L${cx - halfLen + 15},${cy + height * 0.1} 
              Q${cx - halfLen + 30},${cy - height * 0.3} ${cx - 15},${cy - height * 0.4}
              Q${cx},${cy - height * 0.45} ${cx + 25},${cy - height * 0.35}
              Q${cx + halfLen - 25},${cy + height * 0.05} ${cx + halfLen},${cy + height * 0.4}
              L${cx + halfLen},${cy + height * 0.5}
              Z`
  }
}

const getWindowPath = (carType, length, height) => {
  const cx = 160
  const cy = 100
  const halfLen = length / 2
  
  switch (carType) {
    case 'sport':
    case 'coupe':
      return `M${cx - halfLen + 25},${cy + height * 0.1} 
              Q${cx - halfLen + 45},${cy - height * 0.35} ${cx - 15},${cy - height * 0.42}
              Q${cx},${cy - height * 0.48} ${cx + 25},${cy - height * 0.32}
              Q${cx + halfLen - 35},${cy + height * 0.1} ${cx + halfLen - 20},${cy + height * 0.2}
              Z`
    case 'suv':
    case 'mpv':
      return `M${cx - halfLen + 20},${cy - height * 0.05} 
              L${cx - halfLen + 30},${cy - height * 0.4}
              L${cx + halfLen - 30},${cy - height * 0.4}
              L${cx + halfLen - 20},${cy - height * 0.05}
              Z`
    case 'pickup':
      return `M${cx - halfLen + 20},${cy - height * 0.1} 
              L${cx - halfLen + 30},${cy - height * 0.35}
              L${cx - 25},${cy - height * 0.35}
              L${cx - 25},${cy - height * 0.1}
              Z`
    case 'sedan':
    default:
      return `M${cx - halfLen + 20},${cy + height * 0.05} 
              Q${cx - halfLen + 35},${cy - height * 0.25} ${cx - 10},${cy - height * 0.35}
              Q${cx},${cy - height * 0.4} ${cx + 20},${cy - height * 0.3}
              Q${cx + halfLen - 30},${cy + height * 0.05} ${cx + halfLen - 15},${cy + height * 0.15}
              Z`
  }
}

export const getCarTypeSvgPath = (carType) => {
  const cx = 150
  const cy = 80
  const w = 140
  const h = 35
  
  switch (carType) {
    case 'sport':
    case 'coupe':
      return `M${cx - w/2},${cy + h*0.4} 
              Q${cx - w/2 + 10},${cy - h*0.3} ${cx - 15},${cy - h*0.5}
              Q${cx},${cy - h*0.55} ${cx + 25},${cy - h*0.3}
              Q${cx + w/2 - 15},${cy + h*0.2} ${cx + w/2},${cy + h*0.4}
              Z`
    case 'suv':
    case 'mpv':
      return `M${cx - w/2},${cy + h*0.3} 
              L${cx - w/2 + 10},${cy - h*0.2}
              L${cx - w/2 + 20},${cy - h*0.45}
              L${cx + w/2 - 20},${cy - h*0.45}
              L${cx + w/2 - 10},${cy - h*0.2}
              L${cx + w/2},${cy + h*0.3}
              Z`
    case 'pickup':
      return `M${cx - w/2},${cy + h*0.3} 
              L${cx - w/2 + 10},${cy - h*0.15}
              L${cx - w/2 + 18},${cy - h*0.4}
              L${cx - 15},${cy - h*0.4}
              L${cx - 15},${cy + h*0.1}
              L${cx + w/2},${cy + h*0.1}
              L${cx + w/2},${cy + h*0.3}
              Z`
    case 'sedan':
    default:
      return `M${cx - w/2},${cy + h*0.3} 
              Q${cx - w/2 + 12},${cy - h*0.2} ${cx - 12},${cy - h*0.4}
              Q${cx},${cy - h*0.45} ${cx + 20},${cy - h*0.3}
              Q${cx + w/2 - 20},${cy + h*0.1} ${cx + w/2},${cy + h*0.35}
              Z`
  }
}

export const generatePlaceholderSvg = (model, carType) => {
  const svg = generateCarSvg(model, carType)
  return `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`
}

export const getModelInitials = (name) => {
  if (!name) return '??'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}
