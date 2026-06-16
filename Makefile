.PHONY: help install dev test lint format typecheck migrate migration docker-build docker-up bench clean

help:
	@echo "SWV Development Makefile"
	@echo "========================"
	@echo "install     - Install project with dev dependencies"
	@echo "dev         - Start uvicorn dev server with reload"
	@echo "test        - Run pytest with coverage"
	@echo "lint        - Run ruff check and format check"
	@echo "format      - Run ruff format"
	@echo "typecheck   - Run mypy type checking"
	@echo "migrate     - Run alembic migrations"
	@echo "migration   - Create new alembic migration"
	@echo "docker-build - Build Docker image"
	@echo "docker-up   - Start Docker Compose services"
	@echo "bench       - Run load tests"
	@echo "clean       - Remove __pycache__ directories"

install:
	pip install -e ".[dev]"

dev:
	uvicorn backend.main:app --reload

test:
	pytest --cov=backend --cov-report=term --cov-report=html

lint:
	ruff check backend/ && ruff format --check backend/

format:
	ruff format backend/

typecheck:
	mypy backend/

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m

docker-build:
	docker compose build

docker-up:
	docker compose up -d

bench:
	python -m backend.benchmarks.load_test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
