# Chapter 8. Surrogate Models and Bayesian Optimization

> Author: Quantum Swordsman
> Volume III · Intelligence: Putting Models into the System

## 1. The Problem: When Every Evaluation Is Expensive

Grid search and random search rest on a hidden assumption: evaluating the objective once costs almost nothing. Automotive styling development violates that assumption. Scoring one set of styling parameters means building the vehicle and running the quality evaluator — hundreds of milliseconds per shot in software; in real engineering, one evaluation may be a CFD run, a clay model, or an expert review, costing hours or weeks. In a world of expensive evaluations, **deciding which parameter set deserves the next evaluation is itself the most valuable decision.**

Brute force hits two walls here: the dimension wall and the cost wall. EVOLUTION AI's styling search space has 14 continuous dimensions (carved out of the 22-dimensional CarParams, with the 8 dimensions carrying size, regulation, and structural hard points frozen). Even ten grid points per dimension would mean 10^14 evaluations. The proposition of this chapter is: **when evaluation is expensive, trade a GP surrogate plus an acquisition function for data efficiency, and keep convergence judgment defensible rather than automatic.** The essence of Bayesian optimization is not cleverer sampling; it is pricing uncertainty — every unit of evaluation budget must buy back the most information possible.

## 2. Principles

### Principle 1. Build the surrogate first, then talk about search

The first weapon of Bayesian optimization is not the acquisition function but the surrogate: a cheap probabilistic model that approximates the expensive true objective. The platform uses a Gaussian process with an RBF kernel, isotropic length scale ℓ=0.25 in normalized space, diagonal jitter of 1e-6, and Cholesky-based solves — the whole engine runs on NumPy and SciPy alone. The value of a GP is not raw fitting accuracy; it is that it returns a posterior mean and an uncertainty together. It knows where it does not know, and that is the precondition for pricing exploration.

> **When this does not apply**: when observations are cheap and massively parallel, a surrogate is surplus — brute-force grid search is cheaper. A GP surrogate only pays off in a world where every evaluation is expensive.

### Principle 2. The acquisition function prices exploration

With mean and uncertainty in hand, the acquisition function answers "where to sample next." Expected Improvement (EI, ξ=0.01) favors regions with both room to improve and high uncertainty; Upper Confidence Bound (UCB, κ=2.0) lifts the posterior mean by κσ across the board and is more willing to visit unsampled areas. Both are maximized over a candidate pool of 4096 random points — a derivative-free, naturally parallel, deliberately simple optimizer. Minimization objectives are negated internally so that one shared maximization path serves both goals.

### Principle 3. Cold start must be honest

With fewer than two observations, the GP carries no information, and any "model suggestion" would be posturing. The engine therefore performs random space-filling in this phase and says so explicitly; only after two observations does it switch to GP-driven acquisition. An honest cold start is the "signal first" principle restated inside the algorithm.

### Principle 4. Convergence criteria must be defensible

"Not improving anymore" is not the same as "converged." The platform tracks two reference signals. First, the best score is monotonically non-decreasing across rounds and enters a plateau where the slope approaches zero — empirically within 20–40 rounds. Second, the EI acquisition value falls below the 0.01 minimum-improvement threshold (`ei_xi`), meaning the expected gain from further exploration is negligible. Watching only the score mistakes a local plateau for the finish line; watching only EI ignores evaluation noise. In the current code the loop uses the EI minimum improvement 0.01 as its stopping reference, and the plateau or convergence call is made by session observation and human judgment — there is no `converged` field and no automatic convergence verdict. Automatic dual-criterion convergence [Partially Implemented — the EI stopping reference is in place, the automatic verdict is not] is a roadmap item, not a shipped behavior.

<figure class="doc-figure"><img src="../docs/images/en/paper-bayes-engine.svg" alt="Bayesian optimization loop with GP surrogate"><figcaption><strong>Figure 8-1 | The Bayesian optimization loop: GP surrogate (left) and the five-step iteration (right)</strong> How to read: in the left panel, amber dots are evaluated samples, the green line is the posterior mean, the shaded band is the ±σ confidence region (wider means more uncertain), and the pink dashed line marks the EI maximum — the next sampling point. The right panel shows the five-step loop (initial DOE → real evaluation → surrogate update → EI selection → suggestion output). The inset convergence trace shows the best score monotonically non-decreasing, reaching a plateau within 20–40 rounds.</figcaption></figure>

## 3. Case Study: The Full Lifecycle of One Session

The platform's Bayesian module has only 7 endpoints, yet it makes the loop of "suggest → evaluate → report → converge → export" a reproducible first-class citizen.

**Step one, create the session.** `POST /bayes/sessions` carries the parameter space (14 dimensions by default, with engineering bounds such as length 4000–6200 and wheelbase 2400–3700), the goal direction, the acquisition function, and a random seed. An empty space, duplicate names, or `max <= min` all return 400 — the contract stops illegal experiments at the door.

**Step two, suggest.** `suggest` returns parameter sets guaranteed inside the bounds. With fewer than two observations this is honest random filling; afterward it is GP-plus-acquisition targeted suggestion.

**Step three, evaluate for real.** The suggested parameters are used to build the vehicle and scored through `/ai/evaluate-quality` as an engineering proxy, or handed to human review. This is the only expensive step in the loop, and it is the one all data efficiency exists to serve.

**Step four, report back.** `observe` requires parameters covering all 14 dimensions of the space; unknown, missing, or out-of-bounds values return 400. On receipt, the GP retrains immediately and beliefs update.

**Step five, converge and export.** `best` returns the current optimum (409 when no observation exists — never a fabricated empty best); `samples` exports every observation, with `feature_order` aligned position-by-position to the training pipeline's feature columns. An optimization campaign thus settles into a supervised training dataset.

<figure class="doc-figure"><img src="../docs/images/en/bayes2-chart.svg" alt="Quantified Bayesian convergence: best-score curve and EI decay"><figcaption><strong>Figure 8-2 | How convergence is referenced: the two signals of score plateau and EI decay</strong> How to read: the left panel shows the best score monotonically non-decreasing across rounds, entering a near-zero-slope plateau within 20–40 rounds; the right panel shows the EI acquisition value decaying logarithmically, crossing below the 0.01 minimum-improvement threshold (`ei_xi`) when further exploration is negligible. Today the two signals serve as stopping references reviewed by a person; cross-confirming them as an automatic convergence verdict is a roadmap item.</figcaption></figure>

Engine correctness is backed by experiment: on the controlled one-dimensional objective `-(x-0.7)²`, both EI and UCB run 15 suggest–observe rounds, and both push the best-so-far past the -0.01 band, effectively reaching the known optimum. The 12 tests in `backend/tests/test_bayes.py` cover the session lifecycle, boundary validation, directional correctness, and export format. One caution: sessions live in process memory and are wiped on backend restart — a deliberate simplicity. Anything worth keeping must go through `samples` export; memory belongs to data, not to the process.

**Cross-Domain Mapping.**

- Here = each geometry evaluation is expensive, so a GP surrogate plus an EI acquisition function spends the budget where it buys the most information. In LLM evaluation = annotation and human grading are expensive too, so active sampling picks the most informative items instead of scoring everything.
- Here = feasibility filtering masks the candidate pool once and, when candidates run short, falls back visibly and records the statistics. In RAG retrieval budgeting = hard constraints prune candidates first, then value ranks them, and every discard is explainable.

**Capability status.** The suggest / observe / best loop and feasibility filtering are [Implemented · Test-Locked] (backend suite collects 411 cases, including 1 skip and 2 xfail). The 0.01 EI minimum improvement is a stopping reference, not a convergence criterion; automatic two-criterion convergence is a roadmap item [Partially Implemented].

## 4. Anti-Patterns and Their Costs

**Anti-pattern 1: Random search masquerading as Bayesian optimization.** No surrogate, no acquisition, just uniform sampling and luck. The cost is evaluation budget sprayed evenly across a 14-dimensional space where most regions are useless, multiplying the rounds to convergence.

**Anti-pattern 2: Treating the surrogate as truth.** Using the GP posterior mean directly as the quality score, skipping real evaluation. The cost is a model that lies confidently where it has no data, and an optimization that converges to a phantom optimum existing only in the surrogate.

**Anti-pattern 3: Single-signal convergence.** Declaring victory when the score curve flattens. The cost is mistaking a local plateau for the global end — or, conversely, abandoning a still-profitable region too early in the presence of noise.

**Anti-pattern 4: Observation formats divorced from training.** Field order, units, and conventions in the optimization log disagree with the training pipeline. The cost is that accumulated observations cannot be replayed as a training set; the bridge between search and learning is quietly dismantled.

## 5. Operational Checklist

1. When defining a search space, write each dimension's name, unit, and engineering bounds (following the default 14-dimensional space); frozen hard-point dimensions stay out of the space.
2. Fix the random seed for every experiment so the suggestion sequence is reproducible.
3. Reported observations must cover every dimension of the space; reject incomplete ones outright.
4. Default to EI; switch to UCB for multi-modal objectives or wider coverage, and record κ.
5. Treat the score plateau and the EI minimum-improvement threshold (0.01, `ei_xi`) as stopping references; the convergence call itself is made by session observation and human judgment (automatic dual-criterion convergence is a roadmap item).
6. Export and archive through `samples` as soon as a session converges; never rely on in-process memory.
7. Before feeding exported samples into training, verify `feature_order` matches the training pipeline position by position.
8. Maintain convergence tests for the optimizer (following the 15-round one-dimensional experiment) and rerun them on every change.

## 6. Chapter Self-Check

1. Can your optimizer say why the next evaluation point deserves its budget? If not, it is just random search.
2. When you declare an optimization converged, how many independent pieces of evidence do you hold? With only one, it is not yet time to declare.
3. Can the observations from your last optimization campaign be replayed today as training data, exactly as recorded? If not, where did the bridge between search and learning break?
