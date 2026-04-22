from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production_readiness import evaluate_env_readiness, load_env, restore_drill_readiness  # noqa: E402


def git_output(args: list[str]) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[str, str, dict[str, Any] | None]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    data = None
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        detail = body or str(exc)
        return "FAIL", f"{url} returned HTTP {exc.code}: {detail}", None
    except urllib.error.URLError as exc:
        return "FAIL", f"{url} unreachable: {exc}", None

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return "FAIL", f"{url} did not return JSON", None
    if not isinstance(data, dict):
        return "FAIL", f"{url} returned unexpected JSON", None
    return "OK", f"{url} returned JSON", data


def fetch_json(base_url: str, path: str) -> tuple[str, str, dict[str, Any] | None]:
    url = f"{base_url.rstrip('/')}{path}"
    status, detail, data = request_json(url)
    if status != "OK" or data is None:
        return status, detail.replace(url, path), data

    if path == "/health":
        ok = data.get("status") == "ok"
    elif path == "/health/ready":
        ok = data.get("status") == "ready"
    elif path == "/auth/setup-status":
        ok = data.get("has_admin") is True
    elif path == "/public/overview":
        ok = {"active_cars", "pending_requests", "active_trips", "available_cars"} <= set(data)
    else:
        ok = True
    detail = f"{path} {'passed' if ok else 'failed'}"
    return ("OK", detail, data) if ok else ("FAIL", f"{path} failed predicate", data)


def render_check_line(prefix: str, label: str, detail: str) -> str:
    return f"- `{prefix}` {label}: {detail}"


def summarize_admin_readiness(base_url: str) -> dict[str, Any]:
    username = os.getenv("CUTOVER_ADMIN_USERNAME", "").strip()
    password = os.getenv("CUTOVER_ADMIN_PASSWORD", "")
    if not username or not password:
        return {
            "status": "SKIP",
            "summary": "Липсват CUTOVER_ADMIN_USERNAME / CUTOVER_ADMIN_PASSWORD; admin readiness snapshot остава manual-only.",
            "items": [],
        }

    login_status, login_detail, login_data = request_json(
        f"{base_url.rstrip('/')}/auth/login",
        method="POST",
        payload={"username": username, "password": password},
    )
    if login_status != "OK" or not isinstance(login_data, dict):
        return {
            "status": "FAIL",
            "summary": f"Login failed for CUTOVER_ADMIN_USERNAME: {login_detail}",
            "items": [],
        }

    access_token = login_data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        return {
            "status": "FAIL",
            "summary": "Login response did not include an access token.",
            "items": [],
        }

    readiness_status, readiness_detail, readiness_data = request_json(
        f"{base_url.rstrip('/')}/ops/readiness",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if readiness_status != "OK" or not isinstance(readiness_data, dict):
        return {
            "status": "FAIL",
            "summary": f"/ops/readiness failed after login: {readiness_detail}",
            "items": [],
        }

    items = readiness_data.get("items")
    if not isinstance(items, list):
        return {
            "status": "FAIL",
            "summary": "Readiness response did not include an items list.",
            "items": [],
        }

    typed_items = [item for item in items if isinstance(item, dict)]
    blockers = sum(1 for item in typed_items if item.get("status") == "fail" and item.get("required", True))
    warnings = sum(1 for item in typed_items if item.get("status") == "warn")
    ready = readiness_data.get("ready") is True
    summary_status = "FAIL" if blockers else "WARN" if warnings or not ready else "OK"
    item_order = {"fail": 0, "warn": 1, "pass": 2}
    focus_ids = {"restore_drill", "admin_redundancy", "netfleet", "notifications", "active_admin"}
    focus_items = sorted(
        (
            item
            for item in typed_items
            if item.get("status") != "pass" or item.get("id") in focus_ids
        ),
        key=lambda item: (item_order.get(str(item.get("status")), 3), str(item.get("label", ""))),
    )[:5]

    return {
        "status": summary_status,
        "summary": (
            f"ready={ready}; {blockers} blockers; {warnings} warnings; "
            f"app_env={readiness_data.get('app_env', 'unknown')}; "
            f"database={readiness_data.get('database_backend', 'unknown')}"
        ),
        "items": focus_items,
    }


def report_text(env_path: Path, app_url: str, out_path: Path) -> str:
    env = load_env(env_path)
    env_checks = evaluate_env_readiness(env)
    failed = [item for item in env_checks if item.status == "fail"]
    warnings = [item for item in env_checks if item.status == "warn"]
    passed = [item for item in env_checks if item.status == "pass"]
    restore = restore_drill_readiness(env, strict=True)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    admin_readiness = summarize_admin_readiness(app_url)

    live_checks = [
        fetch_json(app_url, "/health"),
        fetch_json(app_url, "/health/ready"),
        fetch_json(app_url, "/auth/setup-status"),
        fetch_json(app_url, "/public/overview"),
    ]

    lines = [
        "# FleetFlow Cutover Report",
        "",
        f"- Generated at (UTC): `{timestamp}`",
        f"- Repository: `dmedarov/Lessons-C-`",
        f"- Branch: `{git_output(['git', 'branch', '--show-current'])}`",
        f"- Commit: `{git_output(['git', 'rev-parse', '--short', 'HEAD'])}`",
        f"- Env file: `{env_path}`",
        f"- Target URL: `{app_url}`",
        f"- Output file: `{out_path}`",
        "",
        "## Automated snapshot",
        "",
        "### Env readiness",
        f"- Summary: `{len(failed)} blockers · {len(warnings)} warnings · {len(passed)} OK`",
    ]

    if failed:
        lines.append("- Blocking items:")
        lines.extend(render_check_line("FAIL", item.label, item.ui_detail) for item in failed)
    if warnings:
        lines.append("- Warning items:")
        lines.extend(render_check_line("WARN", item.label, item.ui_detail) for item in warnings)
    if passed:
        lines.append("- OK items:")
        lines.extend(render_check_line("OK", item.label, item.ui_detail) for item in passed)

    lines.extend(
        [
            "",
            "### Restore drill evidence",
            render_check_line(restore.status.upper(), restore.label, restore.ui_detail),
            "",
            "### Public live checks",
        ]
    )
    lines.extend(
        render_check_line(
            status,
            detail.split(":")[0].replace(" passed", "").replace(" failed", ""),
            detail,
        )
        for status, detail, _ in live_checks
    )

    lines.extend(
        [
            "",
            "### Authenticated admin readiness",
            render_check_line(admin_readiness["status"], "Admin readiness snapshot", admin_readiness["summary"]),
        ]
    )
    if admin_readiness["items"]:
        lines.append("- Focus items:")
        lines.extend(
            render_check_line(
                str(item.get("status", "warn")).upper(),
                str(item.get("label", item.get("id", "item"))),
                str(item.get("detail", "")),
            )
            for item in admin_readiness["items"]
        )

    lines.extend(
        [
            "",
            "## Manual-only checks still required",
            "",
            "- GitHub Security / Dependabot review in the GitHub web UI",
            "- Secret rotation metadata if any alert is real",
            "- Visual review of the authenticated admin `/ops/readiness` panel on the real production URL",
            "- Live role rehearsal: employee -> approver -> reception -> return",
            "- Final operator / witness signoff",
            "",
            "## GitHub Security notes",
            "",
            "- Dependabot alert count: `________________`",
            "- Secret alert provider / title: `________________`",
            "- Rotation completed: `YES / NO`",
            "",
            "## Signoff",
            "",
            "- Operator: `________________`",
            "- Witness: `________________`",
            "- Verdict: `GO / STOP`",
            "",
            "See also:",
            "- `docs/PRODUCTION_CUTOVER_CHECKLIST.md`",
            "- `docs/PRODUCTION_READINESS_ASSESSMENT.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    env_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".env")
    app_url = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8001"
    if not env_path.exists():
        print(f"ERROR: {env_path} does not exist. Run `make setup` first.")
        return 1

    report_dir = Path(os.getenv("CUTOVER_REPORT_DIR", ROOT / "cutover-reports"))
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = report_dir / f"cutover-report-{stamp}.md"
    out_path.write_text(report_text(env_path, app_url, out_path))
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
