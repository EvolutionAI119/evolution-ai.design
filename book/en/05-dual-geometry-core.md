# Chapter 5 One Vector, Four Expressions: The Dual Geometry Core

> Author: Quantum Swordsman
> Volume II · Architecture: Giving Complexity Its Proper Place

## 1. The Problem: Why Is "What You See Is What You Deliver" So Hard?

There is a tacit fault line in the daily work of styling departments: what is seen in the review meeting and what the engineering department receives are not the same thing. Previews run on triangle meshes—fast, fluid, rotatable in real time. Delivery requires NURBS surfaces—precise, smoothable, acceptable to downstream CAD. The traditional bridge between them is called reverse fitting: deriving surfaces from meshes. Fitting always has residuals, residuals always demand manual repair, and manual repair is never reproducible. Every line a designer edits on the preview side must be "translated" again on the engineering side, and translation is never symmetric.

The root of the fault line is not a shortage of tools but expressions that do not share a source. Mesh and surface are driven by two separate bodies of data, evolve separately, and are aligned by hand. The proposition of this chapter: **one vector, three families of derivatives—geometric expressions, quality metrics, and exchange formats, all forward-generated from the same parameter vector, eliminating secondary fitting.** When all three families are pure functions of the same vector, "what you see is what you deliver" turns from slogan into theorem: the shape approved in the preview and the shape delivered in the STEP file are generated from the same parameters, with zero divergence.

<figure class="doc-figure"><img src="../docs/images/en/paper-nurbs-pipeline.svg" alt="The Class-A surface pipeline: control mesh, surface lofting, continuity verification"><figcaption><strong>Figure 5-1 ｜ The Class-A pipeline: control mesh → surface lofting → G0/G1/G2 continuity verification</strong> Read it this way: three panels left to right—the control mesh (control points rearranged by design parameters), surface lofting (semantic patches skinned with G2-enforcing boundaries), and the continuity spectrum (G0 position / G1 tangent / G2 curvature, green marking the Class-A threshold). The bottom bar states why NURBS, not meshes, is the engineering expression: analytic precision, parametric drive, industrial compatibility.</figcaption></figure>

## 2. Principles

**Principle 1: One parameter source; everything else is derived.** The system permits exactly one human-editable object—the parameter vector. Meshes, surfaces, scores, and export files are all derived from it, and derivation may carry no hidden state of its own. Every editing entry that "pulls a vertex directly on the mesh" or "patches a region by hand on the surface side" manufactures a second source of truth.

> **When this does not apply**: non-parametric freeform modeling—sculptural modeling has no parameter vector to serve as the single source, and this principle yields to explicit version snapshots and diffing.

**Principle 2: Expressions live downstream; take the family you need.** The derivatives of one parameter vector come in three families. Geometric expressions: the preview mesh (10 parts, 176 vertices, 316 faces) and the NURBS surfaces (33 for a full vehicle). Quality metrics: G0/G1/G2 counts, reflection-line scores, and the A–D composite grade. Exchange formats: eight geometric formats (glb / gltf / stl / obj / iges / step / igs / stp), led by the dual links STL/GLB on the mesh side and STEP/IGES on the NURBS side, with OBJ/GLTF/IGS/STP kept for compatibility. Each family has its use, but none deserves the title "master expression"—they are pure-function projections of the same 22-dimensional vector, and which family you read depends on the question at hand.

**Principle 3: Refuse secondary fitting; take the forward road to the end.** Generate surfaces from parameters forward; do not fit surfaces from meshes backward. Forward generation has no fitting residual, and every designer edit propagates exactly into control-point changes. Backward fitting forever carries an irreducible approximation error that accumulates with every edit. Secondary fitting saves one-off development cost; what it pays is uncertainty in every iteration.

**Principle 4: Tolerances come first; criteria are born with the construction.** Quality standards are not an inspection procedure after construction but a constituent of the construction itself: continuity thresholds, sampling density, and grading rubrics are fixed at generation time. Problems found by after-the-fact inspection can only be reworked; criteria endogenous to construction can prevent them.

## 3. Case Anatomy: How Two Pipelines Share One Vector

In EVOLUTION AI, a vehicle is described by the 22-dimensional CarParams (`algorithm_model/car_modeling/car_params.py`), and this single object is the common input to two geometric pipelines.

**The mesh path serves interaction.** The parametric body is built from longitudinal and circumferential section rings (default discretization 48×24) and assembled with wheels, lamps, grille, mirrors, and glass into a 10-part vehicle mesh of 176 vertices and 316 faces, feeding the Three.js viewport for real-time preview and STL/GLB tessellated export. The assembler also reports per-part vertex and face counts, bounding boxes, and stable part colors so the frontend can render, identify, and count.

**The NURBS path serves engineering.** A separate builder constructs the body as true NURBS surfaces from the control mesh—33 surfaces for a full vehicle—with dedicated modules building front and rear end caps that meet the body with G1 tangent transitions. Companion freeform operators cover sweeping and filleting; STEP is emitted by a pure-Python writer (`algorithm_model/freeform/step_writer.py`) following ISO 10303-21, with no dependency on an Open CASCADE (OpenCascade)-scale kernel. The crucial point: surfaces are generated directly from parameters, not reverse-fitted from triangle meshes—there is no fitting residual.

**Quality and export are downstream of the same source.** The continuity checker (`continuity_checker.py`) samples the four parametric boundaries of each named surface (50 points per edge by default) and judges every seam against G0 0.1 mm and G1 1.0° thresholds, writing TXT/CSV reports; the surface-quality package produces G0/G1/G2 counts, reflection-line scores, and A–D grades on the mesh side. Two paths, two granularities, complementary criteria: exact NURBS continuity at the seams, plus curvature distribution across the tessellated body.

The book involves two sets of G0/G1/G2 thresholds, belonging to the two links respectively; they must not be mixed up:

| Link | Object checked | G0 | G1 | G2 | Unit | Code source |
|---|---|---|---|---|---|---|
| Tessellated-mesh holistic evaluation | Discrete mesh | — | 5° | 2° | degrees | `surface_quality/continuity.py`, `grader.py` |
| NURBS seam-by-seam | Adjacent surface patches | 0.1 mm | 1.0° (plus visual 5.0°) | — | mm/° | `car_modeling/continuity_checker.py` (50 points per edge) |

The chain thus closes: `CarParams ──► mesh assembly ──► interactive preview / STL / GLB` and `CarParams ──► NURBS body + G1 end caps ──► G0/G1/G2 analysis ──► STEP/IGES`. Every arrow is a pure function of the same parameter vector. The export engine actually supports eight geometric formats: STL/GLB as the primary mesh-pipeline outputs and STEP/IGES as the primary NURBS-pipeline outputs, with OBJ/GLTF/IGS/STP retained for compatibility (plus JSON parameter export). This is why the Bayesian optimizer of Chapter 3 can treat "styling plus quality" as a single evaluable function—suggest one parameter set and all three derivative families materialize at once; no representation needs manual reconstruction.

<figure class="doc-figure"><img src="../docs/images/en/phil-closedloop.svg" alt="The end-to-end closed loop: parameters, NURBS generation, quality evaluation, Bayesian optimization"><figcaption><strong>Figure 5-2 ｜ The end-to-end loop: parameters → NURBS generation → quality evaluation → Bayesian optimization</strong> Read it this way: the horizontal main chain has four steps, and the dashed loop writes suggested parameters back into the next round. The bottom bars give per-round latency (seconds), typical convergence (20–40 rounds), and the human-machine division (people set aesthetic bounds; the machine explores the optimum). The loop can exist only because every step on the main chain is a pure function of the same vector.</figcaption></figure>

**Cross-domain mapping.** "Single source, pure-function derivation" has a strict homologue in evaluation:

- In this platform = one 22-dimensional vector derives three families—geometry, quality, and formats—and any family can be recomputed from the same vector; in LLM evaluation = one locked baseline yields the same score for the same input, and any report can be replayed from the baseline. What "no secondary fitting" is called in evaluation is "results are replayable."
- In this platform = deriving surfaces from meshes is forbidden because fitting residuals are irreproducible; in evaluation = deriving scores from reports is forbidden because retroactively patched scores carry no baseline authority. Reverse procedures save one-off cost and pay with credibility in every round.

## 4. Antipatterns and Their Cost

**Bridging with secondary fitting.** Preview on meshes, reverse-fit NURBS before delivery. The cost is fitting residuals plus manual repair: every design iteration repays the translation fee, and repairs are irreproducible—"how was this fixed last time" has no answer.

**Two sources of truth.** Edit one version in the parameter panel, then hand-pull another on the mesh side. Flexible in the short run, disastrous in the long: nobody can compute the difference between the two shapes, and between the version the review approved and the version engineering received yawns a gap of manual reconciliation.

**Separate preview and delivery geometry.** Simplified models for fluency in preview; refined models rebuilt for delivery. The cost is institutionalized "what you see is not what you get": what the review approved was never the thing to be manufactured.

**Tolerances inspected after the fact.** Build geometry casually, check quality before delivery. Problems can then only be reworked, not prevented; and rework near delivery has no time budget, so it ends in quality compromise.

## 5. Operating Checklist

| Item | Pass criterion | Evidence in this repository (file or command) |
|---|---|---|
| Parameters are the only editable object | No entry bypasses parameters to edit geometry directly | 22-dim CarParams as the sole input, `algorithm_model/car_modeling/car_params.py` |
| Three derivative families share one source | Geometry (mesh/NURBS), quality (G0/G1/G2, A–D), and formats (eight exports) are all forward-generated from parameters | 176-vertex mesh assembly (`body.py` + assembler); 33 NURBS surfaces (`body_nurbs.py`) |
| No secondary-fitting path exists | The codebase contains no mesh→NURBS reverse-fitting procedure | Both pipelines start from CarParams; see `docs/EVOLUTION_AI_paper.md` §4 |
| Tolerances are endogenous | Continuity thresholds are fixed at construction and judged seam by seam | G0 0.1 mm / G1 1.0°, 50 samples per edge, TXT/CSV from `continuity_checker.py` |
| Exports verify independently | STEP output opens in third-party kernels | Pure-Python `step_writer.py` (ISO 10303-21) plus a bundled FreeCAD verification macro |
| One loop round is reproducible | Parameters → three derivative families → score in one command | `python algorithm_model/test_all.py` five-module self-check |

## 6. Chapter Self-Check

1. In your system, are the shape the designer reviews and the file the engineer receives generated from the same parameter set? If not, who aligns the difference, at which step, and at what cost?
2. Does your codebase contain any procedure that "derives the expression from the result" by fitting? If so, on whose account is the residual booked?
3. Are quality standards honored during construction, or inspected before delivery? For problems caught by inspection, how long is the road back to the construction side?
