.DEFAULT_GOAL := help

COMPOSE_PROD := docker compose -f docker-compose.postgres.yml
COMPOSE_DEV  := docker compose

.PHONY: help setup prod dev down logs test guard-env

help:
	@echo "FleetFlow"
	@echo ""
	@echo "  make setup   Create .env with generated secrets (run once)"
	@echo "  make prod    Build and start production stack (PostgreSQL + app)"
	@echo "  make dev     Build and start dev stack (SQLite, demo data)"
	@echo "  make down    Stop all containers"
	@echo "  make logs    Tail application logs"
	@echo "  make test    Run test suite"

setup:
	@if [ -f .env ]; then \
		echo ".env already exists — skipping (delete it to regenerate)."; \
	else \
		cp .env.example .env; \
		python3 -c "\
import secrets, pathlib; \
p = pathlib.Path('.env'); \
t = p.read_text(); \
t = t.replace('replace-with-a-long-random-secret', secrets.token_urlsafe(48)); \
t = t.replace('replace-with-a-strong-db-password', secrets.token_urlsafe(32)); \
p.write_text(t)"; \
		echo ""; \
		echo ".env created — secrets generated automatically."; \
		echo "Before going live, set CORS_ALLOW_ORIGINS to your domain."; \
	fi

prod: guard-env
	$(COMPOSE_PROD) up --build -d
	@echo ""
	@echo "FleetFlow is up → http://localhost:8000"
	@echo "Fresh install? Run 'make logs' to find your one-time bootstrap token."

dev: guard-env
	$(COMPOSE_DEV) up --build -d
	@echo ""
	@echo "FleetFlow (dev) → http://localhost:8000"
	@echo "Accounts: admin/AdminPass123  ivan/IvanPass123  maria/MariaPass123"

down:
	@$(COMPOSE_PROD) down 2>/dev/null || true
	@$(COMPOSE_DEV) down 2>/dev/null || true

logs:
	@$(COMPOSE_PROD) logs --follow car-pool 2>/dev/null || \
	 $(COMPOSE_DEV)  logs --follow car-pool

test:
	pytest -q

guard-env:
	@test -f .env || { echo "Run 'make setup' first to create .env"; exit 1; }
