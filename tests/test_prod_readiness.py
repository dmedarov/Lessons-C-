from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.go_live_check import restore_drill_messages


ROOT = Path(__file__).resolve().parents[1]


def run_prod_check(env_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/prod_check.py"), str(env_file)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_prod_check_accepts_generated_live_ready_env(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    secret = "s" * 48
    password = "p" * 32
    env_file.write_text(
        "\n".join(
            [
                "APP_ENV=prod",
                f"SECRET_KEY={secret}",
                f"POSTGRES_PASSWORD={password}",
                "POSTGRES_IMAGE=postgres:16",
                f"DATABASE_URL=postgresql://fleetflow:{password}@postgres:5432/fleetflow",
                "CORS_ALLOW_ORIGINS=https://fleetflow.company.bg",
                "DEV_SEED_DEMO_DATA=false",
                "NETFLEET_API_KEY=",
                "LOG_FORMAT=auto",
            ]
        )
    )

    result = run_prod_check(env_file)

    assert result.returncode == 0
    assert "OK: production environment looks ready." in result.stdout
    assert "WARNING: NETFLEET_API_KEY is empty" in result.stdout


def test_prod_check_rejects_placeholders_and_example_origin(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "APP_ENV=dev",
                "SECRET_KEY=replace-with-a-long-random-secret",
                "POSTGRES_PASSWORD=fleetflow-dev-password",
                "POSTGRES_IMAGE=cgr.dev/chainguard/postgres:latest",
                "DATABASE_URL=postgresql://fleetflow:fleetflow-dev-password@postgres:5432/fleetflow",
                "CORS_ALLOW_ORIGINS=https://fleetflow.example.com",
                "DEV_SEED_DEMO_DATA=true",
            ]
        )
    )

    result = run_prod_check(env_file)

    assert result.returncode == 1
    assert "APP_ENV must be prod" in result.stdout
    assert "SECRET_KEY must be generated" in result.stdout
    assert "POSTGRES_PASSWORD must be generated" in result.stdout
    assert "POSTGRES_IMAGE must be pinned" in result.stdout
    assert "CORS_ALLOW_ORIGINS must be the real production origin" in result.stdout
    assert "DEV_SEED_DEMO_DATA must be false" in result.stdout


def test_production_compose_passes_runtime_settings_to_app_container() -> None:
    compose = (ROOT / "docker-compose.postgres.yml").read_text()

    for key in (
        "CORS_ALLOW_ORIGINS",
        "POSTGRES_PASSWORD",
        "REFRESH_TOKEN_TTL_SECONDS",
        "DEV_SEED_DEMO_DATA",
        "LOGIN_RATE_LIMIT_ATTEMPTS",
        "BOOTSTRAP_RATE_LIMIT_ATTEMPTS",
        "NOTIFICATION_TIMEOUT_SECONDS",
        "LOG_FORMAT",
        "SMTP_HOST",
        "SLACK_WEBHOOK_URL",
        "TEAMS_WEBHOOK_URL",
    ):
        assert f"{key}:" in compose
    assert "POSTGRES_IMAGE:-postgres:16" in compose


def test_backup_restore_operator_scripts_are_documented_and_guarded() -> None:
    makefile = (ROOT / "Makefile").read_text()
    gitignore = (ROOT / ".gitignore").read_text()
    guide = (ROOT / "docs/PRODUCTION_USER_GUIDE.md").read_text()
    backup = (ROOT / "scripts/backup_postgres.sh").read_text()
    restore = (ROOT / "scripts/restore_postgres_drill.sh").read_text()
    smoke = (ROOT / "scripts/smoke_live.py").read_text()

    assert "prod-backup" in makefile
    assert "prod-restore-drill" in makefile
    assert "backups/" in gitignore
    assert "make prod-backup" in guide
    assert "make prod-restore-drill BACKUP=" in guide
    assert "Как да разчетеш най-честите блокери" in guide
    assert "Database password" in guide
    assert "CORS_ALLOW_ORIGINS=https://fleetflow.company.bg" in guide
    assert "pg_dump" in backup
    assert "--format=custom" in backup
    assert "chmod 600" in backup
    assert "fleetflow_restore_drill" in restore
    assert "down -v --remove-orphans" in restore
    assert "pg_restore" in restore
    assert "restore-drill-ok.json" in restore
    assert "Restore drill evidence written" in restore
    assert "/auth/setup-status" in smoke
    assert "no active admin exists" in smoke


def test_go_live_check_accepts_fresh_restore_drill_marker(tmp_path: Path) -> None:
    marker = tmp_path / "restore-drill-ok.json"
    backup = tmp_path / "fleetflow.dump"
    backup.write_text("not-a-real-dump")
    marker.write_text(
        (
            "{"
            '"succeeded": true,'
            '"checked_at": "2026-04-21T10:00:00Z",'
            f'"backup_path": "{backup}",'
            '"restore_project": "fleetflow_restore_drill",'
            '"restore_db": "fleetflow_restore_drill"'
            "}"
        )
    )

    errors, warnings = restore_drill_messages(
        {"RESTORE_DRILL_MARKER": str(marker), "RESTORE_DRILL_MAX_AGE_HOURS": "168"},
        now=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
    )

    assert errors == []
    assert warnings == []


def test_go_live_check_rejects_missing_and_stale_restore_drill_marker(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    errors, warnings = restore_drill_messages({"RESTORE_DRILL_MARKER": str(missing)})
    assert warnings == []
    assert "Restore drill evidence is missing" in errors[0]

    marker = tmp_path / "restore-drill-ok.json"
    marker.write_text(
        '{"succeeded": true, "checked_at": "2026-04-14T10:00:00Z", "backup_path": ""}'
    )
    errors, _ = restore_drill_messages(
        {"RESTORE_DRILL_MARKER": str(marker), "RESTORE_DRILL_MAX_AGE_HOURS": "24"},
        now=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
    )

    assert any("older than 24 hours" in error for error in errors)


def test_operator_scripts_have_valid_syntax() -> None:
    for script in (
        "scripts/backup_postgres.sh",
        "scripts/restore_postgres_drill.sh",
        "scripts/go_live_check.py",
        "scripts/smoke_live.py",
    ):
        if script.endswith(".py"):
            command = [sys.executable, "-m", "py_compile", str(ROOT / script)]
        else:
            command = ["bash", "-n", str(ROOT / script)]
        result = subprocess.run(
            command,
            cwd=ROOT,
            env={**os.environ, "PYTHONPYCACHEPREFIX": "/tmp/fleetflow-pycache"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert result.returncode == 0, result.stdout
