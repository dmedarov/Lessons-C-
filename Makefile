.DEFAULT_GOAL := help

COMPOSE_PROD := docker compose -f docker-compose.postgres.yml
COMPOSE_DEV  := docker compose
PYTHON       := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
PIP_AUDIT    := $(shell if [ -x .venv/bin/pip-audit ]; then echo .venv/bin/pip-audit; else echo pip-audit; fi)
APP_URL      ?= http://127.0.0.1:8001

.PHONY: help setup prod prod-check go-live-check cutover-report prod-backup prod-restore-drill audit-prod audit-prod-full secrets-scan secrets-scan-history release-check qa-premium smoke-live dev down logs test test-e2e guard-env guard-backup

help:
	@echo "FleetFlow"
	@echo ""
	@echo "  make setup   Create .env with generated secrets (run once)"
	@echo "  make prod    Build and start production stack (PostgreSQL + app)"
	@echo "  make prod-check Validate .env before live production cutover"
	@echo "  make go-live-check Validate env, restore drill evidence, release gates and live smoke"
	@echo "  make cutover-report APP_URL=http://... Generate a markdown cutover evidence snapshot"
	@echo "  make prod-backup Create a PostgreSQL backup under backups/"
	@echo "  make prod-restore-drill BACKUP=backups/file.dump Validate backup in an isolated restore project"
	@echo "  make audit-prod Audit pinned runtime dependencies"
	@echo "  make audit-prod-full Audit runtime dependencies with resolver"
	@echo "  make secrets-scan Fail if tracked files contain real-looking secret values"
	@echo "  make secrets-scan-history Scan all git refs for real-looking secret values"
	@echo "  make release-check Run local production release gates"
	@echo "  make qa-premium Run release gates + browser role smoke"
	@echo "  make smoke-live APP_URL=http://... Smoke a running app URL"
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

go-live-check: guard-env
	$(PYTHON) scripts/go_live_check.py .env
	$(MAKE) release-check
	$(MAKE) smoke-live APP_URL=$(APP_URL)

cutover-report: guard-env
	$(PYTHON) scripts/cutover_report.py .env "$(APP_URL)"

prod-backup: guard-env
	bash scripts/backup_postgres.sh

prod-restore-drill: guard-env guard-backup
	bash scripts/restore_postgres_drill.sh "$(BACKUP)"

audit-prod:
	$(PIP_AUDIT) --disable-pip --no-deps -r requirements.txt

audit-prod-full:
	$(PIP_AUDIT) -r requirements.txt

secrets-scan:
	$(PYTHON) scripts/scan_secrets.py

secrets-scan-history:
	$(PYTHON) scripts/scan_secrets.py --all-refs

release-check: audit-prod secrets-scan
	PYTHONPYCACHEPREFIX=/tmp/fleetflow-pycache $(PYTHON) -m py_compile app.py db.py schemas.py security.py production_readiness.py routers/*.py fleet_intelligence/*.py scripts/*.py
	$(PYTHON) -m pytest -q
	node --check static/app.js
	node --check static/i18n.js

qa-premium: release-check test-e2e
	@echo ""
	@echo "Premium QA gate passed."
	@echo "Optional live container smoke: make smoke-live APP_URL=$(APP_URL)"

smoke-live:
	$(PYTHON) scripts/smoke_live.py "$(APP_URL)"

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
