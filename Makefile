# Makefile for FastAPI Enterprise Demo

.PHONY: help install dev-install test test-unit test-integration lint format clean docker-build docker-up docker-down migrate migration

help: ## Show this help message
	@echo "FastAPI Enterprise Demo - Available Commands:"
	@echo "=============================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

dev-install: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest -m "not integration"

test-integration: ## Run integration tests only
	pytest -m integration

test-cov: ## Run tests with coverage
	pytest --cov=app --cov-report=html --cov-report=term-missing

test-watch: ## Run tests in watch mode
	pytest-watch

lint: ## Run linting
	flake8 app/
	mypy app/

format: ## Format code
	black app/ tests/
	isort app/ tests/

format-check: ## Check code formatting
	black --check app/ tests/
	isort --check-only app/ tests/

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/ .mypy_cache/

docker-build: ## Build Docker images
	docker-compose -f docker-compose.prod.yml build

docker-up: ## Start all services with Docker Compose
	docker-compose -f docker-compose.prod.yml up -d

docker-down: ## Stop all services
	docker-compose -f docker-compose.prod.yml down

docker-logs: ## Show Docker logs
	docker-compose -f docker-compose.prod.yml logs -f

docker-shell: ## Open shell in API container
	docker-compose -f docker-compose.prod.yml exec api bash

docker-worker-shell: ## Open shell in worker container
	docker-compose -f docker-compose.prod.yml exec worker bash

dev: ## Start development environment
	docker-compose up -d postgres rabbitmq redis
	sleep 5
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

worker: ## Start background job worker
	python worker.py

migrate: ## Run database migrations
	alembic upgrade head

migration: ## Create new migration
	alembic revision --autogenerate -m "$(MSG)"

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

setup-dev: dev-install ## Setup development environment
	cp env.example .env
	pre-commit install
	@echo "Development environment setup complete!"
	@echo "Edit .env file with your configuration"
	@echo "Run 'make dev' to start the development server"

check: format-check lint test ## Run all checks

ci: ## Run CI pipeline
	make format-check
	make lint
	make test
	make docker-build

security: ## Run security checks
	bandit -r app/
	safety check

performance: ## Run performance tests
	pytest tests/test_performance.py -v

load-test: ## Run load tests
	locust -f tests/load_test.py --host=http://localhost:8000

docs: ## Generate API documentation
	python -c "from main import app; import json; print(json.dumps(app.openapi(), indent=2))" > openapi.json

deploy-staging: ## Deploy to staging
	docker-compose -f docker-compose.prod.yml -f docker-compose.staging.yml up -d

deploy-prod: ## Deploy to production
	docker-compose -f docker-compose.prod.yml up -d

backup-db: ## Backup database
	docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U user fastapi_demo > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db: ## Restore database from backup
	docker-compose -f docker-compose.prod.yml exec -T postgres psql -U user fastapi_demo < $(BACKUP_FILE)

monitor: ## Show system monitoring
	docker-compose -f docker-compose.prod.yml exec api curl -s http://localhost:8000/api/v1/metrics | grep -E "(http_requests_total|background_jobs_total)"

health-check: ## Check system health
	curl -s http://localhost:8000/api/v1/health | jq .

logs-api: ## Show API logs
	docker-compose -f docker-compose.prod.yml logs -f api

logs-worker: ## Show worker logs
	docker-compose -f docker-compose.prod.yml logs -f worker

logs-all: ## Show all logs
	docker-compose -f docker-compose.prod.yml logs -f

restart-api: ## Restart API service
	docker-compose -f docker-compose.prod.yml restart api

restart-worker: ## Restart worker service
	docker-compose -f docker-compose.prod.yml restart worker

scale-worker: ## Scale worker service
	docker-compose -f docker-compose.prod.yml up -d --scale worker=$(REPLICAS)

update-deps: ## Update dependencies
	pip-compile requirements.in
	pip-compile requirements-dev.in

install-deps: ## Install dependencies from compiled requirements
	pip-sync requirements.txt requirements-dev.txt