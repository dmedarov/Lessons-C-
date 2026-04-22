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


def fetch_json(base_url: str, path: str) -> tuple[str, str]:
    url = f"{base_url.rstrip('/')}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        return "FAIL", f"{path} unreachable: {exc}"

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return "FAIL", f"{path} did not return JSON"
    if not isinstance(data, dict):
        return "FAIL", f"{path} returned unexpected JSON"

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
    return ("OK", f"{path} {'passed' if ok else 'failed'}") if ok else ("FAIL", f"{path} failed predicate")


def render_check_line(prefix: str, label: str, detail: str) -> str:
    return f"- `{prefix}` {label}: {detail}"


def report_text(env_path: Path, app_url: str, out_path: Path) -> str:
    env = load_env(env_path)
    env_checks = evaluate_env_readiness(env)
    failed = [item for item in env_checks if item.status == "fail"]
    warnings = [item for item in env_checks if item.status == "warn"]
    passed = [item for item in env_checks if item.status == "pass"]
    restore = restore_drill_readiness(env, strict=True)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

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
    lines.extend(render_check_line(status, detail.split(":")[0].replace(" passed", "").replace(" failed", ""), detail) for status, detail in live_checks)

    lines.extend(
        [
            "",
            "## Manual-only checks still required",
            "",
            "- GitHub Security / Dependabot review in the GitHub web UI",
            "- Secret rotation metadata if any alert is real",
            "- Authenticated admin `/ops/readiness` screen review on the real production URL",
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
