.PHONY: help setup test run clean docker-build docker-up docker-down deploy

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Work Order Processing Pipeline$(NC)"
	@echo "$(BLUE)==============================$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

setup: ## Install dependencies and set up environment
	@echo "$(BLUE)Setting up environment...$(NC)"
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	cd dbt && dbt deps
	@echo "$(GREEN)✓ Setup complete!$(NC)"

test: ## Run all tests (pytest + dbt)
	@echo "$(BLUE)Running pytest...$(NC)"
	pytest -v
	@echo "$(BLUE)Running dbt tests...$(NC)"
	cd dbt && dbt test
	@echo "$(GREEN)✓ All tests passed!$(NC)"

test-unit: ## Run unit tests only
	pytest -v -m "not integration"

test-integration: ## Run integration tests only
	pytest -v -m integration

test-coverage: ## Run tests with coverage report
	pytest --cov=src --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report: htmlcov/index.html$(NC)"

run-pipeline: ## Run complete pipeline
	@echo "$(BLUE)Running work order pipeline...$(NC)"
	python scripts/run_pipeline.py
	@echo "$(GREEN)✓ Pipeline complete!$(NC)"

run-check: ## Check pipeline status without running
	python scripts/run_pipeline.py --check-only

run-ocr: ## Run OCR extraction only
	python src/extractors/ocr_service.py

run-corrections: ## Run data corrections only
	bq query --use_legacy_sql=false < sql/create_corrected_table.sql

run-ml: ## Run ML categorization only
	python src/transformers/ml_categorizer.py

run-dbt: ## Run dbt transformations only
	cd dbt && dbt run

dbt-test: ## Run dbt tests
	cd dbt && dbt test

dbt-docs: ## Generate and serve dbt documentation
	cd dbt && dbt docs generate && dbt docs serve

clean: ## Clean up temporary files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache htmlcov .coverage
	rm -rf dbt/target dbt/logs dbt/dbt_packages
	@echo "$(GREEN)✓ Cleaned up temporary files$(NC)"

lint: ## Run code linters
	flake8 src tests
	black --check src tests
	mypy src

format: ## Format code with black
	black src tests scripts

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose -f docker-compose-github.yml build
	@echo "$(GREEN)✓ Docker images built!$(NC)"

docker-up: ## Start Docker containers
	@echo "$(BLUE)Starting containers...$(NC)"
	docker-compose -f docker-compose-github.yml up -d
	@echo "$(GREEN)✓ Containers running!$(NC)"
	@echo "Airflow UI: http://localhost:8081"
	@echo "dbt docs: http://localhost:8080"

docker-down: ## Stop Docker containers
	docker-compose -f docker-compose-github.yml down

docker-logs: ## View Docker logs
	docker-compose -f docker-compose-github.yml logs -f

docker-exec: ## Execute command in pipeline container
	docker-compose -f docker-compose-github.yml exec pipeline /bin/bash

deploy-terraform: ## Deploy infrastructure with Terraform
	@echo "$(BLUE)Deploying infrastructure...$(NC)"
	cd infrastructure/terraform && terraform init && terraform apply
	@echo "$(GREEN)✓ Infrastructure deployed!$(NC)"

deploy-airflow: ## Deploy Airflow DAG to Cloud Composer
	gcloud composer environments storage dags import \
	  --environment=work-order-composer \
	  --location=us-central1 \
	  --source=airflow/dags/work_order_pipeline.py

export-data: ## Export all data to CSV
	./scripts/export_all_data.sh

check-bigquery: ## Check BigQuery tables status
	bq ls work-orders-435517:work_orders_production
	bq ls work-orders-435517:work_orders_production_analytics

install-hooks: ## Install git pre-commit hooks
	pre-commit install

ci: test lint ## Run CI checks (tests + linting)
	@echo "$(GREEN)✓ CI checks passed!$(NC)"

.DEFAULT_GOAL := help
