# API Reference Overview

> Version: platform v1.2.x (regenerated from source on 2026-10-22)
> **153 HTTP endpoints** in total: 151 across 19 route modules, and 2 system endpoints in `main.py`; unified prefix `/api/v1`.
> Requests/responses are JSON (except export/download endpoints).
>
> Auth markers:
> - 🔐 Authentication required: `Authorization: Bearer <JWT>` (`get_current_user`)
> - 👑 Admin required: admin-level dependency (`require_admin` / `require_superadmin`)
> - 🔹 Optional auth: associates the user when a JWT is present (`get_optional_user`)
> - Unmarked: public
>
> Interactive docs: `http://localhost:8000/docs` when the backend is running.

<figure class="doc-figure">
  <img src="docs/images/en/api-lifecycle.svg" alt="API request lifecycle in eight steps" loading="lazy">
  <figcaption><strong>Fig. 1 ｜ API request lifecycle in eight steps: axios → CORS → security headers → routing → auth → validation → business → response</strong> How to read: The top row (①–④) covers request entry; the bottom row (⑤–⑧) covers processing and response. The red dashed line is the unified error channel: any failure returns a structured error, with 5xx also logged to backend-error.log.</figcaption>
</figure>

<figure class="doc-figure">
  <img src="docs/images/en/api2-hero.svg" alt="API panorama: client, gateway, 19 route modules and data/runtime" loading="lazy">
  <figcaption><strong>Fig. 2 ｜ API panorama: client → gateway → 19 route modules → data and runtime</strong> How to read: The browser and scripts on the left carry a JWT over HTTPS into the unified gateway; the middle shows 19 route modules (auth contains both the auth and api-keys routers); the right shows ORM, files, cache and the algorithm layer. The footer states 19 modules and 151 route endpoints plus 2 system endpoints = 153. The figure shows call structure only, not traffic or performance.</figcaption>
</figure>

<figure class="doc-figure">
  <img src="docs/images/en/api2-chart.svg" alt="Ranked bar chart of endpoint counts across route modules" loading="lazy">
  <figcaption><strong>Fig. 3 ｜ Endpoint counts of the 19 route modules in descending order (151 total)</strong> How to read: The x-axis is endpoint count (0–20) and the y-axis lists modules; analytics 21, modify 15, training 15, auth 12 and import_export 11 form the top five, totaling 74 or 49.0%, itemized in the Top-5 card at right. The 19 bars sum to 151; the other 2 system endpoints appear in §20. Bar length compares the interface surface of each module directly.</figcaption>
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

## 8. Workflows — workflow.py (9)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/workflows/` | Create workflow | |
| GET | `/workflows/` | List workflows (project_id / status filters) | |
| POST | `/workflows/training-review` | Create a training-review workflow | |
| POST | `/workflows/{workflow_id}/steps/{step_id}/review` | Submit a workflow-step review | |
| GET | `/workflows/{workflow_id}` | Workflow detail | |
| POST | `/workflows/{workflow_id}/execute` | Execute workflow | |
| GET | `/workflows/{workflow_id}/steps` | List workflow steps | |
| PUT | `/workflows/{workflow_id}` | Update workflow | |
| DELETE | `/workflows/{workflow_id}` | Delete workflow | |

## 9. Quality and Topology — quality.py (9)

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/topology/optimize/` | Topology optimization | |
| POST | `/quality/check/` | Create quality-check report | |
| POST | `/quality/g2-check/` | Dedicated G2-continuity check | |
| GET | `/quality/reports/` | List quality reports (project_id / model_id filters) | |
| GET | `/quality/reports/{report_id}` | Quality-report detail | |
| POST | `/data/handover/` | Data-handover preparation | |
| GET | `/parameters/` | List parameter sets | |
| GET | `/reports/{report_path}` | Download report file (path-style) | |
| GET | `/exports/{export_path}` | Download export file (path-style) | |

## 10. AI Training — training.py (15)

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
| GET | `/ai/trained-models` | List trained models | |
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

## 16. Admin Console — admin.py (7)

The standalone admin UI is served by the backend at `/admin`; these are its supporting endpoints.

| Method | Path | Function | Auth |
|---|---|---|---|
| GET | `/admin/users` | List users | 👑 |
| GET | `/admin/login-records` | Query login records | 👑 |
| POST | `/admin/users/{user_id}/active` | Enable/disable a user | 👑 |
| POST | `/admin/users/{user_id}/reset-password` | Reset a user's password | 👑 |
| POST | `/admin/users/{user_id}/role` | Change a user's role | 👑 |
| GET | `/admin/audit-logs` | Admin audit log | 👑 |
| GET | `/admin/backend-errors` | Backend error log query | 👑 |

## 17. Analytics & Community — analytics.py (21)

Tracking statistics, community messages/reference leads, notification center, and data export.

| Method | Path | Function | Auth |
|---|---|---|---|
| POST | `/analytics/track` | Page-view tracking | 🔹 |
| POST | `/analytics/track/duration` | Dwell-time tracking | |
| GET | `/analytics/public-summary` | Public statistics summary | 👑 |
| GET | `/analytics/messages` | List community messages | |
| POST | `/analytics/messages` | Post a message | 🔹 |
| POST | `/analytics/messages/{message_id}/reply` | Reply to a message | 🔹 |
| POST | `/analytics/messages/{message_id}/like` | Like a message | |
| POST | `/analytics/messages/{message_id}/hide` | Hide a message | 👑 |
| GET | `/analytics/references` | List reference leads | |
| POST | `/analytics/references` | Submit a reference lead | 🔹 |
| GET | `/analytics/references/all` | All reference leads (admin) | 👑 |
| POST | `/analytics/references/{reference_id}/verify` | Verify a reference lead | 👑 |
| GET | `/analytics/overview` | Operations overview | 👑 |
| GET | `/analytics/visits` | Visit statistics | 👑 |
| GET | `/analytics/registrations` | Registration statistics | 👑 |
| GET | `/analytics/interactions` | Interaction statistics | 👑 |
| GET | `/analytics/notifications` | List notifications (own) | 🔐 |
| GET | `/analytics/notifications/unread-count` | Unread notification count | 🔐 |
| POST | `/analytics/notifications/{notification_id}/read` | Mark a notification read | 🔐 |
| POST | `/analytics/notifications/read-all` | Mark all read | 🔐 |
| GET | `/analytics/export` | Export statistics (CSV/JSON) | 👑 |

## 18. Design Intent Parsing — design_intent.py (3)

Structured parsing of natural-language design intents (public endpoints available to guests).

| Method | Path | Function | Auth |
|---|---|---|---|
| GET | `/design-intent/examples` | List intent examples | |
| POST | `/design-intent/parse` | Parse a natural-language design intent | |
| POST | `/design-intent/parse-variants` | Parse and generate parameter variants | |

## 19. Auth and API Keys — auth.py (9)

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

<figure class="doc-figure">
  <img src="docs/images/en/api2-matrix.svg" alt="Matrix of the 19 modules by four auth levels" loading="lazy">
  <figcaption><strong>Fig. 4 ｜ Matrix of 19 modules × auth level</strong> How to read: The four columns are public, 🔹 optional, 🔐 required and 👑 admin; each cell is the endpoint count at that level for the module. Column totals are 114 / 9 / 12 / 16 = 151, with public endpoints at 75.5%. Takeaway: read endpoints are mostly public while writes and administration converge on required or admin; analytics spans all four levels (4/4/4/9) and training spans three (10/1/4), making them the most finely layered modules.</figcaption>
</figure>

---

## 20. System Endpoints (defined directly in main.py)

| Method | Path | Function |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/i18n/config` | Internationalization config (default / supported languages) |

---

## 21. Standard Error Responses

| Status | Meaning |
|---|---|
| 400 | Business validation failure (out-of-range parameters, illegal space definition) |
| 401 | Missing / invalid JWT |
| 404 | Resource or session not found |
| 405 | Method not allowed (with Allow header) |
| 409 | State conflict (e.g. querying best with no observations) |
| 422 | Request-body schema failure (with field-error detail) |
| 503 | Optional capability not ready (PyTorch / Ollama / missing WeChat config, etc.) |

<figure class="doc-figure">
  <img src="docs/images/en/api2-legend.svg" alt="API reference legend: auth markers, method colors, path notation and status codes" loading="lazy">
  <figcaption><strong>Fig. 5 ｜ Legend: auth markers, HTTP method colors, path notation and status-code semantics</strong> How to read: Card A gives the four auth markers with their endpoint counts (unmarked 114, 🔹 9, 🔐 12, 👑 16); Card B gives method colors (GET blue, POST green, PUT amber, DELETE red); Card C gives path and parameter notation (unified prefix `/api/v1/{module}/{action}`, resource parameters such as `{project_id}`, file paths `{path}/{filename}`); Card D gives status-code semantics (400/422 validation failure, 401 auth failure, 404/405 resource or method errors plus 409 state conflict, 503 capability not ready). Check this card before reading any module table.</figcaption>
</figure>
