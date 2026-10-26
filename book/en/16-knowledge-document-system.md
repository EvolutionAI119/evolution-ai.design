# Chapter 16 · Documentation as Product: The Knowledge Base and Consistency Auditing

> Author: Quantum Swordsman (量子剑客)
> Volume V · Organization: how humans and machines divide labor
> Core proposition: documentation must be verified against the same source as the code; documentation drift is forbidden.

---

## 1. Introduction: when documents become inputs to the system

Traditional teams treat documentation as an accessory to delivery: the code is written first, the docs are patched in later, and human memory holds the two together. In AI-native development this arrangement fails outright, for two reasons. First, AI agents are a new class of reader—they consult the README, the architecture document, and the API reference to decide how to modify code. A drifted document no longer merely misleads human readers; it becomes a wrong instruction to an agent, amplifying deviation at industrial speed. Second, every commitment a complex system makes lives in its documents: endpoint counts, table structures, threshold conventions, test baselines. Once documents detach from the source, commitments can no longer be checked, and the team's trust in the system dissolves.

Documentation drift rarely comes from malice; it comes from inertia. Changing one line of code takes a minute, synchronizing five documents takes half an hour, so the debt is deferred. The bill arrives during integration, reviews, and the onboarding of new members. This chapter's position is simple: documentation is not the shadow of code but a product of the same rank. It has owners, acceptance criteria, automated auditing—and it is verified against the same source as the code.

## 2. Principles

### 2.1 Documentation is a product

Every document should have a named owner, an intended audience, and acceptance criteria; it is reviewed and changed together with the code. A documentation "defect" can be defined as concretely as a code defect: a number that disagrees with the source, a dead link, an unlabeled counting convention, a promised capability that does not exist. Only what can be defined as a defect can be filed as a defect—and only then does documentation have quality.

### 2.2 The source code is the single source of truth

Facts of scale—endpoint counts, table counts, page counts, parameter dimensions, test counts—are allowed exactly one origin: the current codebase. Every number in a document should be able to answer "which piece of source or which command produced it." Documents may organize, explain, and narrate; they may not invent facts. When a disagreement is found, the document is corrected to match the source, never the reverse.

### 2.3 Mechanical checking first, judgment second

Whatever a script can check should not be left to the human eye. Counting, dead links, and missing navigation entries are mechanical work and belong to a deterministic script. The script extracts facts only; "how this should be phrased" remains a human judgment. The division of labor in documentation mirrors that in design: machines enumerate and compare; humans qualify and adjudicate.

### 2.4 History is not rewritten; conventions are always labeled

Historical reports are archives, not living documents. Old numbers are preserved with their dates and counting conventions; new baselines start a new line. It is forbidden to splice numbers from different dates into a single conclusion, and forbidden to retroactively edit the facts inside a historical report. The object of an audit is "whether current documents agree with reality," not "whether history looks tidy."

<figure class="doc-figure"><img src="../docs/images/en/meta-architecture.svg" alt="Three layers plus one resource library" loading="lazy"><figcaption><strong>Figure 16-1 | The layered knowledge base: three layers and one library</strong> Reading guide: the knowledge system is organized by level—the philosophy layer answers "why this way," the method and strategy layer answers "how to act," the engineering layer answers "how to build," and a shared resource library settles reusable material below. Consistency auditing guards precisely the alignment between layers, and between documents and code.</figcaption></figure>

## 3. Case study: how one-click auditing actually works

The platform turns documentation consistency into a repeatable skill (doc-code-audit). When triggered, it first runs a deterministic script built only on the standard library to extract a factual baseline from the source: the total number of HTTP endpoints (the APIRouter variables across route modules plus the system endpoints in main.py), the number of ORM tables (the `__tablename__` entries in database.py), the number of frontend pages (route records in router.js), the number of CarParams fields, and the dimensionality of the default Bayesian search space. It then checks every statement of scale in the documents against that baseline, correcting documents to match the source wherever they disagree. Dead links must be fixed to paths verified to exist—guessing is forbidden; `file:///` machine-local links are rewritten as repository-relative paths; and the script is re-run until it reports zero problems. If the session also involves code changes, the three test layers are executed for real and their actual output is used as evidence.

This mechanism guards a factual baseline shared across the entire repository: 19 route modules, 154 HTTP endpoints, 17 ORM tables, 12 frontend pages, and roughly 1,027 automated tests (200 algorithm, 411 backend, 416 frontend). The architecture document declares at the top that "all modules, paths, and data in this document take the current codebase as the sole source of truth," labeled with the corresponding version and date. The evolution of the test baseline is likewise traceable: 201 cases on 2026-08-09, 489 on 2026-09-27, 483 items on 2026-10-11, and roughly 1,027 as the current baseline (2026-10-25, per `docs/VALIDATION_REPORT_20261025.md`)—five figures, each with its own date and convention, and every citation must name its time point. The endpoint counting convention was unified from the historical 118 to the current 154 (152 route endpoints plus 2 system endpoints); the old number is preserved and labeled rather than erased from the report.

<figure class="doc-figure"><img src="../docs/images/en/phil-closedloop.svg" alt="End-to-end closed loop from intent to verification and back to knowledge" loading="lazy"><figcaption><strong>Figure 16-2 | The document–code closed loop</strong> Reading guide: every stage of the loop—intent, implementation, verification, archiving—produces both code artifacts and document artifacts; the audit circuit pulls the documents back to the source for checking, and the deviation itself becomes new knowledge input. An open-loop document inevitably drifts; only a closed-loop document can remain trustworthy over time.</figcaption></figure>

**Cross-Domain Mapping.**

- Here = docs live in the same repository as code and are reconciled within the same commit; a stale number counts as a defect. In a RAG knowledge base = documents and index must be rebuilt together; a lagging index is a wrong answer.
- Here = the glossary and chapters cite each other, with one source for every figure. In LLM evaluation = the evaluation spec and the scoring script share one origin, so "the metric in the doc" and "the metric in the script" never diverge.

## 4. Anti-patterns and their costs

| Anti-pattern | Observable behavior | Cost |
|---|---|---|
| Numbers from impression | "About a hundred-odd endpoints" written into a formal document | Numbers contradict one another; readers cannot tell which is fact |
| Promising nonexistent capabilities | The whitepaper describes interfaces not yet implemented | External commitments cannot be honored; reviews lose their baseline |
| Dead and machine-local links | Links point to deleted files or `file:///` paths | Navigation collapses; new readers get lost at the first step |
| Mixing conventions | Adding test counts from different dates to manufacture "growth" | The evidence system is distorted; every number is thereafter suspected |
| The annual cleanup | Documents are overhauled once a year in a burst | Drift outpaces cleanup; auditing degenerates into ritual |
| Audit without repair | Inconsistencies are listed but nobody claims them | The longer the problem list, the more numb the team becomes |

These anti-patterns share one feature: each severs the feedback loop between document and source. Once the loop is broken, a document stops being part of the system and becomes folklore about it.

## 5. Operational checklist

1. Does every document have a named owner, and does its header state the corresponding version or date?
2. For every number of scale in a document, can you point to its source-code origin or generating command?
3. Is there a deterministic script that automatically checks baseline facts such as endpoint, table, and page counts?
4. Is the dead-link count zero, with every fix verified against a real target first?
5. Are historical snapshots labeled with date and counting convention, and left unedited in their factual bodies?
6. Are document changes reviewed and committed together with the corresponding code changes?
7. When an audit finds a problem, is the document corrected against the source and the verification re-run until the script reports zero issues?
8. Are key figures—such as the ~1,027-test baseline—consistent across all current documents?

## 6. Self-check

1. Pick any three numbers from your documents at random: can you trace each one back to source code or command output within ten minutes?
2. If an AI agent modified your code guided solely by your documents, how far would drifted documents amplify the deviation?
3. The last time someone "changed the code and forgot the docs," how long did the debt survive, and how expensive was its discovery?
