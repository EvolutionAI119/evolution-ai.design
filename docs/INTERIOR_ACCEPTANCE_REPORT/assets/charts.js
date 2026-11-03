// 图表初始化（验收报告实测数据，单位 mm）
(function () {
  var style = getComputedStyle(document.documentElement)
  var accent = style.getPropertyValue('--accent').trim()
  var accent2 = style.getPropertyValue('--accent2').trim()
  var ink = style.getPropertyValue('--ink').trim()
  var muted = style.getPropertyValue('--muted').trim()
  var rule = style.getPropertyValue('--rule').trim()
  var bg2 = style.getPropertyValue('--bg2').trim()

  var types = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']
  var baseAxis = {
    axisLabel: { color: muted, fontFamily: 'JetBrains Mono' },
    axisLine: { lineStyle: { color: rule } },
    splitLine: { lineStyle: { color: rule, type: 'dashed' } }
  }
  var tooltip = {
    trigger: 'axis',
    appendToBody: true,
    backgroundColor: bg2,
    borderColor: rule,
    textStyle: { color: ink, fontSize: 12 }
  }

  // ---- 图 2：前排 H 点 X 修复前后 ----
  var shift = echarts.init(document.getElementById('chart-shift'), null, { renderer: 'svg' })
  shift.setOption({
    animation: false,
    tooltip: tooltip,
    legend: { textStyle: { color: muted }, top: 0 },
    grid: { left: 56, right: 20, top: 44, bottom: 34 },
    xAxis: Object.assign({ type: 'category', data: types }, baseAxis),
    yAxis: Object.assign({ type: 'value', name: 'H1 X (mm)', nameTextStyle: { color: muted } }, baseAxis),
    series: [
      {
        name: '修复前（方向盘反推）',
        type: 'bar',
        data: [491, 249, 260, 67, 393, 304],
        itemStyle: { color: muted, borderRadius: [3, 3, 0, 0] },
        barGap: '10%'
      },
      {
        name: '修复后（门洞锚定）',
        type: 'bar',
        data: [371, 270, 310, 180, 455, 468],
        itemStyle: { color: accent, borderRadius: [3, 3, 0, 0] },
        markLine: {
          symbol: 'none',
          label: { color: accent2, formatter: '前门洞前缘（各车型不同）', position: 'insideEndTop' },
          lineStyle: { color: accent2, type: 'dashed' },
          data: []
        }
      }
    ]
  })
  window.addEventListener('resize', function () { shift.resize() })

  // ---- 图 3：上下车通行余量 ----
  var entry = echarts.init(document.getElementById('chart-entry'), null, { renderer: 'svg' })
  entry.setOption({
    animation: false,
    tooltip: tooltip,
    grid: { left: 56, right: 20, top: 30, bottom: 34 },
    xAxis: Object.assign({ type: 'category', data: types }, baseAxis),
    yAxis: Object.assign({ type: 'value', name: 'mm', nameTextStyle: { color: muted }, min: 0 }, baseAxis),
    series: [{
      name: '坐垫前缘 → 前门洞前缘',
      type: 'bar',
      data: [160, 160, 160, 246, 160, 160],
      itemStyle: {
        color: function (p) { return p.value > 160 ? accent2 : accent },
        borderRadius: [3, 3, 0, 0]
      },
      label: { show: true, position: 'top', color: ink, fontFamily: 'JetBrains Mono' },
      markLine: {
        symbol: 'none',
        label: { color: accent2, formatter: '判据下限 160' },
        lineStyle: { color: accent2, type: 'dashed', width: 1.5 },
        data: [{ yAxis: 160 }]
      }
    }]
  })
  window.addEventListener('resize', function () { entry.resize() })
})()
