# API Reference Overview

> Version: platform v1.2 (generated from source on 2026-09-27)
> **118 HTTP endpoints** in total: 116 across 16 route modules (113 `@router` plus 3 API-key endpoints on `keys_router`), and 2 system endpoints in `main.py`; unified prefix `/api/v1`.
> Requests/responses are JSON (except export/download endpoints).
>
> Auth markers:
> - 🔐 Authentication required: `Authorization: Bearer <JWT>` (`get_current_user`)
> - 🔹 Optional auth: associates the user when a JWT is present (`get_optional_user`)
> - Unmarked: public
>
> Interactive docs: `http://localhost:8000/docs` when the backend is running.

<figure class="doc-figure">
  <img src="docs/images/api-lifecycle.svg" alt="API request lifecycle in eight steps" loading="lazy">
  <figcaption><strong>Fig. 1 API request lifecycle in eight steps: axios → CORS → security headers → routing → auth → validation → business → response</strong>How to read: The top row (①–④) covers request entry; the bottom row (⑤–⑧) covers processing and response. The red dashed line is the unified error channel: any failure returns a structured error, with 5xx also logged to backend-error.log.</figcaption>
</figure>

---

## 1. Project Management — project.py (5)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/projects/` | Create project | |
| GET | `/projects/` | List projects (filter by status) | |
| GET | `/projects/{project_id}` | Project detail | |
| PUT | `/projects/{project_id}` | Update project | |
| DELETE | `/projects/{project_id}` | Delete project | |

## 2. Model Files — model.py (4)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/models/upload/` | Upload model file (multipart; optional project_id) | |
| GET | `/models/` | List models (filter by project_id) | |
| GET | `/models/{model_id}` | Model detail | |
| DELETE | `/models/{model_id}` | Delete model | |

## 3. Model Building — build.py (6)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/build/` | Build model | |
| POST | `/build/rebuild` | Rebuild | |
| POST | `/build/batch` | Batch build | |
| GET | `/build/cache` | Build-cache status | |
| DELETE | `/build/cache/{model_id}` | Clear a model's cache | |
| GET | `/build/status/{model_id}` | Query build status | |

## 4. Body Generation — car.py (6)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/car/generate` | Generate the complete body | |
| POST | `/car/generate/component` | Generate a single body part | |
| GET | `/car/components` | List generatable parts | |
| GET | `/car/parameters` | Body-generation parameter config | |
| POST | `/car/regenerate` | Regenerate the body | |
| POST | `/car/export` | Export generated body data | |

## 5. Model Modification — modify.py (15)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/modify/surfaces/create` | Create NURBS surface | |
| GET | `/modify/surfaces/{surface_id}` | Query surface | |
| POST | `/modify/surfaces/{surface_id}/modify` | Modify surface | |
| POST | `/modify/surfaces/{surface_id}/control-point` | Update control point | |
| GET | `/modify/surfaces/{surface_id}/evaluate` | Evaluate surface point (u, v) | |
| DELETE | `/modify/surfaces/{surface_id}` | Delete surface | |
| GET | `/modify/parameters` | Parameter list | |
| POST | `/modify/parameters/add` | Add parameter | |
| POST | `/modify/parameters/update` | Update parameter | |
| GET | `/modify/parameters/automotive` | Automotive engineering parameters | |
| POST | `/modify/measurements/distance` | Distance measurement | |
| POST | `/modify/measurements/angle` | Angle measurement | |
| GET | `/modify/measurements/summary` | Measurement summary | |
| GET | `/modify/history` | Modification history | |
| POST | `/modify/history/undo` | Undo | |

## 6. Model Export — export.py (4)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/export/` | Create export task | |
| GET | `/export/download/{model_id}/{format}` | Download file in the given format | |
| GET | `/export/formats` | Supported export formats | |
| GET | `/export/history/{model_id}` | Model export history | |

## 7. Model Variants — variant.py (7)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/variants/` | Create variant | |
| GET | `/variants/{model_id}` | List model variants | |
| GET | `/variants/{model_id}/history` | Variant version history | |
| GET | `/variants/{model_id}/{variant_id}` | Variant detail | |
| DELETE | `/variants/{model_id}/{variant_id}` | Delete variant | |
| POST | `/variants/compare` | Compare variants | |
| POST | `/variants/{model_id}/{variant_id}/rollback` | Roll back to a variant | |

## 8. Workflows — workflow.py (7)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/workflows/` | Create workflow | |
| GET | `/workflows/` | List workflows (project_id / status filters) | |
| GET | `/workflows/{workflow_id}` | Workflow detail | |
| POST | `/workflows/{workflow_id}/execute` | Execute workflow | |
| GET | `/workflows/{workflow_id}/steps` | List workflow steps | |
| PUT | `/workflows/{workflow_id}` | Update workflow | |
| DELETE | `/workflows/{workflow_id}` | Delete workflow | |

## 9. Quality and Topology — quality.py (8)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/topology/optimize/` | Topology optimization | |
| POST | `/quality/check/` | Create quality-check report | |
| GET | `/quality/reports/` | List quality reports (project_id / model_id filters) | |
| GET | `/quality/reports/{report_id}` | Quality-report detail | |
| POST | `/data/handover/` | Data-handover preparation | |
| GET | `/parameters/` | List parameter sets | |
| GET | `/reports/{report_path}` | Download report file (path-style) | |
| GET | `/exports/{export_path}` | Download export file (path-style) | |

## 10. AI Training — training.py (14)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/ai/train` | Create backend PyTorch training task | 🔐 |
| GET | `/ai/tasks` | List training tasks (own; admin: all) | 🔐 |
| GET | `/ai/tasks/{task_id}` | Task detail | 🔐 |
| POST | `/ai/tasks/{task_id}/cancel` | Cancel task | 🔐 |
| GET | `/ai/training/capabilities` | Training capabilities and concurrency | |
| POST | `/ai/train/batch` | Generate synthetic sample batch synchronously | 🔹 |
| GET | `/ai/dataset-stats` | Dataset statistics | |
| GET | `/ai/car-types` | Car-type metadata | |
| GET | `/ai/styles` | Style metadata | |
| GET | `/ai/brands` | Brand metadata | |
| GET | `/ai/model-weights` | Produced model checkpoints | |
| POST | `/ai/evaluate-quality` | Styling-parameter quality evaluation | |
| POST | `/ai/generate-design` | Generative design | |
| POST | `/ai/optimize` | Parameter optimization | |

## 11. AI Assistant — ai.py (3)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/ai/chat` | NURBS expert dialogue (Ollama) | |
| GET | `/ai/models` | List available Ollama models | |
| GET | `/ai/health` | Ollama / NURBS service health | |

## 12. Bayesian Optimization — bayes.py (7)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/bayes/sessions` | Create session (space / goal / acquisition / seed) | |
| GET | `/bayes/sessions/{session_id}` | Session summary | |
| DELETE | `/bayes/sessions/{session_id}` | Delete session | |
| GET | `/bayes/sessions/{session_id}/suggest` | Suggest parameters (n, 1–32) | |
| POST | `/bayes/sessions/{session_id}/observe` | Report observation (parameters + score) | |
| GET | `/bayes/sessions/{session_id}/best` | Current best observation | |
| GET | `/bayes/sessions/{session_id}/samples` | Export training samples | |

For details see [bayes_optimization.md](bayes_optimization.md).

## 13. Parameterized Textures — texture.py (3)

| Method | Path | Function | Auth |
|---|---|---|---|
| GET | `/texture/regions` | List texture-applicable regions | |
| POST | `/texture/analyze` | Pattern/texture analysis | |
| POST | `/texture/apply/{session_id}` | Apply texture to a session | |

## 14. Import / Re-Param / Export — import_export.py (11)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/import-export/import` | Create import session from parameters | |
| POST | `/import-export/import/file` | Upload file to create session (multipart) | |
| GET | `/import-export/{session_id}/params` | Parameter list | |
| GET | `/import-export/{session_id}/params/groups` | Parameter groups | |
| PUT | `/import-export/{session_id}/params` | Modify parameters (overrides) | |
| GET | `/import-export/{session_id}/preview` | 3D preview | |
| POST | `/import-export/{session_id}/export` | Multi-format export | |
| GET | `/import-export/{session_id}/download/{filename}` | Download exported file | |
| GET | `/import-export/{session_id}/snapshot` | Parameter snapshot | |
| GET | `/import-export/sessions` | Session list | |
| DELETE | `/import-export/{session_id}` | Delete session | |

## 15. Unified LLM Proxy — llm_proxy.py (4)

| Method | Path | Function | Auth |
|---|---|---|---|
| GET | `/llm/providers` | List configured providers | 🔹 |
| POST | `/llm/{provider}/chat/completions` | Chat completion | 🔹 |
| POST | `/llm/{provider}/embeddings` | Embeddings | 🔹 |
| POST | `/llm/{provider}/images/generations` | Text-to-image | 🔹 |

## 16. Auth and API Keys — auth.py (9)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/auth/register` | Register, return JWT | |
| POST | `/auth/login` | Password login, return JWT | |
| GET | `/auth/me` | Current user info | 🔐 |
| GET | `/auth/methods` | Probe enabled login methods | |
| GET | `/auth/wechat/qr` | WeChat open-platform scan QR code | |
| GET | `/auth/wechat/callback` | WeChat open-platform callback | |
| GET | `/auth/mp/authorize` | Official-account web-authorization entry | |
| GET | `/auth/mp/poll` | Poll authorization result by ticket | |
| GET | `/auth/mp/callback` | Official-account authorization callback | |
| GET | `/api-keys` | List current user's API keys | 🔐 |
| PUT | `/api-keys/{provider}` | Set API key (encrypted backend-side) | 🔐 |
| DELETE | `/api-keys/{provider}` | Delete API key | 🔐 |

> Note: auth.py contains two routers, `auth` and `keys_router`, with 12 endpoints in total;
> the module count (9) includes only the `auth` router; the 3 api-keys endpoints are listed here as well.

---

## 17. System Endpoints (defined directly in main.py)

| Method | Path | Function |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/i18n/config` | Internationalization config (default / supported languages) |

---

## 18. Standard Error Responses

| Status | Meaning |
|---|---|
| 400 | Business validation failure (out-of-range parameters, illegal space definition) |
| 401 | Missing / invalid JWT |
| 404 | Resource or session not found |
| 405 | Method not allowed (with Allow header) |
| 409 | State conflict (e.g. querying best with no observations) |
| 422 | Request-body schema failure (with field-error detail) |
| 503 | Optional capability not ready (PyTorch / Ollama / missing WeChat config, etc.) |
