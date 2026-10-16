# Flight Performance Measured Data Analysis Report

> Anti-Gravity Flight Control System · Five Technical Targets · Full Data Verification Across Six Vehicle Types
> Report date: 2026-10-16 · Platform version: VTOL + full-stack anti-gravity flight control (main 974bad89)

**Full visual edition (7 data charts + 3 structural diagrams, incl. a dedicated "Theoretical Derivation of the Anti-Gravity Drive" chapter, self-contained single-file HTML)**:

- English: <a href="../en/flight_performance_analysis.html" target="_blank" rel="noopener">Flight Performance Data Analysis (full visual report)</a>
- 中文版：<a href="../flight_performance_analysis.html" target="_blank" rel="noopener">飞行性能实测数据分析报告（可视化全文）</a>

## Measured results for the five technical targets

| Technical target | Limit | Measured range (6 types) | Verdict |
|---|---|---|---|
| 1. Hover attitude deviation | ≤±2° | ±0.728° ~ ±0.767° | ALL PASS, 2.6× margin |
| 2. 360° in-place turn | smooth, stable | 15.0 s (45°/s comfort limit, quintic C² profile) | ALL PASS, unlimited multi-turn |
| 3. Endurance multiple (equal battery) | ≥3× | ×3.17 (sport) ~ ×3.83 (pickup) | ALL PASS, ≥5.7% margin |
| 4. Energy peak factor | ≤1.25 | ×1.14 ~ ×1.17 | ALL PASS, no significant peak |
| 5. Flight control latency | ≤100 ms | 76 ~ 80 ms | ALL PASS, ≥20 ms margin |

## Triple data-verification chain

1. **Formula-envelope reproduction**: every metric is computed by pure-math formulas, with a dual implementation sharing the same formulas — front-end `src/utils/flightPhysics.js` and back-end `car_generator.flight_envelope`; report charts are pre-rendered as inline SVG from the same formulas, not hand-copied values.
2. **Test-matrix lock**: front-end vitest 285/285 (35 dedicated flight cases), back-end pytest 386 passed (14 flight-branch cases) — formula regression, range clamping and the zero-geometry-change contract are all assertion-guarded.
3. **Live verification on the public site**: a browser-automation agent completed a 7/7-pass full-flow check at `https://evolution-ai.design/#/designer`; real-time HUD readings matched offline formulas digit-for-digit (sedan hover 27.03 kW · ×3.66).

## Model self-consistency (honesty by design)

- sport is the only type whose field share is not capped (0.688 < 0.75), and it also has the lowest endurance multiple — the parameter→performance response is physically consistent.
- With dark-energy/dark-matter ratios set to 0, the system **honestly degrades** to conventional-propulsion performance (endurance ×1.0, peak factor ×1.31 over limit); UI and back-end verdicts flip to false in sync — there is no "fudged pass" path.

## Data boundary disclosure

This platform is a parametric design-simulation platform: the energy baseline (55 kW/t^1.2), field-maintenance specific power (12 W/kg) and vehicle density (120 kg/m³) are engineering-model assumptions; "measured" means real-time computed readings of the deployed artifact verified in the public environment — not wind-tunnel or flight-test-grade measurement.

## Provenance

- `src/utils/flightPhysics.js` · `backend/app/car_generator.py` (commit 974bad89)
- `src/tests/flightPhysics.spec.js` (35 cases) · `backend/tests/test_flight_branch.py` (14 cases)
- Public deployment gh-pages 5c5dfdc · live-check record in Chapter 08 of the visual report
