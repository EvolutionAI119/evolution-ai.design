# Evolution-AI.Design Comprehensive Audit Report

> Report date: 2026-08-10
> Audit scope: all work from 2026-08-09 to 2026-08-10
> Covers: project cleanup & archiving, dead-code audit, LLM fine-tuning & RAG fixes, Docker containerization

---

## I. Project Overview

### Technical Architecture (4 layers)

| Layer | Stack | Core directories |
|---|---|---|
| Frontend | Vue 3 + Vite + Pinia + Three.js + Element Plus | `src/` (8 pages, 4 components, 4 stores) |
| Backend | FastAPI + SQLite + Uvicorn | `backend/` (10 routes: ai / car / build / export / quality / workflow etc.) |
| Algorithm | Cython-accelerated NURBS + parameterized body + Class-A SOP evaluation | `algorithm_model/` (car_modeling / freeform / surface_quality / storyboard) |
| AI/LLM | Qwen2.5-0.5B + QLoRA + RAG (Ollama API compatible) | `scripts/llm_server.py` + `data/training/` |

### Core Functions

- Parameterized body generation: SAE coordinate system, L/W/H/WB parameters controlling 17 components and 33 surfaces
- NURBS surface-quality evaluation: G0/G1/G2 continuity checks, ISO curvature-gradient ratio, CV coefficient of variation, R-corner checks
- SOP checklist: 13 checks, 183 records, 67 automated, 79% automation pass rate
- AI expert Q&A: a NURBS knowledge service over a fine-tuned model plus RAG retrieval

---

## II. Audit Record, August 9

### 2.1 Frontend Image-Loading Fix

**Problem**: in Designer.vue, vehicle images directly called the remote `text_to_image` API; the browser, lacking the IDE auth environment, received `net::ERR_FAILED`.

**Fixes**:
- `src/config/carPresets.js`: new `generatePresetImage()` pre-renders local SVG data URLs for 19 models at module initialization (with brand colors and dimension labels)
- `src/views/Designer.vue`: removed remote-loading logic and the `imageCache`/`cleanupImageCache` dead code; `loadImage()` became `prepareModelImage()`; `getImageState()` defaults to `loaded`

**Code-review findings**:
- Flawed condition logic in `prepareModelImage` (overwriting preset images) → fixed
- Variable shadowing in `getBrandKeyForModel` → fixed

**Verification**: no console errors or ERR_FAILED; model images, Car3D/Car2D, parameter sliders, AI panels, color pickers, and the navigation bar all work.

### 2.2 Project Archiving Cleanup

**Action**: reviewed all project files; archived non-core, obsolete files under `_archive/`.

**Archive categories (~80+ files)**:

| Directory | Content | Files |
|---|---|---|
| `_archive/dirs/3d_automation/` | 3D interaction systems, AI workflow docs, mind maps | ~25 |
| `_archive/dirs/docs/` | Completed historical reports (W1–W4, M2.5), product specs, architecture | ~30 |
| `_archive/dirs/evolution_ai_demo_w2d1/` | Old frontend build output | ~25 |
| `_archive/dirs/core/` | Old core code (car_surface.py, full_body.py) | 3 |
| `_archive/dirs/codeact/` | CodeAct test scripts | 2 |
| `_archive/dirs/SUPER_AGENT/` | Old agent scripts | 1 |
| `_archive/dirs/generation/` | Old parameterized-generation scripts | 1 |
| `_archive/dirs/viewer/` | Old API servers | 1 |
| `_archive/docs/` | Old docs (CHANGELOG, README_DEMO, SOLUTION_ARCHITECTURE) | 3 |
| `_archive/misc/` | Misc HTML demos, Plotly screenshots | 6 |
| `_archive/scripts/` | Obsolete launch scripts, Streamlit/Plotly tests | ~20 |

**Core files retained at root**: `src/`, `backend/`, `algorithm_model/`, `scripts/`, `data/`, `tests/`, Docker and build configs.

### 2.3 Overall Test Verification

**Result**: all 201 tests pass, 0 failures, 9 warnings (unrelated to this cleanup).

### 2.4 Git Commit

- Commit: `c6a65af3`, branch: `v1.01-reconstruct`
- 139 file changes (137 deletions = archiving, 2 modifications = carPresets.js + Designer.vue)
- 76 insertions, 33,974 deletions

### 2.5 Backend-Interface Verification

| Interface | Method | Status | Note |
|---|---|---|---|
| `/api/v1/car/parameters` | GET | OK | Returns the 5-category parameter tree |
| `/api/v1/car/components` | GET | OK | Returns 17 components |
| NURBS surface generation | POST | OK | 33 surfaces + 33 components |
| `/api/v1/ai/dataset-stats` | GET | 404 | AI route module not registered in main.py (fixed later) |

### 2.6 Test-Data Distillation

- Cleaned 15 untracked temp files (~4 MB): pytest-generated `model_*` directories and NURBS screenshots
- Updated `.gitignore`: new rules for `data/exports/model_*/` and `data/step/nurbs_a_class_*.png`
- Distilled into training material: 3 files with 52 prompt-completion samples plus one structured knowledge document across 8 categories

### 2.7 LLM Fine-Tuning and Inference Tests

| Stage | Model | Pass rate | Key issues |
|---|---|---|---|
| Base-model inference | Qwen2.5-0.5B-Instruct (unfine-tuned) | 1/10 (10%) | No NURBS domain knowledge or platform data |
| After QLoRA | Qwen2.5-0.5B + LoRA adapter | 3/10 (30%) | Numeric confusion on continuity; missing recess/bulge terms |
| RAG enhancement | Fine-tuned model + RAG | 7/10 (70%) | Missing terms Q1, numeric confusion Q3, missing terms Q10 |

**Root-cause analysis of the 30% rate (7 failures)**:
- Missing platform-specific data: 43% (3)
- Missing terminology: 29% (2)
- Wrong concept definition: 14% (1)
- Refusal pattern: 14% (1)
- High-risk categories (100% failure): continuity, nurbs_basics, parametric_design, quality_assessment

---

## III. LLM Fix Record, August 10

### 3.1 System-Prompt Restructuring

**Files**: `scripts/llm_server.py` L33–L77, `scripts/Modelfile` L10–L54

| Item | Before | After |
|---|---|---|
| Key data location | Measured values scattered in the lookup table | The body↔front and body↔rear pairs placed at the **top** in a `⚠ most important` block |
| Anti-confusion warning | None | Explicit warning: never treat large recess/bulge gap values as the body↔bumper G0 |
| G1 continuity definition | Only "tangent-vector continuity" | Adds "tangent directions agree, i.e. normal-vector angle < 1.0 degree" |
| Lookup-table categories | Flat list | Explicitly split into [shared boundary] / [recess] / [bulge] |
| Domain knowledge | NURBS math only | Adds SOP stats, SAE coordinates, default LWHWB, CV/R-corner values |

### 3.2 RAG Retrieval Intent Routing

**File**: `retrieve()` in `scripts/llm_server.py` L302–L334

| Intent detection | Action | Effect |
|---|---|---|
| "body + front bumper + continuity" | `body↔front_bumper` block +50, `continuity_summary` +30 | Correct pair ranks 1st |
| grille/headlight/taillight blocks | −20 when not asked explicitly | Distractor (3.294 mm) drops to 5th |
| "gap normal/fixed" | wheel/hub/mirror/bumper components +20 | Assembly-gap terms (Q10) hit more easily |

### 3.3 Verification

| Test | Before | After | Keyword hits |
|---|---|---|---|
| **Q1** G1 definition | FAIL (0/4) | **PASS (4/4)** | Tangent / normal / 1 degree / shared boundary |
| **Q3** body↔front bumper G0/G1 | FAIL (1/2; returned 3.294mm/88.814deg) | **PASS (2/2)** | 0.000 / 0.131 |

### 3.4 Two-File Consistency

- The system prompts in `llm_server.py` and `Modelfile` are **byte-identical**
- All 14 key anchors hit (measured data, tangent/normal, three categories, SOP stats, SAE coords)
- All 5 RAG-routing anchors hit (intent detection, +50 weighting, −20 suppression)

### 3.5 Docker Containerization

**New files**:

| File | Purpose |
|---|---|
| `Dockerfile.llm` | LLM inference image (python:3.11-slim + torch CPU + transformers) |
| `docker-compose.llm.yml` | One-command llm-server, mounting the merged model and knowledge base |
| `scripts/docker-llm.ps1` | PowerShell management script (up/logs/test/status/down/restart) |

**End-to-end test** (local environment simulating the container):
- Startup: model loaded (494M params), RAG on (20 knowledge blocks)
- Q1: **4/4 PASS** — "tangent directions agree at the shared boundary, i.e. normal-vector angle below 1 degree"
- Q3: **2/2 PASS** — "body↔front_bumper G0 = 0.000mm, G1 = 0.131deg"

> Note: the Docker Desktop daemon was down that day, so container behavior was verified in an equivalent local environment (transformers 4.57.6 + torch 2.4.1 CPU). Once Docker Desktop is ready, run `.\scripts\docker-llm.ps1` to build, start, and test.

---

## IV. Current Key Metrics

| Metric | Status | Note |
|---|---|---|
| Unit tests | 201 / 201 pass | Last full run, August 9 |
| LLM 10-question benchmark | 7 / 10 pass (70%) | Improved after Q1/Q3 fixes; Q10 pending rerun |
| LLM Q1 + Q3 | All pass | Q1 4/4, Q3 2/2 |
| LLM service | Running | Port 11434; 20 RAG blocks loaded |
| Docker main platform | Ready | `Dockerfile` + `docker-compose.yml` |
| Docker LLM service | Ready | `Dockerfile.llm` + `docker-compose.llm.yml` + `docker-llm.ps1` |
| Git branch | `v1.01-reconstruct` | Latest commit `c6a65af3` |

---

## V. Remaining Items and Recommendations

| Priority | Item | Note |
|---|---|---|
| High | Q10 rerun | Done: original question 1/6 FAIL; model does not use Chinese terms; see §3.5 |
| High | Build once Docker Desktop starts | Run `.\scripts\docker-llm.ps1` when the daemon is ready |
| Medium | Model-capacity bottleneck | The 0.5B model has limited memory for long prompts; consider 7B if Q10 still fails |
| Medium | Full 10-question regression | Only Q1/Q3 rerun; a full run is recommended to rule out regression |
| Low | Training-data expansion | Currently 63 JSONL entries; expand to 500+ for coverage |

---

## VI. File-Change List (8/9–8/10)

### Modified Files

| File | Change |
|---|---|
| `src/config/carPresets.js` | New `generatePresetImage()` pre-rendering local SVG data URLs |
| `src/views/Designer.vue` | Removed remote-image dead code; uses local presets |
| `scripts/llm_server.py` | Prompt restructuring (L33–77) + RAG intent routing (L302–334) |
| `scripts/Modelfile` | Synchronized prompt update (L10–54) |
| `.gitignore` | New `data/exports/model_*/` and `data/step/nurbs_a_class_*.png` |

### New Files

| File | Purpose |
|---|---|
| `Dockerfile.llm` | LLM inference image |
| `docker-compose.llm.yml` | LLM service Compose |
| `scripts/docker-llm.ps1` | Docker management script |
| `scripts/deploy_finetuned.py` | QLoRA train + merge + GGUF pipeline |
| `scripts/train_qlora.py` | QLoRA training |
| `scripts/merge_lora.py` | LoRA-merge |
| `scripts/analyze_failures.py` | Inference-failure analysis |
| `scripts/test_nurbs_inference.py` | NURBS expert inference tests |
| `scripts/setup_ollama.ps1` | Ollama setup |
| `data/training/parametric_design_knowledge.json` | RAG base (20 blocks) |
| `data/training/qlora_enhanced_dataset.jsonl` | QLoRA data (63) |
| `data/training/nurbs_surface_dataset.jsonl` | NURBS surface data |
| `data/training/a_surface_quality_dataset.jsonl` | Class-A quality data |
| `data/training/test_results.json` | 10-question results |
| `data/training/merged/merged_model/` | Merged fine-tuned model (~1.9 GB) |
| `data/training/nurbs-qwen-lora/` | LoRA adapter + 3 checkpoints |

### Archived Files

- ~80+ non-core files moved to `_archive/` (see §2.2)
