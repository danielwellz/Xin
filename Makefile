POETRY ?= poetry
PNPM ?= pnpm
FRONTEND_DIR := services/frontend
WIDGET_DIR := services/widget

.PHONY: setup lint typecheck format test test-unit test-integration test-contract coverage load-test verify ci frontend-ci widget-ci prompt-check demo deploy-dev deploy-k8s backup restore-backup

setup:
	$(POETRY) install

lint:
	$(POETRY) run ruff check src tests

typecheck:
	$(POETRY) run mypy

format:
	$(POETRY) run ruff format src tests
	$(POETRY) run ruff check src tests --fix

test:
	$(POETRY) run pytest

test-unit:
	$(POETRY) run pytest -m unit

test-integration:
	$(POETRY) run pytest -m integration

test-contract:
	$(POETRY) run pytest -m contract

coverage:
	$(POETRY) run coverage run -m pytest
	$(POETRY) run coverage report --fail-under=85

load-test:
	$(POETRY) run locust -f tests/load/locustfile.py --headless --users 100 --spawn-rate 20 --run-time 5m

verify: lint typecheck coverage

frontend-ci:
	$(PNPM) --prefix $(FRONTEND_DIR) install
	$(PNPM) --prefix $(FRONTEND_DIR) lint
	$(PNPM) --prefix $(FRONTEND_DIR) test
	$(PNPM) --prefix $(FRONTEND_DIR) e2e -- --headless

widget-ci:
	$(PNPM) --prefix $(WIDGET_DIR) install
	$(PNPM) --prefix $(WIDGET_DIR) test
	$(PNPM) --prefix $(WIDGET_DIR) build

prompt-check:
	$(POETRY) run python scripts/verify_prompts.py

ci: lint typecheck coverage test-contract prompt-check frontend-ci widget-ci

ifndef ADMIN_TOKEN
$(error ADMIN_TOKEN environment variable must be set to a platform_admin JWT)
endif

demo:
	docker compose up -d postgres redis qdrant minio orchestrator channel_gateway ingestion_worker
	$(POETRY) run python scripts/demo_onboarding.py --api-token $(ADMIN_TOKEN) --base-url $${DEMO_BASE_URL:-http://localhost:8000}

deploy-dev:
	bash scripts/deploy/deploy_dev.sh

deploy-k8s:
	kubectl apply -k deploy/overlays/prod

backup:
	./scripts/backups/create_backup.sh

ifndef RESTORE_TIMESTAMP
restore-backup:
	$(error RESTORE_TIMESTAMP must be provided (e.g. make restore-backup RESTORE_TIMESTAMP=20240110T120000Z))
else
restore-backup:
	$(POETRY) run python scripts/restore_from_backup.sh --timestamp $(RESTORE_TIMESTAMP)
endif
