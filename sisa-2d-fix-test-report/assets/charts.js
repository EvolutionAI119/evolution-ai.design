// SISA 2D 比例修正测试报告 · 图表（数据以 2026-10-15/16 实测为准）
(function () {
  var st = getComputedStyle(document.documentElement);
  var accent = st.getPropertyValue('--accent').trim();
  var accent2 = st.getPropertyValue('--accent2').trim();
  var ink = st.getPropertyValue('--ink').trim();
  var muted = st.getPropertyValue('--muted').trim();
  var rule = st.getPropertyValue('--rule').trim();
  var bg2 = st.getPropertyValue('--bg2').trim();

  var axisStyle = {
    axisLine: { lineStyle: { color: rule } },
    axisLabel: { color: muted },
    splitLine: { lineStyle: { color: rule } }
  };

  /* ── 图 1：sisa-g 高度分层 修正前 vs 修正后（平台基准）── */
  var c1 = echarts.init(document.getElementById('chart-belt-compare'), null, { renderer: 'svg' });
  c1.setOption({
    animation: false,
    tooltip: { trigger: 'axis', appendToBody: true, valueFormatter: function (v) { return v + ' mm'; } },
    legend: { data: ['修正前（内核跨距口径）', '修正后（平台 coupe 档）'], textStyle: { color: muted }, top: 0 },
    grid: { left: 60, right: 24, top: 40, bottom: 36 },
    xAxis: { type: 'category', data: ['腰带高度', '机盖高度', '行李箱高度'], ...axisStyle },
    yAxis: { type: 'value', name: 'mm（离地）', nameTextStyle: { color: muted }, max: 1050, ...axisStyle },
    series: [
      { name: '修正前（内核跨距口径）', type: 'bar', data: [792, 712, 760],
        itemStyle: { color: muted, borderRadius: [3, 3, 0, 0] }, barGap: '20%',
        label: { show: true, position: 'top', color: muted } },
      { name: '修正后（平台 coupe 档）', type: 'bar', data: [950.4, 864, 864],
        itemStyle: { color: accent, borderRadius: [3, 3, 0, 0] },
        label: { show: true, position: 'top', color: accent, fontWeight: 600 } }
    ]
  });
  window.addEventListener('resize', function () { c1.resize(); });

  /* ── 图 2：平台六车型 LINE_RATIOS 校准基准 ── */
  var c2 = echarts.init(document.getElementById('chart-line-ratios'), null, { renderer: 'svg' });
  c2.setOption({
    animation: false,
    tooltip: { trigger: 'axis', appendToBody: true, valueFormatter: function (v) { return 'H × ' + v; } },
    legend: { data: ['机盖 hood', '腰带 belt', '行李箱 trunk'], textStyle: { color: muted }, top: 0 },
    grid: { left: 56, right: 24, top: 40, bottom: 36 },
    xAxis: { type: 'category', data: ['sedan\n(E级)', 'suv\n(Cayenne)', 'coupe\n(911)', 'sport\n(488)', 'mpv\n(V级)', 'pickup\n(F-150)'], ...axisStyle },
    yAxis: { type: 'value', name: '比例（占车高 H）', nameTextStyle: { color: muted }, min: 0.5, max: 0.72, ...axisStyle },
    series: [
      { name: '机盖 hood', type: 'bar', data: [0.62, 0.64, 0.60, 0.62, 0.56, 0.62],
        itemStyle: { color: accent2, borderRadius: [3, 3, 0, 0] },
        label: { show: true, position: 'top', color: muted, fontSize: 10, formatter: function (p) { return p.value.toFixed(2); } } },
      { name: '腰带 belt', type: 'bar', data: [0.68, 0.68, 0.66, 0.66, 0.66, 0.66],
        itemStyle: { color: accent, borderRadius: [3, 3, 0, 0] },
        label: { show: true, position: 'top', color: accent, fontSize: 10, fontWeight: 600, formatter: function (p) { return p.value.toFixed(2); } } },
      { name: '行李箱 trunk', type: 'bar', data: [0.60, 0.62, 0.60, 0.62, 0.62, 0.58],
        itemStyle: { color: muted, borderRadius: [3, 3, 0, 0] },
        label: { show: true, position: 'top', color: muted, fontSize: 10, formatter: function (p) { return p.value.toFixed(2); } } }
    ]
  });
  window.addEventListener('resize', function () { c2.resize(); });

  /* ── 图 3：全量测试结果构成 ── */
  var c3 = echarts.init(document.getElementById('chart-tests'), null, { renderer: 'svg' });
  c3.setOption({
    animation: false,
    tooltip: { trigger: 'item', appendToBody: true },
    legend: { orient: 'vertical', right: 10, top: 'center', textStyle: { color: muted } },
    series: [{
      type: 'pie', radius: ['58%', '80%'], center: ['42%', '50%'],
      label: { show: true, position: 'center', formatter: '687\n用例', color: ink, fontSize: 22, fontWeight: 700, lineHeight: 30 },
      data: [
        { value: 686, name: '通过（passed）', itemStyle: { color: accent2 } },
        { value: 1, name: '跳过（skipped）', itemStyle: { color: muted } },
        { value: 0, name: '失败（failed）', itemStyle: { color: '#c2410c' } }
      ]
    }]
  });
  window.addEventListener('resize', function () { c3.resize(); });
})();
