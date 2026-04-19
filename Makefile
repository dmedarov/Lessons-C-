.DEFAULT_GOAL := help

COMPOSE_PROD := docker compose -f docker-compose.postgres.yml
COMPOSE_DEV  := docker compose
DOCKER_IMAGE := dmedarov/fleetflow
GIT_SHA      := $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

.PHONY: help setup prod dev down logs test push release guard-env

help:
	@echo "FleetFlow"
	@echo ""
	@echo "  make setup    Create .env with generated secrets (run once)"
	@echo "  make prod     Build and start production stack (PostgreSQL + app)"
	@echo "  make dev      Build and start dev stack (SQLite, demo data)"
	@echo "  make down     Stop all containers"
	@echo "  make logs     Tail application logs"
	@echo "  make test     Run test suite"
	@echo "  make push     Build image locally and push to Docker Hub"
	@echo "  make release  Backup DB → pull latest image → restart stack"

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

push:
	@echo "▶ 1/2  Building $(DOCKER_IMAGE):$(GIT_SHA)..."
	docker build -t $(DOCKER_IMAGE):latest -t $(DOCKER_IMAGE):$(GIT_SHA) .
	@echo "▶ 2/2  Pushing to Docker Hub..."
	docker push $(DOCKER_IMAGE):latest
	docker push $(DOCKER_IMAGE):$(GIT_SHA)
	@echo ""
	@echo "✓ Pushed $(DOCKER_IMAGE):latest  ($(GIT_SHA))"

release: guard-env
	@mkdir -p backups
	@PGUSER=$$(grep -m1 '^POSTGRES_USER=' .env | cut -d= -f2); \
	 PGDB=$$(grep -m1 '^POSTGRES_DB=' .env | cut -d= -f2); \
	 BACKUP="backups/backup_$$(date +%Y%m%d_%H%M%S).sql"; \
	 echo "▶ 1/3  PostgreSQL backup → $$BACKUP"; \
	 if $(COMPOSE_PROD) ps --quiet postgres 2>/dev/null | grep -q .; then \
	   $(COMPOSE_PROD) exec -T postgres \
	     pg_dump -U "$$PGUSER" "$$PGDB" > "$$BACKUP" \
	     && echo "    ✓ Saved $$BACKUP" \
	     || echo "    ✗ pg_dump failed — continuing without backup"; \
	 else \
	   echo "    ⚠ postgres container not running — skipping backup"; \
	 fi
	@echo "▶ 2/3  Pull latest image from Docker Hub..."
	$(COMPOSE_PROD) pull car-pool
	@echo "▶ 3/3  Restart stack with new image..."
	$(COMPOSE_PROD) up -d --no-build
	@echo ""
	@echo "✓ Released $(GIT_SHA). Run 'make logs' to verify."

guard-env:
	@test -f .env || { echo "Run 'make setup' first to create .env"; exit 1; }
