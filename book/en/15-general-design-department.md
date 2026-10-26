# Chapter 15 · The General Design Department: A Human–Machine Hall for Deliberation

> Author: Quantum Swordsman (量子剑客)
> Volume V · Organization: how humans and machines divide labor
> Core proposition: machines supply candidates and evidence; humans retain judgment and accountability.

---

## 1. Introduction: when generation becomes cheap, judgment becomes the bottleneck

Automotive styling is constrained simultaneously by market context, brand DNA, engineering hard points, manufacturing processes, and shifting cultural taste. It is a textbook open complex giant system. No single role can produce a global answer: a designer can tell whether a proposal "looks like this brand," an engineer can tell whether it can be built, and a model can enumerate thousands of parameter sets overnight. Yet none of them can individually bear the responsibility for declaring "this is the final version." Solving a complex problem is first an organizational problem and only second a tooling problem.

Once AI enters development, teams tend to fall into one of two extremes. The first is instrumentalization: the process stays untouched, a generate button is attached at the end, and AI becomes a faster drawing pencil while complexity remains ungoverned. The second is outsourcing: aesthetic and brand judgment is delegated to a composite score, the team reads only the ranking, and the search converges on proposals that score well but no longer resemble a car. The former changes nothing about the organization; the latter abandons accountability. Neither is AI-native.

The general design department and the metasynthesis hall proposed by Qian Xuesen offer a third form: an overall plan governs the subsystems, a triangular loop of expert system, machine system, and knowledge system handles complex problems, and the principle of "human–machine combination with humans in the lead" is preserved. This chapter asks how that organizational form becomes a running system rather than a management slogan.

<figure class="doc-figure"><img src="../docs/images/en/syst-image.svg" alt="An open complex giant system: six external sources surrounding a central vehicle" loading="lazy"><figcaption><strong>Figure 15-1 | An open complex giant system: the vehicle as an emergent result of multi-source coupling</strong> Reading guide: the dashed frame is the system boundary; market, brand, technology, manufacturing, culture, and users continuously cross it with constraints and feedback. Inside the frame sit the parameter space, surface patches, quality gates, and data flows that constitute the many subsystems. The central vehicle cannot be explained by any one subsystem—precisely why a general design department must establish the whole before dividing it into parts.</figcaption></figure>

> **Boundary statement.** The "metasynthesis seminar hall" and the "general design department" described here are **organizational discipline and design principles [Design Principle]**, not a module inside the platform. What the codebase carries today is their engineering shadow: eight frozen hard parameters, fixed thresholds (G0 0.1 mm / G1 1.0°), JSONL audit trails, and the separation of advice from adjudication. **There is no automated seminar-hall module**; reading it as a shipped feature is a misreading.

## 2. Principles

### 2.1 Establish the whole first: fix interfaces before parallel implementation

The first duty of a general design department is overall planning, not doing the subsystems' work for them. Operationally, this means freezing the layering, boundaries, and interface contracts before allowing modules to evolve independently. The department does not write algorithms, but it decides the shape in which algorithms are called. Once an interface becomes a contract, subsystem schedules stop holding each other hostage; once an interface stays vague, even strong local capabilities cancel each other out during integration.

### 2.2 Three-system division: experts qualify, machines quantify, knowledge remembers

The expert system frames the question, sets boundaries, and makes value judgments. The machine system performs massive exploration, precise computation, and pattern recognition. The knowledge system stores, retrieves, and activates experience. These are not three voters in parallel but three consecutive responsibilities: qualitative judgment defines the shape of the search space, quantitative search finds solutions inside that shape, and knowledge turns each solution into a prior for the next round. Remove any corner and the loop degenerates into an open line.

### 2.3 Separate recommendation from adjudication

A machine may provide candidates, evidence, and confidence, but it cannot sign on a human's behalf. Every proposal that enters delivery must have a named adjudicator and a traceable evidence chain. What is separated is not authority but the attribution of error: a bad recommendation can be corrected, while a bad adjudication must be owned. This discipline determines whether the system can be repaired when it fails.

### 2.4 Report absence honestly

Machine capability has limits. When a dependency is missing, the system should explicitly return unavailability or a degraded marker rather than filling the interface with simulated data. Trust can only rest on honesty; one fabricated "machine opinion" is enough to discredit every recommendation that follows. Honest degradation is not a capability defect; it is part of the system's credibility.

<figure class="doc-figure"><img src="../docs/images/en/syst-legend.svg" alt="Legend of the metasynthesis hall: three systems, decision rights, and signal states" loading="lazy"><figcaption><strong>Figure 15-2 | How to read the hall: three systems, decision rights, and signal states</strong> Reading guide: shape and color identify ownership—blue circles belong to the expert system, green squares to the machine system, purple hexagons to the knowledge system. Line style identifies authority: solid lines mean human-led adjudication, dashed lines mean machine recommendations, and red lines mean explicit degradation. Filled signal dots indicate evidence; hollow dots indicate its absence. "Humans in the lead" appears on the diagram as the human remaining at the vertex of the loop.</figcaption></figure>

## 3. Case study: how the EVOLUTION AI hall actually runs

### 3.1 The general design department: thin-shell orchestration and an independent algorithm package

The backend consists of 19 route modules and 154 HTTP endpoints (152 route endpoints plus 2 system endpoints). It connects downward to 17 ORM tables and upward to 12 frontend pages. What matters is not the count but the division of labor: `algorithm_model` is an independently installable Python package with its own entry points, dependencies, and tests. The backend performs parameter validation, authentication, persistence, and orchestration; it does not reimplement geometry.

This is the technical expression of a general design department. The orchestration layer does not manufacture parts; it defines the assembly contract between them. The algorithm package can run, be tested, and be replaced without the web layer. When the geometry kernel is upgraded, the external semantics of all 154 endpoints remain unchanged; when a page is revised, the algorithm package is untouched. The payoff of establishing the whole first is precisely this non-hostage-taking mode of evolution.

### 3.2 The expert system: thresholds are defined by people

The continuity thresholds G1 5° and G2 2°, together with the A/B/C/D cutoffs of 0.85, 0.70, and 0.50, were not learned by a model. They encode a consensus among surface engineers. The platform turns them into executable criteria so that every evaluation uses the same ruler—but the graduations on that ruler are always set by people. The NURBS expert dialogue follows the same logic: it supplies domain knowledge and retrieval cues, while the choice of proposal and the tolerance for deviation remain with designers and quality engineers.

### 3.3 The machine system: exploring inside a human frame

A Bayesian session searches a 14-dimensional space that people carve out of the 22-dimensional CarParams; dimensions carrying sizes, regulatory constraints, and structural hard points are frozen. The acquisition function (EI or UCB) answers only "where should the next parameter set be tried," never "which design is more beautiful." After scores are fed back, the Gaussian-process surrogate updates its belief; the loop uses the EI minimum improvement 0.01 (`ei_xi`) as its stopping reference, and the plateau—typically reached within 20 to 40 rounds—is confirmed by session observation and human judgment. The machine performs rational exploration; value judgment stays on the human side.

### 3.4 The knowledge system: turning the last round into the next prior

The samples exported after each session are the fossil record of every qualitative-to-quantitative transition. They can enter a training task and become input to the next model, or enter the knowledge base and become a reference for the next review. The purpose of the knowledge system is not archiving but shortening the distance to a valid solution next time. The platform organizes more than twelve documents into a four-layer, three-dimensional knowledge graph so that knowledge appears at the moment it must be mobilized rather than sleeping in a directory.

**Cross-Domain Mapping.**

- Here = humans adjudicate direction; machines supply comparable candidates and evidence. In RAG = humans define the evaluation set and machines run the regression; metrics never replace acceptance judgment.
- Here = the seminar's output is a decision with an evidence chain, not a consensus memo. In agent release review = go-live conditions are a checkable list, not "the team feels good about it".

## 4. Anti-patterns and their costs

| Anti-pattern | Observable behavior | Cost |
|---|---|---|
| Feature stacking without a whole | Each module invents its own parameter conventions; endpoints grow while contracts drift | Repeated alignment during integration; numbers in documents stay inconsistent |
| Score-based adjudication | Brand and aesthetic judgment is outsourced to a composite score | High-scoring but off-brand proposals; the team loses its ability to explain choices |
| Review becomes demo | Reviews show renderings only, not quality reports or feedback records | Decisions cannot be reconstructed; the same dispute recurs |
| Fabricated signals | Missing dependencies are filled with simulated data | Trust collapses; even genuine signals are thereafter suspected |
| Responsibility vacuum | "The AI generated it" is offered as an excuse | Nobody owns delivery; defects cannot be assigned to a role |

These costs share one structure: each is an efficiency choice in the short term and an overdraft on maintainability in the long term. Feature stacking saves the time of overall design and pays double during integration. Score-based adjudication saves an argument and leaves the team unable to explain, in the next project, why that proposal was chosen. Fabricated signals save one embarrassing error message and destroy the baseline for every later judgment.

## 5. Operational checklist

1. Is there a one-page overall plan stating layering, boundaries, interface contracts, and non-negotiable invariants?
2. Does every review supply candidates, quality reports, variant differences, and feedback records together?
3. Does every proposal entering delivery have a named adjudicator and a signing time?
4. Do scoring criteria carry a version number and a definer, and do changes follow the knowledge-layer process?
5. When a machine capability is missing, does the system return 503 or an explicit degradation instead of a silent simulation?
6. Can the algorithm package be installed, run, and tested without the web layer?
7. Are the samples produced this round exported, archived, and retrievable by the next round?
8. Do all ~1,027 tests pass (200 algorithm, 411 backend, 416 frontend)?

## 6. Self-check

1. Is your team currently "using AI to accelerate the old process," or has it reorganized work around the expert–machine–knowledge division?
2. Can the most recent design adjudication be traced, within five minutes, to the exact parameters, quality report, and adjudicator?
3. If every model capability were switched off tomorrow, could your process still produce an honest, deliverable result?
