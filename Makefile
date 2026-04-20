.DEFAULT_GOAL := help

COMPOSE_PROD := docker compose -f docker-compose.postgres.yml
COMPOSE_DEV  := docker compose
PYTHON       := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

.PHONY: help setup prod prod-check prod-backup prod-restore-drill dev down logs test test-e2e guard-env guard-backup

help:
	@echo "FleetFlow"
	@echo ""
	@echo "  make setup   Create .env with generated secrets (run once)"
	@echo "  make prod    Build and start production stack (PostgreSQL + app)"
	@echo "  make prod-check Validate .env before live production cutover"
	@echo "  make prod-backup Create a PostgreSQL backup under backups/"
	@echo "  make prod-restore-drill BACKUP=backups/file.dump Validate backup in an isolated restore project"
	@echo "  make dev     Build and start dev stack (SQLite, demo data)"
	@echo "  make down    Stop all containers"
	@echo "  make logs    Tail application logs"
	@echo "  make test    Run test suite"
	@echo "  make test-e2e Run optional Playwright browser smoke"

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
	@echo "FleetFlow is up → http://localhost:$${APP_PORT:-8000}"
	@echo "Fresh install? Run 'make logs' to find your one-time bootstrap token."

prod-check: guard-env
	$(PYTHON) scripts/prod_check.py .env

prod-backup: guard-env
	bash scripts/backup_postgres.sh

prod-restore-drill: guard-env guard-backup
	bash scripts/restore_postgres_drill.sh "$(BACKUP)"

dev: guard-env
	$(COMPOSE_DEV) up --build -d
	@echo ""
	@echo "FleetFlow (dev) → http://localhost:$${APP_PORT:-8000}"
	@echo "Accounts: admin/AdminPass123  ivan/IvanPass123  maria/MariaPass123"

down:
	@$(COMPOSE_PROD) down 2>/dev/null || true
	@$(COMPOSE_DEV) down 2>/dev/null || true

logs:
	@$(COMPOSE_PROD) logs --follow car-pool 2>/dev/null || \
	 $(COMPOSE_DEV)  logs --follow car-pool

test:
	$(PYTHON) -m pytest -q

test-e2e:
	$(PYTHON) -m pytest e2e -q || test $$? -eq 5

guard-env:
	@test -f .env || { echo "Run 'make setup' first to create .env"; exit 1; }

guard-backup:
	@test -n "$(BACKUP)" || { echo "Usage: make prod-restore-drill BACKUP=backups/fleetflow-....dump"; exit 1; }
