# 飞行性能实测数据分析报告

> 反重力飞控系统 · 五项技术目标 · 六车型全量数据核验
> 报告日期：2026-10-16 · 数据平台版本：VTOL + 反重力飞控全栈（main 974bad89）

**完整可视化版（7 张数据图表 + 3 幅结构示意图，含「反重力驱动技术理论推导」专章，自包含单文件 HTML）**：

- 中文版：<a href="docs/flight_performance_analysis.html" target="_blank" rel="noopener">飞行性能实测数据分析报告（可视化全文）</a>
- English: <a href="docs/en/flight_performance_analysis.html" target="_blank" rel="noopener">Flight Performance Data Analysis (full visual report)</a>

## 五项技术目标实测结果

| 技术目标 | 限值 | 六车型实测区间 | 结论 |
|---|---|---|---|
| 1. 悬停姿态偏差 | ≤±2° | ±0.728° ~ ±0.767° | 全达标，余量 2.6× |
| 2. 360° 原地转向 | 平滑无失稳 | 15.0 s（45°/s 舒适限，quintic C² 剖面） | 全达标，无限制多圈 |
| 3. 续航倍数（同电量） | ≥3× | ×3.17（sport）~ ×3.83（pickup） | 全达标，最低余量 5.7% |
| 4. 能耗峰值因子 | ≤1.25 | ×1.14 ~ ×1.17 | 全达标，无明显峰值 |
| 5. 飞控响应延迟 | ≤100 ms | 76 ~ 80 ms | 全达标，余量 ≥20 ms |

## 数据三重验证链

1. **公式包线复现**：全部指标由纯数学公式计算，前端 `src/utils/flightPhysics.js` 与后端 `car_generator.flight_envelope` 同公式双实现；报告图表以同一公式预渲染为内嵌 SVG，非手抄数值。
2. **测试矩阵锁定**：前端 vitest 285/285（飞行专项 35 项）、后端 pytest 386 过（飞行分支 14 项）——公式回归、越界钳位、几何零改动契约均有断言守护。
3. **公网环境实测**：经浏览器自动化在 `https://evolution-ai.design/#/designer` 完成 7/7 项全流程校验，HUD 实时读数与离线公式逐位吻合（sedan 悬停 27.03 kW · ×3.66）。

## 模型自洽性（诚实性设计）

- sport 是唯一场份额未顶格（0.688 < 0.75）的车型，其续航倍数恰为最低——参数→性能响应物理一致。
- 将暗能量/暗物质占比调至 0 时，系统**如实退化**为传统动力性能（续航 ×1.0、峰值因子 ×1.31 超限），UI 与后端判定同步转假，不存在任何"凑数达标"路径。

## 数据边界声明

本平台为参数化设计仿真平台：能耗基准（55 kW/t^1.2）、场维持比功率（12 W/kg）、整车密度（120 kg/m³）为工程估算模型假设；"实测"指部署产物的实时计算读数经公网环境核验，不等同于风洞/试飞级测量。

## 溯源

- `src/utils/flightPhysics.js` · `backend/app/car_generator.py`（提交 974bad89）
- `src/tests/flightPhysics.spec.js`（35 项）· `backend/tests/test_flight_branch.py`(14 项)
- 公网部署 gh-pages 5c5dfdc · 实测记录见可视化报告第 08 章
