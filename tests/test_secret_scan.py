from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_scan_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "scan_secrets.py"
    spec = importlib.util.spec_from_file_location("scan_secrets", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["scan_secrets"] = module
    spec.loader.exec_module(module)
    return module


def test_secret_scan_allows_documented_placeholders() -> None:
    scanner = _load_scan_module()
    text = "\n".join(
        [
            "SECRET_KEY=replace-with-a-long-random-secret",
            "POSTGRES_PASSWORD=fleetflow-dev-password",
            "DATABASE_URL=postgresql://fleetflow:replace-with-a-strong-db-password@postgres:5432/fleetflow",
            "NETFLEET_API_KEY=your-netfleet-company-api-key",
            "SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-}",
        ]
    )

    assert scanner.scan_text(".env.example", text) == []


def test_secret_scan_flags_real_infrastructure_values() -> None:
    scanner = _load_scan_module()
    leaked_secret = "8e4b40f0aa3b4d2f9f856d28bb5d164e956f0e56a7473dbf"
    leaked_password = "FleetProdDbPassword2026"
    leaked_netfleet_key = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    text = "\n".join(
        [
            f"{'SECRET_KEY'}={leaked_secret}",
            f"{'POSTGRES_PASSWORD'}={leaked_password}",
            f"{'DATABASE_URL'}=postgresql://fleetflow:{leaked_password}@postgres:5432/fleetflow",
            f"{'NETFLEET_API_KEY'}={leaked_netfleet_key}",
        ]
    )

    findings = scanner.scan_text("leak.env", text)

    assert [finding.detail for finding in findings] == [
        "SECRET_KEY appears to contain a real value",
        "POSTGRES_PASSWORD appears to contain a real value",
        "DATABASE_URL appears to contain a real value",
        "NETFLEET_API_KEY appears to contain a real value",
    ]


def test_secret_scan_flags_private_key_blocks() -> None:
    scanner = _load_scan_module()

    marker = "-----BEGIN OPENSSH " + "PRIVATE KEY-----"
    findings = scanner.scan_text("id_rsa", marker)

    assert len(findings) == 1
    assert findings[0].kind == "private_key"


def test_secret_scan_path_skip_ignores_local_worktrees() -> None:
    scanner = _load_scan_module()

    assert scanner.should_skip_path(Path(".claude/worktrees/example/.env"))
    assert scanner.should_skip_path(Path("test-results/e2e/screenshot.png"))
    assert not scanner.should_skip_path(Path(".env.example"))


def test_history_scan_skips_its_own_synthetic_fixture_file() -> None:
    scanner = _load_scan_module()

    assert "tests/test_secret_scan.py" in scanner.ALL_REFS_FIXTURE_PATHS
