# Chapter 7. The Unified Workbench: Information Architecture of 12 Pages

> Author: Quantum Swordsman
> Volume II · Architecture: Giving Complexity Its Proper Place

## 1. The Problem: More Pages, Less Truth?

Frontend projects have a common way of dying. The first page is polished. By the fifth page, everyone writes their own way. By the twelfth, the same project data exists in three versions across three pages, and the same car looks different in two views. Page count itself is not the crime. The disease is that **every page hoards its own copy of state, its own slice of logic, and its own private understanding of the backend.** In the late stages, the team no longer debates "what does the user see" but "which page is telling the truth."

EVOLUTION AI has 12 routed pages: Dashboard, Designer, DesignCopilot, Projects, ProjectDetail, DeepLearning, Quality, Deliver, Demo, Help, Community, and Contact. Together they share 154 backend endpoints — about 12.8 per page. If each page organized its own data and logic, twelve pages would amount to twelve small backends. The proposition of this chapter is: **pages do not restate geometry logic, and state has exactly one source of truth.** A unified workbench is not a unified visual style; it is a unified information architecture. Pages handle presentation and interaction only; data flows from a single store layer, a single API layer, and a single backend contract.

## 2. Principles

### Principle 1. Four-stage orchestration, with pages as the thinnest stage

The full journey of one click is: page → store → API → 19 route modules / 154 endpoints → 17 tables. Page components contain no geometry, no business rules, and no field guessing. They read state from Pinia stores, call the per-domain interfaces exported from `src/api.js` (`projectAPI` through `bayesAPI`), and hand results to rendering. Algorithms converge behind the backend routes, in the `algorithm_model` layer. When a page needs a new capability, the first question should be "which API domain owns this," not "let me compute it inside the component."

### Principle 2. State has a single source of truth

Four stores serve the whole site: auth, designer, project, and ui. Every piece of data has one authoritative home, and pages hold references, not copies. The API layer is equally singular: `api.js` maintains one axios instance (baseURL `/api/v1`), injects the JWT uniformly, and handles 401 uniformly — clearing the token and broadcasting the `evoai:auth-required` event to drive a global login recovery, instead of twelve pages each improvising their own redirect.

### Principle 3. Degradation must be visible in the interface

The unity of a workbench includes a unified way of failing. When the backend is unreachable, the project list falls back to mock data labeled as such. When PyTorch, Ollama, CLIP, or Redis is missing, the corresponding capability area shows a 503 or a "geometric features only" degradation label — never a counterfeit success. Guest mode keeps the whole site readable, with a login prompt appearing when a write is attempted. Capabilities vary in strength; the interface never blurs that fact.

### Principle 4. Copy and language are architecture too

The platform carries full Chinese-English bilingual copy through vue-i18n. Internationalization is not a translation sprint before release; it is part of the information architecture: a term in both languages points to the same contract field, and knowledge-base documents switch with the platform language. A system whose languages disagree is two systems sharing one domain name.

## 3. Case Study: How 12 Pages Share One Truth

<figure class="doc-figure"><img src="../docs/images/en/prod2-image.svg" alt="Twelve-page unified workbench: parameter panel, 3D viewport and quality panel in concert"><figcaption><strong>Figure 7-1 | The workbench on one screen: parameter panel → 3D viewport → quality panel</strong> How to read: the left sliders are a visible slice of the 22-dimensional CarParams; the vehicle profile in the middle is driven live by the parameters and can be dragged and rotated; the right side shows quality readings of the same model. The twelve entries at the bottom correspond to all routed pages. The key conclusion is that the three panel types share one model state — change one parameter and the 3D view and the quality readout change together; there are not three copies of the data.</figcaption></figure>

Take Designer, the platform's core workbench. It offers car-type, style, and brand parameter selection; `carAPI.generate` builds the vehicle with live 3D rendering; and cloud capabilities — dataset statistics, synthetic sample batches, quality evaluation, generative design, parameter optimization — all go through `aiAPI`. There is not one line of geometry code in the page. It does not know how surfaces are lofted; it only knows what the contracts return.

Deliver shows a different kind of unity. The import-modify-export chain (`importExportAPI`) is organized as a single session object: upload a file or JSON parameters to create a session, then query the parameter tree, modify parameters, snapshot, preview in 3D, export in multiple formats, and download — all under one session_id. The page's information structure mirrors the backend's session contract directly, rather than inventing a private frontend model.

DeepLearning and Quality share the pattern of "polling one truth." After a training task is created, the page polls `GET /ai/tasks/{id}` once per second until a terminal state; quality reports are read from `qualityAPI.list`, with historical string reports normalized into structured display. State lives in the backend; pages are observers on a timeline. This is also why the frontend's 416 of the ~1,027 tests are possible at all: they target stores, API modules, and guards, not pixels.

<figure class="doc-figure"><img src="../docs/images/en/prod2-graphic.svg" alt="Parametric body side-view proportions and dimension bounds"><figcaption><strong>Figure 7-2 | One 22-dimensional vector drives four expressions; a page is only one consumer</strong> How to read: the amber dimension lines mark hard parameter bounds (length 4000–6200, wheelbase 2400–3700, and so on); the green profile and the purple reference profile are two instances of the same vector; the four rows on the right show how one vector feeds mesh, NURBS, quality, and export. Change any dimension in a page and all four paths refresh together — the "unity" of the workbench ultimately converges on this vector.</figcaption></figure>

**Cross-Domain Mapping.**

- Here = twelve pages share one Pinia store and one set of API modules; no page keeps a private copy. In a general agent console = session state, tool calls, and artifact preview all derive from one runtime state, so switching views never creates a second truth.
- Here = writes give optimistic feedback, roll back on failure, and report the error explicitly. In an LLM evaluation panel = a rejected score submission must revert to the unsubmitted state rather than leave a fake success on screen.

## 4. Anti-Patterns and Their Costs

**Anti-pattern 1: Pages hoarding state copies.** Every page copies backend data into local variables and processes it privately. The cost is multiple versions of the same data and an endless dispute over "which page is authoritative."

**Anti-pattern 2: Business logic embedded in components.** Geometry conversions, permission checks, and field mappings written inside Vue components. The cost is logic that backend contracts cannot constrain and layered tests cannot cover; change one place, break three.

**Anti-pattern 3: A request style per page.** Some pages use axios, some use fetch, some concatenate URLs by hand. The cost is twelve dialects of authentication, error handling, and degradation — and a 401 that silently vanishes on one page.

**Anti-pattern 4: Silent degradation.** The backend is down, and the page shows an empty table or spins forever. The cost is that users misread "system failure" as "no data," and decisions get built on blank space.

## 5. Operational Checklist

1. When a new page is proposed, first declare which stores and which API domains it consumes, in a header comment or document.
2. Forbid geometry and business rules inside page components; when found, push them down to a store or the backend.
3. All requests go through the single axios instance in `src/api.js`; pages may not build their own HTTP clients.
4. Field-name conversion happens exactly once at the store boundary; raw backend naming must not appear inside pages.
5. Define a degraded state for every page — what it shows and what it labels when the backend is unreachable — and implement it.
6. Route all page copy through i18n keys; new terms enter both languages together.
7. Page tests target stores and API modules (following the existing 416 cases in `src/tests/`), not pixels.
8. Pages that write must use the shared `evoai:auth-required` login flow, not hand-rolled dialog logic.

## 6. Chapter Self-Check

1. Pick any piece of business data. Can you name, within five seconds, which store holds its authoritative version and which endpoint it came from?
2. If you deleted one page entirely, would backend contracts and all other pages be completely unaffected? If not, some logic is in the wrong layer.
3. If the entire backend went down right now, what would your twelve pages each show — twelve accidents, or one designed degradation?
