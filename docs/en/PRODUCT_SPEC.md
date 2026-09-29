# Product Function Specification

> Version: platform v1.2 (updated from code status on 2026-09-27)
> This document describes the platform's **implemented** functions; page functions correspond one-to-one with the interfaces / stores the source code invokes.

---

## 1. Product Positioning

EVOLUTION AI is an AI platform for automotive styling development, aiming at
"**from one sentence to a 3D full vehicle**": full-chain support from concept-parameter input → parameterized modeling → AI optimization → quality analysis → engineering delivery.

The platform also hosts:

- **Design side**: real-time parameterized body generation and 3D preview, variant management, brand-vehicle knowledge base;
- **Intelligence side**: deep-learning training, generative design, Bayesian optimization, NURBS expert dialogue, unified LLM proxy;
- **Engineering side**: CAD import/re-param, Class-A quality checks, multi-format export and data handover;
- **Account side**: registration/login (password / WeChat), API-key management.

---

## 2. User Roles

| Role | Core need | Main pages |
|---|---|---|
| Automotive styling designer | Fast generation and comparison | Designer, DeepLearning, Demo |
| Project lead | Managing projects, models, workflows | Dashboard, Projects, ProjectDetail |
| Surface/quality engineer | Class-A checks and engineering delivery | Quality, Deliver |
| ML engineer | Training tasks, sample generation and export | DeepLearning (with Bayesian linkage) |
| Registered user | Account and personal API keys | Login, Account |
| Administrator | Sees all training tasks; user-management fields in place | Whole site (is_admin) |

---

## 3. Core Usage Scenarios (End-to-End)

<figure class="doc-figure">
  <img src="docs/images/en/product-journey.svg" alt="End-to-end journey" loading="lazy">
  <figcaption><strong>Fig. 3-1 End-to-end journey: guest experience → sign-up unlock → creation and optimization → review and delivery</strong>How to read: Three role swimlanes with a serpentine line — guests browse with zero friction; the amber node fires the login prompt on write actions; blue nodes are user creation flows; green is admin review and delivery, purple is operations. The right panel lists six journey principles.</figcaption>
</figure>

1. **Parameterized concept design**: choose vehicle type/style/brand and parameters in Designer → generate a 3D full vehicle → cloud sample batch / quality evaluation / generative design / optimization → save variants and compare.
2. **CAD import / re-param / export**: upload a CAD/model file in Deliver → parse parameters → modify with 3D preview → choose a format, export, download.
3. **Quality-driven iteration**: start a quality check in Quality → review reports and history → return to the design side to adjust by score.
4. **ML training loop**: create a backend PyTorch task in DeepLearning → poll progress/metrics → cancel or complete; samples can be produced by the Bayesian container.
5. **Bayesian search**: create a session → suggested parameters → score backfill → converge → export training samples.
6. **Account and login**: register / password login / WeChat scan or official-account authorization; configure LLM-provider API keys in Account.

---

## 4. Page Function Definitions

### 4.1 Dashboard (`/`)

- Overview home: capability and module navigation.
- Login state from the global route guard and the auth store.

### 4.2 Designer (`/designer`)

The AI parameterized designer and core workbench:

- Vehicle/style/brand parameter selection and panel input;
- `carAPI.generate` produces the full vehicle, rendered in 3D in real time;
- Cloud capabilities (via `aiAPI`):
  - `getDatasetStats` dataset statistics;
  - `trainBatch` cloud synthetic sample batch;
  - `evaluateQuality` styling-parameter quality evaluation;
  - `generateDesign` generative design;
  - `optimize` parameter optimization.

### 4.3 Projects (`/projects`)

- Project list (status filter), data via project store → `projectAPI.list`;
- Create (`projectAPI.create`);
- Delete (`projectAPI.delete`);
- Mock-project fallback when the backend is unavailable.

### 4.4 ProjectDetail (`/projects/:id`)

- Detail (`projectAPI.get`), edit/update (`projectAPI.update`);
- Model builds and status (buildAPI), model-file management (modelAPI);
- Variants (variantAPI) and workflows (workflowAPI) organized within the detail.

### 4.5 DeepLearning (`/deep-learning`)

The deep-learning designer:

- Create backend PyTorch tasks via `aiAPI.train` with task parameters (epochs/batch_size/lr etc.);
- Poll tasks with `getTask` (status, progress, metrics, logs), cancel with `cancelTask`;
- List tasks with `listTasks`;
- Training capabilities and concurrency via `getTrainingCapabilities`;
- Sections introducing style transfer and other capabilities (i18n copy).

### 4.6 Quality (`/quality`)

- Start a quality check with `qualityAPI.check`;
- Report list (filter by project/model) with `qualityAPI.list`;
- Report detail with `qualityAPI.get`: grade, G0/G1/G2, report data;
- Historical string reports automatically normalized into structured display.

### 4.7 Deliver (`/deliver`)

The engineering delivery center over the full import/re-param/export chain (`importExportAPI`):

- Session list; import via JSON parameters or direct file upload (`importModel` / `importFile`);
- Query parameters `getParams`, modify `modifyParams`;
- Snapshot `getSnapshot`; 3D preview;
- Multi-format export `exportModel`, file download `downloadFile`;
- Session deletion.

### 4.8 Demo (`/demo`)

Function demonstration: fetch body parameters (`carAPI.getParameters`), generate a demo vehicle (`carAPI.generate`), export (`carAPI.export`).

### 4.9 Login (`/login`, public)

- Probe login methods with `authAPI.methods`, showing available entries per backend config;
- Password login / registration (auth store → authAPI);
- WeChat open-platform scan: QR via `wechatQr`;
- Official-account web authorization: `mpAuthorize` → poll ticket via `mpPoll`;
- On success, write the token and return to the redirect address.

### 4.10 Account (`/account`)

- Current account info;
- LLM-provider API-key management (`apiKeyAPI`): list, set, delete (Fernet-encrypted backend-side).

### 4.11 Help (`/help`)

- **3D Knowledge Graph**: 12 knowledge-base documents as 3D nodes clustered in 4 layers (Philosophy & Methodology / Strategy & Academic / Architecture & API / Quality & Validation), with logical links between nodes; drag to rotate, scroll to zoom, click a node to load the original Markdown as inline HTML;
- **Module Manual**: function descriptions, entry paths, and practical tips for the page modules;
- **Doc System**: the four-layer knowledge-system overview and three engineering principles (Signal First / Thin Orchestration / Full Auditability).

---

## 5. Platform Capability Matrix

| Capability domain | Implemented capabilities |
|---|---|
| Body generation | Full/single-part parameterized generation, parameter query, regeneration, export |
| Model management | Upload, list, detail, delete, build/rebuild/batch, cache management |
| Variants & versions | Create, list, detail, history, compare, rollback |
| Workflows | Create, list, detail, execute, steps, update, delete |
| Quality engineering | Quality checks, report list/detail, topology optimization, data handover |
| Import/export | File/parameter import, parameter tree and groups, re-param, preview, snapshot, multi-format export, download |
| AI training | Backend PyTorch training, task management, synthetic batches, capability query |
| AI analysis | Quality evaluation, generative design, parameter optimization, dataset statistics |
| Bayesian optimization | Sessions, suggestions (EI/UCB), observations, best, sample export |
| LLM | Multi-provider unified proxy (chat/embeddings/text-to-image), NURBS expert dialogue, local expert service |
| Texture design | Region list, pattern analysis, application to sessions |
| Auth | Register, password login, WeChat scan / official-account authorization, JWT, encrypted API-key management |
| Internationalization | Chinese / English bilingual |
| Knowledge base | Parameters and design-language metadata for 5 brands and 19 models, semantic queries and similarity retrieval |
| Graph & Help | 3D graph (12 docs / 4 layers / logical links), module manual, doc-system overview, inline Markdown reading |

---

## 6. Non-Functional Requirements

- **Internationalization**: vue-i18n Chinese–English with full page coverage.
- **Usability degradation**: backend unavailable → frontend mock fallback; PyTorch / Ollama / Redis / CLIP missing → 503 or automatic degradation, never faking success.
- **Security**: JWT auth, Fernet API-key encryption, production SECRET_KEY fail-fast, unified security headers and CORS allow-list (see architecture doc).
- **Observability**: frontend request/response logging; persisted training-task progress, metrics, and logs.
- **Deployment adaptability**: local development (Vite/FastAPI/cpolar) and Docker Compose production.

---

## 7. Constraints and Boundaries

- This document describes only implemented functions; planned capabilities (e.g. production PostgreSQL, an expanded traditional-pattern library) are outside the list.
- Scripts under `scripts/` are historical data-collection / training aids and are not web-product functions.
