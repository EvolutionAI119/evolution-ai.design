// 验收报告图表（数据与 carInteriorLayout 真源输出一致，单位 mm）
(function () {
  var style = getComputedStyle(document.documentElement)
  var accent = style.getPropertyValue('--accent').trim()
  var accent2 = style.getPropertyValue('--accent2').trim()
  var ink = style.getPropertyValue('--ink').trim()
  var muted = style.getPropertyValue('--muted').trim()
  var rule = style.getPropertyValue('--rule').trim()
  var bg2 = style.getPropertyValue('--bg2').trim()

  var types = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']
  var axisText = { color: muted, fontFamily: 'JetBrains Mono', fontSize: 11 }
  var tooltip = {
    trigger: 'axis',
    appendToBody: true,
    backgroundColor: bg2,
    borderColor: rule,
    textStyle: { color: ink, fontSize: 12 }
  }

  // ---- 图 1：关键间隙实测 ----
  var gaps = echarts.init(document.getElementById('chart-gaps'), null, { renderer: 'svg' })
  gaps.setOption({
    animation: false,
    tooltip: tooltip,
    legend: { textStyle: { color: muted }, top: 0 },
    grid: { left: 60, right: 24, top: 56, bottom: 32 },
    xAxis: { type: 'category', data: types, axisLabel: axisText, axisLine: { lineStyle: { color: rule } } },
    yAxis: {
      type: 'value', name: 'mm', nameTextStyle: { color: muted },
      axisLabel: axisText, splitLine: { lineStyle: { color: rule, type: 'dashed' } }
    },
    series: [
      { name: '门饰板↔座椅 (下限20)', type: 'bar', data: [85, 110, 87, 110, 95, 110], itemStyle: { color: accent, borderRadius: [3, 3, 0, 0] } },
      { name: '扶手↔座椅 (下限30)', type: 'bar', data: [55, 80, 57, 80, 65, 80], itemStyle: { color: accent + '99', borderRadius: [3, 3, 0, 0] } },
      { name: '中控↔座椅 (下限20)', type: 'bar', data: [85, 110, 87, 110, 95, 110], itemStyle: { color: muted, borderRadius: [3, 3, 0, 0] } },
      { name: '顶棚↔头枕 (下限30)', type: 'bar', data: [120, 316, 93, 57, 335, 405], itemStyle: { color: accent2 + 'cc', borderRadius: [3, 3, 0, 0] } }
    ]
  })
  window.addEventListener('resize', function () { gaps.resize() })

  // ---- 图 2：滑轨全行程端点余量（负值 = 穿透） ----
  var travel = echarts.init(document.getElementById('chart-travel'), null, { renderer: 'svg' })
  travel.setOption({
    animation: false,
    tooltip: tooltip,
    legend: { textStyle: { color: muted }, top: 0 },
    grid: { left: 70, right: 30, top: 56, bottom: 32 },
    xAxis: {
      type: 'value', name: 'mm', nameTextStyle: { color: muted },
      axisLabel: axisText, splitLine: { lineStyle: { color: rule, type: 'dashed' } }
    },
    yAxis: { type: 'category', data: types.slice().reverse(), axisLabel: axisText, axisLine: { lineStyle: { color: rule } } },
    series: [
      {
        name: '最前端：膝部余量',
        type: 'bar',
        data: [62, 215, 10, 10, 135, 84],
        itemStyle: {
          color: function (p) { return p.value < 0 ? accent2 : accent },
          borderRadius: 3
        },
        label: { show: true, position: 'right', color: ink, fontFamily: 'JetBrains Mono', fontSize: 11 }
      },
      {
        name: '最后端：靠背↔B柱余量',
        type: 'bar',
        data: [1122, 49, 107, 222, 10, 10],
        itemStyle: {
          color: function (p) { return p.value < 0 ? accent2 : muted },
          borderRadius: 3
        },
        label: { show: true, position: 'right', color: ink, fontFamily: 'JetBrains Mono', fontSize: 11 }
      }
    ]
  })
  window.addEventListener('resize', function () { travel.resize() })
})()
