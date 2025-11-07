POETRY ?= poetry

.PHONY: setup lint typecheck format test test-unit test-integration test-contract coverage load-test verify

setup:
	$(POETRY) install

lint:
	$(POETRY) run ruff check src tests

typecheck:
	$(POETRY) run mypy

format:
	$(POETRY) run black src tests
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

verify: lint typecheck test
