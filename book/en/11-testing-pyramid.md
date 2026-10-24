# Chapter 11. The Testing Pyramid and the 955-Case Baseline

> Author: Quantum Swordsman
> Volume IV · Engineering: Converging Uncertainty into Delivery

## 1. The Question

The most common misjudgement in AI-native systems is to treat a successful demonstration as a usable system. On a parametric styling platform, moving one slider for vehicle length changes the geometry kernel, the interface contract and the front-end rendering at the same time. A language model answering one specialist question correctly may fail the next. A demonstration proves that one path worked at one moment; testing must answer a different question: after anyone modifies any layer, does the system still keep the promises already made?

Two concrete questions follow. First, given a limited testing budget, at which layer should cases be placed so that the shortest feedback loop yields the strongest fault localisation? Second, how can a set of pass counts become reviewable evidence rather than a ritual of reassurance? This chapter takes the EVOLUTION AI platform's 955-case baseline as its sample and discusses engineering answers to both.

## 2. Principles

**First, price each layer separately instead of spreading effort evenly.** The value and cost of tests follow a pyramid. Lower layers run faster, produce more stable results and localise failures more precisely; higher layers approach real user paths but are slower, more fragile and harder to diagnose. Geometric invariants, numerical boundaries and pure-function behaviour belong in algorithm unit tests. Cross-module fields and state machines belong in back-end integration tests. Component interaction and state synchronisation belong in front-end component tests. End-to-end coverage keeps a few main chains that prove the system still starts and completes one real piece of business.

**Second, a baseline is a contract, and every number carries a date and a definition.** The statement "955 cases pass" means something only when the layer breakdown, the execution commands, and the treatment of skips and expected failures are stated. Once a baseline enters a document it becomes an external promise; every later increase must be re-run and re-defined, never stitched from numbers of different dates.

**Third, a red light matters more than a coverage figure.** Coverage describes which code was executed; a gate answers whether a change may be merged, and one cannot substitute for the other. High coverage without blocking failures is expensive decoration; modest coverage with reliable red lights is a dependable foundation.

**Fourth, every defect must leave a test behind.** Each fix should add a case that fails reliably on the old code. The fix proves that this instance was corrected; the regression case proves it cannot return in the same form. A fix without a case is temporary first aid.

## 3. Anatomy of the Case

The platform's current baseline is 955 cases across three independent suites: 205 in the algorithm layer, 388 in the back end, and 362 in the front end. The back-end suite includes one skip (requiring `RUN_REAL_LLM=1` to call a real model) and two expected failures: the curvature pipeline has migrated to SISA and cannot be imported platform-side, so both cases are marked xfail. The three result classes are reported separately—skips and expected failures are neither counted as passes nor hidden as failures. The algorithm directory also contains `test_all.py`, a one-stop five-module self-check covering full-vehicle modelling, surface quality, simulated annealing, storyboard generation and the full pipeline. It sits outside the 955 sum because it tests assembled runnability rather than independent cases.

<figure class="doc-figure"><img src="../docs/images/en/test-pyramid.svg" alt="The platform testing pyramid: four verification layers, from algorithm units (200) and front-end components (111) up to back-end API integration (178) and live browser checks"><figcaption><strong>Figure 11-1 ｜ The platform testing pyramid: four verification layers</strong> How to read: from bottom to top—algorithm units, front-end components, back-end API integration and live browser checks; the lower the layer, the faster and more stable it is. The 200/111/178 figures are the snapshot of 27 September 2026 (a historical definition); the current baseline has since evolved to 205 algorithm, 388 back-end and 362 front-end cases, 955 in total. The point is the structure, not any single number: the algorithm layer is largest because mathematics is the root; E2E stays minimal as a smoke check.</figcaption></figure>

The three layers account for 21.5%, 40.6% and 37.9%; back end plus front end is 78.5%. This is not arbitrary: with 19 route modules and 153 HTTP endpoints against only 12 pages, the endpoint density is roughly 12.8 per page. The interface surface far exceeds the page surface, so the back end must carry heavier contract verification, while front-end tests concentrate on Pinia state, component rendering, API modules and route guards.

The evolution of the numbers must be equally reviewable. The snapshot of 9 August 2026 recorded 201 cases, all passing; 27 September 2026 recorded 489 (200 algorithm, 178 back end, 111 front end, plus a five-module self-check); 11 October 2026 recorded 483 items (341 back-end passes, one skip, two expected failures, 142 front-end passes), with 12 topology-closure, two guest-mode and three admin-console cases listed separately. The current 955-case baseline dates from after October 2026. The four sets belong to different dates and definitions: any citation must state its time point, an old snapshot cannot replace the current baseline, and definitions must not be added together to manufacture growth.

<figure class="doc-figure"><img src="../docs/images/en/october-test-results.svg" alt="Snapshot of 11 October 2026: 341 back-end integration, 142 front-end component, 12 topology-closure, 2 guest-mode and 3 admin-console cases, 483 items with zero failures"><figcaption><strong>Figure 11-2 ｜ Snapshot of 11 October 2026: 483 items executed across five layers, zero failures</strong> How to read: the five bars are back-end integration (341), front-end components (142), topology closure (12), guest mode (2) and the standalone admin console (3); the badges state the back-end composition of 341 pass / 1 skip / 2 xfail. The value of the figure is definitional transparency: skips and expected failures are listed explicitly instead of being swallowed by the words "all green".</figcaption></figure>

As for content, the platform turns its least negotiable constraints into assertions. The closed-body programme added 12 cases in `test_car_topology_closure.py`, covering the sealing of seven opening classes: front fascia panel, tailgate panel, A/C-pillar wedges, cowl strip, underbody tray, wheel-arch liners and interior shelf. Guest mode added two cases: a token-less request to a protected endpoint must resolve to the built-in guest account, and starting production with `GUEST_MODE` enabled must fail. The standalone admin console added three: `/admin/` returns the admin HTML, static assets are reachable, and `unsafe-eval` appears only in the CSP of the admin document. The common property is that one assertion locks one non-negotiable boundary, rather than merely inflating a count.

Five defects recorded in the validation report show how "a fix must carry verification" works: a statistics-dictionary contract drift (callers needed `total_vertices`), a fixture using an outdated box reshape for the section mesh, `build_body` construction order disturbed by automatic processing, `run_full_pipeline` reshaping from an eight-vertex box and crashing immediately, and inconsistent endpoint counts in documents (113/116). Each was given a repair location and a verification path. The unification to 118 endpoints belongs to the 27 September 2026 snapshot; the current definition is 153 (151 route endpoints plus two system endpoints). Old numbers are retained and labelled rather than erased—this is itself part of an auditable baseline.

## 4. Anti-Patterns and Their Costs

**The ice-cream cone.** Pouring most of the budget into end-to-end tests looks closest to the user but produces long feedback loops and frequent random failures. A failed geometry assertion may originate in the proxy, authentication, serialisation or rendering. The team spends its time re-running and guessing instead of localising.

**Coverage worship.** Large amounts of code are executed to make a number look good, but effective assertions are missing. A passing test proves only that no exception was raised, not that the output is correct. Such a suite creates false confidence during refactoring.

**Mocking everything.** Unit layers replace the database, authentication and file system with mocks, so the integration layer disappears. Real failures tend to occur at boundaries: drifted field names, uncommitted transactions, a missing terminal state in a state machine.

**Letting tests take the guest bypass.** If the test environment inherits `GUEST_MODE` during the account-archiving period, every 401/403 case is silently admitted as a guest and the semantics of authorisation collapse. The platform therefore forces `GUEST_MODE=false` in `backend/tests/conftest.py`, making "tests must exercise real authentication" a hard constraint.

**Number drift.** A document says 489 while the code has reached 955. The cost is not one wrong citation but the loss of credibility of the entire evidence system; afterwards every number is suspect.

**Treating expected failure as success.** xfail is an honest label, but it needs an owner and an exit condition. Left unattended, it becomes hidden debt that conceals a real capability gap.

## 5. Operational Checklist

1. Fix three layer boundaries and commands: run `python -m pytest tests/ -q` under `algorithm_model/`, `python -m pytest -q` under `backend/`, and `npx vitest run` at the repository root; fixtures are not borrowed across layers.
2. Make every command independently reproducible in a clean environment, without relying on a developer's residual state.
3. Treat red as a block: the main branch must be fully green before merge; skips and expected failures are listed explicitly with reasons (e.g. `RUN_REAL_LLM=1`, the SISA migration).
4. Record the baseline in a table: date, command, per-layer counts, skips and xfails; keep old rows when updating.
5. Label historical snapshots with date and definition: 201 (9 Aug), 489 (27 Sep) and 483 (11 Oct) are snapshots and are never mixed with the current 955.
6. Prioritise contract tests: field names, enum values, state transitions and error codes need assertions, so that "it returned" never substitutes for "it returned correctly".
7. Isolate the test environment: `conftest.py` forces guest mode and debug switches off, uses separate databases and temporary directories, and never touches production keys.
8. Attach a regression case to every defect fix: the repair commit includes a test that fails on the old code.
9. Classify warnings: register known warnings as owned, non-blocking items and review periodically; never silently convert a warning into a pass.
10. Run the full suite periodically: update the baseline from that day's output, not from an earlier report.

## 6. Self-Check

1. Can your baseline be reproduced in a clean environment with one command? If not, is the gap in environment isolation, data preparation or command packaging?
2. In your last three defect fixes, how many left a regression case that fails on the old code? For those that did not, who carries the risk?
3. Do all the test numbers you cite carry a date and a definition? When documents and code disagree, what rule does your team use to decide which is the fact?
