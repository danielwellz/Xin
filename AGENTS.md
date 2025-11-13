# Repository Guidelines

## Project Structure & Module Organization
- Place application code in `src/`, using a `chatbot/` package for core conversation flows and an `adapters/` subpackage for I/O or platform bindings.
- Group reusable prompt templates under `src/chatbot/prompts/` and shared utilities under `src/chatbot/utils/`.
- Keep tests in `tests/` mirroring the `src/` layout (`tests/unit/chatbot/test_core.py`, `tests/integration/test_cli.py`, etc.).
- Store sample conversations or assets in `examples/` and contributor docs in `docs/`.

## Build, Test, and Development Commands
- `poetry install` — create the virtualenv and install all runtime and dev dependencies.
- `poetry run pytest` — execute the complete automated test suite; add `-k name` for targeted runs.
- `poetry run python -m chatbot.cli --tenant-id <uuid> --brand-id <uuid> --channel-id <uuid>` — launch the local chatbot entry point for manual testing against a running orchestrator.
- `make format` — run `ruff format` plus `ruff check --fix` before opening a pull request.

## Coding Style & Naming Conventions
- Target Python 3.11; prefer `dataclass` structures for message payloads and keep functions under 50 lines.
- Follow `ruff`'s lint rules with 88-character lines; use `black`-compatible formatting (`ruff format`) for consistency.
- Adopt descriptive snake_case for functions and module names, PascalCase for public classes, and SCREAMING_SNAKE_CASE for constants.
- Document non-obvious workflows with module-level docstrings or README snippets co-located in each package.

## Testing Guidelines
- Write `pytest` tests alongside features; unit tests should mock external APIs while integration tests can hit local fakes.
- Name tests after the behavior under test (e.g., `test_generate_reply_handles_unknown_intent`).
- Enforce high coverage on dialogue policy modules; run `poetry run coverage run -m pytest` locally when touching decision logic.

## Commit & Pull Request Guidelines
- Use Conventional Commit prefixes (`feat:`, `fix:`, `refactor:`, etc.) to keep history searchable.
- Reference related issues in the body (`Closes #42`) and summarize observable behavior changes.
- PRs must include: concise summary, testing evidence (`pytest`, lint results), and updated docs or examples when user-visible behavior changes.

## Security & Configuration Tips
- Keep API keys and secrets out of source control; load them via `.env` files consumed by `python-dotenv`.
- Validate incoming payloads with `pydantic` models and log sanitized request fragments only.
- Store uploaded knowledge assets exclusively through the configured object storage credentials (`STORAGE_*` settings).

## Prompt Library
Reference these prompts before starting any major milestone so every contributor triggers the right scripted workflow.

### Backend & Frontend Delivery
The original five backend/frontend prompts have been executed and archived after Phase 3. Use the integrated delivery plan for any future cross-stream coordination: `docs/delivery/integrated_plan.md`.

### Hardening & Launch
| Prompt | Triggering Condition | Link |
| --- | --- | --- |
| Production Infra & Observability | Execute at the outset of Phase 4 hardening (TLS, systemd, monitoring). | [docs/MASTER_PROMPTS_HARDENING.md](docs/MASTER_PROMPTS_HARDENING.md#prompt-1--production-infrastructure--observability-hardening) |
| Security Assurance & Compliance | Start once infra prompt is underway and before GA security reviews. | [docs/MASTER_PROMPTS_HARDENING.md](docs/MASTER_PROMPTS_HARDENING.md#prompt-2--security-assurance--compliance-review) |
| Load, Chaos & Resilience Validation | Launch prior to scale testing or SLO sign-off; rerun before major releases. | [docs/MASTER_PROMPTS_HARDENING.md](docs/MASTER_PROMPTS_HARDENING.md#prompt-3--load-chaos-and-resilience-validation) |
| QA, Data Integrity & Release Verification | Kick off when regression/verification window begins for a release candidate. | [docs/MASTER_PROMPTS_HARDENING.md](docs/MASTER_PROMPTS_HARDENING.md#prompt-4--qa-data-integrity-and-release-verification) |
| Launch Readiness & Post-Launch Guardrails | Use during final go/no-go prep and post-launch war-room planning. | [docs/MASTER_PROMPTS_HARDENING.md](docs/MASTER_PROMPTS_HARDENING.md#prompt-5--launch-readiness-rollback-and-post-launch-guardrails) |
