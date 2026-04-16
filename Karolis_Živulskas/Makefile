.PHONY: help install dev-up dev-down migrate worker beat api test lint typecheck flower keywords-import keywords-list keywords-export

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies and Playwright browsers
	pip install -e ".[dev]"
	playwright install chromium

dev-up:  ## Start local dev stack via docker-compose
	docker-compose up -d
	@echo "Services:"
	@echo "  Postgres        → localhost:5432"
	@echo "  Redis           → localhost:6379"
	@echo "  Elasticsearch   → localhost:9200"
	@echo "  Grafana         → http://localhost:3000  (admin/repops)"
	@echo "  Prometheus      → http://localhost:9090"
	@echo "  Loki            → localhost:3100"
	@echo "  Flower          → http://localhost:5555"

dev-down:  ## Stop local dev stack
	docker-compose down

migrate:  ## Run Alembic DB migrations
	alembic upgrade head

migrate-new:  ## Create new Alembic migration (MSG= required)
	alembic revision --autogenerate -m "$(MSG)"

worker:  ## Start Celery worker (all queues)
	celery -A repops.workers.app worker --loglevel=info \
		-Q collection,analysis,reporting,default

beat:  ## Start Celery beat scheduler
	celery -A repops.workers.app beat --loglevel=info --scheduler celery.beat:PersistentScheduler

api:  ## Start FastAPI dev server with hot-reload
	uvicorn repops.api.main:app --reload --host 0.0.0.0 --port 8000

flower:  ## Start Celery Flower task monitor
	celery -A repops.workers.app flower --port=5555

test:  ## Run full test suite with coverage
	pytest --cov=repops --cov-report=term-missing --cov-report=html

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v

test-integration:  ## Run integration tests (requires docker-compose up)
	pytest tests/integration/ -v

lint:  ## Lint and auto-fix with ruff
	ruff check . --fix
	ruff format .

typecheck:  ## Run mypy type checker
	mypy repops/

ci: lint typecheck test  ## Full CI check (lint + types + tests)

keywords-import:  ## Load data/keywords/keywords.csv into the database
	python scripts/import_keywords.py

keywords-import-dry:  ## Preview what keywords-import would change (no DB writes)
	python scripts/import_keywords.py --dry-run

keywords-list:  ## Print all keywords currently in the database
	python scripts/import_keywords.py --list

keywords-export:  ## Export the database keyword list back to a CSV file
	python scripts/import_keywords.py --export data/keywords/keywords_export.csv
