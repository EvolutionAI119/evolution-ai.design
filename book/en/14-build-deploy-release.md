# Chapter 14. Build, Deploy and Release

> Author: Quantum Swordsman
> Volume IV · Engineering: Converging Uncertainty into Delivery

## 1. The Question

Releasing an AI-native platform is far more than "package and upload". The algorithm layer carries a Cython extension that must be compiled; the front end drags along a heavy 3D library like Three.js; the back end must pass secret validation before it boots; and the knowledge-base documents have to ship with the site. Two engineering questions follow. First, why does the build output look the way it does? When `dist/` contains nine chunks, each chunk should exist for a reason, not as the bundler's improvisation. Second, can the deployment topology be reproduced on a fresh machine? If going live depends on seven manual steps in one engineer's memory, every release is an unauditable performance.

The proposition of this chapter is: **build output that can be explained, deployment topology that can be reproduced**. Explainable means the output structure corresponds one-to-one with declared intent; reproducible means the topology lives entirely in declarative files, comes up with one command, is gated by health checks, and receives its secrets only from the environment.

## 2. Principles

**First, the output is the documentation.** Every rule in the build configuration is a recorded decision: why this large library is cached whole, why that small one gets its own chunk. Reading the configuration should reconstruct the intent; reading the output should verify it.

**Second, the topology is declarative and start-up is a single command.** How many services exist, who depends on whom, and which volume holds the data are all declared in compose files. The first deployment and the hundredth run the same command and produce the same result.

**Third, secrets are separated from artefacts.** Images and static bundles never carry secrets; secrets are injected by the environment at run time, and a missing secret fails fast. What may be public is thoroughly public; what must stay secret never enters a build.

**Fourth, minimise the published surface.** The public site carries only public functions; no admin code enters the public bundle—routes, menus and chunks are all removed, and the console is hosted separately by the back end.

## 3. Anatomy of the Case

Start with the build side. The `manualChunks` function in `vite.config.js` is a decision list with comments: `@element-plus/icons-vue` is matched before `element-plus`—because the latter's id contains the former's substring, and with the wrong order the icon library would be merged into the wrong chunk. Three.js splits into a `three` core and a `three-examples` add-on chunk, cached separately; `vue`, `markdown-it` and `axios` each stand alone. The comments also record the counter-decision: "large libraries are deliberately cached whole rather than split without limit—over-splitting multiplies the request count and destroys library-level cache benefits", which is why `chunkSizeWarningLimit` is raised to 1000kB to silence meaningless size warnings. Two further release-side decisions: `base: './'` uses relative paths to keep the bundle portable, and `sourcemap: false` limits the information exposed in public artefacts. The `docsPlugin` copies the Markdown, PDF, HTML and SVG files under `docs/` into `dist/docs/` at build time, so the knowledge base ships with the site at the same version as the code—documentation-as-product in its delivery form.

<figure class="doc-figure"><img src="../docs/images/en/october-deployment.svg" alt="Production deployment topology: the browser talks to one same-origin Nginx entry; / serves the dist static site, /api and /admin proxy to the FastAPI back end, data lands in PostgreSQL and Redis, hosted on a compliant mainland cloud host"><figcaption><strong>Figure 14-1 ｜ Production deployment topology: same-origin reverse proxy with mainland compliance</strong> How to read: the browser speaks to a single Nginx entry—`/` is served from the dist static site, while `/api` and `/admin` are proxied to the FastAPI back end, with data in PostgreSQL and Redis. The lower left shows GitHub Pages hosting the public static site (zero admin code); the lower right states the hosting constraints: a 2C4G cloud host with swap, a four-service Docker stack, an in-country domain with ICP filing, a mainland server requirement for WeChat scan login, and no cross-border data transfer. Every line in the topology corresponds to a line in the compose and nginx configurations.</figcaption></figure>

On the deployment side the repository keeps two complementary topologies. The root `Dockerfile` is the all-in-one form: a multi-stage build compiles the Cython extension of the NURBS kernel in the builder stage; the run stage executes as a non-root user (uid 1000), declares the `/app/data` and `/app/logs` volumes, and health-checks `/health`. The root `docker-compose.yml` orchestrates it into a four-service stack—backend, PostgreSQL 16, Redis 7 (with `requirepass` enforced) and nginx; the database exposes no 5432 to the outside by default, and start-up order converges through `depends_on: service_healthy`. The `deploy/` directory holds the split form: `backend.Dockerfile` (python:3.11-slim, a non-root appuser, the `start.py` entry, health-checking `/api/v1/health`) and `frontend.Dockerfile` (`npm ci` then `vite build` on node:20-alpine, artefacts handed to nginx:1.27-alpine) build separately; `deploy/docker-compose.yml` exposes only port 80 to the outside, declares `SECRET_KEY` as required via `${SECRET_KEY:?...}`, and keeps Redis as an optional, commented-out service.

The last mile of the traffic entry is pinned down by the nginx configuration. `deploy/nginx.conf` turns off `server_tokens`, aligns `client_max_body_size 64m` with the back end's 50MB upload limit, and enables gzip for JSON and static assets. `default.conf.template` writes the routing as five blocks: `/api/v1`, `/docs` and `/openapi.json` proxy to the back end while forwarding `X-Request-ID` and the real IP (echoing the audit chain of Chapter 12); `/admin` proxies separately to the back-end-hosted console; hashed `/assets/` and images are cached for a year; unknown paths fall back to `index.html` for the SPA; and dotfiles (`.env`, `.git`) are denied outright. The minimised published surface shows in the division of labour: the gh-pages static site contains no admin code at all, and the admin console is hosted independently by the back end's StaticFiles under `/admin/`, with the login gate enforced server-side.

The first-deployment command chain is therefore short: `npm run build` produces `dist/`; `docker compose up -d --build` raises the whole stack; a fresh database takes one `alembic upgrade head`; and legacy SQLite data, if needed, is migrated once by `backend/scripts/migrate_sqlite_to_pg.py`. Local development is another declared topology—Vite on 5173, FastAPI on 8000 and a cpolar tunnel on 4040—while the LLM inference service is orchestrated separately in `docker-compose.llm.yml`, never holding the main stack hostage.

**Cross-Domain Mapping.**

- Here = frontend bundle, backend image, and algorithm package are version-locked together, and rollback is atomic. In an LLM application = model version, prompt version, and evaluation baseline must ship together, or a rollback cannot reproduce the outputs of that moment.
- Here = build chunking is decoupled from deployment topology; development and production differ only in one access layer. In an agent platform = the capability list ships with the version and is externally checkable, so "the docs say it exists" never outruns production.

**Capability status.** Build chunking, images, and deployment topology are [Implemented · Test-Locked]; canary release and automated rollback are roadmap items [Partially Implemented].

## 4. Anti-Patterns and Their Costs

**Splitting chunks without limit.** Worshipping "smaller is better" and giving every dependency its own file multiplies the request count, destroys library-level caching, and makes the first screen slower. Size-warning-driven splitting is vanity engineering.

**Baking secrets into images.** Writing SECRET_KEY into a Dockerfile or static configuration leaks it the moment the image is pushed, and rotation then requires rebuilding the artefact. Secrets belong to run time, not build time.

**Exposing the database to the public network.** Mapping 5432 to all host interfaces "for debugging". The commented-out port mapping in compose is a design: open it temporarily when needed and close it after—never leave it open by default.

**Shipping admin code in the public site.** Admin routes, menus and chunks distributed with the public bundle. An attacker does not need to guess the console address; they can download the source and study it at leisure. Every extra measure of published surface thins the defence.

**Orchestration without health checks.** Treating a dependency container's "started" as "ready" sends traffic to a process still initialising. `depends_on` with `service_healthy` is not ceremony; it is the only defence against start-up ordering faults.

**Documents drifting from artefacts.** The site goes live while the knowledge base stays a version behind. Documents must enter `dist/` with the build, shipping and rolling back together with the code.

## 5. Operational Checklist

1. Build with `npm run build`; when changing `manualChunks`, update the decision rationale in the comments at the same time.
2. Audit the chunk list in `dist/`: every large file needs a stated owner and reason—merge or delete what cannot be explained.
3. First deployment: `docker compose up -d --build`, then `docker compose exec backend bash -c "cd /app/backend && alembic upgrade head"`.
4. Generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(48))"`; they go only into `.env`, never into a Dockerfile or a command payload.
5. After start-up, verify health checks—the back end's `/api/v1/health` and the nginx probes—before opening traffic.
6. nginx exposes only 80/443; database and Redis ports are unmapped by default, and temporary debugging binds `127.0.0.1` only.
7. Align upload limits at both ends: `client_max_body_size` and the back end's `MAX_FILE_SIZE` share one definition.
8. Before publishing the public bundle, verify zero admin code: no `/admin` route, no admin chunk, no console entry.
9. Put the data volumes (`pg-data`, `evoai-data`) under a backup plan; containers are disposable, volumes are not.
10. Rehearse rollback together with release: roll the static site back by image tag, and keep database changes on reversible migrations.

## 6. Self-Check

1. Open your build output: can the reason for every chunk be found in the configuration comments? Are the unexplained ones intent or accident?
2. Given a fresh machine, a repository and one `.env`, can a single command reproduce the whole topology? Which manual steps remain undeclared?
3. Does your public artefact contain code or secrets that should not be there? What check proves "it does not", instead of believing "it does not"?
