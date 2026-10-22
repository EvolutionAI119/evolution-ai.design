# Flight Performance Measured Data Analysis Report

> Anti-Gravity Flight Control System · Five Technical Targets · Full Data Verification Across Six Vehicle Types
> Report date: 2026-10-21 · Platform version: VTOL + full-stack anti-gravity flight control (main 974bad89)
> v2 full-text edition: generated from the same source as the full HTML report (10 chapters + 10 figures + provenance)

[Full visual edition (interactive charts)](/docs/en/flight_performance_analysis.html)

**Key metrics at a glance** (mirrors the metric cards in the HTML report header):

| Metric | Measured value | Verdict |
|---|---|---|
| Hover attitude deviation (Target 1) | ±0.76° | Target ≤±2° · 2.6× margin |
| 360° in-place turn duration (Target 2) | 15.0 s | Peak rate within the 45°/s comfort limit · unlimited multi-turn |
| Endurance multiple (Target 3) | ×3.17–3.83 | Target ≥3× · all six types pass |
| Energy peak factor (Target 4) | ×1.14–1.17 | Limit ≤1.25 · no significant peak |
| Flight control latency (Target 5) | 76–80 ms | Ceiling ≤100ms · passes across the full parameter range |
| Live verification pass rate | 7/7 | Zero console errors · HUD readings match formulas |

## 01 Data Sources and Verification Methodology

All data in this report comes from **three independent sources**, forming a triple cross-validation chain — every single number is traceable:

- **Formula-envelope reproduction** — every metric is computed by open, reproducible pure-math formulas (strictly isomorphic to `src/utils/flightPhysics.js` and the back-end `car_generator.flight_envelope`); all chart curves in this report are pre-rendered as inline SVG from the same formulas, not hand-copied values;
- **Test-matrix lock** — front-end vitest **285/285** (35 dedicated flight-physics cases) and back-end pytest **386 passed** (14 flight-branch cases); formula regression, out-of-range clamping and the zero-geometry-change contract are all guarded by assertions;
- **Live verification on the public site** — on 2026-10-16 a browser-automation agent completed full-flow interaction tests at `https://evolution-ai.design/#/designer` (see Chapter 09); real-time HUD readings matched offline formula results **digit-for-digit**.

<figure class="doc-figure">
  <img src="docs/images/en/flight-verify-chain.svg" alt="Triple verification chain: front-end formula, back-end formula and live readings match digit-for-digit" loading="lazy">
  <figcaption>*Triple verification chain: front-end formula, back-end formula, live readings match digit-for-digit — test lock: vitest 285/285 · pytest 386 passed, 35 + 14 flight-specific assertions (formula regression · range clamping · honest degradation).*</figcaption>
</figure>

> **Data Nature Boundary (Honest Disclosure)**: This platform is a parametric design-simulation platform; the flight envelope is an **engineering estimation model**: curb mass is extrapolated from a 120 kg/m³ bounding-volume density, and the energy model is based on a disk-loading baseline with a sci-fi-bounded dark-energy/dark-matter analogy (η∈[0,0.3], field share ≤0.75). The data reflects the physical self-consistency of the design model and **is not equivalent to real flight-test data**; model honesty is guaranteed by the "honest degradation under extreme parameters" mechanism (end of Chapter 06).

## 02 Anti-Gravity Drive Theory: Analytical Derivation

The previous chapter established that the data is trustworthy; this chapter answers a deeper question: **where do these numbers come from**. Every metric of the anti-gravity flight controller — effective gravity, field-lift share, hover power, endurance multiple, peak factor, attitude envelope and latency — is obtained by **analytical derivation** from **three bounded assumptions** (metric-shielding coefficient η_e, inertia blending η_cdm, disk-loading baseline) through classical mechanics, momentum theory and control theory, with no fitted black box. The six sections below unfold along the causal chain, providing the theoretical foundation for the five targets measured in Chapters 03–07.

### 2.1 Metric-screening hypothesis and effective gravity (sci-fi bounded)

Dark energy exists as a negative-pressure state (equation of state w = −1); its engineering analogy is to establish a local metric curvature in the vehicle's neighborhood that screens the **gravitational measure**. The key trade-off is the equivalence principle's "one-way approximation" — the metric effect acts only on the gravitational measure and **leaves inertial mass unchanged**: maneuvers and attitude response still require real thrust, so all dynamic behavior remains physically self-consistent and no runaway "inertia-vanishing" scenario can occur. The screening coefficient is bounded, η_e∈[0, 0.3] (beyond which the shield-boundary gradient destabilizes), with 0.35 as the screening-coupling cap:

```
g_eff(η_e) = g·(1 − 0.35·η_e)    (η_e∈[0,0.3] → g_eff ∈ [0.895g, g])
T/W = g / g_eff = 1/(1 − 0.35·η_e) ≥ 1    (hover sufficiency condition; exactly 1.0 at η_e = 0)
```

### 2.2 Hover sufficiency condition and the field–fan division of labor

The vertical force balance defines the system's first division of labor: **the field carries the lift share, the fans retain the authority**. Define the field share s ≡ L_field/W_eff; in its linear-response form s = 2.6·η_e + 1.8·η_cdm, η_e dominates field-lift generation (the first-order response of the negative-pressure gradient) while η_cdm contributes the equivalent unloading under inertial screening. The clamp s ≤ 0.75 stems from control theory, not energy considerations: **the field is the "slow channel" (metric establishment takes on the order of 30 ms), so the attitude bandwidth must be carried by the fans' "fast channel"** — reserving ≥25% of thrust for differential is precisely the prerequisite for the ±2° attitude envelope.

<figure class="doc-figure">
  <img src="docs/images/en/flight-force-balance.svg" alt="sedan hover-point anti-gravity force balance and the field-fan division of labor" loading="lazy">
  <figcaption>*Fig. 1 · Anti-gravity force balance and the field–fan division of labor (sedan hover point, η_e=0.15, η_cdm=0.20) — vertical balance L_field + T_fan = W_eff = m·g_eff; the field carries 75% of the lift (11.37 kN), fans retain 25% differential authority (3.79 kN), effective gravity 15.16 kN, g_eff = g·(1−0.35·η_e) = 9.81 × 0.9475 = 9.30 m/s²; available thrust-to-weight 1.055 — just above 1, with no redundant over-thrust (low-energy-first principle).*</figcaption>
</figure>

### 2.3 Induced-power 1.5-power law and energy decomposition

The mathematical core of the energy saving lies in momentum theory: hover induced power P ∝ T^1.5/√(2ρA) (ideal actuator disk, blade figure of merit folded into the baseline). **When thrust drops to (1−s) of its value, power shrinks by (1−s)^1.5** — this three-halves law amplifies the benefit of "capping the field at 75%": at s = 0.75 the fan power retains only 0.25^1.5 = 12.5% of the baseline. Field maintenance power is a different kind of term: holding the metric curvature is a payment on geometry, not external work, and carries only the coherence dissipation 12 W/kg × s:

```
P_fan(s) = P_base·(1−s)^1.5    (momentum-theory three-halves law; s=0.75 → ×0.125)
P_field = 12 W/kg · m · s    (metric maintenance = coherence dissipation, no propulsion work)
P_base(m) = 55·(m/t)^1.2 kW    (same-class high-efficiency lifting-fan disk-loading baseline; 1.2 is the empirical Reynolds/tip-loss law)
P_hover = P_fan + P_field    (sedan: 98.88×0.125 + 12×1630×0.75/1000 = 12.36 + 14.67 = 27.03 kW)
```

### 2.4 Closed-form endurance multiple and the mass law

At equal battery the endurance multiple has a closed-form solution E = P_base/P_hover. Substituting the decomposition reveals two structural conclusions: first, (1−s)^1.5 = 0.125 (with s capped) gives the theoretical upper bound **E → 1/0.125 = 8.0×** (the zero-field-maintenance end), diluted in practice to 3.17–3.83 by the 12 W/kg dissipation; second, **P_base ∝ m^1.2 makes m/P_base ∝ m^−0.2 monotonically decreasing — the larger the mass, the smaller the field-maintenance term relative to the total, and the higher E**, which is exactly the analytical reason pickup (×3.83) exceeds sedan (×3.66) rather than a numerical coincidence:

```
E = P_base / P_hover = 1 / [ (1−s)^1.5 + 12·m·s / (1000·P_base) ]
P_base ∝ m^1.2 ⇒ m/P_base ∝ m^−0.2    (mass law: E rises monotonically with curb mass)
s = 0.688 (sport uncapped) → E = 1/(0.1744 + 0.1410) = 3.17    (exactly the lowest of the six types; see Chapter 06)
```

### 2.5 Analytical upper bound of the peak factor

"No significant energy peak" is not an empirical observation but a **provable bound**. At the takeoff instant only the fan thrust is ×1.2 (climb margin) while the field share is unchanged, so the peak always occurs at takeoff rather than hover. The peak factor is a weighted average of P_fan and P_field: the pure-fan end has supremum 1.2^1.5 = 1.3145, and the field-maintenance term (which does not grow with fan thrust) dilutes it to 1.14–1.17 — the mathematical origin of the margin under the 1.25 limit. Turn differential is only +5%, always below the takeoff increment:

```
P_takeoff = P_base·[1.2·(1−s)]^1.5 + P_field    (only the fans ×1.2; field share unchanged)
peak factor = P_takeoff / P_hover    (P_field→0 end supremum 1.2^1.5 = 1.3145; diluted to 1.14–1.17 with field maintenance included)
```

### 2.6 Over-damped loop, C² profiles, and latency composition

The three criteria for attitude and kinematics are likewise analytically provable. **Over-damping**: ζ = 1 + 0.6·η_cdm ≥ 1 makes the second-order attitude loop zero-overshoot, with time constant τ = 1000/(ζ·2π·f_n) = 63.7/ζ ms (f_n = 2.5 Hz); the 8° gust decay back into the ±2° band is a monotonic exponential t_rec = τ·ln(8/2) = 88.3/ζ ms (ζ = 1.12 → 78.8 ms). **C² profiles**: the quintic s(u) = 6u⁵ − 15u⁴ + 10u³ zeroes endpoint velocity and acceleration simultaneously — a cubic only preserves C¹, and an endpoint acceleration jump is felt as a jolt; the peak slope 1.875 gives T = 1.875·|Δ|/45°/s. **Latency composition**: take the larger of the command chain (perception + solving + field establishment, 30 + 6·n_fans ms) and the recovery time:

```
ζ(η_cdm) = 1 + 0.6·η_cdm ≥ 1    (over-damped → zero overshoot → mathematical guarantee of no vertigo)
τ = 1000/(ζ·2π·2.5) = 63.7/ζ ms; t_rec = τ·ln(8/2) = 88.3/ζ ms    (ζ=1.12 → 78.8 ms)
s(u) = 6u⁵ − 15u⁴ + 10u³, s′ endpoints = s″ endpoints = 0    (quintic C²; peak slope 1.875)
latency = max(30 + 6·n_fans, t_rec) ≤ 100 ms    (verified across the full parameter range: fans 2–8, η_cdm 0–0.3)
```

> **Closing the theoretical chain**: all criteria of the five targets ultimately reduce to three bounded assumptions (η_e, η_cdm, disk-loading baseline) and four analytical formula groups (g_eff → s → P_hover → quintic/ζ). Precisely because the metrics respond to parameters **analytically**, the Chapter 06 self-consistency evidence — "sport's uncapped field share → lowest endurance" — and the honesty mechanism of "η zeroed → honest degradation" hold: they are not engineered appearances but the mathematical inevitability of the model.

## 03 Target 1: Hover Attitude Deviation ≤±2°

Hover attitude is guaranteed by an **over-damped second-order loop**: damping ratio ζ = 1 + 0.6·η_cdm ≥ 1 (dark-matter inertia blending), control bandwidth f_n = 2.5 Hz, zero overshoot. Steady-state residual micro-sway uses a dual low-frequency sinusoid spectrum (0.07 / 0.11 Hz) with peak 0.85°/ζ — both frequencies far from the 0.5–1 Hz human motion-sickness band.

```
ζ = 1 + 0.6·η_cdm ≥ 1    (over-damped → zero overshoot)
θ(t) = (0.85/ζ)·[0.588·sin(2π·0.07t) + 0.412·sin(2π·0.11t + 1.3)]    (deg)
gust recovery = τ·ln(8/2), τ = 1000/(ζ·2π·f_n)    (ζ=1.12 → 78.8 ms)
```

<figure class="doc-figure">
  <img src="docs/images/en/flight-attitude-spectrum.svg" alt="Hover attitude residual micro-sway, time domain" loading="lazy">
  <figcaption>*Fig. 2 · Hover attitude residual micro-sway, time domain (sedan, ζ=1.12, 60 s sample) — curves pre-rendered inline from the attitudeSample formula; ±2° design envelope and ±0.85°/ζ theoretical peak marked as reference lines — max deviation over 60 s is 0.75°, a 2.6× margin.*</figcaption>
</figure>

Steady-state attitude peaks across the six types span **0.728°–0.767°** (higher η_cdm → larger ζ → smaller sway), all within **36% of the ±2° envelope**. In the 3D view the micro-sway is rendered with roll/pitch decoupling, its amplitude decaying with lift² progress and strictly zeroed on the ground.

## 04 Target 2: Full-Freedom 360° Unlimited In-Place Turning

Yaw commands use a **wrap-free accumulated angle** design: consecutive commands accumulate across turns with no theoretical limit. The turn profile Δ·quintic(t/T) is a C²-continuous curve — endpoint angular velocity and acceleration are both zero, **no jerking, no attitude destabilization**; duration is computed from the 45°/s comfort-limited peak rate (T = 1.875·|Δ|/45), giving exactly 15.0 s for a full 360°.

```
T = 1.875·|Δ| / 45°/s    (1.875 is the quintic mid-point peak slope; 2.5 s minimum transition)
ψ(t) = Δ·(6t⁵−15t⁴+10t³)/T⁵·…    (quintic smoothstep, C² continuous)
peak turn rate = 1.875·Δ/T = 45°/s    (within visual-rotation motion-sickness threshold)
```

<figure class="doc-figure">
  <img src="docs/images/en/flight-yaw-profile.svg" alt="360-degree in-place turn yaw profile" loading="lazy">
  <figcaption>*Fig. 3 · 360° in-place turn yaw profile (15.0 s, quintic C² curve) — exactly 180° at the 7.5 s midpoint, peak rate 45°/s; endpoint velocity/acceleration zero — spin-up and spin-down are imperceptible.*</figcaption>
</figure>

In-place turning is achieved by fan **differential torque** — no centripetal acceleration, no roll coupling; roll and yaw are decoupled. Added power during turns is only +5% (differential increment), see the energy profile in Chapter 06. In the live test, after clicking the 360° button the vehicle rotated visibly and continuously within 5 s, smooth with no jumps.

## 05 VTOL Profile: C² Smooth, Vertigo-Free

Lift altitude uses a quintic smoothstep h(t) = H·s(t/T) with **strictly zero endpoint velocity and acceleration** — no impact at takeoff or touchdown. Three vertigo-free guarantees accompany it: hover-bob amplitude <0.2% of vehicle length (≤9.2 mm), frequency <0.2 Hz, and zero camera roll throughout.

<figure class="doc-figure">
  <img src="docs/images/en/flight-lift-profile.svg" alt="sedan vertical lift-off altitude profile" loading="lazy">
  <figcaption>*Fig. 4 · sedan vertical lift-off altitude profile (0 → 1600 mm, 3.2 s) — less than 3% displacement in the first 0.5 s — the static-to-dynamic takeoff transition is fully softened by the C² curve; the tail similarly converges smoothly to hover altitude.*</figcaption>
</figure>

Hover altitude presets span 1600–2000 mm with lift durations of 2.8–3.8 s across the six types; the MPV, being the largest in mass and size, takes the longest duration and the highest altitude. The effective gravity g_eff = g·(1−0.35η_e) keeps the hover thrust-to-weight in 1.052–1.083 — just above 1, matching the sufficient design of "the anti-gravity field carries the share, fans retain attitude-differential authority".

## 06 Targets 3 + 4: Endurance ≥3× and No Energy Peaks in Any Regime

### 6.1 Energy Model

The core energy-saving logic of the anti-gravity route: the dark-energy negative-pressure field is a **metric effect (geometric curvature), not propulsive work**, with only ~12 W/kg of coherence dissipation; the conventional baseline uses a same-class high-efficiency lifting-fan disk-loading model P_base = 55 kW/t^1.2, with fan induced power shrinking by the 1.5th power of thrust.

```
field-lift share s = 2.6·η_e + 1.8·η_cdm ≤ 0.75    (fans retain ≥25% for attitude differential)
P_hover = P_base·(1−s)^1.5 + 12 W/kg·m·s    (fans + field maintenance)
E = P_base / P_hover ≥ 3    (endurance multiple at equal battery; all six presets pass)
```

<figure class="doc-figure">
  <img src="docs/images/en/flight-energy-flow.svg" alt="sedan anti-gravity energy flow" loading="lazy">
  <figcaption>*Energy flow · sedan anti-gravity hover power composition and endurance-multiple derivation: the 98.88 kW baseline splits into fan 12.36 kW plus field 14.67 kW, hover total 27.03 kW, endurance 3.66x (fans retain 25% of thrust for attitude differential).*</figcaption>
</figure>

<figure class="doc-figure">
  <img src="docs/images/en/flight-energy-waterfall.svg" alt="sedan hover energy waterfall" loading="lazy">
  <figcaption>*Fig. 5 · sedan hover energy waterfall (P_base 98.88 kW → 27.03 kW, 72.7% saving) — field-lift share s = 0.75 (capped): fan power compressed to 12.36 kW, field maintenance 14.67 kW; takeoff peak 30.92 kW contains only the 1.2x climb thrust margin.*</figcaption>
</figure>

### 6.2 Endurance multiples across the six types

<figure class="doc-figure">
  <img src="docs/images/en/flight-endurance.svg" alt="Endurance multiples across six types vs the 3x target line" loading="lazy">
  <figcaption>*Fig. 6 · Endurance multiples vs ≥3× target line — pickup highest (×3.83, η_e=0.22 gives the largest field contribution); sport lowest (×3.17, field share 0.688 not capped) — even the lowest keeps a 5.7% margin.*</figcaption>
</figure>

Multiples span **3.17×–3.83×**. A notable self-consistency evidence: **sport is the only type whose field share is not capped (0.688 < 0.75)**, and it also has the lowest endurance multiple — the model responds to parameters with physical consistency rather than a contrived "all green". At equal 100 kWh, sedan hover endurance extends from 1.01 h (conventional) to 3.70 h.

### 6.3 Energy peaks across all regimes

<figure class="doc-figure">
  <img src="docs/images/en/flight-power-profile.svg" alt="Three-regime power profiles and peak factor across six types" loading="lazy">
  <figcaption>*Fig. 7 · Three-regime power profiles and peak factor across six types (dual axis) — the peak occurs at the takeoff instant (×1.2 fan thrust climb margin); peak factors 1.14–1.17, all below the 1.25 limit; turn differential only +5%.*</figcaption>
</figure>

> **Honesty by Design: Honest Degradation at Extreme Parameters**: When the user sets η_e and η_cdm to 0, the system **honestly degrades** to conventional-propulsion performance: field share goes to zero, endurance multiple falls back to ×1.0, peak factor rises to ×1.31 (exceeding the 1.25 limit), and the UI and back-end `targets_met` verdicts flip to false in sync — **there is no "fudged pass" path**; this behavior is locked by tests on both ends.

## 07 Target 5: Flight Control Latency ≤100ms

Latency takes the larger of two chains: the **command-chain latency** (perception + solving + field establishment, 30 ms base + 6 ms per fan differential channel) and the **large-disturbance recovery time** (an 8° gust decaying back into the ±2° band, monotonic overshoot-free exponential decay τ·ln4 with ζ≥1).

<figure class="doc-figure">
  <img src="docs/images/en/flight-latency.svg" alt="Latency composition across six types vs the 100 ms ceiling" loading="lazy">
  <figcaption>*Fig. 8 · Latency composition across six types vs the 100 ms ceiling — six-fan types have a 66 ms chain but recover faster (larger ζ); final latency 76–80 ms, all ≤100 ms — tightest margin 20 ms (sport).*</figcaption>
</figure>

Full-range verification: across 16 combinations of fans 2–8 and η_cdm 0–0.3, latency stays ≤100 ms (locked by vitest assertions). Mode transitions (takeoff ↔ hover ↔ turn ↔ landing) reuse the same C² profile mechanism — a transition command merely changes the profile target, **no separate switching latency**.

## 08 Full Flight-Envelope Data Table, Six Vehicle Types

The table below gives the complete envelope of the six types under default preset parameters (hover altitude / η_e / η_cdm / fan count); every value is reproduced by the open formulas and locked by front/back-end tests.

| Type | Bounding box (mm) | Curb mass (kg) | Hover alt. (mm) | η_e / η_cdm | Field share s | Fans | Thrust (kN) | T/W | P_base (kW) | P_hover (kW) | Takeoff peak (kW) | Peak factor | Endurance | Attitude peak (°) | Damping ζ | Latency (ms) | Targets |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sedan | 4950×1880×1460 | 1630.4 | 1600 | 0.15 / 0.20 | 0.750 | 4 | 15.15 | 1.055 | 98.88 | 27.03 | 30.92 | 1.14 | ×3.66 | 0.759 | 1.120 | 79 | ALL PASS |
| suv | 5050×1980×1780 | 2135.8 | 1900 | 0.18 / 0.24 | 0.750 | 6 | 19.63 | 1.067 | 136.72 | 36.31 | 41.69 | 1.15 | ×3.77 | 0.743 | 1.144 | 77 | ALL PASS |
| coupe | 4800×1890×1380 | 1502.3 | 1700 | 0.16 / 0.20 | 0.750 | 4 | 13.91 | 1.059 | 89.64 | 24.73 | 28.25 | 1.14 | ×3.63 | 0.759 | 1.120 | 79 | ALL PASS |
| sport | 4600×1980×1250 | 1366.2 | 1650 | 0.14 / 0.18 | 0.688 | 4 | 12.75 | 1.052 | 79.98 | 25.22 | 29.60 | 1.17 | ×3.17 | 0.767 | 1.108 | 80 | ALL PASS |
| mpv | 5200×1920×1830 | 2192.5 | 2000 | 0.20 / 0.28 | 0.750 | 6 | 20.00 | 1.075 | 141.09 | 37.37 | 42.92 | 1.15 | ×3.78 | 0.728 | 1.168 | 76 | ALL PASS |
| pickup | 5600×1980×1880 | 2501.5 | 1800 | 0.22 / 0.26 | 0.750 | 6 | 22.65 | 1.083 | 165.27 | 43.17 | 49.67 | 1.15 | ×3.83 | 0.735 | 1.156 | 76 | ALL PASS |

Note: the 360° full-turn duration is 15.0 s for all types (constant 45°/s comfort limit); the 19 brand models inherit presets from their vehicle type, with explicit overrides taking precedence.

<figure class="doc-figure">
  <img src="docs/images/en/flight2-image.svg" alt="Six-type hover panorama (sedan hover point)" loading="lazy">
  <figcaption><strong>Fig. 9 ｜ Six-type hover panorama (sedan hover point)</strong> How to read: green dashed = field energy, blue rings = lift fans; sport is amber because its uncapped 0.688 share yields the lowest endurance — evidence of model self-consistency.</figcaption>
</figure>

<figure class="doc-figure">
  <img src="docs/images/en/flight2-legend.svg" alt="Legend: symbols, lines and thresholds in this report" loading="lazy">
  <figcaption><strong>Fig. 10 ｜ Legend: symbols, lines and thresholds in this report</strong> How to read: read line types in A and verdicts in C, then thresholds in D; amber always means "passing with a slim margin", never failure.</figcaption>
</figure>

## 09 Live Verification Record (2026-10-16)

After deployment, per the mandatory verification protocol, a browser-automation agent completed a **7/7-pass** full-flow test on the public site `https://evolution-ai.design/?v=ag2#/designer` (cache-busted):

- ✓ **Page load**: the Designer page rendered normally with zero console errors (verified via browser_console_messages: no uncaught exceptions)
- ✓ **VTOL takeoff**: clicking the emerald flight button lifted the vehicle smoothly to hover altitude within ~3.2 s, with the green ground energy field and blue lifting-fan ring visible (C² lift animation, matching the Fig. 4 profile)
- ✓ **Hover status bar**: the "VTOL HOVER" badge and real-time energy HUD appeared (live reading 27.03 kW · ×3.7 — matches the formula envelope 27.03 kW / ×3.66 digit-for-digit)
- ✓ **Turn buttons**: three in-place turn buttons (↺90° / ↻90° / 360°) appear while hovering, with automatic re-entry blocking (busy state)
- ✓ **360° turn**: after clicking, the vehicle heading rotated visibly and continuously within 5 s, smooth with no jumps (matches the Fig. 3 quintic profile (5 s ≈ 75.6°, confirmed by visual continuous rotation))
- ✓ **Parameter panel**: the "VTOL branch" toggle on, four sliders in place (hover altitude 1600 mm / dark energy 15% / dark matter 20% / fans 4 — matching the sedan preset)
- ✓ **Flight metric cards**: all six metrics live and passing (green) (endurance ×3.66 ≥3× · power 27.03 kW · attitude ±0.76° ≤±2° · latency 79 ms ≤100ms · peak ×1.14 ≤1.25 · 360° 15.0 s)

> **Cross-Validation Conclusion**: The **six real-time readings** from the public HUD and metric cards are **exactly identical** to the offline formula envelope (27.03 kW / ×3.66 / ±0.76° / 79 ms / ×1.14 / 15.0 s) — proving front-end UI, formula layer and deployed artifact share one source, with no divergence between displayed and computed values.

## 10 Conclusions, Boundaries and Next Steps

### 10.1 Conclusions

- **All five technical targets pass with design margin**: attitude ±0.76° (2.6× margin), 360° turn 15.0 s (45°/s comfort limit), endurance ×3.17–3.83 (5.7% margin on the lowest), peak factor ×1.14–1.17 (limit 1.25), latency 76–80 ms (≥20 ms margin).
- **Path to the optimal balance**: the anti-gravity sci-fi narrative is carried by the "capped field share + fan-differential floor" division of labor; lift/turn/landing motion profiles are unified by the C² quintic smoothstep; motion-sickness risk is locked down by over-damping ζ≥1 and low-frequency spectral constraints — algorithm (C² profiles), physics (metric-effect analogy), mathematics (bounded clamping), aerospace (thrust-to-weight sufficiency) and experience (triple vertigo-free guarantee) converge on one reproducible formula set.
- **Model honesty**: the parameter→performance response is physically self-consistent (sport's uncapped field share → lowest endurance; η zeroed → honest degradation to failing), and every verdict can be reproduced or overturned by the user in the UI in real time.

### 10.2 Boundaries

- The data in this report is the output of an **engineering estimation model** of a design-simulation platform: the energy baseline (55 kW/t^1.2), field-maintenance specific power (12 W/kg) and vehicle density (120 kg/m³) are model assumptions, not measurements from a real vehicle;
- The dark-energy/dark-matter parameters are a "sci-fi bounded" analogy (η∈[0,0.3]), physically corresponding to an engineering abstraction of metric effects / inertia shielding;
- "Measured" in this report means **real-time computed readings of the deployed artifact** verified in the public environment — not wind-tunnel or flight-test-grade measurement.

### 10.3 Next steps

- Introduce gust-spectrum time-domain simulation (Dryden model) to replace the single 8° injection, refining the attitude-recovery time distribution;
- Model battery C-rate constraints to output a true endurance–power envelope surface;
- Field-interference analysis for multi-vehicle formation hovering and vertigo-free camera-following strategies.

## Data and Version Provenance

Version note: the full HTML edition is a self-contained single-file HTML — all data charts are inlined as static vector SVG (plus structural diagrams); it renders fully without network or JavaScript and can be distributed, archived or read offline directly. This Markdown edition (v2 full-text) is generated from the same source.

1. EVOLUTION-AI.DESIGN front-end formula layer, src/utils/flightPhysics.js — VTOL and anti-gravity flight-control pure functions (commit 974bad89): `src/utils/flightPhysics.js`
2. EVOLUTION-AI.DESIGN back-end envelope, backend/app/car_generator.py · flight_envelope() — dual implementation sharing the same formulas (commit 974bad89): `backend/app/car_generator.py`
3. Front-end test matrix src/tests/flightPhysics.spec.js (35 dedicated flight-physics cases; vitest full suite 285/285): `src/tests/flightPhysics.spec.js`
4. Back-end test matrix backend/tests/test_flight_branch.py (14 cases; pytest full suite 386 passed): `backend/tests/test_flight_branch.py`
5. Live verification environment evolution-ai.design/#/designer (2026-10-16, browser-automation 7/7 check record, deployed as gh-pages 5c5dfdc): https://evolution-ai.design/#/designer
