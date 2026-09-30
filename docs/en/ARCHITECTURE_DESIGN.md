# Architecture Design Document

> Corresponding version: platform v1.2 (updated from source-code status after the full review on 2026-09-27)
> Every module, path, and datum in this document takes the current codebase as its sole source of truth.

---

## 1. Overall Architecture

<figure class="doc-figure">
  <img src="docs/images/en/whitepaper-arch.svg" alt="Platform architecture overview" loading="lazy">
  <figcaption><strong>Fig. 1-1 Platform architecture overview: frontend / backend / algorithm / data layers plus deployment channel</strong>How to read: Read as an architecture overview — four layers annotated with inter-layer call protocols, and a deployment channel listing dev, production, tunnel and static publishing; the algorithm layer has zero framework dependencies and can run standalone.</figcaption>
</figure>

The platform uses a five-layer architecture:

```
┌──────────────────────────────────────────────────────────────┐
│ L1 Frontend   Vue 3.4 + Vite 5 + Three.js 0.166              │
│               Element Plus + Pinia + vue-router (hash) + vue-i18n │
├──────────────────────────────────────────────────────────────┤
│ L2 Gateway    Vite dev proxy / Nginx                         │
│               /api/v1 → FastAPI (8000); public via cpolar HTTPS │
├──────────────────────────────────────────────────────────────┤
│ L3 Backend    FastAPI 0.104 + Pydantic v2                    │
│               16 route modules / 118 endpoints (incl. 2 system); thin-shell orchestration │
├──────────────────────────────────────────────────────────────┤
│ L4 Algorithm  algorithm_model (independently installable)    │
│               NURBS full-vehicle / freeform free surfaces /  │
│               surface_quality evaluation & optimization / storyboard │
├──────────────────────────────────────────────────────────────┤
│ L5 Infrastructure  SQLite (development) + SQLAlchemy 2.0 (11 ORM tables) │
│               File storage; optional Redis; Docker Compose   │
└──────────────────────────────────────────────────────────────┘
```

**Key design decisions**:

1. **Decoupling algorithms from the web**: `algorithm_model/` is an independent Python package with its own entry points (`main.py`/`api.py`), dependencies, and tests; the backend only orchestrates.
2. **Parallel dual geometry pipelines**:
   - mesh pipeline (trimesh parameterized meshes) — real-time frontend preview, GLB/STL export;
   - NURBS pipeline (self-developed NURBS core + STEP writer) — STEP engineering output, G0/G1/G2 Class-A analysis.
3. **Truthful capability degradation**: when optional capabilities (PyTorch, Ollama, Redis, CLIP) are missing, return 503 or degrade automatically — never fake success.
4. **Defense in depth**: JWT auth, Fernet-encrypted API keys, production SECRET_KEY fail-fast, unified security headers, CORS allow-list.

---

## 2. Frontend Structure

Source root: `src/`. Ten routed pages (hash mode):

| Route | Page | Core responsibility |
|---|---|---|
| `/` | Dashboard | Platform overview and function entries |
| `/designer` | Designer | AI parameterized designer: parameter panel + real-time 3D rendering |
| `/projects` | Projects | Project list |
| `/projects/:id` | ProjectDetail | Project detail and model management |
| `/deep-learning` | DeepLearning | Deep-learning designer: training batches, style/generative design |
| `/quality` | Quality | Quality checks and report list |
| `/deliver` | Deliver | Engineering delivery and data handover |
| `/demo` | Demo | Function demonstration |
| `/login` | Login | Login (password + WeChat scan/official-account authorization), public |
| `/account` | Account | Account and API-key management |

Key directories:

- `components/`: Car2D, Car3D, MarkdownRenderer, TechSelectionMatrix
- `stores/`: Pinia — auth / designer / project / ui
- `api.js`: unified axios instance (baseURL `/api/v1`), exporting `projectAPI` … `bayesAPI` per domain
- `config/carPresets.js`: brand presets (5 brands, 19 models)
- `utils/`: carImageManager, imageGenerator, llm, useCarSessionImage
- `i18n.js`: Chinese–English bilingual

Global route guard: accessing a protected page without a token redirects to `/login` with a return address.

---

## 3. Backend Structure

Backend root: `backend/`; application entry `app/main.py` (assembled by `create_app()`); launch script `start.py`.

### 3.1 Route Modules (16 modules, 116 endpoints: 113 `@router` + 3 on `keys_router`; `main.py` adds 2 system endpoints — **118 HTTP endpoints in total**)

| Module file | Final path prefix | Endpoints | Responsibility |
|---|---|---:|---|
| project.py | `/api/v1/projects` | 5 | Project CRUD |
| model.py | `/api/v1/models` | 4 | Model upload/query/delete |
| build.py | `/api/v1/build` | 6 | Build/rebuild/batch/cache |
| car.py | `/api/v1/car` | 6 | Body & part generation, parameters, export |
| modify.py | `/api/v1/modify` | 15 | NURBS surfaces, parameters, measurement, history |
| export.py | `/api/v1/export` | 4 | Model export and download |
| variant.py | `/api/v1/variants` | 7 | Variants/versions/comparison/rollback |
| workflow.py | `/api/v1/workflows` | 7 | Workflows & steps, execution |
| quality.py | `/api/v1` (quality/topology/data etc.) | 8 | Quality checks, topology optimization, data handover, file download |
| training.py | `/api/v1/ai` | 14 | PyTorch training tasks, sample batches, analysis |
| ai.py | `/api/v1/ai` | 3 | NURBS expert dialogue, Ollama models/health |
| bayes.py | `/api/v1/bayes` | 7 | Bayesian session lifecycle |
| texture.py | `/api/v1/texture` | 3 | Parameterized texture analysis & application |
| import_export.py | `/api/v1/import-export` | 11 | Full import → re-param → export chain |
| llm_proxy.py | `/api/v1/llm` | 4 | Unified multi-provider LLM proxy |
| auth.py | `/api/v1/auth`, `/api/v1/api-keys` | 12 | Register/login/WeChat (9), API-key management (3) |

Endpoint-by-endpoint detail: see [api_reference.md](api_reference.md).

### 3.2 Domain Modules (`backend/app/`)

| Module | Responsibility |
|---|---|
| `bayes_optimizer.py` | RBF Gaussian process + EI/UCB Bayesian engine (pure numpy/scipy) |
| `brand_knowledge.py` | Brand/model knowledge queries, semantic matching, similarity retrieval |
| `cad_importer.py` | CAD (STL/STEP etc.) import, point-cloud analysis, fallback |
| `car_generator.py` | NURBS body generation from parameter configurations |
| `nurbs.py` | NURBS data structures and operations |
| `texture_analyzer.py` | Texture geometric/semantic feature extraction |
| `clip_semantics.py` | CLIP semantic features (optional; auto-degrades) |
| `session_store.py` | General session storage |
| `security.py` | JWT issue/verify, DI (`get_current_user` / `get_optional_user`) |
| `config.py` | pydantic-settings; production SECRET_KEY fail-fast |
| `database.py` | Engine, SessionLocal, 11 ORM tables |
| `schemas.py` | Pydantic request/response models |

### 3.3 Configuration and Plugins

- `backend/config/automotive_parameters.json`: styling specification (dimensions / body parts / angles / Class-A parameters / proportions)
- `backend/config/brand_design_knowledge.json`: knowledge base for 5 brands and 19 models
- `backend/rhino_plugin/`: Rhino plugin (commands + semantic API); `rhino/` at the project root holds the brand-DNA panel
- `scripts/llm_server.py` + `Modelfile`: local LLM expert service (Docker / local dual mode)

---

## 4. Algorithm-Layer Structure (algorithm_model/)

| Sub-package | Content |
|---|---|
| `car_modeling/` | Parameterized full vehicle: `car_params` (22 dimensions), `body` (section-ring mesh), `body_nurbs`, `body_ends*` (G1/attached ends), `glass/wheels/lights/grille/mirrors/seams/trim`, `assembler` (assembly & stats), `blending` (three sections + tumblehome), `continuity_checker`, `sop_checklist` |
| `freeform/` | NURBS core (`nurbs_core`), free surfaces, sweep, fillet, STEP writer; Cython acceleration (`_nurbs_cy.pyx`) |
| `surface_quality/` | Curvature, G0/G1/G2 continuity, reflection lines, grading, simulated-annealing smoothing; Cython (`_quality_cy.pyx`) |
| `storyboard/`, `storyboard_viewer/` | Storyboard generation (templates) and Markdown/HTML rendering |
| `examples/` | 17 examples (full vehicle, NURBS STEP, G1 continuity, SOP reports, etc.) |

Unified external entry: `api.py` (build_car / get_car_stats / evaluate_surface / optimize_surface / make_storyboard / render_storyboard / run_full_pipeline).

---

## 5. Data Model (11 ORM Tables)

| Table | Model class | Key fields |
|---|---|---|
| projects | Project | name, description, status |
| model_files | ModelFile | project_id, filename/filepath, file_type, status, params_json, car_data_json |
| workflows | Workflow | project_id, name, type, status |
| workflow_steps | WorkflowStep | workflow_id, model_id, step_name/type, status, progress, input/output, error |
| quality_reports | QualityReport | project_id, model_id, overall_score, passed, report_data, report_path |
| parameter_sets | ParameterSet | project_id, name, params |
| model_variants | ModelVariant | model_id, name, parent_variant_id, params_json, car_data_json |
| users | User | email (unique), username, password_hash, wechat_unionid/openid, is_active/is_admin |
| api_keys | ApiKey | user_id, provider, key_encrypted; unique on (user_id, provider) |
| parameter_records | ParameterRecord | name (unique), value |
| training_tasks | TrainingTask | user_id, name, dataset, config_json, status, progress, metrics_json, logs |

Relationships: Project 1–N ModelFile / Workflow / QualityReport; Workflow 1–N WorkflowStep;
ModelFile 1–N ModelVariant (with self-referencing parent); User 1–N ApiKey.

---

## 6. Key Data Flows

<figure class="doc-figure">
  <img src="docs/images/en/arch-dataflow.svg" alt="Car-generation request data flow" loading="lazy">
  <figcaption><strong>Fig. 6-1 Complete data flow of a car-generation request (including error branches)</strong>How to read: Three swimlanes (browser, backend, algorithm/data); blue solid arrows trace the happy path ①HTTPS → ②auth/validation → ③orchestration → ④evaluation → ⑤200 OK; the red dashed branch shows 401s never reach the algorithm layer and turn into the global login prompt.</figcaption>
</figure>

### 6.1 The AI Parameterized-Design Loop

```
Designer page → carAPI.generate(params)
             → car_generator parameterized generation (mesh preview + data)
             → ModelFile persistence (params_json / car_data_json)
Frontend Car3D renders in real time; variants saved/compared/rolled back via variantAPI
```

### 6.2 Full Import → Re-Param → Export Chain

```
Upload → cad_importer parse (point-cloud analysis fallback) → import_export session
      → GET params (tree/groups) → PUT params (override)
      → GET preview (3D) → POST export (multi-format) → download
```

### 6.3 Bayesian Optimization → Training Linkage

```
POST /bayes/sessions → suggest (GP + EI/UCB)
  → /ai/evaluate-quality (or human) scoring → observe backfill, iterate
  → /samples export (feature_order + features/score)
  → /ai/train backend PyTorch; /ai/tasks poll status
```

### 6.4 WeChat Login

```
Login → probe /auth/methods
      → open-platform scan (/auth/wechat/qr → callback)
        or official-account web authorization (/auth/mp/authorize → frontend polls /auth/mp/poll → callback)
      → JWT (evoai_token)
```

---

## 7. Cross-Cutting Concerns

- **Auth**: JWT (PyJWT), hashed passwords; sensitive endpoints use `Depends(get_current_user)`, semi-open ones `get_optional_user`.
- **Key management**: user LLM API keys stored with Fernet symmetric encryption; cpolar authtoken / app secrets live only in `.env`, never in command payloads.
- **Security headers**: `main.py` middleware injects X-Content-Type-Options / X-Frame-Options / CSP / Referrer-Policy / Permissions-Policy / Cache-Control; removes `server: uvicorn`.
- **CORS**: open in DEBUG; explicit production allow-list; the `ACAO: *` + credentials combination is forbidden (with an ASGI correction middleware).
- **Exception handling**: StarletteHTTPException / RequestValidationError / Exception / 405 handled uniformly; error responses likewise complete CORS.

---

## 8. Deployment Architecture

- **Local development**: Vite 5173 + FastAPI 8000 + cpolar 4040 (HTTPS tunnel, public domain).
  Long-running services launch as detached top-level processes (`.trae/skills/launch-services-detached`).
- **Containerized**: `deploy/docker-compose.yml` (backend / frontend / nginx; required-env validation),
  images built by `deploy/*.Dockerfile`, reverse-proxied by `deploy/nginx.conf` and `default.conf.template`.
- **LLM service**: `docker-compose.llm.yml` + `Dockerfile.llm` (Ollama/expert model), auto-switching Docker/local.

---

## 9. Quality Baseline

| Suite | Cases | Result |
|---|---:|---|
| algorithm_model pytest (tests/) | 200 | All pass |
| algorithm_model one-stop self-check (test_all.py) | 5 modules | All pass |
| backend pytest (tests/) | 178 | All pass |
| frontend vitest | 111 | All pass |
| **Total** | **489+** | **All green** |

How to run: see the "Testing" section of the root README.
