# Chapter 4 Five-Layer Architecture and Thin Orchestration

> Author: Quantum Swordsman
> Volume II · Architecture: Giving Complexity Its Proper Place

## 1. The Problem: Which Layer Should Complexity Live In?

A familiar accident scene: the frontend drags the "vehicle length" slider, the request lands in some route handler on the backend, and inside that handler sit three hundred lines of geometry computation that write to the database midway and return a bare dict on failure. Six months later nobody dares touch the function—the geometry expert dare not, because authentication is wired in; the backend engineer dare not, because transactions are wired in; the frontend dare not, because the response shape is historical. The complexity has not disappeared. It has simply moved into the wrong floor.

The old sermon about layered architecture gains a new reason in AI-native systems: AI components keep evolving, while web contracts must stay stable. If geometry algorithms grow inside HTTP handlers, every algorithm upgrade is an interface gamble. If authorization logic seeps into the algorithm package, every permission change re-runs the numeric test suite. The proposition of this chapter: **the web layer only orchestrates, and the algorithm kernel can be installed, tested, and replaced independently.** Complexity goes to its proper floor not by convention but by hard constraints on dependency direction.

<figure class="doc-figure"><img src="../docs/images/en/arch2-layers.svg" alt="Sliced view of the five-layer architecture"><figcaption><strong>Figure 4-1 ｜ The five-layer architecture in slices: L1 frontend → L2 access → L3 backend → L4 algorithm → L5 infrastructure</strong> Read it this way: the top-down slices show dependency direction, and each layer is annotated with its key components and external protocols (HTTP/JSON, proxying, function calls, ORM). L4 is an independently installable package with no FastAPI dependency, testable without L1–L3. There is exactly one layering constraint: upper layers may depend on lower layers; lower layers must not know the upper ones exist.</figcaption></figure>

## 2. Principles

**Principle 1: Dependencies point one way; lower layers never look up.** The value of layering is not a prettier diagram but monotonic dependency: an upper layer may call a lower one, and a lower layer must not import a single symbol from above. Once this holds, every layer can be understood and replaced alone. Once it is broken—even by one "convenient" backward import—layering degenerates into folder naming.

**Principle 2: The web layer is a thin shell; orchestration does not compute.** An HTTP handler has a fixed list of duties: validate parameters, authorize, persist, orchestrate, map errors. It contains no geometry formulas, no optimization mathematics, no hand-rolled business rules. The test is plain: if a handler exceeds the three-beat rhythm of receive—delegate—return, it is secretly growing a second heart.

**Principle 3: The algorithm kernel is independently installable.** Algorithmic capability is the system's heavy asset. It deserves its own package structure, its own entry points, its own dependency manifest, and its own test suite. Whether `pip install` plus the full numeric test suite runs on a machine with no database and no web framework is the touchstone of algorithmic independence.

**Principle 4: Capability boundaries are drawn between layers.** Detection and degradation of optional capabilities (PyTorch, CLIP, Redis, LLMs) must happen on inter-layer interfaces: the lower layer truthfully reports what it lacks, and the upper layer chooses a degradation path and labels it. Failures are not hidden inside layers; success is not fabricated between them.

## 3. Case Anatomy: Five Layers, Each in Its Place

EVOLUTION AI divides into five layers. L1, the frontend: Vue 3.4 + Vite 5 + Three.js 0.166, twelve hash-routed pages. L2, access: Vite Dev Proxy in development, Nginx in production, a unified `/api/v1` prefix, and a cpolar HTTPS tunnel for public exposure. L3, backend services: FastAPI 0.104 + Pydantic v2, 19 route modules serving 153 endpoints—151 routed plus 2 system endpoints declared in `main.py`. L4, algorithms: the independently installable `algorithm_model` package with four subpackages (car_modeling, freeform, surface_quality, storyboard). L5, infrastructure: SQLite with SQLAlchemy 2.0 across 17 ORM tables, file storage, optional Redis, and Docker Compose deployment.

Evidence of the thin shell lives in the endpoints. Take the Bayesian module: the seven endpoints in `backend/app/routes/bayes.py` do exactly four things—validate the parameter space (non-empty, unique names, lower bound below upper), delegate to the session registry in `bayes_optimizer.py`, map the optimizer's explicit exceptions to HTTP 400/404/409, and persist observations. The Cholesky factorization of the Gaussian process, the scoring of the 4096-point candidate pool, and the EI/UCB computation all live in the pure NumPy/SciPy implementation on the L4 side; not a single formula appears in the route file.

Evidence of algorithmic independence lives in the tests. L4's 205 pytest cases run in about four seconds with no web component present, and `algorithm_model/test_all.py` provides a one-command, five-module self-check (vehicle modeling, surface quality, simulated annealing, storyboard generation, and the full pipeline). Neither suite imports FastAPI, touches a database, or starts an HTTP server. L4 can be cloned alone onto any machine and verified—that is the operational definition of "independently installable, testable, replaceable." When the geometry kernel is upgraded, the external semantics of all 153 endpoints remain unchanged; when a page is redesigned, the algorithm package is not implicated.

<figure class="doc-figure"><img src="../docs/images/en/whitepaper-arch.svg" alt="Platform four-layer-plus-pipeline architecture overview"><figcaption><strong>Figure 4-2 ｜ The platform overview: read protocols and deployment paths separately</strong> Read it this way: the four layers—frontend, backend, algorithm, data—are annotated with their call protocols, while the right column lists four deployment paths (development, production, public tunnel, static publishing). The key reading is dependency monotonicity: every arrow points downward, and none points back up.</figcaption></figure>

## 4. Antipatterns and Their Cost

**The fat controller.** Business logic inside route handlers; geometry, transactions, and authorization tangled together. The cost: changing any one of the three requires understanding all of them, regression failures cannot be localized, and the function becomes a legacy nobody dares touch.

**Lower layers looking up.** The algorithm package imports the web framework's exception classes; the data layer reads request context. It saves one parameter passing and places the weight of the whole building on a single point of the foundation—afterward, every independent L4 test must first erect L3 scaffolding.

**Cross-layer shortcuts.** The frontend bypasses orchestration to call the algorithm service directly, or orchestration bypasses the ORM to hand-assemble SQL. Every shortcut wears the inter-layer contract down a notch; by the time a layer needs replacing, the contract exists in name only.

**Fabricated success between layers.** A lower dependency goes missing and the upper layer pads the response with fake data. The cost, as Chapter 1 established: trust can be overdrawn only once. The inter-layer interface is the last place in the system where the truth can still be told; if it falls, honesty elsewhere is meaningless.

## 5. Operating Checklist

| Item | Pass criterion | Evidence in this repository (file or command) |
|---|---|---|
| Dependency direction is monotonic | No lower layer imports any upper-layer symbol | L4 `algorithm_model/` has zero FastAPI dependency; constraint documented in `docs/ARCHITECTURE_DESIGN.md` |
| Handlers are thin shells | Each handler only validates, authorizes, persists, orchestrates, maps errors | `backend/app/routes/bayes.py` and the other 19 modules serving 153 endpoints |
| The algorithm package installs alone | Numeric tests pass with no web or database present | `pytest algorithm_model/tests` (205 cases, ~4 s); `python algorithm_model/test_all.py` |
| Inter-layer protocols are explicit | One protocol per boundary: HTTP/JSON, function calls, ORM | L2 `/api/v1` prefix; L3–L4 via `algorithm_model/api.py`; L5 via SQLAlchemy 2.0 |
| Capability probing happens between layers | Missing optional capabilities are reported below and degraded—and labeled—above | PyTorch/CLIP/Redis degradation contracts; 503 branches among the 388 backend tests |
| Each layer verifies independently | Three suites with separate commands and directories | 205 algorithm + 388 backend + 362 frontend = 955 |

## 6. Chapter Self-Check

1. Can you copy the algorithm directory onto a machine with no web framework and pass its full test suite with one command?
2. Can you replace one layer's implementation wholesale without changing any endpoint's external semantics?
3. Does your architecture diagram contain any dependency arrow pointing upward? If so, why must it exist?
