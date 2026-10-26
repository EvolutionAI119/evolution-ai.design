# Appendix C · Baseline Facts of This Platform (Auditable Figures)

> Author: Quantum Swordsman

This appendix is the single source of every empirical figure used in the book. Each entry can be re-verified against the repository's public documents; when citing a number from this appendix, cite its source file as well. Paths are relative to the repository root.

---

## C.1 Backend Route Modules (19 modules, 152 route endpoints)

| Module file | Path prefix | Endpoints | Responsibility | Source |
|---|---|---:|---|---|
| project.py | `/api/v1/projects` | 5 | Project CRUD | `docs/ARCHITECTURE_DESIGN.md` §3.1 |
| model.py | `/api/v1/models` | 4 | Model file upload/query/delete | same |
| build.py | `/api/v1/build` | 6 | Model build/rebuild/batch/cache | same |
| car.py | `/api/v1/car` | 6 | Body & part generation, params, export | same |
| modify.py | `/api/v1/modify` | 15 | NURBS surfaces, params, measurement, history | same |
| export.py | `/api/v1/export` | 4 | Model export & download | same |
| variant.py | `/api/v1/variants` | 7 | Variants/versions/compare/rollback | same |
| workflow.py | `/api/v1/workflows` | 9 | Workflows & steps, execution, training review | same |
| quality.py | `/api/v1` (quality/topology/data etc.) | 9 | Quality checks, G2 check, topology optimization, data handover, downloads | same |
| training.py | `/api/v1/ai` | 15 | PyTorch training tasks, sample batches, trained models, analysis endpoints | same |
| ai.py | `/api/v1/ai` | 3 | NURBS expert chat, Ollama models/health | same |
| bayes.py | `/api/v1/bayes` | 7 | Bayesian optimization session lifecycle | same |
| texture.py | `/api/v1/texture` | 3 | Parametric texture analysis & application | same |
| import_export.py | `/api/v1/import-export` | 11 | Import → modify → export full-chain sessions | same |
| llm_proxy.py | `/api/v1/llm` | 4 | Unified proxy across LLM providers | same |
| design_intent.py | `/api/v1/design-intent` | 3 | Natural-language design intent parsing & variants | same |
| analytics.py | `/api/v1/analytics` | 21 | Tracking stats, community messages/reference leads, notifications, data export | same |
| admin.py | `/api/v1/admin` | 8 | Admin console: users/login records/audit/error logs | same |
| auth.py | `/api/v1/auth`, `/api/v1/api-keys` | 12 | Register/login/WeChat authorization (9), API key management (3) | same |
| **Total** | — | **152** | — | — |

**Endpoint count verification**: 5+4+6+6+15+4+7+9+9+15+3+7+3+11+4+3+21+8+12 = **152**.
`main.py` adds 2 system endpoints, yielding **154 HTTP endpoints** (scope: 152 routes + 2 system).
HTTP method distribution: GET 76 / POST 63 / PUT 4 / DELETE 9, totaling 152, cross-checked row-by-row against per-module totals.
Source: `docs/ARCHITECTURE_DESIGN.md` §3.1 (incl. Figure 3-1 caption).

## C.2 ORM Tables (17 tables)

| # | Table | Model class | Domain group | Source |
|---:|---|---|---|---|
| 1 | projects | Project | Project/workflow/model | `docs/ARCHITECTURE_DESIGN.md` §5; `backend/app/database.py` |
| 2 | model_files | ModelFile | Project/workflow/model | same |
| 3 | workflows | Workflow | Project/workflow/model | same |
| 4 | workflow_steps | WorkflowStep | Project/workflow/model | same |
| 5 | quality_reports | QualityReport | Quality/params/variants | same |
| 6 | parameter_sets | ParameterSet | Quality/params/variants | same |
| 7 | model_variants | ModelVariant | Quality/params/variants | same |
| 8 | parameter_records | ParameterRecord | Quality/params/variants | same |
| 9 | users | User | Users/audit/keys | same |
| 10 | login_records | LoginRecord | Users/audit/keys | same |
| 11 | admin_audit_logs | AdminAuditLog | Users/audit/keys | same |
| 12 | api_keys | ApiKey | Users/audit/keys | same |
| 13 | training_tasks | TrainingTask | Training tasks | same |
| 14 | page_views | PageView | Community/notification/tracking | same |
| 15 | messages | Message | Community/notification/tracking | same |
| 16 | external_references | ExternalReference | Community/notification/tracking | same |
| 17 | notifications | Notification | Community/notification/tracking | same |

**Count verification**: 4 + 4 + 4 + 1 + 4 = **17 tables**. Relationship chain: Project 1—N ModelFile / Workflow / QualityReport; Workflow 1—N WorkflowStep; ModelFile 1—N ModelVariant (self-referencing parent); User 1—N ApiKey / LoginRecord / Notification.

## C.3 Frontend Pages (12 pages, hash routing)

| # | Route | Page | Core responsibility | Source |
|---:|---|---|---|---|
| 1 | `/` | Dashboard | Platform overview & feature entries | `docs/ARCHITECTURE_DESIGN.md` §2 |
| 2 | `/designer` | Designer | AI parametric designer: parameter panel + real-time 3D | same |
| 3 | `/copilot` | DesignCopilot | Design copilot: intent parsing + parameter variants | same |
| 4 | `/projects` | Projects | Project list | same |
| 5 | `/projects/:id` | ProjectDetail | Project detail & model management | same |
| 6 | `/deep-learning` | DeepLearning | Deep-learning designer: training batches, style/generative design | same |
| 7 | `/quality` | Quality | Quality checks & report list | same |
| 8 | `/deliver` | Deliver | Engineering delivery & data handover | same |
| 9 | `/demo` | Demo | Feature demo (incl. VTOL flight physics) | same |
| 10 | `/help` | Help | Help center: 3D knowledge graph, module manuals, documentation system | same |
| 11 | `/community` | Community | Community interaction (messages, reference leads) | same |
| 12 | `/contact` | Contact | Contact & feedback | same |

Note: the VTOL flight physics on the `/demo` page is a deliberate cross-domain technology demonstration—it verifies that the geometry/physics kernel can migrate beyond the automotive domain and is not counted in the automotive platform's feature baseline. The login/account pages are source-sealed at `src/views/Login.vue` and `src/views/Account.vue` (guest access without login; not counted among the 12 routed pages).

## C.4 Automated Tests (~1,027-case baseline, 2026-10-25)

| Test suite | Cases | Result | Source |
|---|---:|---|---|
| algorithm_model pytest (tests/) | 200 | all pass | `docs/VALIDATION_REPORT_20261025.md` (SHA b42e51e4) |
| backend pytest (tests/) | 411 collected (408 passed + 1 skipped + 2 xfailed) | all pass | same |
| frontend vitest | 416 | all pass | same |
| **Total** | **~1,027** | **all green** | same |

**Count verification**: 200 + 411 + 416 = **1,027**. The backend's 1 skip (requires `RUN_REAL_LLM=1`) and 2 expected failures (curvature pipeline migrated to SISA, marked xfail) are listed separately and never mixed into "passed." A separate `test_all.py` one-stop five-module self-check verifies post-assembly runnability and is **not counted in the baseline sum**. Layer shares: algorithm 19.5% / backend 40.0% / frontend 40.5%; backend + frontend total 827 cases (80.5%).
Historical scope (for backtracking only, not the current baseline): the 2026-09-27 snapshot recorded 489 cases (algorithm 200 / backend 178 / frontend 111, plus a 5-module self-check) — source `docs/VALIDATION_REPORT_20260927.md` §1–§2. The 955-case figure (205/388/362) was an intermediate 2026-10 scope and has been superseded by the 2026-10-25 measurement.

## C.5 Core Algorithm Specifications

| Metric | Value | Source |
|---|---|---|
| CarParams parameter vector | 22 dimensions | `docs/evolution_systems_thinking.md` ("22-dim parameters × 176 vertices × 33 surfaces"); `docs/PRODUCT_SPEC.md` §4.2 |
| Body mesh vertices | 176 vertices | `docs/evolution_systems_thinking.md` (magnitude row) |
| NURBS surface patches | 33 surfaces | same; `docs/AUDIT_REPORT_20260810.md` ("17 components, 33 surfaces") |
| Continuity grades | G0 / G1 / G2 — mesh evaluation thresholds G1 < 5°, G2 < 2°; engineering checks judge seam by seam at G0 0.1 mm, G1 1.0° (no separate G2 tolerance) | `docs/ARCHITECTURE_DESIGN.md` §7 legend; `algorithm_model/surface_quality/` |
| Bayesian default optimization space | 14 dimensions (normalized [0,1]) | `docs/bayes_optimization.md` §3; `docs/EVOLUTION_AI_paper.md` ("14-dim default space, GP, EI/UCB, sessions") |
| Gaussian process kernel | isotropic RBF (ℓ=0.25) | `backend/app/bayes_optimizer.py`; Ch. 8 |
| Acquisition functions | EI / UCB | `docs/bayes_optimization.md` |
| Convergence stopping reference | EI minimum improvement 0.01 (`ei_xi`); plateau/convergence confirmed by session observation and human judgment — the code has no `converged` field; automatic dual-criterion convergence is a roadmap item | Ch. 8; `docs/bayes_optimization.md`; `backend/app/bayes_optimizer.py` |
| Geometry export formats | 8 geometric formats (glb/gltf/stl/obj/iges/step/igs/stp) + JSON parameter export; primary: mesh→STL/GLB, NURBS→STEP/IGES; OBJ/GLTF/IGS/STP kept for compatibility | `backend/app/routes/export.py` (SUPPORTED_FORMATS); Ch. 5 |
| Training network | compact MLP (48 hidden units) | `docs/EVOLUTION_AI_paper.md` |

## C.6 Brand Knowledge Base

| Metric | Value | Source |
|---|---|---|
| Brands | 5 brands | `backend/config/brand_design_knowledge.json`; `docs/ARCHITECTURE_DESIGN.md` §3.3; `docs/PRODUCT_SPEC.md` §5 |
| Models | 19 models | same; `src/config/carPresets.js` |

The knowledge base carries brand/model parameters and design-language metadata, supporting semantic query and similarity retrieval (`backend/app/brand_knowledge.py`).

---

**Grand verification**: 152 (route endpoints) + 2 (system endpoints) = **154**; 17 tables; 12 pages; ~1,027 tests (200+411+416, measured 2026-10-25, per `docs/VALIDATION_REPORT_20261025.md`, SHA b42e51e4). All figures agree with `docs/ARCHITECTURE_DESIGN.md`, `docs/api_reference.md`, and `docs/PRODUCT_SPEC.md`. The former scope of 151 routes + 2 system = 153 and the 955-case figure (205/388/362) are historical snapshots, preserved and labeled rather than rewritten.
