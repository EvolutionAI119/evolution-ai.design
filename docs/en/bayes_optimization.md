# Bayesian Optimization Module — User Guide

> **Module role**: the **Bayesian optimization container** behind the machine-learning training backend.
> In the 14-parameter styling space (overall length / width / wheel base, etc.), it uses a Gaussian
> process as the surrogate model and EI / UCB as acquisition functions for automatic optimization.
> Observed samples can be exported in a training format compatible with the `/ai/train` dataset.
>
> Source implementation:
> - Engine: `backend/app/bayes_optimizer.py` (pure numpy + scipy; no new heavy dependencies)
> - Routes: `backend/app/routes/bayes.py`
> - Frontend SDK: `bayesAPI` in `src/api.js`

---

## 1. How It Works — The Optimization Loop

<figure class="doc-figure">
  <img src="docs/images/paper-bayes-engine.svg" alt="Bayesian optimization loop" loading="lazy">
  <figcaption><strong>Fig. 1-1 Bayesian optimization loop: GP surrogate (left) and the five-step iteration (right)</strong>How to read: Left chart: amber dots are evaluated samples, the green curve the posterior mean, the shaded band ±σ uncertainty, and the pink dashed line the EI maximum; right boxes give the five-step loop (DOE → real evaluation → surrogate update → EI → suggestion). The inset shows monotone convergence within 20–40 rounds.</figcaption>
</figure>

**Loop (suggest → evaluate → observe → converge → export)**:

1. Create a session (parameter space, objective direction, acquisition function)
2. `suggest` returns the next set of styling parameters proposed by the engine
3. Evaluate a quality score for that parameter set (e.g. `/ai/evaluate-quality`, real-vehicle simulation, or human rating)
4. `observe` feeds the "parameters → score" pair back; the surrogate updates immediately
5. Repeat 2–4; the GP's understanding of the space converges toward the optimum region
6. `best` returns the current optimum; `samples` exports all observations as training data

**Algorithm behavior**:

- When a session has fewer than 2 observations, `suggest` performs random space-filling (the surrogate is not yet stable); after 2 observations it switches to GP-driven acquisition.
- Both maximize and minimize objectives are handled internally as maximization (minimize negates the score).
- Sessions are stored **in process memory** (the same pattern as the training-task manager). Sessions are cleared on backend restart — use `samples` to persist when needed.

---

## 2. Quick Start (Full Example)

This example uses the default 14-parameter space, a maximize objective, and the EI acquisition function:

```bash
# 1) Create a session
curl -X POST http://localhost:8000/api/v1/bayes/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "sport-proportion", "seed": 42}'
# -> 201; note the returned session_id (shown as $SID below)

# 2) Suggest a parameter set
curl "http://localhost:8000/api/v1/bayes/sessions/$SID/suggest"

# 3) Evaluate the quality score for the suggested parameters (e.g. /ai/evaluate-quality or human rating), then observe
curl -X POST http://localhost:8000/api/v1/bayes/sessions/$SID/observe \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"overall_length": 4600, "overall_width": 1980}, "score": 88.5}'
# Note: observe requires parameters covering ALL parameters in the space; the example shows the field structure only.

# 4) After several iterations, check the best
curl http://localhost:8000/api/v1/bayes/sessions/$SID/best

# 5) Export training samples
curl http://localhost:8000/api/v1/bayes/sessions/$SID/samples
```

The frontend `bayesAPI` (see Section 5) implements the same loop.

---

## 3. API Reference

All endpoints are prefixed with `/api/v1/bayes`; requests and responses are JSON.
Endpoints currently do not enforce authentication and can be called directly.

### 3.1 Create Session

`POST /sessions`

Request body (all fields optional):

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | `""` | Session name |
| `space` | array | default 14-parameter space | Parameter definitions as `{name, min, max}` |
| `goal` | string | `"maximize"` | Objective direction: `maximize` / `minimize` |
| `acquisition` | string | `"ei"` | Acquisition function: `ei` / `ucb` |
| `seed` | integer | none | Random seed for reproducible experiments |

Response: `201 Created`

```json
{
  "session_id": "a1b2c3d4e5f6",
  "name": "sport-proportion",
  "goal": "maximize",
  "acquisition": "ei",
  "n_observations": 0,
  "space": [{"name": "overall_length", "min": 4000.0, "max": 6200.0}],
  "best": null
}
```

Errors: returns `400` when the space is empty, parameter names are duplicated, or any `max <= min`.

### 3.2 Get Session Summary

`GET /sessions/{session_id}` → returns the same summary structure as creation (with live `best`). Returns `404` if the session does not exist.

### 3.3 Delete Session

`DELETE /sessions/{session_id}` → `{"deleted": "<session_id>"}`; returns `404` if not found.

### 3.4 Suggest Parameters

`GET /sessions/{session_id}/suggest?n=1`

| Query param | Type | Default | Range | Description |
|---|---|---|---|---|
| `n` | integer | 1 | 1–32 | Number of parameter sets suggested at once, sorted by acquisition value |

Response:

```json
{
  "session_id": "a1b2c3d4e5f6",
  "acquisition": "ei",
  "suggestions": [
    {"overall_length": 4587.3, "overall_width": 1972.8}
  ]
}
```

All suggested values are guaranteed to lie within the space bounds. Returns `404` if the session does not exist.

### 3.5 Report an Observation

`POST /sessions/{session_id}/observe`

Request body:

| Field | Type | Description |
|---|---|---|
| `parameters` | object | Parameter name → value; **must cover every parameter in the space** |
| `score` | number | Quality score (objective value) for this parameter set |

Response:

```json
{
  "session_id": "a1b2c3d4e5f6",
  "index": 3,
  "n_observations": 4,
  "best": {"index": 2, "parameters": {}, "score": 91.2}
}
```

Errors (all `400`): unknown parameter name, missing parameters, or out-of-bounds values. Returns `404` if the session does not exist.

### 3.6 Get Current Best

`GET /sessions/{session_id}/best`

Response: `{"session_id", "index", "parameters", "score"}`, where `index` is the index of the best observation.
With `goal=minimize`, returns the observation with the lowest score. Returns `409` when the session has no observations, and `404` if it does not exist.

### 3.7 Export Training Samples

`GET /sessions/{session_id}/samples`

Response:

```json
{
  "session_id": "a1b2c3d4e5f6",
  "feature_order": ["overall_length", "overall_width"],
  "goal": "maximize",
  "samples": [
    {"features": {"overall_length": 4600.0, "overall_width": 1980.0}, "score": 88.5}
  ]
}
```

`feature_order` gives the feature-name order, which can directly align the feature columns of a training pipeline; `features` maps parameter name → value, and `score` is the corresponding observation score.

---

## 4. Default Parameter Space

When `space` is omitted, the following 14 styling parameters are used (aligned with the training pipeline PARAM_ORDER; lengths in mm, angles in degrees):

| Parameter | Meaning | Lower | Upper |
|---|---|---:|---:|
| `overall_length` | Overall vehicle length | 4000 | 6200 |
| `overall_width` | Overall vehicle width | 1750 | 2150 |
| `overall_height` | Overall vehicle height | 1100 | 2050 |
| `wheel_base` | Wheel base | 2400 | 3700 |
| `track_width` | Track width | 1450 | 1900 |
| `ground_clearance` | Ground clearance | 80 | 280 |
| `hood_length` | Hood length | 700 | 1700 |
| `roof_height` | Roof height | 300 | 1050 |
| `wheel_diameter` | Wheel diameter | 600 | 850 |
| `windshield_angle` | Windshield angle | 18 | 50 |
| `rear_window_angle` | Rear-window angle | 10 | 50 |
| `rear_slant_angle` | Rear slant angle | 5 | 55 |
| `front_overhang` | Front overhang | 750 | 1150 |
| `rear_overhang` | Rear overhang | 850 | 1350 |

Custom-space example, a one-dimensional optimization: `{"space": [{"name": "x", "min": 0, "max": 1}]}`.
All parameters are continuous; parameter names must be unique.

---

## 5. Frontend SDK (bayesAPI)

`src/api.js` exports `bayesAPI`, with one method per endpoint:

| Method | Endpoint |
|---|---|
| `createSession(data)` | `POST /bayes/sessions` |
| `getSession(sid)` | `GET /bayes/sessions/{sid}` |
| `deleteSession(sid)` | `DELETE /bayes/sessions/{sid}` |
| `suggest(sid, n = 1)` | `GET /bayes/sessions/{sid}/suggest` |
| `observe(sid, parameters, score)` | `POST /bayes/sessions/{sid}/observe` |
| `best(sid)` | `GET /bayes/sessions/{sid}/best` |
| `samples(sid)` | `GET /bayes/sessions/{sid}/samples` |

Usage example:

```js
import { bayesAPI } from '@/api'

const { data: session } = await bayesAPI.createSession({ goal: 'maximize', seed: 42 })
const { data: { suggestions } } = await bayesAPI.suggest(session.session_id)
// ... evaluate suggestions[0] to obtain a score ...
await bayesAPI.observe(session.session_id, suggestions[0], score)
const { data: best } = await bayesAPI.best(session.session_id)
```

---

## 6. Acquisition Functions & Tuning Notes

| Item | Current value / behavior | Effect of adjusting |
|---|---|---|
| GP kernel | RBF (isotropic length scale 0.25 in normalized space) | Larger length scale → smoother surrogate; smaller → more sensitive to local variation |
| GP noise | 1e-6 (observations treated as exact) | Increase when scores are noisy, to avoid over-fitting observations |
| EI minimum improvement `xi` | 0.01 | Increasing encourages exploration of unsampled regions |
| UCB weight `kappa` | 2.0 | Increasing weights exploration (uncertainty) higher; decreasing favors currently known good regions |
| Cold-start observations | 2 | Random space-filling before this count; GP optimization after |
| Candidate pool | 4096 random points | The acquisition maximum is taken over the pool; larger pools are more accurate at slightly higher cost |

Choosing an acquisition function:

- **EI** (default): a robust exploitation / exploration balance; converges fast when the objective is smooth.
- **UCB**: exploration strength is explicitly tunable via `kappa`; suited to multi-modal objectives or when deliberately widening sample coverage.

---

## 7. Integration with the Training Module

1. Session observations are exported via `GET /samples`; the `features` field names match the training pipeline's feature columns, so a training dataset can be built directly.
2. The objective in the loop can be served by existing analysis endpoints: `POST /api/v1/ai/evaluate-quality` provides an engineering proxy quality score for styling parameters.
3. Recommended flow: first run a few Bayesian iterations to obtain high-quality samples near the optimum region, then submit them to the backend PyTorch training via `POST /api/v1/ai/train` — improving sample utilization.

---

## 8. Error-Code Quick Reference

| Status code | Trigger |
|---|---|
| `400` | Empty space / duplicate parameter names / `max <= min` at creation; unknown, missing, or out-of-bounds parameters at observation |
| `404` | Session not found (query / suggest / observe / best / samples / delete) |
| `409` | Querying `best` with no observations |
| `422` | Request body types or field values fail the schema (e.g. illegal goal/acquisition enum) |

---

## 9. Testing

Backend tests: `backend/tests/test_bayes.py` (12 cases), covering:

- Session lifecycle: creation (default 14 parameters / custom space), summary query, deletion
- Suggestions lie within bounds; parameter validation on observation (unknown / out of bounds)
- Correct direction of `best` under maximize / minimize; 409 with no observations
- **Convergence**: 15-round loops with EI / UCB on the 1-D objective `-(x-0.7)²`, best score > -0.01
- Training-sample export format and field order

Run it: in the `backend/` directory, `python -m pytest tests/test_bayes.py -q`.
Frontend route-contract tests live in `src/tests/api.spec.js`.
