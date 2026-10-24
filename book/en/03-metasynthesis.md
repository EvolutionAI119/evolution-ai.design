# Chapter 3 From Qualitative to Quantitative: The Metasynthesis Method

> Author: Quantum Swordsman
> Volume I · The Case for AI-Native

## 1. The Problem: How Does "Elegant and Restrained" Enter an Optimizer?

At a review meeting the design director says: "This version must be elegant and restrained." The engineer returns to a desk where an optimizer accepts only numbers. The sentence cannot be fed into any algorithm—it has no dimensions, no units, no bounds. Tradition offers two solutions, both undignified. The first is to let the engineer "translate" the sentence into a few parameter adjustments by feel, a translation that leaves no trace. The second is to ignore the sentence entirely and let the optimizer converge in a purely numeric space, producing a batch of proposals that score high but do not look like cars.

This is the core question the methodology of complex giant systems must answer: between qualitative judgment and quantitative computation lies not merely a format gap but two kinds of knowledge. Qian Xuesen's **metasynthesis—from the qualitative to the quantitative**—offers the path: organize expert judgment (qualitative), data and models (quantitative), and machine computation (tooling) into one system, and approach a scientific understanding of the complex problem iteratively—human-machine collaboration, with the human in command. This chapter discusses how that method becomes a running software system rather than a slogan.

<figure class="doc-figure"><img src="../docs/images/en/meta-architecture.svg" alt="The three-layer-plus-one-repository knowledge architecture"><figcaption><strong>Figure 3-1 ｜ The "three layers, one repository" knowledge system: the knowledge-side skeleton of metasynthesis</strong> Read it this way: top-down are the philosophy layer (why), the methodology layer (how), and the engineering-practice layer (with what); the dashed band at the bottom is a continuously updated resource index; the right-hand arrow indicates that practice feeds theory from below. Metasynthesis is not a one-off translation but a continuous circulation inside this structure.</figcaption></figure>

## 2. Principles

**Principle 1: Qualitative and quantitative supply each other.** Imagery selects the structure of the parameter space—which dimensions exist, where the bounds lie, which dimensions are frozen. Quantitative scores correct the landing point of imagery—which region of the space "elegant and restrained" actually occupies is decided by observed data. Without either end, the loop degenerates: qualitative only is open-loop discussion; quantitative only is blind search without priors.

**Principle 2: Three bodies, three jobs, in relay.** The expert system poses problems, sets boundaries, and makes value judgments; the machine system performs massive exploration, exact computation, and pattern recognition; the knowledge system stores, retrieves, and reactivates experience. These are not three voters in parallel but a relay in series: the qualitative shapes the search space, the quantitative finds solutions within the shape, and knowledge distills each solution into the next round's prior.

**Principle 3: Beliefs are revisable; a model is the current state of understanding.** A surrogate model is not truth but a formalization of "what we currently believe." Every observation updates it—homologous to the cycle of practice, knowledge, practice again. The engineering requirement: the model must expose its own uncertainty, not emit a bare score, because the uncertainty itself is the guide for the next sample.

**Principle 4: Samples are precipitated knowledge.** An optimization session should yield not only an optimum but the full observation record that led to it. That record is the fossil of each qualitative-to-quantitative leap: it can be replayed as training data so that the next search stands on the previous one's shoulders—individual cognition is thus promoted to organizational cognition.

## 3. Case Anatomy: The Platform's Working Loop

EVOLUTION AI's fundamental working loop is metasynthesis implemented in software. On the qualitative end, "elegant and restrained" passes through design-intent parsing and the brand knowledge base (5 brands, 19 models) and lands as the structure of a parameter space: which 14 of the 22 CarParams dimensions enter the search, what bounds each takes, and which 8 are frozen as regulatory and structural hard points. On the quantitative end, quality evaluation translates "good or not" into regression-safe numbers: G0/G1/G2 counts, reflection-line scores, and an A–D composite grade, with tolerances of 0.1 mm / 1.0° and thresholds of 5° for G1 and 2° for G2. The graduations of the ruler are defined by engineering consensus; the machine merely applies the same ruler every time.

Between the two ends sits a Gaussian-process surrogate (RBF kernel, ℓ=0.25), which organizes observed parameter-to-score pairs into the current belief, emitting a posterior mean and an uncertainty. EI/UCB acquisition functions make rational decisions on top of that belief: with fewer than two observations the engine draws random space-filling points; afterward it generates a pool of 4096 candidates in the unit cube, ranks them by acquisition value, and returns suggestions. Scores flow back through `POST /api/v1/bayes/sessions/{id}/observations`, the belief updates, and the loop continues until the incumbent enters the 0.01 convergence band—in practice a plateau is reached within 20 to 40 rounds.

The decisive part is the lower half of the loop: exported samples carry a `feature_order` identical to the training pipeline's, so they replay directly as a supervised dataset driving the PyTorch training tasks in `backend/app/routes/training.py`. Search (the optimizer proposes candidates) and learning (observations precipitate into training data) thereby close into one ring: everything the Nth round of optimization learned becomes the starting point of round N+1.

<figure class="doc-figure"><img src="../docs/images/en/syst-chart.svg" alt="Convergence of the quality score over observation rounds"><figcaption><strong>Figure 3-2 ｜ Qualitative-to-quantitative convergence: quality score rises with observation rounds</strong> Read it this way: the horizontal axis counts observations, the vertical axis is the composite quality score; the solid line is the best estimate under the current belief, and the shaded band is GP uncertainty. Read three things—the starting point (how strong the qualitative prior is; round one is not zero), the slope (information gained per round), and the band width (how much evidence remains). A plateau arrives within 20–40 rounds, after which further sampling yields diminishing returns.</figcaption></figure>

## 4. Antipatterns and Their Cost

**Pure numeric optimization without priors.** Skip the qualitative translation and search the full parameter space for score. The cost is convergence to solutions that "score high but do not look like cars"—the objective encodes no brand or proportion priors, and the optimizer is merely honestly maximizing the wrong objective.

**Machine verdict replacing human judgment.** The ranking of composite scores is taken directly as the review conclusion. The cost is outsourced value judgment to an entity that cannot be held accountable; once the objective deviates from true intent, the entire team marches systematically in the direction of the deviation without knowing it.

**Knowledge drifting from code.** Experience stays in documents, documents stay in directories, while parameters and thresholds quietly change in code—the classic documentation drift. The cost is a steadily depreciating prior: the next search runs against the previous version of the world, and nobody announced that the world had changed.

**One-shot cleverness.** Every optimization session starts from zero; observation records are discarded after use. The cost is that organizational cognition never accumulates: when an expert retires, the experience retires too; when a project closes, its lessons close with it. A loop without sedimentation is merely warming up, no matter how many turns it completes.

## 5. Operating Checklist

| Item | Pass criterion | Evidence in this repository (file or command) |
|---|---|---|
| Qualitative judgment has a structured landing point | Intent lands as parameter-space structure: dimensions, bounds, frozen entries | Intent endpoint `/api/v1/design-intent`; brand knowledge base `backend/config/brand_design_knowledge.json` |
| The scoring rubric is human-defined and reproducible | Thresholds and tolerances are explicit constants; same input, same score | G1 5°/G2 2°, 0.1 mm/1.0° in `algorithm_model/surface_quality/` |
| The model exposes uncertainty | The surrogate emits mean and variance; sampling uses both | RBF-GP (ℓ=0.25) with EI/UCB in `backend/app/bayes_optimizer.py` |
| Observations can flow back | Scores enter the session via an endpoint and update the belief | `POST /api/v1/bayes/sessions/{id}/observations` |
| Convergence has dual criteria | Incumbent within the 0.01 band and a bounded round budget | Bayesian session convergence logic; observed 20–40-round plateau |
| Samples replay as training data | Exported `feature_order` matches the training pipeline | `/api/v1/bayes/sessions/{id}/samples` → `backend/app/routes/training.py` |

## 6. Chapter Self-Check

1. Can you trace one qualitative requirement (say, "more elegant") through the system to its concrete effect on the parameter space? Wherever the trace breaks, who fills the gap, and when?
2. When your optimizer returns a score, does it also return uncertainty? Without uncertainty, on what basis does a score guide the next sample?
3. Can the observation record of your last optimization session be replayed verbatim as this round's input? If not, where does your organization's experience actually live?
