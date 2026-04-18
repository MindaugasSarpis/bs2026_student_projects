.PHONY: help up down build logs ps clean migrate migrate-new \
        api worker beat lint typecheck \
        keywords-import keywords-import-dry keywords-list keywords-export

DC = docker compose

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------------

up: build  ## Build image, start all services, run migrations
	$(DC) up -d
	@echo "Waiting for database to be ready..."
	@sleep 5
	$(DC) exec api alembic upgrade head
	@echo ""
	@echo "  Admin UI  → http://localhost:8000/admin"
	@echo "  API docs  → http://localhost:8000/docs"
	@echo "  Grafana   → http://localhost:3000  (admin / repops)"
	@echo "  Flower    → http://localhost:5555"

down:  ## Stop all services
	$(DC) down

build:  ## Build the repops Docker image
	$(DC) build

logs:  ## Tail logs from all services
	$(DC) logs -f

ps:  ## Show running container status
	$(DC) ps

clean:  ## Stop all services and delete all volumes (destructive)
	$(DC) down -v --remove-orphans

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

migrate:  ## Apply all pending Alembic migrations
	$(DC) exec api alembic upgrade head

migrate-new:  ## Create a new migration (MSG= required)
	alembic revision --autogenerate -m "$(MSG)"

# ---------------------------------------------------------------------------
# Local development (outside Docker)
# ---------------------------------------------------------------------------

install:  ## Install Python dependencies
	pip install -e ".[dev]"

api:  ## Start FastAPI dev server with hot-reload
	uvicorn repops.api.main:app --reload --host 0.0.0.0 --port 8000

worker:  ## Start Celery worker
	celery -A repops.workers.app worker --loglevel=info -Q collection,analysis,default

beat:  ## Start Celery beat scheduler
	celery -A repops.workers.app beat --loglevel=info

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

lint:  ## Lint and auto-fix with ruff
	ruff check . --fix
	ruff format .

typecheck:  ## Run mypy type checker
	mypy repops/

ci: lint typecheck  ## Full CI check (lint + types)

# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

keywords-import:  ## Import data/keywords/keywords.csv into the database
	python scripts/import_keywords.py

keywords-import-dry:  ## Preview what keywords-import would change (no DB writes)
	python scripts/import_keywords.py --dry-run

keywords-list:  ## Print all keywords currently in the database
	python scripts/import_keywords.py --list

keywords-export:  ## Export keyword database back to CSV
	python scripts/import_keywords.py --export data/keywords/keywords_export.csv
