# Hooshpod RAG Chatbot – Runbook

This guide covers the two supported ways to run the Hooshpod RAG Chatbot backend: directly with PNPM (Node.js 18) and via Docker / Docker Compose.

---

## 1. Prerequisites

| Method | Requirements |
| --- | --- |
| PNPM | Node.js ≥ 18, [PNPM](https://pnpm.io/) ≥ 8 |
| Docker | Docker Engine + Docker Compose plugin |

Ensure MongoDB and Redis are available locally (or reachable) when using the PNPM path. The Docker Compose workflow provisions both services automatically.

Before running either method, copy .env.example to .env and adjust credentials / knowledge-base settings as needed:

`powershell
Copy-Item .env.example .env
# edit .env in your editor of choice
`

Key environment variables:

- MONGO_URI, REDIS_URL – connection strings for persistence.
- OPENROUTER_API_KEY, OPENROUTER_MODEL – OpenRouter credentials.
- KNOWLEDGE_FILE – path to the knowledge base (defaults to ./knowledge.txt).
- EMBEDDING_PROVIDER – xenova (default) or cohere.
- CACHE_SIMILARITY_THRESHOLD, CACHE_MAX_SIMILARITY_CANDIDATES – similarity caching controls.

---

## 2. Running with PNPM

### Install dependencies
`powershell
pnpm install
`

### Development mode (hot reload)
`powershell
pnpm dev
`

The server starts on http://localhost:3000 (configurable via PORT). On startup it will:

1. Connect to MongoDB / Redis.
2. Ingest and embed the knowledge base.
3. Expose the API routes (/chat, /history/:userId, /health).

Stop with Ctrl+C.

### Production build & start
`powershell
pnpm build
pnpm start
`

This compiles TypeScript to dist/ and runs the compiled ESM build with Node 18.

---

## 3. Running with Docker Compose

The repository includes a multi-stage Dockerfile and docker-compose.yml that orchestrate the API, MongoDB, and Redis.

### Build & launch
`powershell
docker compose up --build
`

Compose will:

- Build the application image (pi service) targeting Node.js 18.
- Start MongoDB (mongo service) and Redis (edis service) with persistent volumes.

Once all services are healthy, visit:

- http://localhost:3000/health – health probe ({ "status": "ok" }).
- http://localhost:3000/history/<userId> – history inspection.

Stop with Ctrl+C, or run in detached mode (docker compose up -d) and later shut down via docker compose down.

---

## 4. Smoke Test Checklist

1. curl http://localhost:3000/health
2. POST to /chat with a question:
   `powershell
   curl -X POST http://localhost:3000/chat 
     -H "Content-Type: application/json" 
     -d '{ "message": "What does the Hooshpod platform offer?", "userId": "user-123" }'
   `
3. Re-run the same question and confirm "cached": true.
4. Retrieve history for the user:
   `powershell
   curl "http://localhost:3000/history/user-123?limit=10"
   `

If all checks pass, the service is ready for use.

---

## 5. Testing & Troubleshooting

- **Automated tests:** pnpm test (Vitest) covers chunking, caching, and route validation.
- **OpenRouter errors (401/402/404/429):** confirm API key, model slug, and account quota.
- **Knowledge ingestion fails:** verify KNOWLEDGE_FILE path exists inside the container or workspace.
- **Redis cache misses:** similarity reuse requires embeddings; check logs (edis.* events) and ensure Redis is reachable.
- **Docker build warnings:** if pnpm warns about ignored build scripts, run pnpm approve-builds inside the build context if those scripts are required.

For deeper operational notes, consult the main [README](README.md).
