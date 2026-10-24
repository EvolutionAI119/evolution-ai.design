# Chapter 10. Semantic Interfaces: From Texture to Brand DNA

> Author: Quantum Swordsman
> Volume III · Intelligence: Putting Models into the System

## 1. The Problem: How Aesthetic Judgment Enters an Engineering Process

The most expensive sentences at a styling review are the ones no machine can execute: "make it more aggressive," "this doesn't look like our brand," "the lamp signature needs to be sharper." These judgments are real, important, and impossible to refute — and equally impossible to regress. A design deemed "very on-brand" last week becomes "not quite on-brand" when the jury changes; the same texture image is "sporty" in the morning and "garish" in the afternoon. **Any judgment that cannot be reduced to numbers and versions cannot enter an engineering process** — only the meeting minutes.

EVOLUTION AI answers with a family of semantic interfaces: CLIP scores texture images on six style axes; the brand knowledge layer maps semantic vectors onto profiles of 5 brands and 19 car models; and `BrandDNASchema` writes "does this look like our brand" as executable constraint verdicts. The proposition of this chapter is: **use interpretable semantic scoring to turn aesthetic judgment into regressable numbers.** Algorithms will not replace taste, but aesthetic judgment must earn the same engineering standing as geometric tolerance — with a rubric, a version, and reproducibility.

## 2. Principles

### Principle 1. Language never drives geometry directly; it must first become numbers and schemas

Before natural language or imagery enters the system, intent must be translated into objects with names, units, and bounds. A sentence like "a low, sporty SUV" is parsed by design_intent into structured parameters and parameter variants; a lamp texture is encoded by CLIP into six [0,1] scores. Once translation happens, judgment has a shape. Without translation, language is only atmosphere.

### Principle 2. Fixed rubric, regressable scores

The entire value of a semantic score lies in regression: the same image, the same prompts, and the same weight version must yield the same score. Each of the platform's six style axes binds a Chinese label to a concrete English visual prompt — a deliberate prompt-engineering choice, because CLIP responds far better to concrete visual descriptions than to abstract adjectives. Prompts and the weight version (`openai/clip-vit-base-patch32`, about 605 MB) are archived and managed; only then do scores qualify to enter reviews and optimization loops.

### Principle 3. Semantics must attach to nameable structure

"This car is sporty" is not executable. "Shoulder line rising, greenhouse line lowered, wheel arches flared" is. Semantics must hang on nameable structures: the regions eligible for texture are an explicit list (`/texture/regions`), brand constraints land on brand-gene items, and the feature lines (greenhouse, shoulder, waist, wheel arch, sill) form the styling skeleton. The more specific the attachment point, the more testable the semantics.

### Principle 4. No data means NO_DATA, never a presumed pass

`BrandDNASchema` admits four verdicts: PASS, FAIL, NO_DATA, and N/A. NO_DATA is the most honest of them — when something cannot be measured now, it is labeled as such rather than waved through. When CLIP weights are missing, texture analysis falls back to geometric features and says "geometric features only" in the response. The first virtue of a semantic interface is not cleverness; it is refusing to pretend.

<figure class="doc-figure"><img src="../docs/images/en/phil2-image.svg" alt="Three views of a car with annotated feature lines"><figcaption><strong>Figure 10-1 | Three views and feature lines: the geometric anchors of semantics</strong> How to read: front, side, and top views are three orthogonal projections of the same 22-dimensional parameter vector; the numbered feature lines in the side view (greenhouse, shoulder, waist, wheel arch, sill) form the styling skeleton. For a semantic judgment to be executable, it must attach to these nameable lines — "low stance" must ultimately become numbers for greenhouse height and ground clearance.</figcaption></figure>

## 3. Case Study: From One Texture Image to a Brand Verdict

**The semantic channel for texture.** The texture module has only 3 endpoints: a region list, pattern analysis, and apply-to-session. A reference pattern entering `/texture/analyze` has geometric features and CLIP six-axis semantic features extracted in parallel; the two are fused and applied through `/texture/apply/{session_id}` to the target region of a given session — a lamp lens pattern, for example. When the semantic channel is unavailable, the system falls back to the geometric channel and labels it; the user always knows which kind of evidence they are holding.

**The semantic mapping for brand.** The brand knowledge layer maps the six-axis semantic vector onto brand profiles and recommended models, grounded in a knowledge base of 5 brands and 19 car models (`backend/config/brand_design_knowledge.json`, with the frontend preset mirror in `src/config/carPresets.js`). "Which brand does this image resemble" stops being small talk and becomes a reproducible vector comparison.

**Contract verdicts for DNA.** `BrandDNASchema` pins version 1.0, requires `brand` and `on_brand_constraints` at the top level, and converges rule types to four: zero, range, enum, and sealed. Every constraint is judged independently: zero forbids a feature outright, range defines a numeric corridor, enum restricts discrete values, and sealed freezes a value from change. Verdicts are limited to PASS, FAIL, NO_DATA, and N/A — aesthetic judgment thereby takes the same form as geometric tolerance: itemized, measurable, and rejectable.

**One end-to-end confluence.** A stylist supplies a lamp texture reference. CLIP scores it on the six style axes; brand knowledge recommends matching DNA and parameter adjustments; the Deliver page applies those adjustments inside an import-modify-export session and produces STEP output. Throughout, the designer can consult the local NURBS expert about a continuity warning. Semantics, parameters, and engineering delivery close the loop inside one system, and no step requires "paraphrasing by feel."

## 4. Anti-Patterns and Their Costs

**Anti-pattern 1: The black-box composite score.** One unexplainable number standing in for taste. The cost is a score that cannot be attributed or regressed, and reviews that degenerate into a shouting match of "trust the score or trust me."

**Anti-pattern 2: Prompt drift.** Style-axis prompts edited casually and never archived. The cost is that the same image scores differently this week than last, every historical verdict silently expires, and nobody can say when.

**Anti-pattern 3: Language straight to geometry.** Having a large model generate geometry directly from a sentence, skipping parameters and schemas. The cost is output that can be neither edited nor audited; every generation is like the first.

**Anti-pattern 4: NO_DATA presumed PASS.** Unmeasurable constraints waved through by default. The cost is a brand-verdict table stuffed with evidence-free consent — and the discovery, after something goes wrong, that the pass rate was always fictional.

## 5. Operational Checklist

1. Give every semantic axis a Chinese label and a concrete English visual prompt; manage prompts in version control (following `clip_semantics.py`).
2. Pin the weight version and loading path; when weights are missing, fall back to geometric features with an explicit label.
3. Before semantic scores enter reviews, verify same-image-same-prompt-same-score, and encode regression cases in tests.
4. Maintain an explicit list of texture-eligible regions; forbid the implicit convention that any region will do.
5. Express brand constraints with the four rule types — zero, range, enum, sealed; anything beyond the four triggers a review of the rule design itself.
6. Keep the NO_DATA verdict; every "cannot measure" goes on the record as itself.
7. Route every natural-language entry through design_intent into parameters or variants; never connect it directly to geometry generation.
8. Update the knowledge base (5 brands, 19 car models) and its frontend mirror together, avoiding dual-track facts.

## 6. Chapter Self-Check

1. Can your "brand fit" say which constraints compose it and what each one returned? If not, it is still a slogan.
2. Rerun last week's semantic scoring today — do the scores match? If not, on what grounds do they serve as review evidence?
3. When CLIP weights are missing, does your interface honestly label "geometric features only" — or quietly produce results that look the same?
