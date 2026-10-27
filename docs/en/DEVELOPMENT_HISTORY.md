# Development History of EVOLUTION-AI.DESIGN

**Period covered**: 2026-08-18 → 2026-10-25
**Version**: v1.0 (2026-10-25)
**Nature**: engineering chronicle and decision log — not a product manual

---

## Executive Summary

In roughly 68 days EVOLUTION-AI.DESIGN grew from a project skeleton into a platform combining parametric car styling, Class-A surface algorithms and an anti-gravity flight branch. Five threads run through it:

1. **Backend & algorithm foundation** (09-27): auth, LLM proxy, training backend, CAD import, Bayesian optimisation, G0/G1/G2 surface criteria.
2. **Platform engineering & compliance** (09-29 → 10-11): RBAC, community, notifications, impact evidence, PostgreSQL/Docker, CSP, SEO, CNAME, JD Cloud deployment runbook.
3. **Account system retired → guest-only mode** (10-11): an explicit **requirement pivot** — WeChat login, Account and Admin all left the public frontend.
4. **Single-source refactor of 2D/3D styling** (10-07 → 10-25, the longest and densest thread): NURBS continuous body → unified proportion semantics → pure-function greenhouse glazing → wheel-arch envelope and fitment → door/side-window coupling → bevel and door-aperture cleanup.
5. **Capability expansion in parallel with documentation** (10-16 anti-gravity flight, 10-22 brand DNA, 10-23 → 10-25 five-graphics rule, bilingual papers, methodology book).

As of 2026-10-25 the mainline rests at `b42e51e4`, published to gh-pages as `9fd5f04a`, with public artefacts MD5-identical to the local build. **The only open issue** is the user report "the door opening is still obstructed after opening the door": the geometric occluders were found and fixed; the residual perceptual issue (the swung door panel itself plus an interior-free dark cavity) still awaits a decision.

---

## Evidence & Scope

| Source | Used for | Reliability |
| --- | --- | --- |
| `main` git log (111 commits, `--date=short`) | dates, change scope, intent | primary, verifiable |
| `gh-pages` log (18 commits) | release cadence, source↔release mapping | primary |
| Project memory (constraints / conventions / lessons) | decision rationale, hard constraints, pitfalls | primary, distilled from past sessions |
| Session memory `topics.md` (20260920 → 20261025) | originating context of requirements | primary (summary level) |
| This session's context (geometry remediation) | 10-24/10-25 aperture details | primary, with measurements |
| Public MD5 verification (run this session) | release closure | primary, measured |

**Not included**: implementation details not present in the sources above, plans that never happened, and commits that exist only in the other repository (SISA backend).

---

## Phase 0 — Engineering Foundation (2026-08-18)

- `dd3e689a` completed project scaffolding, hardened `.gitignore`, committed the **19-brand car-image test baseline**.
  - Decision: legislate first (.gitignore + test baseline), then build features — runtime artefacts must never pollute the repo.
- `58ec8694` packaged E2E regression as a reusable CLI tool and updated the runbook.
  - Decision: **regression must be re-runnable by any session in one command**; this is the root of the later "single source + full regression" discipline.

> Gap: no commits between 08-19 and 09-26. The requirements discussed in that window (the 2026-09-20 session mentions a RHINO algorithm plugin to rapidly rescale body proportions) never reached code.

---

## Phase 1 — Backend & Algorithm Foundation (2026-09-27)

A single-day foundation batch that marks the project's watershed:

- `43848a01` user auth, WeChat login, LLM proxy, training backend, deployment engineering.
- `7a8a7c3a` / `f3df5905` full-vehicle CAD import tests (STL/STEP/CATPart/Wire), with CATPart fallback assertions aligned to the real copy (`proprietary / not supported / Fallback`).
- `1b9f0310` fixed two web-side 500s; production **fail-fast** when `SECRET_KEY` is the development default.
- `3196eabf` Bayesian optimisation container: GP surrogate + EI/UCB acquisition, wired to training-sample export.
- `a4673cea` / `12790533` fixed self-check contract drift and the `run_full_pipeline` panel-mesh-from-box-body defect.
- `ff351db3` / `b24d4e46` full retrospective: README rewrite plus architecture, product, API and paper documents; knowledge base aligned to v1.2 source facts.
- `1c2c1e8c` new `doc-code-audit` skill (one-click docs↔source verification).
- `90d9ae17` Help Center 3D knowledge system + bilingual document library + login→training→review chain.

**Decision essence**: documentation is a deliverable, not a by-product; introducing `doc-code-audit` means "the docs are wrong" is now managed as a defect.

---

## Phase 2 — Permissions, Community and "Evidence-based" Features (2026-09-29 → 10-03)

- `ddc5043b` four-tier RBAC, admin console, login audit.
- `94f13289` AI creative tools (style transfer / sketch-to-3D / dream design) wired to real generation endpoints (previously placeholders).
- `3034b1f6` login state moved to **memory only**; all auth persistence removed.
- `a0bd5235` notification centre; `e33cb3e7` community page plus a superadmin-only impact-evidence panel.
- `5106f049` (10-01) verifiable impact evidence system.
- `fef68f19` (10-02) AI design-intent engine: one natural-language sentence → a full-vehicle proposal.
- `f9d02b78` curvature/G2 continuity extracted into a standalone component (wired into the Quality page on 10-03 by `dca5c975`).
- `856c2651` multi-tool collaboration protocol v1 plus launcher domain compatibility, single-instance guard and owner markers.
- `72bcf6cc` LLM key isolation: per-platform credentials + key registry (registry holds no plaintext).

**Decision essence**:
1. "Verifiable" became a product principle — every impact/performance claim must trace to evidence (later applied to the 10-11 audit report and the 10-16 flight test report).
2. Several AI tools editing one repo is the norm, so a **collaboration protocol** is established before parallelism is allowed.

---

## Phase 3 — Security, Deployment and Retiring the Account System (2026-09-29 → 10-11)

- 09-29 `a35000de` Phase 5a hardening: API rate limiting, production `DEBUG` fail-fast, `.env.example`.
- 09-29 `0b0f971c` Phase 5a infrastructure: **PostgreSQL + Alembic**, Docker productionisation (nginx / TLS / non-root uid 1000).
- 10-01 `274592ef` / `d5ce5092` CNAME and `.nojekyll` added to `public/` — the custom domain and `_`-prefixed assets no longer vanish on deploy.
- 10-11 `c45d9ccc` **Admin moved out of the public frontend**, hosted independently by FastAPI at `/admin` behind a login gate.
- 10-11 `864421d5` CSP `unsafe-eval` released only for the `/admin` scope (fixing the white screen caused by blocked vue-i18n compilation).
- 10-11 `6040bac4` **account system retired**: full-feature guest mode; nav item `Account` → `Contact` (Icemtrainer@hotmail.com).
- 10-11 `a40226e6` JD Cloud 2C4G one-click deployment checklist and server bootstrap (2 GB swap against OOM, same-origin `/api` reverse proxy).
- 10-15 `456427f5` / `424936a0` SEO baseline (robots / sitemap / meta) and favicon (brand SVG + multi-size ICO).

**Pivot record (important)**: WeChat QR login → retired. The causal chain is explicit: cpolar's free tier issues a new random domain on every restart, so the WeChat test-account "web authorisation domain" no longer matches the real callback (error 10003) and cannot self-heal locally; additionally, production with WeChat QR login must sit on a compliant mainland server. The choice was to **take the whole account system offline** rather than keep patching it. That decision also pulled Admin out of the public build.

---

## Phase 4 — Knowledge Base and Bilingual Documentation (2026-09-27 → 10-23)

- 09-27 `90d9ae17` bilingual documentation skeleton; 09-29 `a2cd4a2d` 16 professional SVGs covering 26 documents; `779c9159` lightbox zoom + 42 bilingual "caption + reading guide" entries; `9bfac7fc` 16 illustrations localised to English.
- 09-29 `35ef47da` site-wide mixed-language cleanup, establishing "**one language per content block**, proper nouns and technical abbreviations exempt".
- 10-11 `2a87fcd9` / `76ebde0d` standardised audit/test-report visualisation (9 SVGs: bar/donut/bar-horizontal/flow/architecture/topology/timeline) with figcaption language and typography rules.
- 10-22 `d84d68b5` knowledge-document system upgrade and full audit alignment.
- 10-23 `79ed3b66` **five-graphics rule** applied everywhere: 16 Chinese + 15 English documents, each covering image / chart / diagram / legend / figure.
- 10-24 `d1190a2a` academic paper Chinese edition added (Chinese body + English companion).
- 10-25 `12af61bc` new *AI-Native Software Development Methodology* book (18 chapters + 4 appendices, bilingual, authored as 量子剑客).

**Decision essence**: the documentation system is a hard deliverable — key metrics, core claims and hierarchy must become standard charts of the right type, with 100% accurate data.

---

## Phase 5 — Single-Source Refactor of 2D/3D Styling (2026-10-07 → 10-25)

The longest, most reworked and most constrained thread — and the arena of this session.

### 5.1 NURBS continuous body and full closure (10-07 → 10-10)

- `ed26e0a4` constrained MPV rear window/rails; added pickup-specific topology.
- `bac62b71` frontend sliders now **actually drive geometry**, returning measured surface quality (previously decoupled).
- `ea41ce3b` NURBS continuous body rebuild (phase 2) plus rendering fixes.
- `6df66e06` paint reflection tuning; wheel-arch eyebrow fade to remove the step.
- `4ab70371` full-vehicle closure: all 7 opening classes sealed; part dimensions, fitment and topology aligned.
- `7c128f4c` streamlined form: plan-view taper + fastback rounding, removing the "box" feel.

### 5.2 Unified proportion semantics and 2D/3D single source (10-11)

- `1bfb91ef` proportion semantics corrected: **ground-to-roof height = H**, 2D/3D share `LINE_RATIOS`, pickup-specific topology.
  - Rationale recorded in memory: the old metric used kernel shoulder/span ratios, putting the belt line 150–190 mm below the real car — oversized greenhouse, undersized hood.
- `1e184b83` 3D side outline G1 fillets + 2D/3D outline alignment + view-orientation fix.
- `1789014c` 2D fixes: belt line lowered, glazing joined to body, annotations normalised.
- `eeced937` Cayenne 2D pipeline rebuild and SISA shared-render integration; `292304ae` removed the SISA Ref badge and guide overlays from the 2D RENDER panel.

### 5.3 Greenhouse topology and tumblehome (10-12 → 10-14)

- `548b4e87` 3D fallback path splits glass from body per the 2D greenhouse layout: windshield / side window / B-pillar / rear window get independent materials.
- `c2b65d4e` `carGlass.js` pure functions; `3a788352` side-glass tumblehome parameterised (sport 26° / coupe 24° / sedan 18° / suv 12° / mpv 10° / pickup 8°).
- `94cfe37d` `dloZAt` / `pillarPlacement` pure functions with tests; `2e704a51` `buildDloFrame` / `buildDloStrip` with 8 unit tests.
- `6d49d6ca` body greenhouse narrows in tandem with glass angle (A/B/C-pillar silhouettes and roof follow tilt/barrel).
- `e213d7df` / `775af17d` / `c57b9ff6` the three glass parameters wired through **Designer sliders → frontend 3D → backend NURBS**, with 19 brand-certified models backfilled by `car_type`.

**Decision essence**: every geometric computation becomes a zero-dependency pure function with unit tests, making "2D and 3D use the same formula" an assertable fact rather than a verbal promise.

### 5.4 Wheel-arch envelope, wheel houses and fitment criteria (10-21)

- `d26ab6d4` realistic wheel-arch envelope: `WHEEL_ENVELOPE` six-type table + `deriveWheelArch` (`ry = r + jounce + gapTop`, `rx = (r + c_steer + gapSide)/√(1−(jounce/ry)²)·(1+0.5·flatten)`; front axle includes full-lock sweep, rear axle uses `gapSide×0.8`).
- `5159e216` greenhouse glass topology: six models' glass parts fit the body's G1 fillets exactly (`ROOF_FILLETS` single source + `filletXAtY` root finding).
- `f6bea5cc` wheel-house interference fixed + missing parts completed: tyres tucked inside the sidewall (`deriveWheelFitment`), full-width dark arch liner, lamps/bumpers moved onto the outer surface, door handles added, 2D/3D approach/departure angles established.
  - Key finding: "missing part" reports must first be checked for **burial** — head/tail lamps and bumpers were originally inside the body solid, not unmodelled.
- `489d698d` 3D approach/departure expression changed from **solid deflector lips** to **amber construction lines** (the lip's lowest point hung at 0.4·gc, reading as a scraping skid plate).
- `9869eea1` wheel-house liner topology fix: circular tube → an embedded elliptical open shell matching the arch mouth (12 mm inset), eliminating 15 mm front/rear wall and 44 mm top intersections.

### 5.5 Door and side-window coupling (10-22 → 10-23)

- `0d4e2283` side windows split along door seams and **opening together with the doors**; seams / handles / B-pillar parameterised to real-car ranges.
- `fc16c3da` 2D engineering drawing gains glazing-seam annotations.
- `c17db990` the open state **cuts a real door aperture**, removing door-panel/sidewall geometric duplication; lift devices redistributed symmetrically about the centre.
- Hard constraint recorded: front and rear door glass must be parented to the corresponding hinge group, rotating co-axially and at the same angle as the panel; the open state must satisfy "real physical space, unique geometric object".

### 5.6 Realistic glazing and G1 fillets (10-24)

- `f0409161` coupe/sport two-door layout, dark low-reflection realistic glass (`envMapIntensity = 0`, no pale-blue mirroring), windshield/rear window wrapping the roof G1 fillets.
- `15ccf5b4` fixed windshield/rear-window whitening and the roof step crease (offset tapering to roof-flush).
- `d6636bc6` fixed glass sinking into the body: offset now adds the bevel expansion and stays equidistant along the whole run (`GLASS_GAP = BODY_BEVEL_SIZE + GLASS_SURFACE_GAP`).
- `98a4e59e` door-aperture inner walls re-classified as interior material, removing the full-width body-coloured slab.

### 5.7 Bevel size and door-aperture cleanup (10-24 → 10-25, this session)

The user raised the same class of defect twice, in two rounds.

**Round 1 — "redundant duplicate body faces and creases from mis-topology" (`353e68ce`)**

| Defect | Root cause | Fix |
| --- | --- | --- |
| "White duplicate face" on the roof | `bevelSize = 0.03` stepped the roof edge in by 25 mm, reading as an extra plate | `BODY_BEVEL_SIZE` 0.03 → **0.012** |
| Body 60 mm wider than specified | `depth = W` plus bevel extending `bevelThickness` at both Z ends | `bodyDepth = W − 2×bevel`, `bodyExtentZ = W/2` |
| Wheel-arch creases | 90° concave corner in `archNotch` makes the bevel miter self-intersect | 12 mm fillet (`Q` quadratic Bézier) giving tangent continuity |

Verification: `vitest` 15 files / **416 tests** green; multi-camera screenshots; public MD5 byte-identical to local `dist`; degenerate triangles cut from 28 (arch corners) to only the extreme bumper corners (not visible).

**Round 2 — "the door opening is still obstructed after opening the door" (`b42e51e4`)**

This round exposed a genuine regression left by round 1 and corrected several earlier misdiagnoses.

| Defect | Root cause | Fix |
| --- | --- | --- |
| Door-seam strips floating in the middle of the aperture once open | The six strips from `addSeam` were parented to the car group, not the hinge, so they never left with the door | Collected in `doorSeams`; `s.visible = doorProgress < 0.02` |
| Doors, seams, handles, mirrors and wheels all floating 12 mm outside the body | `deriveWheelFitment` still used the old `W/2 + bevel`, while the true half-width had become `W/2` | Function now takes the real `bodyHalfZ`; `Car3D` passes `bodyExtentZ` |

**Key methodological lessons (now in memory)**:

1. **`Page.navigate` to the same URL (including hash) does not reload an SPA** — page state (`visible`, materials) leaks across scripts, producing a false "aperture is clear" conclusion. Correct approach: navigate to `about:blank` first.
2. **`requestAnimationFrame` is throttled in background tabs** — the door animation stalls (`rotY` stuck at 0.02); `Page.bringToFront` is mandatory.
3. **A/B isolation is the only reliable way to judge "is there any extra geometry"** — only after hiding every door and still seeing a clean aperture could "the hole is clear" be asserted.
4. **Final measurement (public site)**: a ray through the aperture centre along Z reports **0 hits** (fully open); the only remaining coverage is the door panel itself, swung about the front hinge by ~70° (`rotY = 1.222`, default `door_open_angle = 70`), plus the door glass rotating with it.

---

## Phase 6 — Anti-Gravity Flight Branch (2026-10-16)

- `2c87cb02` smooth vertical take-off and landing (VTOL) branch: all models gain flight capability with a non-nauseating hover experience.
- `974bad89` full-stack anti-gravity flight control: 360° in-place yaw, attitude micro-sway, energy HUD, flight-performance cards.
- `9cc516c6` flight performance measurement report (bilingual) integrated into Help Center.
- `ce97bd25` dedicated chapter deriving the anti-gravity drive theory.

**Decision essence**: the flight profile is declared a **bounded engineering estimation model** (for platform metric consistency and design-space exploration, not an experimentally validated physical law), keeping sci-fi narrative out of engineering credibility. All formulas were cross-checked against `flightPhysics.js`.

---

## Phase 7 — Brand Styling DNA and Security Fence (2026-10-22)

- `a38de31f` brand DNA system and Phase 5a security fence: `brand_dna` loading, On-Brand judgement, 2D features; confidential data excluded via `.gitignore`, only `demo_public.json` kept.
- `427f8a0b` guest mode opened site-wide; Help knowledge base upgrade; 3D/2D styling fixes.
- `fbf25f2a` service skills and reference material: `launch-services` detached three-service skill (with a cloudflared fallback tunnel), RAG grounding demo tool, SISA 2D integration reference and verification report.

**Decision essence**: the brand DNA module is **fully isolated** from the SISA core algorithm layer (imports no SISA internals, only the standard library and numpy); confidential DNA is memory-only, never persisted, never committed.

---

## Decision Ledger

| # | Decision | Rationale at the time | Impact | Evidence |
| --- | --- | --- | --- | --- |
| D1 | Extract all geometry into pure functions (`carProfile` / `carGlass` / `flightPhysics`) | 2D, 3D and the backend must share one source or proportions drift | Contracts lockable by unit tests; no more eyeballing | `c2b65d4e` `94cfe37d` `2e704a51` |
| D2 | Proportion semantics changed to "ground-to-roof height = H" | Old metric put the belt line 150–190 mm low, greenhouse oversized | Six model silhouettes aligned with real cars | `1bfb91ef` |
| D3 | Glass offset uses fixed constants `BODY_BEVEL_SIZE + GLASS_SURFACE_GAP` | The old tapering offset sank glass into the body at the roof | No step at windshield / side window / roof junctions | `15ccf5b4` `d6636bc6` |
| D4 | Bevel 30 mm → 12 mm, with `depth = W − 2×bevel` | 30 mm bevel stepped the roof in 25 mm and widened the car 60 mm | Roof duplicate face gone; width exactly 1.88 m | `353e68ce` |
| D5 | 12 mm fillet on the wheel-arch concave corner | 90° concave bevel miter self-intersects | Arch creases gone | `353e68ce` |
| D6 | Open state cuts a real aperture instead of layering a panel | Panel/sidewall duplication violates "unique geometric object" | Aperture walls needed interior material | `c17db990` `98a4e59e` |
| D7 | Seam strips hide as the door opens | Strips were parented to the body, so they hung in mid-air | Floating strips gone (6/6 hidden, measured) | `b42e51e4` |
| D8 | `deriveWheelFitment` takes the real half-width | Using `W/2 + bevel` pushed doors and wheels 12 mm out | Panel inside face flush with the sidewall (0.940 measured) | `b42e51e4` |
| D9 | Account system retired; site-wide guest mode | WeChat auth domain drifted with cpolar's random domain; not locally fixable | Login/Account/Admin removed from public entries | `6040bac4` `c45d9ccc` |
| D10 | Admin built separately (`vite.admin.config.js`) and served by FastAPI | Admin code must not enter public artefacts | Public build contains no admin routes/code | `c45d9ccc` |
| D11 | Layout baselines drawn as lines in 3D, not solids | Solid deflector lips created a false lowest point and skid-plate look | Approach/departure angles became amber construction lines | `489d698d` |
| D12 | Flight capability declared a "bounded engineering estimation model" | Protect engineering credibility from sci-fi framing | Statement carried in reports and UI | `974bad89` `ce97bd25` |
| D13 | Release = local multi-camera verification → build → gh-pages → **public MD5 verification** | Browser ES-module and CDN caches make "looks unfixed" inevitable | "Fixed but unverified" becomes process-impossible | memory constraint + actual runs on 10-24/10-25 |

---

## Requirement Evolution and Pivots

1. **RHINO algorithm plugin (09-20) → self-built 2D/3D rendering**: the plugin stayed a concept; the delivered form is in-platform parametric styling plus a backend NURBS generation chain.
2. **WeChat login + account system (shipped 09-27) → guest-only (retired 10-11)**: compliance and maintenance cost outweighed benefit; the system was taken offline wholesale, with `Account` replaced by `Contact`.
3. **3D as "illustrative" → 3D must be point-for-point identical to 2D**: from 10-11, "2D/3D outlines 100% matched" became a hard constraint, which directly produced `LINE_RATIOS` / `deriveCarProfile` single-sourcing.
4. **Glass "binary mesh split" → spec mandates UV alphaMap decal + marching-squares 0.5 contour**: the mesh-split ceiling is a boundary that always runs along mesh edges (constant stair-stepping). Memory records this as a must-replace approach (note: code state was not re-verified this round).
5. **Open door "layered panel" → "cut a real hole with a single panel"**: the 10-23 pivot, which then drove 10-24 interior-wall materials and 10-25 seam/fitment fixes.
6. **Defect triage method pivoted**: from "guess from a screenshot" to "A/B isolation + ray intersection + measured hinge angle". That pivot is the most valuable output of 10-25.

---

## Verification and Delivery Discipline

- **Single source**: every geometric quantity has exactly one computation entry point (`LINE_RATIOS`, `WHEEL_ENVELOPE`, `ROOF_FILLETS`, `BODY_BEVEL_SIZE`, `shellHalfZAt`).
- **Test gates**: frontend 15 files / 416 tests; an earlier 10-11 record shows "341 + 142 regression"; the SISA backend once reached 773 passed with zero regression.
- **Multi-camera visual checks**: side, isometric, bumper 45°, oblique close-up — any anomaly triggers a revert-and-fix.
- **Release loop**: `npx vitest run` → `npm run build` → copy `dist` into an ASCII-path gh-pages worktree (`D:\ghp-deploy-tmp`) → push → **public `Get-FileHash -Algorithm MD5` byte comparison with local**.
- **Deployment propagation window**: after a push, `index.html` updates first while **newly hashed assets may still return 404 for a few minutes** (measured 2026-10-25: the same URL returned 200 on retry). Verification must therefore retry until every chunk referenced by `index.html` is retrievable — a 404 does not mean the artefact is missing.
- **Pre-push patent guard**: a hook scans unpushed commits and blocks those matching patent features; `EVOAI_ALLOW_PUSH=1` is an escape hatch only.
- **Known tool traps**: the dev server (5173) HMR / ES-module strong cache makes browser agents hit stale code — always re-verify with a **production build on a fresh preview port**.

---

## Current State (as of 2026-10-25)

| Item | State | Evidence |
| --- | --- | --- |
| `main` HEAD | `b42e51e4` "fix(door): seam strips floating after opening + doors/wheels 12 mm outside body" | git log |
| Release HEAD | `9fd5f04a` "deploy: door obstruction and door-body protrusion fixed (main b42e51e4)" | git log |
| Build artefacts | `index-BbAf-Bd5.js` (130,023 B), `Car3D-BgSfGzHc.js` (24,934 B), `flightPhysics-DrBn6TG_.js` (16,852 B) | `dist/assets` |
| Public verification | all three key chunks **MD5-identical** local vs public | measured this session |
| Aperture geometry | ray along Z through aperture centre: 0 hits (fully open); door panel `rotY = 1.222` (≈70°) | CDP measurement this session |
| Defect status | floating seam strips and 12 mm protrusion — fixed and released | `b42e51e4` |

---

## Open Issues and Next Steps

1. **"Still obstructed after opening the door" is not yet confirmed closed by the user.**
   - Proven: the aperture is fully open with no extra geometry; floating seam strips hidden; doors and wheels flush.
   - Remaining visible: the door panel swung ~70° about the front hinge and the door glass rotating with it (normal physical behaviour), plus the perception of a dark cavity because the cabin has no interior.
   - Three options awaiting a decision: (a) raise the default open angle (e.g. 70° → 82° for a smaller side-view projection); (b) add an inner trim face to the door panel; (c) model a minimal cabin interior (floor / seats / door cards) so the aperture reads as a cabin rather than a void.
2. **Glass colour separation via alphaMap**: the spec is settled (UV alphaMap + marching-squares 0.5 contour); whether the code has actually replaced the binary mesh split was not verified this round.
3. **SISA-side synchronisation backlog**: `car_body.build_closed_shell`, `feature_lines.build_wheel_arch`, `dimension_plan` arch radii still need a same-batch upgrade to match `carProfile.js`, otherwise cross-repo metrics drift again.
4. **Patent-guard substring false positives**: the guard matches substrings, so a protected two-character geometry keyword also matches longer ordinary comment words that contain it; currently avoided by rewording, but should be fixed with word-boundary matching (the specific keyword stays in the internal ticket, not in this repo).
5. **Account system disposal**: retired ≠ deleted; whether backend auth/WeChat code is kept and whether docs should be marked "offline" is undecided.

---

## Recorded Gaps (explicitly declared)

- **2026-08-19 → 2026-09-26 (~38 days) has no commits and no topics file**: the project's founding motive, the earliest prototype discussion and the early SISA kernel shape are absent from the available context.
- **2026-09-21 → 09-26 has session memory but no topic summaries**: that week's daily goals cannot be reconstructed.
- **Backend/SISA repository commits (e.g. `42a59a3` viewport maximise, `50ba708` SISA Phase 2 master-surface splitting, `a994821` wheel-arch envelope sync) exist only as lesson entries in memory**; this repository's git log cannot verify their dates or ordering.
- **The 10-24 and 10-25 aperture investigation**: intermediate conclusions from multiple CDP diagnostic scripts (some disproved, e.g. the false "aperture fully clear" reading) are preserved as lessons, but the scripts themselves were temporary and mostly not committed.
- To fill any of these gaps, please supply the corresponding session records or the backend repository's git log.
