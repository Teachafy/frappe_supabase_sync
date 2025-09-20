# Makefile for Frappe-Supabase Sync Service

.PHONY: help install dev test lint format clean docker-build docker-run docker-dev docker-test

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies in virtual environment"
	@echo "  dev         - Run development server"
	@echo "  test        - Run tests"
	@echo "  test-unit   - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code with black and isort"
	@echo "  clean       - Clean up temporary files"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run  - Run Docker container"
	@echo "  docker-dev  - Run development Docker container"
	@echo "  docker-test - Test Docker container"

# Virtual environment setup
venv:
	python -m venv venv
	venv/bin/pip install --upgrade pip

install: venv
	venv/bin/pip install -r requirements.txt
	venv/bin/pip install -r requirements-dev.txt

# Development
dev:
	venv/bin/python main.py

# Testing
test:
	venv/bin/pytest tests/ -v

test-unit:
	venv/bin/pytest tests/test_sync_components_unit.py -v

test-integration:
	venv/bin/pytest tests/test_comprehensive_sync_issues.py -v

test-coverage:
	venv/bin/pytest tests/ --cov=src --cov-report=html --cov-report=xml

# Code quality
lint:
	venv/bin/flake8 src/ tests/
	venv/bin/mypy src/
	venv/bin/bandit -r src/

format:
	venv/bin/black src/ tests/
	venv/bin/isort src/ tests/

# Cleanup
clean:
	rm -rf __pycache__/
	rm -rf src/**/__pycache__/
	rm -rf tests/**/__pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

# Docker commands
docker-build:
	docker build -t frappe-supabase-sync .

docker-build-dev:
	docker build -f Dockerfile.dev -t frappe-supabase-sync:dev .

docker-run:
	docker run -d --name sync-service -p 8000:8000 \
		-e REDIS_URL=redis://localhost:6379/0 \
		-e FRAPPE_URL=${FRAPPE_URL} \
		-e FRAPPE_API_KEY=${FRAPPE_API_KEY} \
		-e FRAPPE_API_SECRET=${FRAPPE_API_SECRET} \
		-e SUPABASE_URL=${SUPABASE_URL} \
		-e SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY} \
		-e SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY} \
		-e WEBHOOK_SECRET=${WEBHOOK_SECRET} \
		-e FRAPPE_WEBHOOK_TOKEN=${FRAPPE_WEBHOOK_TOKEN} \
		-e LOG_LEVEL=INFO \
		frappe-supabase-sync

docker-dev:
	docker run -d --name sync-service-dev -p 8001:8000 \
		-e REDIS_URL=redis://localhost:6379/0 \
		-e FRAPPE_URL=${FRAPPE_URL} \
		-e FRAPPE_API_KEY=${FRAPPE_API_KEY} \
		-e FRAPPE_API_SECRET=${FRAPPE_API_SECRET} \
		-e SUPABASE_URL=${SUPABASE_URL} \
		-e SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY} \
		-e SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY} \
		-e WEBHOOK_SECRET=${WEBHOOK_SECRET} \
		-e FRAPPE_WEBHOOK_TOKEN=${FRAPPE_WEBHOOK_TOKEN} \
		-e LOG_LEVEL=DEBUG \
		-v $(PWD)/src:/app/src \
		-v $(PWD)/main.py:/app/main.py \
		-v $(PWD)/custom_mappings.json:/app/custom_mappings.json \
		frappe-supabase-sync:dev

docker-test:
	docker run --rm -p 8000:8000 \
		-e REDIS_URL=redis://localhost:6379/0 \
		-e FRAPPE_URL=http://test-frappe.com \
		-e FRAPPE_API_KEY=test_key \
		-e FRAPPE_API_SECRET=test_secret \
		-e SUPABASE_URL=https://test.supabase.co \
		-e SUPABASE_ANON_KEY=test_anon_key \
		-e SUPABASE_SERVICE_ROLE_KEY=test_service_key \
		-e WEBHOOK_SECRET=test_webhook_secret \
		-e FRAPPE_WEBHOOK_TOKEN=test_token \
		-e LOG_LEVEL=INFO \
		frappe-supabase-sync

docker-stop:
	docker stop sync-service sync-service-dev || true
	docker rm sync-service sync-service-dev || true

# Docker Compose
compose-up:
	docker-compose up -d

compose-down:
	docker-compose down

compose-dev:
	docker-compose up sync-service-dev redis

compose-logs:
	docker-compose logs -f

# CI/CD helpers
ci-test:
	python -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements.txt
	venv/bin/pip install -r requirements-dev.txt
	venv/bin/pytest tests/ --cov=src --cov-report=xml --junitxml=pytest-report.xml -v

ci-lint:
	python -m venv venv
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements-dev.txt
	venv/bin/flake8 src/ tests/
	venv/bin/black --check src/ tests/
	venv/bin/isort --check-only src/ tests/
	venv/bin/mypy src/ --ignore-missing-imports
	venv/bin/bandit -r src/ -f json -o bandit-report.json || true
