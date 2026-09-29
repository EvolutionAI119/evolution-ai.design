# EVOLUTION AI — Styling Development Methodology

> Version: v1.2 (2026-09-27)
> Document ID: EVOLUTION-AI-METH-2026
> Role: turning platform capabilities into an executable styling-development method — how the process runs, how the tools are used, how decisions are made
> Companion documents: this guide answers "how to do it"; [Design Philosophy](design_philosophy.md) answers "why"; [Meta-Theory](design_meta_theory.md) answers "how knowledge is layered"; [Whitepaper](whitepaper.md) answers "what the platform is"

---

## 1. The Methodological Overview

<figure class="doc-figure">
  <img src="docs/images/method-pipeline.svg" alt="Five-stage pipeline with stage gates" loading="lazy">
  <figcaption>Fig. 1-1 Five-stage pipeline with G1–G4 stage gates (failed gates loop back for revision)</figcaption>
</figure>

### 1.1 One Claim

**From one sentence to a 3D full vehicle**: the essence of styling development is to take a vague conceptual intent and, through constrained generation and quantifiable evaluation, converge it step by step into precise, engineering-deliverable geometry.

### 1.2 Three Methodological Pillars

| Pillar | Meaning | Landing point on the platform |
|---|---|---|
| Parameters as language | Expressing both design intent and engineering hard points with one parameter space | 22-dimension CarParams + 14-dimension Bayesian space |
| The loop as process | The infinite cycle of generate → evaluate → feedback → adjust | Designer + Quality Center + Bayesian sessions |
| Evidence as decisions | All option comparisons based on auditable data | Variant comparison, quality reports, training-task records |

### 1.3 Five Dimensions of the Methodology

The platform methodology unfolds across five dimensions covering the full lifecycle of a real styling project:

```
① Development process   — how stages are divided and connected
② Design concept/style  — how the aesthetic direction is set and kept consistent
③ Details & technology  — how styling language lands in engineering
④ Time & resources      — pace, parallelism, decision efficiency
⑤ Users & care          — for whom we design, how it is verified
```

---

## 2. Dimension One: The Development Process

### 2.1 The Three-Stage Main Process

| Stage | Key activities | Platform tools | Output |
|---|---|---|---|
| **Front-end research** | Brand context, market context, user research, reference-vehicle analysis | Demo Center, brand-vehicle knowledge base, user-aesthetics research | Design direction and parameter baseline |
| **Styling design** | Parameter input, full-vehicle generation, option comparison, variant management | Designer, Project / Project Detail, Deep Learning | Multiple 3D proposals and variant sets |
| **Engineering development** | CAD import & re-parametrization, quality checks, format export, handover | Delivery Center, Quality Center, workflows | Class-A surfaces and engineering delivery packages |

### 2.2 The Embedded AI-Collaborative Process

AI is not an add-on at the end of the process; it is embedded in every stage:

| Stage | AI role |
|---|---|
| Front-end research | Vehicle knowledge-base retrieval, texture/style semantic analysis (CLIP) |
| Styling design | Generative design, cloud sample batches, Bayesian search, LLM expert dialogue |
| Engineering development | Automated continuity checking, automated quality grading, export automation |

### 2.3 Process Discipline

- **Hard points first**: freeze size, proportion, and posture parameters before local smoothing — otherwise optimization and evaluation lose their reference;
- **Explicit state**: the state of every project, task, and session must come from system data, never verbal status;
- **Traceable**: every parameter change and score should land in a variant/record so proposals remain reversible.

---

## 3. Dimension Two: Design Concept and Style

### 3.1 Inputs for Establishing Style

- **Brand DNA**: the generational inheritance of core styling language (the platform uses a real brand-vehicle library as reference);
- **Technical characteristics**: electrification hard points (wheel-base ratio, absence of front-engine constraints) shape new proportions;
- **Cultural context**: Chinese aesthetic paradigms (spirit resonance, warmth and restraint) and user-aesthetic segmentation.

### 3.2 Style-Consistency Methods

| Method | Operation |
|---|---|
| Parameter baseline | Starting from the 22 parameters of a brand benchmark vehicle rather than from zero |
| Theme naming | Unifying the team's understanding of direction through narrative themes |
| Storyboard expression | Translating style intent into visual communication assets via video storyboards |
| Proportion control | Constraining deviation through parameter bounds (validation rules) to prevent style drift |

### 3.3 Interior–Exterior Unity

Interior and exterior share one design-language system: styling cognition follows the three-layer structure of "volume → form/feature → graphic elements"; stylistic unity is established first at the volume layer and then descends layer by layer.

---

## 4. Dimension Three: Detail Design and Technical Innovation

### 4.1 The Path by Which Styling Language Lands

```
Aesthetic imagery (subjective) → parameterized rules (computable) → NURBS surfaces (manufacturable)
```

| Link | Platform method |
|---|---|
| Curvature / corners | R-corner regulation thinking → parameterized sections and NURBS fillet surfaces |
| Surface construction | Loft / sweep / blend / revolve + G2 smoothing |
| Continuity | Continuity checker (0.1 mm / 1.0°) outputting deviation pair by pair |
| Texture & decoration | Parameterized texture analysis (six-dimension CLIP semantics) and application |
| Lighting / interaction | Combining lighting geometry with semantic analysis |

### 4.2 Dual Geometry Paths

- **Fast path**: parameterized section meshes generated in seconds, for concept exploration and option comparison;
- **Precise path**: NURBS free-form surfaces plus STEP export, for engineering delivery.
- Both paths share one parameter space, guaranteeing "what you see is what you deliver."

### 4.3 Quality Built In

Quality is not a final-inspection stage but part of the construction rules: G2 smoothing is applied when the surface is generated, and quality grading is available after every generation — forming **quality-driven iteration**.

---

## 5. Dimension Four: Time and Resource Planning

### 5.1 Pace and Parallelism

| Principle | Method |
|---|---|
| Second-level iteration | Parameterized full-vehicle generation and evaluation complete in seconds; proposal count is no longer limited by manpower |
| Parallel work | Modeling, training, and Bayesian sessions proceed in parallel (background threads) |
| Asynchronous convergence | Training/optimization runs as tasks; the frontend polls status rather than blocking |

### 5.2 Countering Process Entropy

In complex projects, environments and opinions continually increase uncertainty. Methodological countermeasures:

- Constraint the proposal space with parameter validation and boundary rules (**constraints are freedom**);
- Use auditable scores as the selection mechanism, preventing decisions from being driven by momentary opinions;
- Fix stage handoffs in workflows (`workflows` / `workflow_steps`) to reduce handover loss.

### 5.3 Decision Mechanism (Selection-Mechanism Theory)

Option selection should follow an explicit mechanism: variant comparison (data) → quality report (evidence) → review decision (recorded). The system does not make final value judgments for people, but ensures every judgment rests on the same set of facts.

---

## 6. Dimension Five: User Orientation and Care

### 6.1 User-Research Methods

- **Cultural geography**: regional aesthetic segmentation (bold North China, sharp Sichuan-Chongqing, plural Lingnan, gentle Jiangnan, vast Northwest);
- **Aesthetic greatest common divisor**: seeking consensus across plural aesthetics rather than imposing a single style;
- **Emotional value first**: styling responds not only to function but to identity and cultural belonging.

### 6.2 Engineering Care

| Aspect | Method |
|---|---|
| Vision | Vision optimization included in styling constraints |
| Operation | Practical consideration of haptic/physical operation |
| Space | Proportion and spatial paradigms serving real occupant scenarios |
| Trust | Explicitly reporting when capability is unavailable rather than misleading decisions with fake data |

---

## 7. Standard Operating Procedures (SOP)

### 7.1 Parameterized Concept-Design SOP

1. Establish design direction and parameter baseline in the project (a brand benchmark vehicle);
2. Adjust parameters in the Designer → generate the full vehicle → preview in 3D;
3. When exploring: create a Bayesian session (or a cloud batch) to generate proposals in bulk;
4. Save key proposals as variants and compare variant by variant;
5. Review the quality grade after each generation; if it falls short, return to parameter adjustment.

### 7.2 CAD Import / Re-Parameterize / Export SOP

1. Upload a CAD/model file in the Delivery Center;
2. Parse to obtain parameters → modify → confirm in 3D preview;
3. Choose a target format (including STEP/GLB), export and download;
4. Archive exports and parameter records into the project.

### 7.3 Quality-Check SOP

1. Start a check in the Quality Center;
2. Review G0/G1/G2 counts, reflection-line score, and overall grade;
3. For precise surfaces, review the continuity checker's pair-by-pair deviations (TXT/CSV);
4. Locate problem areas from the report → return to the design side to adjust → re-check.

### 7.4 ML-Training SOP

1. Export observed samples from a Bayesian session (or use a synthetic sample set);
2. Create a training task on the Deep Learning page (backend PyTorch);
3. Poll progress and metrics; evaluate on completion; failures carry explicit errors;
4. Archive training records for later comparison.

> The platform also provides SOP-checklist capabilities (`car_modeling/sop_checklist.py`) that generate checklists and HTML reports; see examples `examples/example_16_sop_checklist.py` and `example_17_sop_html_report.py`.

---

## 8. Methodology-Maturity Self-Check

Use this checklist to assess whether a project truly applied the methodology:

| # | Check item |
|---|---|
| 1 | Did you start from brand benchmark parameters rather than a blank state? |
| 2 | Were hard points frozen before smoothing/local optimization? |
| 3 | Does every reviewed proposal carry quality data and a variant record? |
| 4 | Was option selection based on the same set of facts (rather than different stories)? |
| 5 | When AI was unavailable, did the team receive an explicit signal? |
| 6 | Were the samples produced by Bayesian/training exported and archived? |
| 7 | Can the final deliverables be traced to specific parameter sets? |
| 8 | Was project knowledge accumulated into reusable organizational assets? |

---

## 9. Closing

The value of methodology lies not in adding process but in letting creation happen under higher certainty: **parameters make intent computable, the loop makes improvement sustainable, evidence makes decisions trustworthy**. When all five dimensions are executed consistently, AI moves from "occasionally astonishing demos" to "a reliable daily production partner."

---

*This methodology corresponds one-to-one with platform v1.2 capabilities; for philosophical roots see the design philosophy, for knowledge layering see the meta-theory, and for validation evidence see the validation report.*
