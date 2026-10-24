# Appendix B · Checklists

> Author: Quantum Swordsman

Four checklists for review and pre-delivery self-inspection. Each line follows the format: **check item —— pass criterion —— repository evidence (file/command)**. All evidence paths are relative to the repository root.

---

## B.1 Architecture Checklist

- [ ] No cross-layer calls in the five-layer split —— the frontend only touches `/api/v1`; the algorithm layer imports no routes —— `docs/ARCHITECTURE_DESIGN.md` §2–§4; `backend/app/routes/*.py` orchestrate only
- [ ] Thin-shell orchestration holds —— route functions only validate, authenticate, and orchestrate; domain logic lives in `backend/app/` and `algorithm_model/` —— `docs/ARCHITECTURE_DESIGN.md` §3.2
- [ ] Algorithm core installs and tests independently —— `algorithm_model/` has no FastAPI dependency; pytest runs standalone —— `python -m pytest tests/ -q` (in algorithm_model, 205 cases all pass)
- [ ] Contracts frozen before implementation —— endpoints, tables, and state machines are documented and match the code —— `docs/api_reference.md`; `docs/ARCHITECTURE_DESIGN.md` §5
- [ ] One parameter vector drives four representations —— the 22-dim CarParams drives mesh/NURBS/quality/export with no secondary fitting —— `algorithm_model/car_modeling/car_params.py`; `docs/PRODUCT_SPEC.md` §4.2
- [ ] A single source of truth for state —— Pinia (auth/designer/project/ui); pages never restate geometric logic —— `src/stores/`; `docs/ARCHITECTURE_DESIGN.md` §2
- [ ] Optional capabilities degrade honestly —— missing PyTorch/Ollama/Redis/CLIP yields 503 or degradation, never fake success —— `docs/PRODUCT_SPEC.md` §6; `backend/app/clip_semantics.py`
- [ ] 17 ORM tables match the documentation —— model classes in `database.py` correspond item-for-item to the §5 table —— `backend/app/database.py`; `docs/ARCHITECTURE_DESIGN.md` §5
- [ ] All 19 route modules mounted —— `main.py` include_router covers every module —— `backend/app/main.py`; `docs/ARCHITECTURE_DESIGN.md` §3.1
- [ ] Unified LLM proxy with a fixed registry —— providers go through `llm_proxy.py`; no scattered direct connections —— `backend/app/routes/llm_proxy.py`; `docs/ARCHITECTURE_DESIGN.md` §3.1
- [ ] Centralized configuration —— a single pydantic-settings entry; production SECRET_KEY fails fast —— `backend/app/config.py`

## B.2 Delivery Checklist

- [ ] Three-layer test baseline fully green —— algorithm 205 / backend 388 / frontend 362, totaling 955 —— `python -m pytest tests/ -q`; `python -m pytest -q` (backend); `npx vitest run`
- [ ] One-stop self-check passes —— test_all.py five modules all pass (excluded from the 955 sum) —— `python test_all.py` (algorithm_model directory)
- [ ] Skips and expected failures honestly labeled —— 1 skip (RUN_REAL_LLM) + 2 xfails listed separately —— `docs/ARCHITECTURE_DESIGN.md` §9
- [ ] Build artifacts interpretable —— `npm run build` warning-free with hashed artifact names —— `package.json`; `backend/app/static/admin/assets/`
- [ ] Deployment topology reproducible —— docker-compose validates required environment variables —— `deploy/docker-compose.yml`; `deploy/.env.example`
- [ ] All 12 frontend page routes reachable —— hash-route table matches documentation —— `docs/ARCHITECTURE_DESIGN.md` §2 route table
- [ ] 19 modules / 151 endpoints auditable one by one —— api_reference counts match ARCHITECTURE_DESIGN §3.1 —— `docs/api_reference.md`
- [ ] Import → modify → export chain walkable —— the import_export 11-endpoint session flow smokes green —— `docs/PRODUCT_SPEC.md` §4.7
- [ ] Bayesian session lifecycle usable —— create → suggest → observe → best/samples closed loop —— `docs/bayes_optimization.md` §3; `backend/app/bayes_optimizer.py`
- [ ] Brand knowledge base queryable —— 5 brands / 19 models metadata loads with semantic retrieval —— `backend/config/brand_design_knowledge.json`; `src/config/carPresets.js`
- [ ] Milestone baselines carry date and scope —— every test figure cited with its timestamp; no stale snapshot as the current baseline —— `docs/VALIDATION_REPORT_20260927.md` (historical 489 scope); 955 is the post-2026-10 baseline
- [ ] Release notes synchronized with versions —— README/CHANGELOG match the actual build —— root `README.md` testing section

## B.3 Security Checklist

- [ ] Production SECRET_KEY fails fast —— startup aborts when unset —— `backend/app/config.py`
- [ ] Security headers uniformly injected —— X-Content-Type-Options / X-Frame-Options / CSP / Referrer-Policy / Permissions-Policy / Cache-Control; `server: uvicorn` removed —— `backend/app/main.py` middleware; `docs/ARCHITECTURE_DESIGN.md` §7
- [ ] CORS explicit whitelist —— production forbids ACAO `*` + credentials, with ASGI correction middleware —— `backend/app/main.py`; `docs/ARCHITECTURE_DESIGN.md` §7
- [ ] SSRF protection effective —— outbound requests (LLM/texture) enforce host whitelists and scheme checks —— `backend/app/routes/llm_proxy.py`; Ch. 9, 13
- [ ] JWT issue/verify closed loop —— `get_current_user` / `get_optional_user` injected across protected endpoints —— `backend/app/security.py`
- [ ] API keys encrypted at rest —— Fernet encryption; (user_id, provider) unique —— `backend/app/database.py` (api_keys table); `docs/ARCHITECTURE_DESIGN.md` §5
- [ ] Guest mode denies sensitive operations by default —— unauthenticated read-only pass; admin endpoints still require admin —— `docs/ARCHITECTURE_DESIGN.md` §2 access control
- [ ] Exception handling leaks no internals —— StarletteHTTPException / RequestValidationError / 405 unified; error responses carry CORS —— `backend/app/main.py`; `docs/ARCHITECTURE_DESIGN.md` §7
- [ ] Admin console independently guarded —— `/admin/` serves its HTML and static assets; `unsafe-eval` confined to the admin CSP —— topology/admin 3 tests (`docs/ARCHITECTURE_DESIGN.md` §9)
- [ ] Production GUEST_MODE startup constraint —— enabling GUEST_MODE in production must fail startup (locked by tests) —— guest-mode 2 tests (`docs/ARCHITECTURE_DESIGN.md` §9)
- [ ] Upload type and size validated —— model uploads pass whitelist and size limits —— `backend/app/routes/model.py`
- [ ] Keys never stored in plaintext nor logged —— repo-wide scan finds no plaintext keys or log leakage —— `backend/app/security.py`; `backend/app/routes/auth.py`

## B.4 Documentation Checklist

- [ ] Key figures consistent repo-wide —— 19 modules / 153 endpoints / 17 tables / 12 pages / 955 tests agree across ARCHITECTURE_DESIGN, PRODUCT_SPEC, and README —— `docs/ARCHITECTURE_DESIGN.md` §3.1 §5 §9; `docs/PRODUCT_SPEC.md` §5
- [ ] Endpoint counting scope stated —— 151 routes + 2 system = 153, cross-checked with GET 75 / POST 63 / PUT 4 / DELETE 9 —— `docs/ARCHITECTURE_DESIGN.md` §3.1
- [ ] Historical figures preserved and dated —— 2026-09-27's 489 and the historical 118 scope are timestamped, never rewritten —— `docs/VALIDATION_REPORT_20260927.md`
- [ ] Documents checked against source —— no documentation drift: every table row maps to code —— `docs/ARCHITECTURE_DESIGN.md` §5 vs `backend/app/database.py`
- [ ] Every figure carries a reading guide —— captions include "how to read / takeaway" —— `<figcaption>` blocks in `docs/ARCHITECTURE_DESIGN.md`
- [ ] Chinese and English docs mirror each other —— `docs/` and `docs/en/` correspond chapter-by-chapter with identical figures —— `docs/en/ARCHITECTURE_DESIGN.md`
- [ ] Help-page knowledge graph in sync —— the 12-document / 4-layer graph matches the documentation system —— `docs/PRODUCT_SPEC.md` §4.11; `src/views/Help.vue`
- [ ] References traceable —— external literature goes to Appendix D; repository docs use relative paths —— `book/en/appendix-d-references.md`
- [ ] Terminology unified —— first occurrence bilingual; Appendix A is authoritative —— `book/en/appendix-a-glossary.md`
