# Chapter 18 · Fast Variables and Order Parameters: The Seven Programs of Deep Evolution

> Author: Quantum Swordsman (量子剑客)
> Volume VI · Evolution: letting the system grow by itself
> Core proposition: hold the order parameters firmly, let fast variables try and err, and use the closed loop to sediment experience into structure.

---

## 1. Introduction: why systems "get messier the more they are improved"

Many teams have lived through this: the system is visibly under continuous "optimization," yet the sense of direction is draining away. Last week a review said the front fascia should be sharper; this week the data says rounder scores higher, so the threshold quietly loosens. An architectural boundary set last month gets a breach opened for an "urgent requirement," and the breach never closes again. Every adjustment is defensible in isolation; stacked together, they are drift. The problem is not adjustment itself but the failure to distinguish two kinds of variables. Fast variables are adjustable step by step and respond quickly to disturbances; order parameters change slowly and govern the overall direction of the system's evolution. Changing an order parameter in the manner of a fast variable is the most common root of design losing control.

Synergetics tells us that a system's order is not achieved by controlling every variable but by holding the few order parameters firmly and letting the many fast variables relax freely within their frame. AI-native systems amplify the issue: a machine can produce thousands of fast-variable iterations overnight, and if the order parameters lack institutional protection, the direction of convergence is dragged around by noise and short-term scores. Using the platform's parameter space as the specimen, this chapter gives an engineering method for separating the two time scales, plus seven programs that keep a system in deep evolution.

## 2. Principles

### 2.1 Separate the scales before optimizing anything

Every change proposal must first answer one question: does it modify a fast variable or an order parameter? Per-round parameter values, a single score fed back, a single defect fix—these are fast variables. Brand DNA, quality standards, design philosophy, architectural boundaries—these are order parameters. The two have entirely different change channels, approval levels, and record-keeping requirements; confusing them is losing control.

### 2.2 Fast variables optimize inside the order-parameter frame

Genes first, search second. The shape, boundaries, and frozen dimensions of a search space are themselves instantiations of the order parameters; all fast-variable exploration proceeds inside that frame. Trial and error is fully permitted within the frame—it is the fast variables' job. Outside the frame there is no trial and error, only trespass.

### 2.3 Changing an order parameter must be a knowledge-system event

Adjusting a quality threshold is not editing a number; it is a package event of updating the knowledge base, retraining or re-validating models, and revising the philosophy documents. Every order-parameter transition must follow the knowledge-layer process: a proposal, evidence, an adjudication, a version number. It must never be quietly rewritten by a single round's score or one wave of hot feedback.

### 2.4 Use the closed loop to sediment experience into structure

Deep evolution equals the continuous convergence of fast variables plus the controlled transition of order parameters, and the mechanism connecting the two is the closed loop: theory guides practice, practice produces data, data trains models, and feedback corrects theory. The endpoint of each circuit is not the deliverable but structural sediment—a clearer baseline, a sharper prior, a more explicit boundary.

<figure class="doc-figure"><img src="../docs/images/en/syst-graphic.svg" alt="Fast-variable sawtooth trace inside an order-parameter envelope" loading="lazy"><figcaption><strong>Figure 18-1 | Fast variables and order parameters: two time scales in the parameter space</strong> Reading guide: the sawtooth trace is the fast variables (per-round values, seconds to rounds); the outer envelope is the permitted range given by the order parameters (brand DNA, philosophy, and quality standards, months to years); the middle solid line is the performance baseline. Red vertical lines mark "knowledge-system events"—the baseline can be raised only by updating the knowledge base, retraining models, and revising thresholds, never by a single round's score quietly rewriting it.</figcaption></figure>

## 3. Case study: two time scales and seven programs on the platform

The platform writes the dual time scales into the parameter space itself. The 22-dimensional CarParams are the fast variables' field of action; the 14-dimensional default search space of a Bayesian session, with its boundaries, is the order parameters' institutional constraint on them—dimensions carrying sizes, regulations, and structural hard points are frozen, and the acquisition function only proposes the next trial position inside the frame. The convergence criteria are layered as well: a single-round score is a fast-variable signal; entering the 0.01 convergence band after 20 to 40 rounds ends one round of fast variables; while the G1 5° and G2 2° quality thresholds move with no single-round result—their revision is an evolution-level event. Validation data shows the quality score converging steadily over observation rounds, which is the healthy shape of fast variables working inside a correct frame.

<figure class="doc-figure"><img src="../docs/images/en/syst-chart.svg" alt="Quality score converging over observation rounds" loading="lazy"><figcaption><strong>Figure 18-2 | The healthy shape of fast-variable convergence</strong> Reading guide: the quality score rises with observation rounds and enters a plateau with narrowing variance. Converging inside the order-parameter frame is a sign of health; if the curve oscillates persistently or repeatedly breaks its historical envelope, the first thing to inspect is not the acquisition function but whether the order parameters have been quietly moved.</figcaption></figure>

On this foundation, the platform's deep evolution follows seven programs, each with an explicit systems-science origin and an engineering landing point:

| # | Program | Platform landing (present → direction) |
|---|---|---|
| 1 | Strengthen the general organization | Thin orchestration shell plus an independent algorithm package → governance rules upgraded with scale |
| 2 | Reinforce top-level design | Five-layer architecture and the 153-endpoint contract first → architecture decision records institutionalized |
| 3 | Reshape the knowledge system | Four-layer knowledge base → automated document–code consistency auditing standing guard |
| 4 | Independent innovation | In-house NURBS kernel and a pure-numpy Bayesian engine → multi-fidelity surrogates and learnable kernels |
| 5 | Value practical summarization | 955 tests and validation reports → real optimization-campaign samples steadily replacing synthetic ones |
| 6 | Virtual–real dynamic monitoring | Quality reports and training-task monitoring → system-level tracking of the deviation between virtual metrics and empirical feedback |
| 7 | Continuous evolution and iteration | The theory–practice–training–feedback loop → the programs themselves revised after each circuit |

The seven programs share one structure: each combines an order-parameter action of "holding" with a fast-variable direction of "releasing." Hold the orchestration boundary, release algorithm iteration; hold the contracts, release module evolution; hold the threshold conventions, release trial and error inside the search space. Evolution is not a synonym for change but the coupling of controlled change with guarded constancy.

## 4. Anti-patterns and their costs

| Anti-pattern | Observable behavior | Cost |
|---|---|---|
| Scores rewriting thresholds | A high single-round result directly loosens quality criteria | Order parameters hijacked by noise; standards exist in name only |
| Convergence without transition | Fast variables optimize forever while the knowledge system stays still for years | Local optimum; the platform's capability hits a ceiling |
| Transition without convergence | Direction changes constantly; no search ever finishes | Castles in the air; no round of experience is sedimented |
| Baseline convention drift | Each report switches counting conventions to manufacture "progress" | Evolution becomes unmeasurable; the seven programs lose their instruments |
| Programs as slogans | Program texts exist without engineering landing points or owners | Evolution stays at the level of wishes; the system drifts on as usual |

## 5. Operational checklist

1. Does the change-review form include a "fast variable / order parameter" field, with order-parameter changes routed through the knowledge-layer process?
2. Do the search space's boundaries and frozen dimensions have a documented definer and version?
3. Does every threshold revision synchronously update the knowledge base, re-validate the models, and revise the philosophy documents?
4. When baseline figures (such as the 955 tests) are updated, are date and convention labeled and the old rows preserved?
5. Is the deviation between virtual metrics and empirical feedback monitored and registered as new knowledge?
6. After each closed loop, is it checked whether the landing points of the seven programs themselves need revision?
7. When fast variables fail to converge for long, is the frame suspected of having moved before the acquisition function is blamed?
8. Does every version upgrade answer three questions: is the structure clearer, is the feedback more truthful, and has cognition been sedimented?

## 6. Self-check

1. Did the last actual change in your system's direction come from a controlled order-parameter transition, or from the accumulated drift of many fast-variable micro-adjustments?
2. Your order-parameter list—brand DNA, quality standards, architectural boundaries—can it now be written on one page, each with a named guardian?
3. If all fast-variable optimization stopped for three months, could your system still grow by itself on its existing closed loop?
