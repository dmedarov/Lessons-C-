#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 backups/fleetflow-YYYYmmddTHHMMSSZ.dump" >&2
  exit 1
fi

if [[ ! -f ".env" ]]; then
  for required in SECRET_KEY POSTGRES_PASSWORD DATABASE_URL; do
    if [[ -z "${!required:-}" ]]; then
      echo "ERROR: .env is missing and ${required} is not set. Run make setup first." >&2
      exit 1
    fi
  done
fi

BACKUP_PATH="$1"
if [[ ! -f "${BACKUP_PATH}" ]]; then
  echo "ERROR: backup file not found: ${BACKUP_PATH}" >&2
  exit 1
fi

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.postgres.yml}"
RESTORE_PROJECT="${RESTORE_PROJECT:-fleetflow_restore_drill}"
RESTORE_DB="${RESTORE_DB:-fleetflow_restore_drill}"
KEEP_RESTORE_DRILL="${KEEP_RESTORE_DRILL:-0}"
REMOTE_DUMP="/tmp/fleetflow-restore.dump"

if [[ "${RESTORE_PROJECT}" == "fleetflow_test" || "${RESTORE_PROJECT}" == "fleetflow_prod_smoke" ]]; then
  echo "ERROR: choose a dedicated RESTORE_PROJECT, not an active smoke project." >&2
  exit 1
fi

cleanup() {
  if [[ "${KEEP_RESTORE_DRILL}" != "1" ]]; then
    docker compose -p "${RESTORE_PROJECT}" -f "${COMPOSE_FILE}" down -v --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

docker compose -p "${RESTORE_PROJECT}" -f "${COMPOSE_FILE}" up -d postgres
for _ in {1..30}; do
  if docker compose -p "${RESTORE_PROJECT}" -f "${COMPOSE_FILE}" exec -T postgres sh -c \
    'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker compose -p "${RESTORE_PROJECT}" -f "${COMPOSE_FILE}" exec -T postgres sh -c \
  'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null
docker compose -p "${RESTORE_PROJECT}" -f "${COMPOSE_FILE}" cp "${BACKUP_PATH}" "postgres:${REMOTE_DUMP}"
docker compose -p "${RESTORE_PROJECT}" -f "${COMPOSE_FILE}" exec -T \
  -e RESTORE_DB="${RESTORE_DB}" \
  -e REMOTE_DUMP="${REMOTE_DUMP}" \
  postgres sh -c \
  'dropdb -U "$POSTGRES_USER" --if-exists "$RESTORE_DB" &&
   createdb -U "$POSTGRES_USER" "$RESTORE_DB" &&
   pg_restore -U "$POSTGRES_USER" -d "$RESTORE_DB" --no-owner --no-privileges "$REMOTE_DUMP" &&
   psql -U "$POSTGRES_USER" -d "$RESTORE_DB" -tAc "SELECT COUNT(*) FROM alembic_version;"' \
  | grep -q "1"

echo "Restore drill succeeded into project ${RESTORE_PROJECT}, database ${RESTORE_DB}."
