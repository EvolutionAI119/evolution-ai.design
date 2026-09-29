# EVOLUTION AI Technical Whitepaper

> Version: v1.2 (2026-09-27)
> Document ID: EVOLUTION-AI-WP-2026
> Audience: R&D managers and technical decision-makers in automotive styling
> Reading guide: concepts & value in Chapters 1–3; capability list in Chapter 4; architecture & integration in Chapters 5–6; trustworthiness & evolution in Chapters 7–9

---

## 1. Executive Summary

EVOLUTION AI is an AI styling platform for automotive Class-A surface development, with the product claim of "**from one sentence to a 3D full vehicle**." It restructures the traditional sketch-driven styling process into a parameter-driven engineering flow:

```
Concept parameters → parameterized modeling → AI optimization → quality analysis → engineering delivery
```

Current platform scale (v1.2; all figures anchored to source code):

| Dimension | Scale |
|---|---|
| Frontend | Vue 3 + Vite + Three.js; 11 pages, hash routing + global login guard |
| Backend | FastAPI + Pydantic v2 + SQLAlchemy 2.0; 16 route modules / 118 HTTP endpoints |
| Data | SQLite; 11 ORM tables (including Fernet-encrypted API-key storage) |
| Algorithm | 5 algorithm packages: parameterized full vehicle, NURBS free-form kernel, surface-quality evaluation, storyboard generation & presentation |
| Test baseline | 489+ automated cases (200 algorithm / 178 backend / 111 frontend) plus the one-stop five-module self-check |

Three engineering positions:

1. **Signal, never simulate** — when a dependency is missing, explicitly report unavailable rather than returning fabricated metrics.
2. **Thin-shell orchestration; no rewriting algorithms** — the web layer only orchestrates and persists; geometric and intelligent capabilities reside in independently installable algorithm packages.
3. **Full-chain auditability** — parameters, samples, scores, variants, and training tasks are traceable and reversible.

---

## 2. Industry Background and Problem Definition

### 2.1 Structural Bottlenecks of the Traditional Styling Process

| Link | Traditional approach | Bottleneck |
|---|---|---|
| Concept expression | Hand-rendered sketches | Subjective creativity hard to quantify and reuse |
| Surface construction | Engineers reverse-modeling from lines | Design intent lost in translation |
| Quality verification | Manual surface-by-surface inspection | Long cycles; standards depend on personal experience |
| Option iteration | Week-level round trips | Proposal count limited by manpower |
| Knowledge retention | Scattered in personal files | Organizational knowledge cannot accumulate |

### 2.2 New Demands from Electrification and Intelligence

- Styling hard points change (no front-cabin constraint, higher wheel-base ratio); the parameter space must be redefined;
- Software-defined vehicles require styling and engineering data to collaborate in one digital stream;
- AI capabilities (generative models, visual semantics, LLM experts) must be **reliably** incorporated into engineering rather than remaining demos.

### 2.3 EVOLUTION AI's Answer

Unify design intent and engineering hard points through a **parameter space**; achieve data-efficient automatic search through **Bayesian optimization**; guarantee engineering deliverability through **precise NURBS geometry**; extend creative boundaries through a **heterogeneous AI fusion layer** (vision models + deep learning + LLMs); and orchestrate all five into a closed loop on a web platform.

---

## 3. Platform Overview

<figure class="doc-figure">
  <img src="docs/images/en/product-journey.svg" alt="End-to-end user journey" loading="lazy">
  <figcaption><strong>Fig. 3-1 End-to-end user journey: guest → creator → delivery (aligned with the four-level RBAC)</strong>How to read: Three role swimlanes and a serpentine main line — guests browse freely while write actions trigger the amber login prompt; signing up unlocks parametric modeling, AI tools and Bayesian tuning; the green row is admin-owned review and delivery, purple is operations. The right panel lists six journey design principles.</figcaption>
</figure>

### 3.1 Five User Types and Their Value

| Role | Core need | Platform value |
|---|---|---|
| Styling designer | Fast generation and comparison | Second-level parameterized full vehicles, variant comparison |
| Project lead | Project, model, workflow management | Collaboration across 11 pages, full-chain visible status |
| Surface/quality engineer | Class-A inspection and delivery | G0/G1/G2 grading, multi-format export |
| ML engineer | Training tasks and samples | Backend PyTorch training, Bayesian sample bridge |
| Registered user/admin | Account and permissions | Password/WeChat login, encrypted API-key management |

### 3.2 The Ten Pages

| Page | Path | Function |
|---|---|---|
| Dashboard | `/` | Capability navigation and platform overview |
| Designer | `/designer` | Core parameterized-design workbench |
| Projects | `/projects` | Project CRUD (with mock fallback) |
| Project Detail | `/projects/:id` | Models, workflows, variants |
| Deep Learning | `/deep-learning` | Training tasks, generative design, Bayesian linkage |
| Quality | `/quality` | Quality checks and report history |
| Deliver | `/deliver` | CAD import/re-parametrization, format export |
| Demo | `/demo` | Vehicle display and motion demos |
| Login | `/login` | Password / WeChat-OAuth login |
| Account | `/account` | Profile and LLM API-key configuration |

### 3.3 Four End-to-End Business Flows

1. **Parameterized conceptual design**: parameter input → 3D full vehicle → cloud batch/evaluate/generate/optimize → save variants;
2. **CAD import / re-param / export**: upload → parse parameters → modified preview → multi-format download;
3. **Quality-driven iteration**: quality check → reports/history → return to the design side to adjust;
4. **ML training loop**: create a training task → poll metrics → samples produced through the Bayesian container.

---

## 4. Core Capability System

### 4.1 Parameterized Full-Vehicle Modeling

- **22-dimension CarParams**: primary dimensions (L/W/H/wheelbase), section lengths (hood/cabin/trunk/front/rear overhang), ground clearance, styling parameters (roof arc, windshield rake, rear-glass angle, belt line, fender prominence, wheel-arch bulge), glass depth, wheels (radius/width/spoke count), lights (width/height);
- Parameters carry **boundary validation** (e.g. L ∈ [3.5, 6.0] m); out-of-range values raise explicit errors;
- Section-based body: 48 sections along the vehicle length generate a continuous shell; the `process` switch controls whether construction order is preserved;
- Full-vehicle assembly outputs 10 independent part meshes, operable individually or merged for GLB export.

### 4.2 The NURBS Free-Form Kernel (freeform)

- A self-developed lightweight kernel: NURBS curve/surface basis functions, knot vectors, swept surfaces, fillet surfaces, blend surfaces;
- Writes engineering-grade STEP without any heavy CAD kernel (`step_writer.py`) and provides NURBS body STEP export;
- The continuity checker outputs pair-by-pair deviation reports (TXT/CSV) at 0.1 mm positional / 1.0° angular tolerance, supporting four end-continuity schemes (shared boundary, G1 join, attached ends, etc.).

### 4.3 Surface-Quality Evaluation and Optimization

- **G0/G1/G2 grading**: G1 threshold 5°, G2 threshold 2°;
- **Reflection-line score**: curvature uniformity × 0.5 + smoothness × 0.5;
- **Overall grade**: A (G2 > 85% and reflection > 0.7) / B (G2 > 70% and reflection > 0.5) / C (G2 > 50%) / D;
- **Simulated-annealing smoothing**: objective of squared normal-jump sum, Metropolis acceptance, exponential cooling; suited to local smoothing after hard points freeze.

### 4.4 Bayesian Optimization

- **14-dimension styling space**, RBF-kernel Gaussian process (Cholesky solve) plus EI/UCB acquisition;
- Random space-filling with fewer than 2 observations, then GP-driven;
- Full session lifecycle: create → suggest → observe → best → samples;
- **Sample bridge**: observations export to a training format compatible with `/ai/train`, so real optimization data gradually replaces synthetic samples.

### 4.5 Deep-Learning and LLM Fusion

| Capability | Implementation | Degradation strategy |
|---|---|---|
| Styling-parameter classification/regression | Backend-thread PyTorch training | Explicitly unavailable without PyTorch |
| Texture semantic analysis | Six-axis CLIP scoring | Falls back to geometric features, marked |
| NURBS expert dialogue | Local Ollama / LLM interface | Explicit client error without a key |
| Unified multi-model proxy | 7 LLM providers; Fernet-encrypted keys | Per-provider status visible |

### 4.6 Knowledge-Expression Assets

- **Storyboard system**: 3 built-in templates (car_promotion / tech_demo / minimal_showcase), duration scaling, rendered to Markdown/HTML;
- **Design meta-theory**: Love's nine levels and the ten-dimension autonomous knowledge system (see [design_meta_theory.md](design_meta_theory.md));
- **Methodology and design philosophy**: see [methodology.md](methodology.md) and [design_philosophy.md](design_philosophy.md).

---

## 5. Technical Architecture

<figure class="doc-figure">
  <img src="docs/images/en/whitepaper-arch.svg" alt="Platform architecture: four layers and the deployment channel" loading="lazy">
  <figcaption><strong>Fig. 5-1 Platform architecture: four layers and the deployment channel</strong>How to read: Four layers top-down (Vue 3 frontend, FastAPI backend, standalone algorithm layer, data layer) with call types annotated between layers; the right channel covers development, production, public tunnel and static publishing. Layering rule: upper layers depend on lower ones, never the reverse.</figcaption>
</figure>

### 5.1 Five-Layer Architecture

| Layer | Content |
|---|---|
| L1 Frontend | Vue 3 + Vite + Three.js + Element Plus + Pinia; 11 pages, bilingual i18n, global guard |
| L2 Gateway | Vite dev proxy / Nginx; `/api/v1` → FastAPI:8000; public access via cpolar HTTPS tunnel |
| L3 Backend | FastAPI 0.104 + Pydantic v2; 16 thin-shell route modules / 118 endpoints |
| L4 Algorithm | Independently installable algorithm_model package: car_modeling / freeform / surface_quality / storyboard |
| L5 Infrastructure | SQLite + file storage; optional Redis (degrades to in-process sessions); background training threads |

### 5.2 Data Model (11 ORM Tables)

`projects`, `model_files`, `workflows`, `workflow_steps`, `quality_reports`, `parameter_sets`, `model_variants`, `users`, `api_keys` (Fernet-encrypted), `parameter_records`, `training_tasks`.

### 5.3 Authentication and Security

- JWT (login/WeChat) with a global route guard;
- Training and API-key endpoints enforce authentication; the LLM proxy optionally does;
- API keys are stored with Fernet symmetric encryption; fail-fast if `SECRET_KEY` is missing in production.

See [ARCHITECTURE_DESIGN.md](ARCHITECTURE_DESIGN.md) and [api_reference.md](api_reference.md) for details.

---

## 6. Deployment Forms

| Form | Description |
|---|---|
| Local development | Frontend 5173 + backend 8000 with Vite proxy; a standalone launch script brings up all three services (tunnel/backend/frontend) |
| Public demo | cpolar HTTPS tunnel; static site published to `evolution-ai.design` via GitHub Pages (gh-pages branch + CNAME) |
| Data | SQLite by default with zero external dependencies; file storage configurable |

Demo account: `demo@evolution-ai.design` (demonstration use).

---

## 7. Quality and Trustworthiness Baseline

| Layer | Framework | Cases | Scope |
|---|---|---:|---|
| Algorithm | pytest | 200 | NURBS math, sweep/fillet, constructors, quality, SOP |
| Backend | pytest | 178 | Routes, schemas, optimization services, security, persistence |
| Frontend | vitest | 111 | Stores, components, API modules, guards |
| Self-check | test_all.py | 5 modules | One-stop end-to-end sanity gate |

**Trusted-degradation contract**: no PyTorch → training fails explicitly; no LLM key → explicit client error; no CLIP weights → geometric-feature fallback marked; no Redis → in-process sessions. Every path follows "signal first."

For the latest validation record, see [VALIDATION_REPORT_20260927.md](VALIDATION_REPORT_20260927.md).

---

## 8. Boundaries and Evolution Roadmap

### 8.1 Current Boundaries (Honest Statement)

- The 22 explicit parameters are explainable but cannot express arbitrary free gestures or local sculpting;
- The isotropic RBF GP plus random-pool acquisition is relatively simple; higher dimensions need anisotropic/learnable length scales;
- QLoRA-style organizational project-history fine-tuning is not yet delivered;
- Manufacturing, interference, and aerodynamic objectives are only partially modeled — objective-function design is a greater domain challenge than the optimization mathematics.

### 8.2 Evolution Directions

1. **Parameterization upgrade**: sketch/learned conditioning layers, NURBGen-style generative primitives;
2. **Surrogate upgrade**: multi-fidelity modeling (cheap mesh curvature + expensive precise NURBS evaluation);
3. **Data loop**: real Bayesian campaigns continuously replace synthetic samples and support auditable fine-tuning;
4. **Knowledge systematization**: design meta-theory → styling-language paradigm → organizational knowledge assets.

---

## 9. Closing

EVOLUTION AI demonstrates that the key technologies of modern Class-A surface development — precise NURBS geometry, data-efficient Bayesian optimization, visual-language semantics, and large models — can be combined into one trustworthy web platform rather than isolated tools. The parameter-driven dual-geometry pipeline, the GP+EI/UCB optimizer with its training-data bridge, and the heterogeneous AI fusion layer with truthful degradation jointly shorten the loop from conceptual proportion to engineering STEP output while keeping every result editable and auditable.

---

*Every scale statement in this whitepaper is anchored to the v1.2 source; for validation evidence see the platform validation report, and for academic treatment see the technical paper.*
