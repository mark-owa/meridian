.PHONY: help dev worker test lint fmt up down logs migrate

help:
	@echo "make dev       run the API locally with auto-reload"
	@echo "make worker    run the Celery worker locally"
	@echo "make test      run the backend test suite with coverage"
	@echo "make lint      run ruff"
	@echo "make up        start the full stack (postgres, redis, api, worker, web) via Docker Compose"
	@echo "make down      stop the stack"
	@echo "make logs      tail logs from all services"
	@echo "make migrate   generate a new Alembic migration (make migrate msg=\"add leads table\")"

dev:
	cd backend && uvicorn main:app --reload

worker:
	cd backend && celery -A worker.celery_app worker --loglevel=info

test:
	cd backend && pytest --cov --cov-report=term-missing

lint:
	cd backend && ruff check .

fmt:
	cd backend && ruff check --fix .

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	cd backend && alembic revision --autogenerate -m "$(msg)"
