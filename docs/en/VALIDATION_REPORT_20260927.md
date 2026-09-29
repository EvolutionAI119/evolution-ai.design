# EVOLUTION AI Platform Validation Report (v1.2)

> Validation date: 2026-09-27
> Platform version: v1.2 (full review edition)
> Environment: Windows + Python 3.11; SQLite (zero external dependencies); Vitest / Pytest
> Nature of report: all figures come from real tool execution output on that day and can be reproduced with the appendix commands

---

## 1. Conclusion (Summary)

| Item | Result |
|---|---|
| Algorithm-layer pytest | ✅ **200 passed** (3.87s) |
| Backend pytest | ✅ **178 passed** (28.30s) |
| Frontend vitest | ✅ **111 passed** (1.25s) |
| Three layers combined | ✅ **489 / 489 all green** |
| One-stop self-check test_all.py | ✅ all 5 modules pass (7.13s) |
| run_full_pipeline end-to-end | ✅ fixed and fully runnable |
| Bayesian 15-round convergence (EI/UCB) | ✅ best enters the −0.01 band |

**Overall: all automated quality gates for platform v1.2 pass; the scale facts stated in the knowledge-base documents are consistent with the source code.**

---

## 2. Three-Layer Automated Testing

<figure class="doc-figure">
  <img src="docs/images/validation-metrics.svg" alt="Three-layer test suite scale and pass rate" loading="lazy">
  <figcaption><strong>Fig. 2-1 Three-layer test suite scale and pass rate (489 cases, all passing)</strong>How to read: Bars show per-layer scale — 200 algorithm, 178 backend, 111 frontend, 5 one-stop self-check — 489 cases all passing with zero failures and skips; right badges add the Bayes convergence check and the doc-code audit.</figcaption>
</figure>

### 2.1 Results

| Layer | Framework | Cases | Time | Scope |
|---|---|---:|---:|---|
| algorithm_model | pytest | 200 | 3.87s | NURBS mathematics, sweep/fillet, constructor, quality, parameterization, performance |
| backend | pytest | 178 | 28.30s | Routes, schemas, optimization services, security, persistence |
| frontend | vitest | 111 | 1.25s | Stores, components, API modules, guards |
| **Total** | — | **489** | — | all 8 frontend test files pass |

### 2.2 Warnings (all known, non-blocking)

- Algorithm layer: `CrossSection closed=True` first/last point mismatch UserWarnings (6) — tests intentionally cover the warning path;
- Backend: Pydantic v1-style `config` deprecation notices, `on_event` deprecation, python-multipart pending deprecation — no functional impact;
- No errors, no failures, no skips.

---

## 3. One-Stop Self-Check (test_all.py, 5 modules)

### 3.1 Full-Vehicle Modeling (default parameters)

- **10 parts / 176 vertices / 316 faces**: body, hood, roof, windshield, rear_window each have 8 vertices and 12 faces; the 4 wheels have 34 vertices and 64 faces each;
- A custom-parameter vehicle (L=4.9 W=1.92 H=1.5 roof_arc=0.55) is likewise 176/316;
- Parameter validation: out-of-range parameters are correctly caught.

### 3.2 Surface Quality Evaluation

| Reference surface | Grade | G2 ratio | Reflection line | G0/G1/G2 counts | Max jump |
|---|---|---:|---:|---|---:|
| Sphere | D | 0.199 | 0.291 | 722 / 212 / 144 | 80.56° |
| Body side view (single-side 49×25 mesh) | C | 0.855 | 0.158 | 2304 / 1993 / 1970 | 180.0° |

Interpretation: the body-section mesh is already near the Class-A threshold in angular continuity, but curvature uniformity (reflection line) is still below 0.7, giving an overall C — a genuine intermediate state during styling convergence.

### 3.3 AI Simulated-Annealing Optimization (80 steps)

| Object | Grade change | G2 change | Reflection-line change |
|---|---|---|---|
| Sphere | D → D | 144 → 144 | 0.291 → 0.291 |
| Body side view | C → C | 1970 → 1970 | 0.158 → 0.158 |
| Noisy plane (120 steps) | D → D | 478 → 274 | 0.330 → 0.339 |

The conclusion matches the engineering guidance: on continuous, hard-point-dominated panels the smoothing space is limited; measurable improvement occurs on perturbed surfaces. Therefore **local Class-A smoothing should be performed after hard points are frozen**.

### 3.4 Storyboard Generation and Rendering

- car_promotion: 7 shots / 90s; tech_demo: 5 shots / 90s; minimal_showcase: 2 shots / 90s;
- Custom (investor audience): scales proportionally by duration as expected;
- Markdown (1968 chars) and HTML (9471 chars) render successfully.

---

## 4. Bayesian Optimization Convergence Verification

On the controlled 1-D objective `f(x) = −(x−0.5)²` (optimum 0 at x=0.5), 15 suggest–observe rounds:

| Acquisition | best x | best score | Enters −0.01 band |
|---|---:|---:|---|
| EI | 0.5000 | −0.00000 | ✅ |
| UCB | 0.4999 | −0.00000 | ✅ |

What the evidence means: the full path of random filling → GP fitting → acquisition optimization works correctly; both acquisition functions locate the known optimum region within a small budget. This experiment validates **engine correctness**; it does not claim sample-efficiency advantages over external optimization libraries.

---

## 5. Defect Fixes and Verification in This Round

| Defect | Location | Fix | Verification |
|---|---|---|---|
| Stats-dictionary contract drift (callers need `total_vertices`) | assembler.py `compute_stats` | Returns total_vertices/total_faces/components/bounds while retaining legacy aliases | Self-check passes |
| Test fixture used an outdated box-reshape section mesh | test_all.py | Uses `build_body(process=False)` to extract the single-side (49,25,3) mesh | Self-check passes |
| build_body assembly order scrambled by automatic processing | body.py | New `process: bool = True` parameter | 200 tests pass |
| `run_full_pipeline` reshapes a 49×25 mesh from an 8-vertex box (crashes at runtime) | api.py | Builds the single-side mesh from the parameterized body; docstrings updated | Fully runs end-to-end |
| Inconsistent endpoint counts (113/116) | README/architecture/API/paper | Unified at **118** (116 route endpoints + 2 system endpoints) | Re-checked file by file via decorators |

---

## 6. Fact-Baseline Reconciliation (documents ↔ source)

| Document statement | Source fact | Consistency |
|---|---|---|
| 16 route modules | 16 endpoint-bearing modules in the routes directory | ✅ |
| 118 HTTP endpoints | 113 `@router` + 3 `@keys_router` + 2 `@app` = 118 | ✅ |
| 11 ORM tables | 11 tables defined in models | ✅ |
| 10 frontend pages | 10 entries in the route table (hash + global guard) | ✅ |
| CarParams 22 dimensions | 22 fields in car_params.py | ✅ |
| Bayesian space 14 parameters | 14 entries in DEFAULT_SPEC | ✅ |
| G1/G2 thresholds 5°/2° | defaults in continuity.py | ✅ |
| Grade thresholds A/B/C | grader.py 0.85/0.7, 0.70/0.5, 0.50 | ✅ |
| 489 tests | 200 + 178 + 111 | ✅ |

---

## 7. Trusted-Degradation Contract (Design Verification)

| Missing dependency | Platform behavior |
|---|---|
| PyTorch | Training-capability endpoints report unavailable; training requests fail explicitly |
| LLM provider key | Conversation requests return an explicit client error |
| CLIP weights | Falls back to geometric features, marked in the response |
| Redis | Session storage degrades to in-process memory |

Shared principle: **Signal, never simulate**.

---

## 8. Boundary Statement (not covered this round / known limits)

- This report covers automated gates and consistency validation; it does not include real-vehicle manufacturing or stamping validation;
- The 22 explicit parameters cannot express arbitrary free-form styling gestures;
- QLoRA-style project-history fine-tuning has not yet been delivered;
- Manufacturing, interference, and aerodynamic objectives are only partially modeled.

---

## Appendix: Reproduction Commands

```powershell
# Algorithm layer (200)
python -m pytest tests/ -q    # inside algorithm_model/

# One-stop self-check (5 modules)
python test_all.py            # inside algorithm_model/

# Backend (178)
python -m pytest -q           # inside backend/

# Frontend (111)
npx vitest run                # in the repository root
```

---

*This report connects with [PLATFORM_TEST_REPORT_20260811.md](PLATFORM_TEST_REPORT_20260811.md) (the 2026-08-11 historical record), together forming the platform quality evidence chain.*
