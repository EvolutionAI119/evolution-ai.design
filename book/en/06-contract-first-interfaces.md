# Chapter 6. Contract-First Interface Design

> Author: Quantum Swordsman
> Volume II · Architecture: Giving Complexity Its Proper Place

## 1. The Problem: "It Runs" Is Not "It Ships"

A demo needs one path that works. A deliverable system must answer a different set of questions: who may call this, what goes in, what comes out, what state the system is left in after failure, and whether the tenth module added next quarter will silently break the conventions of the first nine. Once an interface surface grows past a handful of endpoints, the dominant risk shifts from "did we build the feature" to "did we keep the agreement."

EVOLUTION AI carries a substantial surface: 19 route modules with 151 router endpoints, plus 2 system endpoints declared directly in `main.py`, for a total of 153 HTTP endpoints. Seventeen ORM tables hold persistent state. If every module invents its own field names, interprets status in its own way, and picks its own error codes, then 153 endpoints become 153 local dialects, and every frontend integration becomes an exercise in re-learning. Contract-first design is the discipline that collapses local dialect into a globally testable agreement.

The proposition of this chapter is: **endpoints, data tables, and state machines precede implementation, and 100 percent field alignment is a hard constraint.** "Precede" is not a slogan about writing documents before code. It means the shape of the interface must be reviewable, testable, and regression-safe before any business logic is written.

## 2. Principles

### Principle 1. The three-layer contract comes before implementation

Every endpoint has three layers of contract. The call contract defines method, path, and authentication level. The data contract defines request and response fields, types, and valid ranges. The state contract defines legal states and legal transitions. Once these three are fixed, implementation is filling in the blanks; while they remain fluid, more implementation experience only produces more thorough rework. The platform expresses the data contract with FastAPI 0.104 and Pydantic v2, keeps all request and response models in `backend/app/schemas.py`, and exposes an OpenAPI description at `/docs`. Authentication levels are declared through dependency injection rather than scattered `if` statements inside handlers.

### Principle 2. Fields align completely; conversion happens only at the boundary

The backend uses snake_case and the frontend uses camelCase. These are naming habits of two languages, not two data models. The platform converts once, at the boundary: the `snakeToCamel` helper in the designer store normalizes underscored fields from the backend, and pages and components see a single naming convention afterward. The training-sample contract follows the same rule. The `feature_order` exported by a Bayesian session must match the training pipeline position by position; otherwise "the samples are trainable" is a wish rather than a property.

### Principle 3. State machines are explicit and error codes carry meaning

State must not be inferred from a combination of booleans. A workflow may be pending, running, completed, or failed. A step may be pending, completed, or rejected. Workflow status is derived by aggregating step status, and there is no manual path for setting it. Failure must not be wrapped as `200 + {success:false}`. A 400 means business validation failed, 401 means credentials are missing or invalid, 404 means the resource does not exist, 405 means the method is not allowed, 409 means a state conflict, 422 means schema validation failed, and 503 means an optional capability is not ready. When each failure has exactly one exit, the caller can write deterministic recovery logic.

### Principle 4. Contracts must be executable and regression-tested

A contract written only in prose drifts. A contract expressed in types and tests raises an alarm. Of the platform's 955 automated tests (205 algorithm, 388 backend, 362 frontend), the backend suite covers route contracts, parameter validation, and failure branches, while the frontend suite covers API modules and store-level field mapping. The contract is not a consensus reached in a review meeting; it is a gate that every commit must pass again.

## 3. Case Study: How 153 Endpoints Speak One Language

Start with the authentication contract. The 151 router endpoints fall into four tiers: 114 public, 9 optional-auth, 12 required-auth, and 16 admin. This is not an arbitrary tally; it is the structural result of "reads stay mostly open, writes converge to authentication, governance converges to admin." Guest mode lets unauthenticated requests through as guests, yet admin endpoints still demand admin-level dependencies. The same dependency-injection stack serves both open reading and high-privilege governance, so no route re-explains permissions on its own.

<figure class="doc-figure"><img src="../docs/images/en/api2-matrix.svg" alt="Matrix of 19 modules against four authentication levels"><figcaption><strong>Figure 6-1 | The matrix of nineteen modules by four authentication tiers</strong> How to read: the four columns are public, optional, required, and admin; each cell holds the number of endpoints of that module at that tier. Column totals are 114, 9, 12, and 16, summing to 151, cross-checked against row totals. The conclusion is that writes and governance are confined to higher tiers while reads stay open; the matrix turns "are permissions under control" into a checkable fact rather than endpoint-by-endpoint testimony.</figcaption></figure>

Next, the chain contract. The main chain from login to token-based training to workflow review spans four modules — auth, training, workflow, and project — covering 41 endpoints. The chain actually calls only 6 contracts, 14.6 percent. The remaining 35 endpoints are management and extension capabilities that the chain never triggers. The size of the interface surface need not scale with the complexity of the chain: with clear contract boundaries, a small chain can safely consume a large surface.

The Bayesian module shows a different contract density. It has only 7 endpoints, yet it writes the session lifecycle in full. Creation validates that the space is non-empty, names are unique, and every lower bound is below its upper bound, else 400. Querying a missing session returns 404. Asking for the best observation before any exist returns 409, not a fabricated empty optimum. Reporting an observation with unknown, missing, or out-of-bounds parameters is always 400. Before two observations, suggestions come from random space-filling; afterward, from the Gaussian process. State and algorithm phase are expressed by one contract, so the caller never has to guess "can I ask for a suggestion yet."

Brand DNA turns the contract into an exchangeable schema. `BrandDNASchema` pins version 1.0, requires `brand` and `on_brand_constraints` at the top level, allows only PASS, FAIL, NO_DATA, and N/A as verdicts, and converges rule types to zero, range, enum, and sealed. Most important is the semantics of NO_DATA: when something cannot be measured now, it is labeled as such and never presumed to pass. Here the contract constrains not just fields but honesty itself.

## 4. Anti-Patterns and Their Costs

**Anti-pattern 1: Improvised interface growth.** Write the page first, then add whatever endpoint it happens to need, naming fields for the convenience of the moment. The cost is that endpoints multiply faster than understanding; every new module integration means reading source to guess semantics, and 153 endpoints become 153 oral traditions.

**Anti-pattern 2: Dual-track fields.** snake_case on the backend, a re-invented camelCase on the frontend, mapping tables maintained on both sides. Nothing breaks at first; over time a field is inevitably changed on one side only. Such bugs throw no exception — they just make a chart quietly lose a series.

**Anti-pattern 3: State hidden in boolean combinations.** Three booleans — `is_running`, `is_done`, `has_error` — give eight combinations, of which only four are meaningful. The cost is a state machine that tests cannot exhaust, with rejections and cancellations falling into undefined intermediate states.

**Anti-pattern 4: Wrapping failure in 200.** Every response returns 200 and distinguishes outcomes with `success:false`. The cost is that gateways, monitoring, and client retry policies all stop working: 503 no longer means capability unready, 409 no longer means conflict, and diagnosis requires reading business code.

## 5. Operational Checklist

1. Before adding an endpoint, write down in the corresponding `backend/app/routes/` module its method, path, auth level, request fields, response fields, and every failure code.
2. For each resource, list legal states and legal transitions (following the step-aggregation pattern in `workflow.py`); never express state implicitly through boolean combinations.
3. Keep a single naming-conversion point: snake_case to camelCase exactly once at the API boundary (see `snakeToCamel` in the designer store).
4. Establish explicit constants for cross-module data orderings such as `feature_order`, and validate length and order at the consumer.
5. Constrain boundary values with Pydantic models in `schemas.py`; do not substitute ad-hoc checks inside function bodies.
6. Assign each error code exactly one triggering condition; the same failure must never return multiple status codes.
7. Write contract tests covering at least: success path, boundary values, unknown fields, missing fields, out-of-range values, and state conflicts (see `backend/tests/test_bayes.py` and `src/tests/api.spec.js`).
8. When a contract changes, update OpenAPI, the frontend `src/api.js`, and tests together — never ship them in separate batches.

## 6. Chapter Self-Check

1. If all implementation code were deleted, leaving only the endpoint tables, schemas, and state machines, could a newcomer say precisely under what conditions each endpoint returns 400, 404, 409, or 503?
2. Does your frontend convert fields exactly once at the boundary, or is every page guessing backend field names on its own?
3. When an optional capability is missing, does your API return 503 with a reason — or a plausible-looking fake success?
