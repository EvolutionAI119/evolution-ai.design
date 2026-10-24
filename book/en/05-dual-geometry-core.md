# Chapter 5 One Vector, Four Expressions: The Dual Geometry Core

> Author: Quantum Swordsman
> Volume II · Architecture: Giving Complexity Its Proper Place

## 1. The Problem: Why Is "What You See Is What You Deliver" So Hard?

There is a tacit fault line in the daily work of styling departments: what is seen in the review meeting and what the engineering department receives are not the same thing. Previews run on triangle meshes—fast, fluid, rotatable in real time. Delivery requires NURBS surfaces—precise, smoothable, acceptable to downstream CAD. The traditional bridge between them is called reverse fitting: deriving surfaces from meshes. Fitting always has residuals, residuals always demand manual repair, and manual repair is never reproducible. Every line a designer edits on the preview side must be "translated" again on the engineering side, and translation is never symmetric.

The root of the fault line is not a shortage of tools but expressions that do not share a source. Mesh and surface are driven by two separate bodies of data, evolve separately, and are aligned by hand. The proposition of this chapter: **a single parameter vector drives all four expressions—mesh, NURBS, quality, and export—eliminating secondary fitting.** When all four expressions are pure functions of the same vector, "what you see is what you deliver" turns from slogan into theorem: the shape approved in the preview and the shape delivered in the STEP file are generated from the same parameters, with zero divergence.

<figure class="doc-figure"><img src="../docs/images/en/paper-nurbs-pipeline.svg" alt="The Class-A surface pipeline: control mesh, surface lofting, continuity verification"><figcaption><strong>Figure 5-1 ｜ The Class-A pipeline: control mesh → surface lofting → G0/G1/G2 continuity verification</strong> Read it this way: three panels left to right—the control mesh (control points rearranged by design parameters), surface lofting (semantic patches skinned with G2-enforcing boundaries), and the continuity spectrum (G0 position / G1 tangent / G2 curvature, green marking the Class-A threshold). The bottom bar states why NURBS, not meshes, is the engineering expression: analytic precision, parametric drive, industrial compatibility.</figcaption></figure>

## 2. Principles

**Principle 1: One parameter source; everything else is derived.** The system permits exactly one human-editable object—the parameter vector. Meshes, surfaces, scores, and export files are all derived from it, and derivation may carry no hidden state of its own. Every editing entry that "pulls a vertex directly on the mesh" or "patches a region by hand on the surface side" manufactures a second source of truth.

**Principle 2: Expressions live downstream; take the one you need.** Different stages need different geometric expressions: interaction wants triangle meshes (fast), engineering wants NURBS (exact), review wants quality metrics (judgeable), delivery wants STEP/IGES (transferable). Each expression has its use, but none deserves the title "master expression"—they are four projections of the same parameter vector, and which projection you read depends on the question at hand.

**Principle 3: Refuse secondary fitting; take the forward road to the end.** Generate surfaces from parameters forward; do not fit surfaces from meshes backward. Forward generation has no fitting residual, and every designer edit propagates exactly into control-point changes. Backward fitting forever carries an irreducible approximation error that accumulates with every edit. Secondary fitting saves one-off development cost; what it pays is uncertainty in every iteration.

**Principle 4: Tolerances come first; criteria are born with the construction.** Quality standards are not an inspection procedure after construction but a constituent of the construction itself: continuity thresholds, sampling density, and grading rubrics are fixed at generation time. Problems found by after-the-fact inspection can only be reworked; criteria endogenous to construction can prevent them.

## 3. Case Anatomy: How Two Pipelines Share One Vector

In EVOLUTION AI, a vehicle is described by the 22-dimensional CarParams (`algorithm_model/car_modeling/car_params.py`), and this single object is the common input to two geometric pipelines.

**The mesh path serves interaction.** The parametric body is built from longitudinal and circumferential section rings (default discretization 48×24) and assembled with wheels, lamps, grille, mirrors, and glass into a 10-part vehicle mesh of 176 vertices and 316 faces, feeding the Three.js viewport for real-time preview and STL/GLB tessellated export. The assembler also reports per-part vertex and face counts, bounding boxes, and stable part colors so the frontend can render, identify, and count.

**The NURBS path serves engineering.** A separate builder constructs the body as true NURBS surfaces from the control mesh—33 surfaces for a full vehicle—with dedicated modules building front and rear end caps that meet the body with G1 tangent transitions. Companion freeform operators cover sweeping and filleting; STEP is emitted by a pure-Python writer (`algorithm_model/freeform/step_writer.py`) following ISO 10303-21, with no dependency on an Open-CASCADE-scale kernel. The crucial point: surfaces are generated directly from parameters, not reverse-fitted from triangle meshes—there is no fitting residual.

**Quality and export are downstream of the same source.** The continuity checker (`continuity_checker.py`) samples the four parametric boundaries of each named surface (50 points per edge by default) and judges every seam against G0 0.1 mm and G1 1.0° thresholds, writing TXT/CSV reports; the surface-quality package produces G0/G1/G2 counts, reflection-line scores, and A–D grades on the mesh side. Two paths, two granularities, complementary criteria: exact NURBS continuity at the seams, plus curvature distribution across the tessellated body.

The chain thus closes: `CarParams ──► mesh assembly ──► interactive preview / STL / GLB` and `CarParams ──► NURBS body + G1 end caps ──► G0/G1/G2 analysis ──► STEP/IGES`. Every arrow is a pure function of the same parameter vector. This is why the Bayesian optimizer of Chapter 3 can treat "styling plus quality" as a single evaluable function—suggest one parameter set and all four expressions materialize at once; no representation needs manual reconstruction.

<figure class="doc-figure"><img src="../docs/images/en/phil-closedloop.svg" alt="The end-to-end closed loop: parameters, NURBS generation, quality evaluation, Bayesian optimization"><figcaption><strong>Figure 5-2 ｜ The end-to-end loop: parameters → NURBS generation → quality evaluation → Bayesian optimization</strong> Read it this way: the horizontal main chain has four steps, and the dashed loop writes suggested parameters back into the next round. The bottom bars give per-round latency (seconds), typical convergence (20–40 rounds), and the human-machine division (people set aesthetic bounds; the machine explores the optimum). The loop can exist only because every step on the main chain is a pure function of the same vector.</figcaption></figure>

## 4. Antipatterns and Their Cost

**Bridging with secondary fitting.** Preview on meshes, reverse-fit NURBS before delivery. The cost is fitting residuals plus manual repair: every design iteration repays the translation fee, and repairs are irreproducible—"how was this fixed last time" has no answer.

**Two sources of truth.** Edit one version in the parameter panel, then hand-pull another on the mesh side. Flexible in the short run, disastrous in the long: nobody can compute the difference between the two shapes, and between the version the review approved and the version engineering received yawns a gap of manual reconciliation.

**Separate preview and delivery geometry.** Simplified models for fluency in preview; refined models rebuilt for delivery. The cost is institutionalized "what you see is not what you get": what the review approved was never the thing to be manufactured.

**Tolerances inspected after the fact.** Build geometry casually, check quality before delivery. Problems can then only be reworked, not prevented; and rework near delivery has no time budget, so it ends in quality compromise.

## 5. Operating Checklist

| Item | Pass criterion | Evidence in this repository (file or command) |
|---|---|---|
| Parameters are the only editable object | No entry bypasses parameters to edit geometry directly | 22-dim CarParams as the sole input, `algorithm_model/car_modeling/car_params.py` |
| Four expressions share one source | Mesh/NURBS/quality/export are all forward-generated from parameters | 176-vertex mesh assembly (`body.py` + assembler); 33 NURBS surfaces (`body_nurbs.py`) |
| No secondary-fitting path exists | The codebase contains no mesh→NURBS reverse-fitting procedure | Both pipelines start from CarParams; see `docs/EVOLUTION_AI_paper.md` §4 |
| Tolerances are endogenous | Continuity thresholds are fixed at construction and judged seam by seam | G0 0.1 mm / G1 1.0°, 50 samples per edge, TXT/CSV from `continuity_checker.py` |
| Exports verify independently | STEP output opens in third-party kernels | Pure-Python `step_writer.py` (ISO 10303-21) plus a bundled FreeCAD verification macro |
| One loop round is reproducible | Parameters → four expressions → score in one command | `python algorithm_model/test_all.py` five-module self-check |

## 6. Chapter Self-Check

1. In your system, are the shape the designer reviews and the file the engineer receives generated from the same parameter set? If not, who aligns the difference, at which step, and at what cost?
2. Does your codebase contain any procedure that "derives the expression from the result" by fitting? If so, on whose account is the residual booked?
3. Are quality standards honored during construction, or inspected before delivery? For problems caught by inspection, how long is the road back to the construction side?
