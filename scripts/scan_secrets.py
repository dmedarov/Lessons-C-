from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


SENSITIVE_ENV_NAMES = {
    "AWS_SECRET_ACCESS_KEY",
    "AZURE_CLIENT_SECRET",
    "DATABASE_URL",
    "DOCKERHUB_TOKEN",
    "GCP_PRIVATE_KEY",
    "GITHUB_TOKEN",
    "IMAGE_REGISTRY_PASSWORD",
    "NETFLEET_API_KEY",
    "OPENSHIFT_TOKEN",
    "POSTGRES_PASSWORD",
    "SECRET_KEY",
    "SLACK_WEBHOOK_URL",
    "SMTP_PASSWORD",
    "TEAMS_WEBHOOK_URL",
}

ASSIGNMENT_RE = re.compile(
    r"""
    ^\s*(?:-\s*)?["']?
    (?P<name>
        AWS_SECRET_ACCESS_KEY|AZURE_CLIENT_SECRET|DATABASE_URL|DOCKERHUB_TOKEN|
        GCP_PRIVATE_KEY|GITHUB_TOKEN|IMAGE_REGISTRY_PASSWORD|NETFLEET_API_KEY|
        OPENSHIFT_TOKEN|POSTGRES_PASSWORD|SECRET_KEY|SLACK_WEBHOOK_URL|
        SMTP_PASSWORD|TEAMS_WEBHOOK_URL
    )
    ["']?\s*[:=]\s*
    (?P<value>[^#]+?)
    \s*$
    """,
    re.VERBOSE,
)

PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |ENCRYPTED |)PRIVATE KEY-----"
)

PLACEHOLDER_FRAGMENTS = (
    "adminpass",
    "carspass",
    "changeme",
    "dev",
    "dummy",
    "example",
    "fake",
    "fleetflow-dev-password",
    "ivanpass",
    "mariapass",
    "placeholder",
    "postgres-smoke-secret-key",
    "replace-with",
    "secret",
    "set_secret",
    "test",
    "token",
    "your-",
)

IGNORED_DIR_PARTS = {
    ".git",
    ".claude",
    ".venv",
    "backups",
    "data",
    "test-results",
}

ALL_REFS_FIXTURE_PATHS = {
    "tests/test_secret_scan.py",
}


@dataclass(frozen=True)
class SecretFinding:
    path: str
    line: int
    kind: str
    detail: str


def _clean_value(raw: str) -> str:
    return raw.strip().rstrip(",").strip("\"'")


def _is_template_expression(value: str) -> bool:
    return value.startswith("${") or value.startswith("${{")


def _looks_placeholder(value: str) -> bool:
    lowered = value.lower()
    if value == "":
        return True
    if _is_template_expression(value):
        return True
    if any(
        marker in value
        for marker in ("os.getenv", "settings.", "env.get", "f\"", "f'", "{password}")
    ):
        return True
    if lowered in {"none", "null", "true", "false"}:
        return True
    return any(fragment in lowered for fragment in PLACEHOLDER_FRAGMENTS)


def _database_password(value: str) -> str:
    try:
        parsed = urlparse(value)
    except ValueError:
        return ""
    return parsed.password or ""


def is_allowed_placeholder(name: str, raw_value: str) -> bool:
    value = _clean_value(raw_value)
    normalized = name.upper()
    if _looks_placeholder(value):
        return True
    if normalized == "DATABASE_URL":
        password = _database_password(value)
        return not password or _looks_placeholder(password)
    if normalized == "SECRET_KEY" and len(value) < 32:
        return True
    return False


def scan_text(path: str, text: str) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if PRIVATE_KEY_RE.search(line):
            findings.append(
                SecretFinding(path, index, "private_key", "private key block marker")
            )
        for match in ASSIGNMENT_RE.finditer(line):
            name = match.group("name").upper()
            value = match.group("value")
            if name not in SENSITIVE_ENV_NAMES:
                continue
            if is_allowed_placeholder(name, value):
                continue
            findings.append(
                SecretFinding(
                    path,
                    index,
                    "sensitive_assignment",
                    f"{name} appears to contain a real value",
                )
            )
    return findings


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def _git_bytes(args: list[str]) -> bytes:
    result = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def should_skip_path(path: Path) -> bool:
    return any(part in IGNORED_DIR_PARTS for part in path.parts)


def tracked_files() -> list[Path]:
    files = []
    for raw in _git(["ls-files"]).splitlines():
        path = Path(raw)
        if should_skip_path(path):
            continue
        files.append(path)
    return files


def scan_tracked_files(root: Path) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for path in tracked_files():
        full_path = root / path
        try:
            text = full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            continue
        findings.extend(scan_text(str(path), text))
    return findings


def scan_all_refs() -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    scanned_blobs: set[str] = set()
    for raw in _git(["rev-list", "--objects", "--all"]).splitlines():
        parts = raw.split(maxsplit=1)
        if len(parts) != 2:
            continue
        object_id, raw_path = parts
        if raw_path in ALL_REFS_FIXTURE_PATHS:
            continue
        path = Path(raw_path)
        if object_id in scanned_blobs or should_skip_path(path):
            continue
        object_type = _git(["cat-file", "-t", object_id]).strip()
        if object_type != "blob":
            continue
        scanned_blobs.add(object_id)
        data = _git_bytes(["cat-file", "-p", object_id])
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(f"{object_id[:12]}:{raw_path}", text))
    return findings


def format_findings(findings: list[SecretFinding]) -> str:
    lines = [
        "Potential committed secret values were found.",
        "Rotate exposed credentials first, then remove the value from git.",
        "",
    ]
    for finding in findings:
        lines.append(
            f"{finding.path}:{finding.line}: {finding.kind}: {finding.detail}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail if tracked files contain real-looking infrastructure secrets."
    )
    parser.add_argument(
        "--all-refs",
        action="store_true",
        help="scan all reachable git blobs, useful for incident response",
    )
    args = parser.parse_args()
    findings = scan_all_refs() if args.all_refs else scan_tracked_files(Path.cwd())
    if findings:
        print(format_findings(findings), file=sys.stderr)
        return 1
    print("Secret scan passed: no real-looking tracked secret values found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
