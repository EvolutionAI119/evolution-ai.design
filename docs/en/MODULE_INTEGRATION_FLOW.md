# Module Integration Flow: Login Auth → Token-Based Training → Workflow Review

> Version v1.0 · 2026-09-27 · Status: implemented and verified end-to-end
> Related modules: Auth · Training · Workflow · Projects · Frontend DeepLearning

## 1. Overview and Design Goals

This report maps the functional correlation among the auth, training, and workflow modules of the EVOLUTION AI platform, and lands one end-to-end business spine:

1. **Identity verification**: the user logs in, identity is validated, and a valid JWT Token is issued;
2. **Credentialed training**: the Token serves as the identity credential to start and execute project training tasks;
3. **Output review**: training outputs are automatically submitted into the preset workflow review system, ensuring every output passes **compliance review** and **quality review** by human gatekeepers.

Design principles: minimal credential exposure (the Token lives only in frontend memory/localStorage and request headers — never in logs); strict ownership checks (training outputs can only be submitted by their owner); non-bypassable review (the auto-execution channel explicitly rejects review-type workflows).

## 2. Module Correlation Map

<figure class="doc-figure">
  <img src="docs/images/integration-flow.svg" alt="Integration map with review state machine" loading="lazy">
  <figcaption><strong>Fig. 2-1 Integration map: authentication → token training → workflow review, with the review state machine</strong>How to read: The top row chains modules A (authentication), B (token training) and C (workflow review) via JWT and submission packages; below is the review state machine (Draft → InReview → Approved, Rejected looping back in red). The bottom strip notes all three gates live in backend dependency injection.</figcaption>
</figure>

```
┌─────────────┐  ①email+password ┌──────────────┐  ②issue JWT(7d) ┌──────────────────┐
│  Login.vue  │─────────────────▶│ auth.py      │────────────────▶│ auth store        │
└─────────────┘                  │ /auth/login  │                 │ localStorage      │
                                 └──────────────┘                 └────────┬─────────┘
                                                                           │ ③Bearer Token
                                        axios interceptor auto-attaches ◀──┘ (401 → auth-required event)
                                                       │
┌────────────────────┐  ④start training   ┌──────────────────┐
│ DeepLearning.vue   │───────────────────▶│ training.py       │──▶ TrainingTask table
│ (auth gate+polling)│◀──task polling─────│ /ai/train thread  │    (user_id + metrics_json)
└────────────────────┘                    └──────────────────┘         │ ⑤auto-trigger on completion
                                                                           ▼
┌──────────────┐  ⑥attach  ┌───────────────────────────────┐
│ Project      │◀─────────│ workflow.py                    │
└──────────────┘           │ /workflows/training-review     │
       ▲                   │  preset: Compliance→Quality    │
       └──⑦view project──── └───────────────────────────────┘
```

| Module | Core Responsibility | Correlation Points |
| --- | --- | --- |
| Auth | Identity verification, JWT issue/validate | `Depends(get_current_user)` injected into all protected routes |
| Training | PyTorch background jobs, metrics/checkpoints | `TrainingTask.user_id` ownership; output digest as review evidence |
| Workflow | Process orchestration and human review | `Workflow.project_id → Project`; step `input_params` carries training evidence |
| Projects | Resource container | The training-review workflow attaches to the user's project for traceability |

## 3. End-to-End Flow

### 3.1 Login → Token

The frontend `Login.vue` posts credentials to `POST /api/v1/auth/login`; the backend validates and issues a 7-day JWT. The frontend persists `access_token` in localStorage (key `evoai_token`); an axios request interceptor attaches `Authorization: Bearer <token>` to every business request. On 401, the token is cleared and an `evoai:auth-required` event is broadcast to restore the login state globally.

### 3.2 Token → Start Training

The DeepLearning page places an **identity gate** before the "Start Training" action: if not authenticated, a friendly dialog redirects to `/login?redirect=/deep-learning` and returns after login. The backend `POST /ai/train` enforces `Depends(get_current_user)` JWT validation and stamps `user_id` onto the persisted task, guaranteeing ownership at the data layer. The frontend polls `GET /ai/tasks/{id}` every second until the task reaches completed / failed / cancelled.

### 3.3 Training Output → Preset Review Workflow

When the poll observes `completed`, the frontend automatically calls `POST /workflows/training-review` (with the Bearer Token). The backend validates in order: project exists → task belongs to the caller (`TrainingTask.user_id == Token.sub`) → task is completed. It then creates a `training_review` workflow with two **manual** review steps:

1. **Compliance review (compliance)**: data provenance, synthetic-sample declarations, training configuration;
2. **Quality review (quality_review)**: whether best validation accuracy and other output metrics meet the bar.

Both steps carry a training-evidence digest in `input_params` (task_id, task name, dataset, best validation accuracy, submitter email) for full auditability. Reviews advance via `POST /workflows/{id}/steps/{sid}/review`; the `execute` auto-execution channel returns 400 for `training_review` type, preventing any bypass of human review.

## 4. Data Interaction and API Contracts

| Endpoint | Method | Auth | Request Body | Response / Status |
| --- | --- | --- | --- | --- |
| `/api/v1/auth/login` | POST | public | `{email, password}` | `access_token` (JWT, 7 days) |
| `/api/v1/ai/train` | POST | **required** | `{dataset, epochs, batch_size, learning_rate, samples, seed, car_type}` | task object (with polling id) |
| `/api/v1/ai/tasks/{id}` | GET | required | — | task status/progress/metrics (polling) |
| `/api/v1/workflows/training-review` | POST | **required** | `{project_id, task_id}` | 201 workflow; 404 project/task missing; 400 task not completed |
| `/api/v1/workflows/{id}/steps/{sid}/review` | POST | **required** | `{approved: bool, comment?: str(≤500)}` | 200 + `workflow_status`; 400 not reviewable / finalized |
| `/api/v1/workflows/{id}/steps` | GET | optional | — | step details (status/progress/review I/O) |

Conventions: auth failures return `401 {"detail":"缺少认证信息，请先登录"}` or `401 {"detail":"Token 无效或已过期"}`; business validation failures return 400/404 with a readable `detail`; review `comment` is capped at 500 characters.

## 5. Authentication and Authorization Mechanism

- **Issuance**: JWT payload carries `sub` (user_id), `email`, `exp`, `iat`, signed with HS256;
- **Transport**: only via the `Authorization: Bearer` header — never in URL query strings or logs;
- **Validation (AuthN)**: protected routes resolve and verify signature and expiry through `Depends(get_current_user)`; any failure is 401;
- **Ownership checks (AuthZ)**: the submission endpoint double-checks — the task's `user_id` must equal the Token subject (prevents submitting someone else's output) and the task must be in the completed terminal state;
- **Auditability**: review verdicts persist the `reviewer` email and timestamp, forming a non-repudiable evidence chain.

## 6. Review State Machine

```
                 created (auto-triggered on training completion)
                            │
                            ▼
                       ┌─────────┐   any step rejected  ┌─────────┐
                       │ pending │─────────────────────▶│ failed  │
                       └────┬────┘                      └─────────┘
                     first step approved
                            ▼
                       ┌─────────┐   any step rejected  ┌─────────┐
                       │ running │─────────────────────▶│ failed  │
                       │(reviewing)                         └─────────┘
                       └────┬────┘
                    all steps approved
                            ▼
                       ┌──────────┐
                       │ completed │
                       └──────────┘
```

Step-level states: `pending → completed` (approved) or `pending → rejected` (rejected); rejected is terminal, requiring a re-run or separate handling. Workflow-level status is derived by aggregating steps — there is no manual set path.

## 7. Verification Records

End-to-end verification (2026-09-27, all passed):

| # | Scenario | Expected | Observed |
| --- | --- | --- | --- |
| 1 | Call review endpoint without Token | 401 | `{"detail":"缺少认证信息，请先登录"}` |
| 2 | Login for Token + create project | 200 / 201 | pass |
| 3 | Create training-review workflow with Token | 201 + 2 preset steps + evidence | pass |
| 4 | execute the review workflow | 400 rejected | pass |
| 5 | Compliance review approved | workflow: pending→running | pass |
| 6 | Quality review approved | workflow: running→completed | pass |
| 7 | Rejection branch | workflow: →failed | pass |

Regression baseline: vitest 111 tests green, `vite build` passing. Temporary users/projects/workflows created during verification were cleaned up.

## 8. Related Documents

- [Architecture Design](ARCHITECTURE_DESIGN.md): five-layer architecture, route modules, ORM tables
- [API Reference](api_reference.md): all 118 endpoints in detail
- [Development Methodology](methodology.md): five-dimension methodology and SOPs
- [Validation Report](VALIDATION_REPORT_20260927.md): latest platform quality evidence baseline
