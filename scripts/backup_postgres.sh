#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.postgres.yml}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/fleetflow-${STAMP}.dump"

if [[ ! -f ".env" ]]; then
  for required in SECRET_KEY POSTGRES_PASSWORD DATABASE_URL; do
    if [[ -z "${!required:-}" ]]; then
      echo "ERROR: .env is missing and ${required} is not set. Run make setup first." >&2
      exit 1
    fi
  done
fi

mkdir -p "${BACKUP_DIR}"

docker compose -f "${COMPOSE_FILE}" exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  > "${OUT}"

chmod 600 "${OUT}"
echo "Backup created: ${OUT}"
