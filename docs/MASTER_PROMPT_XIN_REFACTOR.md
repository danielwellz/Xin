You are an expert software architect and senior full-stack engineer.

You are working on a project called **Xin ChatBot** – a multi-tenant, multi-channel AI customer messaging platform.

## High-level product goals

Xin ChatBot should:

1. Let businesses (tenants) connect multiple messaging channels:
   - Instagram DMs
   - WhatsApp Business
   - Telegram bot
   - Web chat widget / web inbox

2. Let each tenant upload / configure **knowledge docs and brand info**:
   - FAQs
   - Product info
   - Brand tone / style
   - Any other knowledge sources that exist in this codebase

3. Use AI to answer end-user messages on all these channels:
   - Use the tenant’s **own knowledge docs + brand info** as the main source of truth
   - Maintain brand tone
   - Avoid leaking data between tenants (strict multi-tenancy)

4. Expose a **web UI at `xinbot.ir`** where:
   - New tenants can sign up / be created
   - Tenants can configure channels (IG / WhatsApp / Telegram / Web)
   - Tenants can upload and manage knowledge data
   - Tenants can see conversations / logs
   - All existing UX flows and features in this repo must be preserved or improved – nothing should disappear.

## Infra & environment goals

The production environment:

- VPS IP: `87.107.105.19`
- OS: **Debian 12 (Bookworm)**, freshly installed
- Reverse proxy: Nginx
- Containerization: Docker + docker compose
- CDN / DNS: **ArvanCloud**, with A records for `@` and `www` already pointing to the VPS
- Domain: `xinbot.ir` (and `www.xinbot.ir` if used)

I want **three clean environments**:

1. Local development:
   - Easy `docker compose` or `npm/yarn` commands
   - Hot reload where appropriate
   - Uses `.env.local` (or equivalent) and local DB

2. Local production-like build:
   - Ability to run the full stack locally as close to production as possible
   - Uses `.env.dev` or `.env.docker` (or similar) with an isolated DB

3. VPS / Production (`xinbot.ir`):
   - Docker Compose based deploy
   - Nginx reverse proxy in front of the app
   - TLS (Let’s Encrypt or similar) compatible
   - Clean, reproducible deployment described in a **Deploybook** markdown file

## Your tasks

You now have access to the **entire Xin ChatBot codebase** in this workspace. Your job is to:

1. **Understand the current system**
   - Fully scan the repository.
   - Identify:
     - Language(s) and frameworks (backend, frontend, workers, etc.)
     - How channels are currently integrated (Instagram, WhatsApp, Telegram, Web)
     - How multi-tenancy is implemented (tenant identification, DB isolation, etc.)
     - How knowledge docs / brand info are stored and used
     - How AI / LLM calls are wired in (prompting, context building, etc.)
     - How environment variables and configs are currently organized
     - How the current deployment is set up (docker, nginx, scripts, etc.)

   - Summarize the current architecture in a structured way before changing anything:
     - Components / services
     - Data flow (from user message → AI answer → channel reply)
     - Persistence (DB schemas, queues, caches)
     - Integration points (webhooks, third-party APIs, provider SDKs)

2. **Design an improved architecture**
   Without removing any existing features or integrations:

   - Propose a **clean, scalable architecture** suited to the existing stack.
     Examples of concerns you should address:
     - Clear separation between:
       - Frontend UI (tenant management, knowledge management, dashboards)
       - Backend API / webhooks / auth
       - Background workers / schedulers (if present)
     - Multi-tenant safety and clarity (no tenant data mixing)
     - Channel integrations:
       - Instagram / WhatsApp / Telegram webhooks and callbacks
       - Web chat endpoints / websocket (if any)
     - Knowledge retrieval and AI orchestration:
       - How knowledge docs are ingested, stored, and retrieved
       - How prompts are built per tenant
     - Configuration and secrets:
       - Environment variable strategy
       - Secret vs non-secret config
     - Logging, error handling, and observability, within reason for this project

   - Your design should:
     - Preserve existing business logic and features
     - Be implementable within this repo (no fantasy services)
     - Be compatible with Docker + Nginx on Debian 12
     - Make local dev and production deployment straightforward

   First, describe this target architecture (modules, directories, services) clearly, then refactor towards it.

3. **Refactor and rewrite for best architecture & design**
   - Implement the proposed architecture **directly in this codebase**.
   - You are allowed to:
     - Move files, split modules, rename things for clarity
     - Extract shared libraries / utilities
     - Introduce reasonable layers (e.g., application / domain / infrastructure) appropriate to the tech stack
     - Improve typing, error handling, configuration, and testability

   - You are **not allowed** to:
     - Remove existing features or break existing integrations
     - Remove meaningful configuration options
     - Hard-code secrets

   - Where you replace or significantly change something, preserve behavior and clarify the change with:
     - Comments where needed
     - Refined function and variable names
     - Clear directory structure

   - If there are obvious bugs, race conditions, or security issues in the current code, you should fix them as part of the refactor while keeping behavior equivalent from a product standpoint.

4. **Environment & configuration cleanup**
   - Introduce a clear, consistent environment configuration strategy. For example (adapt this to the tech stack and existing conventions):

     - `.env.local` for local dev
     - `.env.development` or `.env.docker` for local dockerized runs
     - `.env.production` or env vars for the VPS

   - Document:
     - All required env vars
     - Which ones are needed for:
       - Instagram / WhatsApp / Telegram integrations
       - Web/Frontend
       - DB / Redis / queues
       - AI provider(s) (OpenAI, etc.)

   - Ensure configuration can be injected cleanly through Docker Compose and is not hard-wired.

5. **Docker & Nginx production setup (Debian 12 + ArvanCloud + xinbot.ir)**

   Create/update a **production-ready Docker Compose setup** that:

   - Runs the full stack:
     - API backend
     - Frontend/UI (served either as a separate service or static build)
     - Database (if managed locally in Docker)
     - Any worker / scheduler services
   - Uses **named volumes** for persistent data (DB, etc.)
   - Exposes only the necessary ports internally, with Nginx as the external entrypoint.

   Create/update an **Nginx config** suitable for `/etc/nginx/sites-available/xin.conf`, such that:

   - `http://xinbot.ir` → proxies to the frontend (or backend that serves the frontend)
   - `https://xinbot.ir` works once Let’s Encrypt is added
   - Webhooks / APIs are correctly routed to the backend service(s)
   - It plays nicely with ArvanCloud’s CDN sitting in front (no weird caching of webhooks; proper headers)

   This should be written in a way that assumes:
   - VPS: Debian 12
   - Docker and docker compose installed
   - Nginx installed via apt
   - DNS (A records for `@` and `www`) already pointing to `87.107.105.19` via ArvanCloud

6. **Create a Deploybook (step-by-step deployment guide)**

   Create a markdown file at the root of the repo, e.g. `DEPLOYMENT.md` or `deploybook.md`, that explains **exactly** how to deploy the refactored Xin ChatBot to the new Debian 12 VPS.

   This deploybook should include:

   1. **Server bootstrap (Debian 12)**
      - Create and configure main user (e.g. `xin`)
      - Add SSH key
      - Basic security (ufw, SSH config basics)
      - Install Docker + docker compose
      - Install Nginx
      - Any other necessary packages

   2. **Cloning and configuring Xin ChatBot**
      - Directory structure (e.g. `/opt/xin-chatbot/src`, `/opt/xin-chatbot/config`, `/opt/xin-chatbot/volumes`)
      - How to clone the repo and checkout the correct branch
      - How to create the production `.env` file(s) and what variables are required

   3. **Docker Compose usage**
      - Commands to build and start the stack
      - How to run DB migrations / seeds
      - How to check logs

   4. **Nginx + HTTPS**
      - How to place the provided Nginx config into `/etc/nginx/sites-available/xin.conf`
      - How to symlink it into `sites-enabled`
      - How to test the config
      - How to obtain and renew TLS certificates (e.g., using Certbot with Nginx)

   5. **ArvanCloud / CDN notes**
      - Any special headers or configuration considerations for working behind ArvanCloud
      - Caching considerations (especially for dynamic/chat and webhooks)

   6. **Redeploy procedure**
      - How to pull new code
      - How to rebuild and restart services with minimal downtime
      - Any migration steps to keep in mind

7. **Documentation and clarity**

   - Besides `DEPLOYMENT.md` / `deploybook.md`, ensure there is a short high-level `README` update or architecture note that:
     - Describes the main components
     - Shows how to run the project locally (non-Docker and/or Docker)
     - Explains where in the codebase:
       - Tenants are managed
       - Channels are integrated
       - Knowledge docs / brand info live
       - AI orchestrations and prompts are built

8. **General quality expectations**

   - Write clean, idiomatic code consistent with the language and frameworks already used.
   - Prefer clarity over cleverness.
   - Add or fix typing where appropriate.
   - Keep functions and modules focused and cohesive.
   - Avoid introducing large new dependencies unless really justified by the codebase.

## Output style

Work directly on the repository as if you were making a large but careful refactor.

When you describe changes or plans (in comments or markdown files), be explicit and concrete. When you introduce new folders or files, name them in a way that is self-explanatory.

Again: **do not remove any existing features or integrations**. Only improve architecture, design, maintainability, and deployment.

Begin by scanning and summarizing the current architecture, then design the target architecture, then refactor toward it, and finally create the deploybook and documentation.
