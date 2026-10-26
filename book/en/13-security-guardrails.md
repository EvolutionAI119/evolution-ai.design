# Chapter 13. Security Guardrails and Guest Mode

> Author: Quantum Swordsman
> Volume IV · Engineering: Converging Uncertainty into Delivery

## 1. The Question

An AI-native platform has a wider attack surface than a traditional web application. It adds three exposures that traditional systems do not have: the model proxy forwards requests to external LLMs, and a user-controllable URL is a ready-made SSRF channel; users entrust the platform with their API keys for various providers, and the storage format decides the loss when the database is dumped; and for demonstration and acquisition the platform wants anonymous visitors to experience full functionality—between "open" and "breached" there is a single switch. Security design here does not answer "whether to add locks" but three finer questions: what the default posture is, when a violation is discovered, and how openness is explicitly designed.

The proposition of this chapter is: **deny by default, admit explicitly, and fail fast in production**. Deny-by-default converges the attack surface into whitelists; explicit admission gives every opening a name that can be audited; fail-fast moves security violations from "run-time incident" to "start-up error"—better to refuse to boot than to go live with a weakness.

## 2. Principles

**First, deny by default; every admission is a whitelist.** A production CORS whitelist, a fixed provider registry and a strict CSP share one structure: assume the requester is hostile, then list the admitted names one by one. Outside the whitelist there is no "temporary pass".

**Second, fail fast in production; violations stop at start-up.** Security configuration is validated when the application boots, not when it is first attacked. A failed validation raises immediately and the process refuses to come up. A service that cannot start is an incident; a service running with a weak secret is a catastrophe.

**Third, layer the secrets; each has an independent blast radius.** The platform's own signing key, the provider keys entrusted by users, and the deployment-side tunnel credentials are three separate secrets: stored separately, rotated separately, and the compromise of one does not cascade.

**Fourth, openness is explicit design, not a permissions bug.** Guest mode—a site-wide pass—must be a product decision with guardrails: its boundary is written into code, into tests and into start-up validation, not left as a temporary change nobody remembers.

## 3. Anatomy of the Case

Start with where fail-fast lands. The settings model in `backend/app/config.py` carries a production validator: when `ENVIRONMENT=production`, `SECRET_KEY` must not equal the built-in development default and must be at least 32 characters; `DEBUG` must be false (with debug on, CORS degenerates to any origin and 500 responses expose stack traces); `GUEST_MODE` must be off. Any violation makes pydantic raise a `ValidationError` at start-up and the application refuses to go live. The deployment side agrees: `deploy/docker-compose.yml` uses `${SECRET_KEY:?...}` so that a missing secret fails the compose run directly—two gates, one outside and one inside.

Now the layering of secrets. JWTs are signed with PyJWT and passwords are stored hashed; user-entrusted provider API keys enter the `api_keys` table encrypted with Fernet, the encryption key derived from `SECRET_KEY` via SHA256—plaintext keys exist only briefly in the memory that forwards a request. Deployment credentials such as the cpolar authtoken live only in `.env` and are forbidden inside command payloads. The three layers contain one another nowhere, and the loss of any one does not automatically surrender the other two.

Guest mode is the specimen of explicit openness. With `GUEST_MODE` enabled during the account-archiving period, `get_current_user` in `security.py` resolves token-less requests to a built-in guest account (created lazily and idempotently), so the whole site is reachable by anonymous visitors. But this is not unbounded exposure: enabling it in production triggers the fail-fast above; administrative semantics still converge through dependency injection; and on the test side `backend/tests/conftest.py` forces `GUEST_MODE=false`, guaranteeing that 401/403 cases exercise the real authentication path. Two cases in `test_guest_mode.py` lock the boundary: guest admission works, and enabling it in production must fail.

<figure class="doc-figure"><img src="../docs/images/en/october-guest-arch.svg" alt="Guest-mode architecture: the GUEST_MODE switch resolves anonymous requests to a built-in guest account; enabling it in production fails fast; tests force it off"><figcaption><strong>Figure 13-1 ｜ Guest-mode architecture: full access plus production guardrails</strong> How to read: anonymous requests pass through the `GUEST_MODE` switch and the `security.py` bypass to land on the built-in guest account, making Designer, Projects, Quality and the /admin console reachable; the two guardrails on the right are hard constraints—enabling the mode in production is refused at start-up (validated at the same level as a weak SECRET_KEY), and the test suite forces it off via conftest so that authorisation-semantics cases are not silently bypassed by the guest identity.</figcaption></figure>

CSP shows how deny-by-default is refined to path granularity. The security-headers middleware in `main.py` uniformly injects X-Content-Type-Options, X-Frame-Options, CSP, Referrer-Policy, Permissions-Policy and Cache-Control, and strips `server: uvicorn`. The default CSP is strict, with `script-src 'self'`. The standalone admin console, however, depends on vue-i18n's runtime compilation and needs `unsafe-eval`. The platform's answer is not a site-wide relaxation but a path-selected policy: only the `/admin` document admits `unsafe-eval`, while the public API and the main site stay strict. `test_admin_console.py` turns that boundary into an assertion: `unsafe-eval` appears in, and only in, the admin document's CSP.

SSRF is solved by eliminating choice. `llm_proxy.py` hard-codes the official endpoints of seven providers in a registry; users select a provider but can never submit a URL. Request bodies are additionally fenced (50MB globally, 256KB per LLM request, 64 messages, 60,000 characters), and the prompt-injection signature scan records warnings by default. The proxy passes bytes through, but the destination is never decided by the requester.

<figure class="doc-figure"><img src="../docs/images/en/october-csp-scope.svg" alt="CSP scoping: the /admin document admits unsafe-eval for vue-i18n compilation while the public API and main site stay strict"><figcaption><strong>Figure 13-2 ｜ CSP scoping: unsafe-eval admitted for /admin only, strict everywhere else</strong> How to read: the left column is the strict default zone (`/api/v1/*` and the main site, `script-src 'self'`); the right column is the dedicated relaxation for the `/admin` document (only the Function constructor, for vue-i18n compilation); the SecurityHeadersMiddleware in the middle selects the policy by request path. The lower part records where this boundary came from: the admin console rendered a blank page on first test (EvalError); the fix introduced the scoped policy, and a regression test now locks the scope.</figcaption></figure>

**Cross-Domain Mapping.**

- Here = four authentication tiers (public, optional, required, admin) are enforced in one dependency-injection layer, defaulting to deny. In RAG = document permissions must be filtered before retrieval, not scrubbed out of the answer afterwards.
- Here = guest mode allows reads and blocks writes. In a general agent = tool allowlists are granted per session, and unauthorized tools report unavailability truthfully.

**Capability status.** The four auth tiers, guest mode, and default-deny posture are [Implemented · Test-Locked] (152 routed endpoints split 114 / 9 / 12 / 17); threat modeling and key rotation are engineering discipline [Design Principle].

## 4. Anti-Patterns and Their Costs

**Going live on a weak default secret.** SECRET_KEY keeps the development default, so JWT signing and user-key encryption fall together. The opposite of fail-fast is not "it boots" but "it runs naked in silence with a predictable secret".

**Guest mode reaching production.** A demo configuration is carried into deployment and every protected endpoint—including super-admin ones—opens to anonymous visitors. The cost is not merely being attacked: when it happens, no record can tell a visitor from an administrator.

**User-controllable URLs.** The model proxy accepts an endpoint field from the front end. This is textbook SSRF: internal addresses and cloud metadata endpoints are exposed at once. Eliminating the field beats any filtering regex.

**One-size-fits-all CSP.** Either the whole site gets `unsafe-eval` (no CSP in effect) or the whole site is strict (the console goes blank). The correct granularity is path scoping, locked by tests.

**Tests taking the guest bypass.** The test environment inherits `GUEST_MODE=true`, every 401/403 case is admitted, and authentication regression silently dies. One forced-off line in conftest is worth more than a hundred cases.

**Secrets inside command payloads.** Authtokens are written into start-up scripts and command lines. Process lists and shell history are leak surfaces; credentials belong in `.env` and environment variables only.

## 5. Operational Checklist

1. Before a production launch, validate three hard conditions: SECRET_KEY is non-default and at least 32 characters, DEBUG=false, GUEST_MODE=false (see the validator in `config.py`).
2. On the deployment side, use `${SECRET_KEY:?...}` so compose fails on a missing secret, forming a double gate with the application validator.
3. User API keys always enter the `api_keys` table Fernet-encrypted; plaintext never reaches the database or the logs.
4. For every new outbound call, ask "who decided the URL": it must come from a server-side registry; requesters never supply destinations.
5. CSP changes are allowed only as path-scoped relaxations, following the `/admin` pattern, with a regression assertion for each new scope.
6. Security headers are injected uniformly by middleware; ad-hoc per-route rewrites are forbidden.
7. Production CORS whitelists origins explicitly; the combination of ACAO `*` with credentials is forbidden.
8. The test environment forces guest mode and debug switches off in conftest; authorisation cases must take the real path.
9. Give every security boundary at least one test: guest admission, production fail-fast and CSP scoping each have theirs.
10. Credentials live only in `.env`; review scripts and documents before committing so that no secret enters command payloads or git history.

## 6. Self-Check

1. If the production SECRET_KEY were replaced by the development default, would your system refuse to start—or run silently until breached?
2. Does your "open experience" switch have all three locks: forbidden in production, administration still converged, and tests forced onto real authentication? Which one is missing?
3. If an attacker obtained every encrypted user API key in your system, what else would they still need? Is that "something else" exactly one secret?
