.PHONY: dev test lint seed seed-all docker-up docker-down clean export-leads help

# Default Python path for local development
PYTHONPATH := src
export PYTHONPATH

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# === Development ===

dev: ## Start API server in dev mode
	uvicorn xcapitsff.api.app:app --reload --host 0.0.0.0 --port 8000

test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	pytest tests/integration/ -v

test-cov: ## Run tests with coverage
	pytest tests/ --cov=xcapitsff --cov-report=html --cov-report=term

lint: ## Run linter
	ruff check src/ tests/

format: ## Format code
	ruff format src/ tests/

typecheck: ## Run type checker
	mypy src/

# === Data ===

seed: ## Seed leads from TSV
	python scripts/seed_leads.py

seed-kb: ## Seed knowledge base
	python scripts/seed_knowledge.py

seed-all: ## Seed everything (leads + KB + customers + tickets)
	python scripts/seed_all.py

export-leads: ## Export leads to CSV
	python -c "import asyncio; from xcapitsff.core.database import init_db, async_session; from xcapitsff.sales.export import export_leads_csv; \
	async def main(): \
		await init_db(); \
		async with async_session() as db: r = await export_leads_csv(db); print(r.content); \
	asyncio.run(main())" > leads_export.csv
	@echo "Exported to leads_export.csv"

# === Docker ===

docker-up: ## Start all services with Docker
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-build: ## Rebuild Docker images
	docker-compose build

docker-logs: ## Follow Docker logs
	docker-compose logs -f app

# === Database ===

db-migrate: ## Create a new migration
	alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## Apply migrations
	alembic upgrade head

db-downgrade: ## Rollback last migration
	alembic downgrade -1

# === Cleanup ===

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f xcapitsff.db
