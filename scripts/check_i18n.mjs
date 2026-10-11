import fs from 'fs'
const s = fs.readFileSync('src/i18n.js', 'utf8')
function extract(name) {
  const m = s.match(new RegExp('const ' + name + '\\s*=\\s*\\{'))
  if (!m) throw new Error(name + ' not found')
  let start = m.index + m[0].length - 1
  let d = 0, end = start
  for (let j = start; j < s.length; j++) {
    const c = s[j]
    if (c === '{') d++
    else if (c === '}') { d--; if (!d) { end = j; break } }
  }
  return s.slice(start, end + 1)
}
const flat = (o, p = '') => Object.entries(o).flatMap(([k, v]) => v && typeof v === 'object' ? flat(v, p + k + '.') : [p + k])
const zh = new Function('return (' + extract('zh') + ')')()
const en = new Function('return (' + extract('en') + ')')()
const zk = new Set(flat(zh)), ek = new Set(flat(en))
const missEn = [...zk].filter(k => !ek.has(k))
const missZh = [...ek].filter(k => !zk.has(k))
console.log('zh:', zk.size, 'en:', ek.size, '| missing in en:', missEn.length, missEn.slice(0, 5), '| missing in zh:', missZh.length, missZh.slice(0, 5))
for (const k of ['designer.sisaRef', 'designer.toggleSisaRef', 'designer.sisaLegend', 'designer.sisaRmse']) {
  console.log(k, zk.has(k) && ek.has(k) ? 'OK' : 'MISSING')
}
