# Chapter 9. The Deep Learning / LLM Fusion Layer

> Author: Quantum Swordsman
> Volume III · Intelligence: Putting Models into the System

## 1. The Problem: Many Models, One System

By the middle of an AI platform's life, the model list is usually longer than the feature list: a classification network, a vision-language model, seven or eight commercial LLMs, a local expert model. Each model runs on its own, yet together they often form an integration disaster — keys scattered through frontend code, upstream URLs supplied by clients at will, and an interface that still reports "AI generated successfully" when some dependency was never installed. The more models, the more the system resembles a collage of demos rather than a deliverable product.

EVOLUTION AI's fusion layer faces four heterogeneous capabilities: a PyTorch car-type network, CLIP semantic scoring, seven commercial LLM providers, and a local NURBS expert chat. The proposition of this chapter is: **one unified proxy, a fixed registry, SSRF safety, and honest degradation whenever something is missing.** Fusion does not mean wiring up every model; it means giving every capability the same boundary, the same honesty, and the same observability.

## 2. Principles

### Principle 1. Heterogeneous capabilities, isomorphic boundaries

Whether the backing is a neural network on a GPU or an API a thousand miles away, the shape presented to the rest of the system must be identical: an explicit capability endpoint, unified authentication and key resolution, consistent error semantics, and pollable task state. The frontend never needs to know whether a capability is local or remote — availability is a runtime property reported by health checks and capability endpoints, not an assumption hard-coded into the interface.

### Principle 2. The registry is fixed on the server side

The LLM proxy's provider registry is a server-side constant: seven providers — Baidu ERNIE, Alibaba Qwen, Tencent Hunyuan, ByteDance Doubao, DeepSeek, Moonshot Kimi, and SiliconFlow — each with a verified base URL, a default model, declared capabilities (chat / embeddings / images), and a documentation link. Because upstream URLs are not client-supplied parameters, no caller can redirect the server toward an arbitrary internal address. The SSRF attack surface is eliminated structurally, not filtered layer by layer.

### Principle 3. Keys resolve explicitly; absence is an error

Credentials resolve first from environment variables, otherwise from the per-user encrypted store — user API keys are persisted with Fernet symmetric encryption. When a key is missing, the system returns a clear 4xx and never falls back silently to a fake model. Request and response bodies pass through verbatim, upstream status codes propagate as-is, and a capability the registry does not declare returns 501. Honesty is not a UX refinement; it is a security property. A forged success is far more dangerous than an explicit failure.

### Principle 4. Claims must align with executable code

The platform deliberately does not ship a QLoRA-style fine-tuning job runner, and its documents name that as future work. The capability list contains only what is implemented; planned capabilities stay out of the functional definition. This discipline constrains the team itself: every sentence the system says must be cashable against the source tree.

<figure class="doc-figure"><img src="../docs/images/en/whitepaper-arch.svg" alt="Platform four-layer architecture with deployment channel"><figcaption><strong>Figure 9-1 | Where the fusion layer lives: heterogeneous capabilities under a thin web shell</strong> How to read: four layers top-down — frontend, backend, algorithm, data — with call protocols annotated between layers, and a deployment channel on the right covering development, production, public tunnel, and static publishing. DL and LLM capabilities all converge inside the thin backend shell and the standalone algorithm layer: the web tier only orchestrates, models can be replaced, and contracts stay stable.</figcaption></figure>

## 3. Case Study: Four Capability Lines, One Discipline

**The PyTorch car-type network.** A compact MLP maps the 14-dimensional normalized styling vector to car-type classes (48 hidden units, six classes in the shipped configuration). Training runs in a background daemon thread, so the HTTP API returns a task object immediately; the client polls status, progress, and logs, and may cancel. Tasks persist in the `training_tasks` table. The training dataset is synthetic but deterministic: centroids come from real preset centers, per-parameter noise scales control sampling, explicit style and brand transforms perturb designated dimensions, and a seeded generator keeps runs and tests reproducible. When PyTorch is absent, the capability endpoint reports that fact and training requests fail cleanly — instead of returning fabricated metrics.

**CLIP six-axis semantics.** The semantics module wraps `openai/clip-vit-base-patch32` (lazy-loaded, about 605 MB, offline once the weights are cached) and defines six style axes, each paired with a Chinese label and a concrete English visual prompt — a deliberate prompt-engineering choice, because CLIP responds far better to concrete visual descriptions than to abstract adjectives. An image is encoded once and compared against precomputed text embeddings, yielding a [0,1] score per axis. When the weights are missing, the system falls back to geometric features and labels the response "geometric features only," never hiding the downgrade.

**A unified proxy for seven LLM providers.** Chat completions, embeddings, and image generation are uniformly exposed under `/llm/{provider}/...` with optional authentication. A fixed registry, encrypted keys, transparent status propagation, and honest capability declarations — all four principles above are cashed into code here.

**A local NURBS expert chat.** Behind `/ai/chat` sits a local Ollama runtime with NURBS and Class-A domain context. A designer can ask "why does this edge fail G1" without sending design data to any third party; a health endpoint reports whether the local runtime is available. Data never leaving the intranet is the entire reason this path exists.

<figure class="doc-figure"><img src="../docs/images/en/audit2-chart.svg" alt="LLM benchmark: three-stage improvement and failure roots"><figcaption><strong>Figure 9-2 | The LLM ten-question benchmark: 1/10 → 3/10 → 7/10, with failure roots</strong> How to read: the left panel measures the same ten questions three times; the right panel attributes the seven failures at the 30-percent stage, with the top two causes accounting for 72 percent — evidence that the bottleneck was data gaps, not model capacity. A benchmark matters not because the score looks good, but because every jump can say what was fixed and what remains.</figcaption></figure>

**Cross-Domain Mapping.**

- Here = missing capabilities degrade honestly (HTTP 503 without torch, semantic scoring declared unavailable without CLIP) and the caller labels it. In RAG = when retrieval finds no support, the answer is "I don't know" rather than a fluent invention.
- Here = the LLM is an optional add-on; with it switched off, parametric modeling and export still work. In a general agent = the orchestration skeleton outlives any single model vendor, and swapping models does not change the tool contract.

**Capability status.** The pure-NumPy geometry and Bayesian kernels are [Implemented · Test-Locked]; the deep-learning and LLM side is an optional add-on [Partially Implemented]—training returns 503 without torch, and semantic scoring declares itself unavailable without a downloaded CLIP model.

## 4. Anti-Patterns and Their Costs

**Anti-pattern 1: Client-supplied upstream addresses.** Letting callers pass a base URL or arbitrary proxy target. The cost is an open SSRF gate, with the server reduced to an intranet scanner.

**Anti-pattern 2: Keys in the frontend or in logs.** API keys written into frontend storage, URL parameters, or request logs. The cost is a credential-leak surface spanning every browser and every log line.

**Anti-pattern 3: Silent fallback to a fake model.** When a key is missing or an upstream times out, returning template text that impersonates model output. The cost is a decision chain contaminated by fabrication — and once discovered, every genuine output loses trust along with it.

**Anti-pattern 4: Slide-deck capabilities first.** Filling the feature list with planned capabilities that do not exist in code. The cost is acceptance without evidence, and credit repeatedly overdrawn between demo and delivery.

## 5. Operational Checklist

1. When onboarding a model, register it first on the server side: base URL, default model, declared capabilities, documentation link (following `llm_proxy.py`).
2. Take upstream addresses only from registry constants; never accept any URL from a client.
3. Fix the key-resolution order: environment variables, then per-user encrypted storage (Fernet); if both are empty, return 4xx.
4. Give every capability a health or capability endpoint; the frontend renders availability from these, never from hard-coded assumptions.
5. On missing dependencies, fail explicitly or degrade with a label (PyTorch → training fails; CLIP → geometric fallback with annotation).
6. Run every long task as a background thread backed by a persistent task table; return a task object immediately, with polling and cancellation.
7. Seed the training-data generator so runs and tests are reproducible.
8. Audit the capability list against the source tree item by item; anything unimplemented appears only under future work.

## 6. Chapter Self-Check

1. If one LLM provider goes down tomorrow, at which layer and with which status code does your system tell the user? Will the user see "failure" — or "success but blank"?
2. Can you draw your key-resolution order, from environment variable to encrypted store, on one diagram? If not, it was never designed — it merely happened.
3. Is there anything in your feature list that the source tree cannot cash? If so, move it to future work — today.
