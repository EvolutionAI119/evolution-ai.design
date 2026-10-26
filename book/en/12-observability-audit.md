# Chapter 12. Observability and End-to-End Audit

> Author: Quantum Swordsman
> Volume IV · Engineering: Converging Uncertainty into Delivery

## 1. The Question

Tests answer whether the system keeps its promises right now; observability answers an older question: which real execution stands behind that "pass" from three months ago? Who operated on which object at what time? When a quality score of 0.85 is challenged, can it be traced back to the evaluation that produced it, the parameters that fed it, the version that ran it? AI-native systems generate a large share of their output through models and algorithms, which are uncertain by nature. When a conclusion is questioned, a team cannot defend it with recollection and verbal assurance—only with records.

Two groups of concrete questions follow. First, what to record: recording everything drowns the signal and touches privacy; recording too little leaves no evidence at the critical moment. Second, how recording can avoid harming the system: if audit writes share the transaction and the exception path of the business flow, auditing itself becomes a source of failure. The proposition of this chapter is: **every conclusion must be traceable to one real execution**, and what supports that proposition is an audit data structure designed as a first-class citizen—not log-grepping as an afterthought.

## 2. Principles

**First, facts land in tables, not scattered across text logs.** Facts that can be questioned must be structured: who logged in, when, and by what method (`login_records`); which administrator performed which action on which object (`admin_audit_logs`); which visitor visited which page for how long (`page_views`). Structure means the data can be queried and aggregated by person, by object and by time window; plain text logs can only be searched by keyword and luck.

**Second, auditing never blocks the business.** Audit is a side channel of evidence, not a link in the main flow. When an audit write fails, the business must continue. Making audit a synchronous hard dependency lets the observer kidnap the observed.

**Third, record metadata only, never content.** Security events carry IP, path, counts and the names of matched signatures; they never carry prompt bodies, response content or sensitive user data. The value of audit lies in "what happened", not "what was said"—once the latter is stored, it becomes a new attack surface of its own.

**Fourth, every number carries a date and a definition.** The observability system must observe itself: every externally cited metric is labelled with its snapshot time and statistical definition; old and new snapshots are kept side by side and never overwrite each other.

## 3. Anatomy of the Case

Among the platform's 17 ORM tables, three exist purely for audit and observation. `login_records` (LoginRecord) stores the sign-in ledger: time, method (password, WeChat scan, official-account authorisation) and IP. `admin_audit_logs` (AdminAuditLog) stores administrative operations: operator, action and object. `page_views` (PageView) stores page-visit telemetry: path, dwell time and visitor identity. The three are not one universal log table; they are modelled separately according to how each will be questioned: security questions look up sign-ins by person, compliance questions look up operations by object, and product questions look up traffic by page.

The read side is equally structured. The `analytics.py` module exposes 21 endpoints for telemetry statistics—PV/UV, daily/weekly/monthly trends, mean dwell time and page distribution—all aggregated from `page_views`. The `admin.py` module exposes 7 endpoints that surface user management, login records, audit logs and back-end errors to the admin console. The standalone `/admin/` console keeps five tabs—login records, user management, back-end errors, audit logs and impact evidence—so that "who did what in the system" becomes a clickable fact rather than a SQL statement an operator must run by hand.

<figure class="doc-figure"><img src="../docs/images/en/audit2-image.svg" alt="The audit floor of 9–10 August 2026: four parallel workstreams—cleanup, testing, fine-tuning and containerisation—with 201 tests passing"><figcaption><strong>Figure 12-1 ｜ The audit floor: four parallel workstreams of evidence collection (9–10 August 2026)</strong> How to read: the archive box on the left corresponds to dead-code cleanup (137 deletions, about 80 files archived); the central terminal shows the day's 201 passing cases with 9 known warnings; the upper right holds the fine-tuned expert Q&A results; the lower right shows the Docker containerisation artefacts. An audit is not minutes written afterwards: each of the four workstreams left its own reviewable evidence—command output, commit hash c6a65af3, Q&A pass counts and the image inventory.</figcaption></figure>

Beyond the business tables, the platform runs a dedicated security-event stream. `backend/app/fence/audit.py` writes security events as JSONL to `backend/logs/security-audit.jsonl`, rotated by a RotatingFileHandler. Event names follow a "domain.object.result" convention—`auth.login.failure` (brute-force early warning), `authz.denied` (privilege-escalation attempts), `ratelimit.hit` (rate limiting triggered), `llm.request` (LLM proxy call metadata), `llm.guard.injection` (prompt-injection signature matched), and so on. Every record carries the `request_id` filled in by the request-context middleware, so one request can be cross-identified between business logs and the security-event stream. Two design details embody the principles of this section: `emit()` promises never to raise, so an audit failure degrades to one warning log line; and the event payload accepts metadata only—prompt bodies and keys never reach the disk.

The final link of the audit system is its own credibility. The audit report of 10 August 2026 labels "201 cases, all passing" as the baseline of 9 August and keeps it unaltered. The supplementary audit of 11 October 2026 opens a new snapshot: 483 items (341 back-end passes, one skip, two expected failures, 142 front-end passes) plus the merged commit range. Both sets of numbers coexist in the same document, and a legend explicitly forbids either from overwriting the other—the observability system applies the same definitional discipline to its own figures.

<figure class="doc-figure"><img src="../docs/images/en/audit2-legend.svg" alt="Audit legend: status symbols, colour blocks and time definitions; 201 and 483 belong to different snapshots"><figcaption><strong>Figure 12-2 ｜ Audit legend: status, colour blocks and time definitions</strong> How to read: read section D for time definitions first, then sections A/B for status and colour; 201 (9 Aug) and 483 (11 Oct) belong to different snapshots and must not overwrite each other. The legend is itself a visualised audit rule: before any number enters a report, it declares which time point and which definition it belongs to.</figcaption></figure>

**Cross-Domain Mapping.**

- Here = every restyle, training run, and adjudication leaves a JSONL audit record, so the decision chain can be replayed. In a general agent = tool-call traces, intermediate reasoning, and the final action are all retained; incident review does not rely on memory.
- Here = metrics and logs answer "which layer failed". In RAG = retrieval hits, cited sources, and generated passages must align line by line, so a hallucination can be traced to retrieval or to generation.

**Capability status.** JSONL audit trails and request tracing are [Implemented · Test-Locked]; cross-service causal attribution remains a design principle [Design Principle].

## 4. Anti-Patterns and Their Costs

**Treating logs as audit.** Scattered `print` statements and text logs are called an audit system. The cost appears at questioning time: aggregation by person or object is impossible, and grep-produced fragments form neither a chain nor evidence.

**Letting audit block the business.** Audit writes share the business transaction, so a database wobble kills the main flow. The observer kidnaps the observed, and the team eventually switches auditing off "to stay safe"—the most expensive outcome of all.

**Recording everything, including content.** Prompt bodies, responses and even keys are written to logs. Convenient for debugging in the short term; in the long term it copies sensitive data to the least-defended location, and the audit store itself becomes the target of exfiltration.

**Recording success but not failure.** Only successful logins are persisted; `auth.login.failure` is missing. Brute-force attempts are completely invisible until an account falls, and the retrospective finds no door to look through.

**Numbers without definitions.** A report says "all green" without a date, and 201 is conflated with 483. Once the observability system's own numbers lose credibility, its observations of everything else lose authority too.

## 5. Operational Checklist

1. Administrative actions land in `admin_audit_logs`: operator, action and object are all present; follow the assertion style of `test_admin_rbac.py` for `set_active` and `reset_password`.
2. Sign-in events land in `login_records`: time, method and IP at minimum; failures are recorded as faithfully as successes.
3. Page telemetry lands in `page_views`: path, dwell time and visitor_id; aggregate queries read this table only, never the business tables.
4. Security events go through `emit()` in `backend/app/fence/audit.py`; event names follow the "domain.object.result" convention.
5. Audit writes never raise: every new audit point stays a side channel, degrading to a warning log on failure.
6. Payloads carry metadata only: IP, path, counts, signature names; prompt bodies, keys and response content are forbidden in audit.
7. Thread `request_id` through business logs and the security-event stream so one request can be identified at both ends.
8. Audit reading happens in the standalone `/admin/` console; the public front end contains no admin code or routes.
9. Write tests for auditing: after an administrative operation, assert the corresponding row exists in the audit table—do not stop at a 200 response.
10. Metrics cited in reports carry snapshot dates and definitions; old and new snapshots are kept side by side and never overwrite each other.

## 6. Self-Check

1. When a quality conclusion is challenged, can you locate the execution, the parameters and the version that produced it within ten minutes? If not, at which layer does the chain break?
2. When an audit write fails in your system, what happens to the business flow? Was that answer designed, or has it never been asked?
3. Does your security-event stream contain failure records such as `auth.login.failure`? What trace would a brute-force attempt leave in your system today?
