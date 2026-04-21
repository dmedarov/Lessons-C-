from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def test_production_readiness_score_is_consistent_across_handoff_docs() -> None:
    docs = {
        "README.md": _read("README.md"),
        "ROADMAP_IMPROVEMENTS.md": _read("ROADMAP_IMPROVEMENTS.md"),
        "docs/PRODUCTION_USER_GUIDE.md": _read("docs/PRODUCTION_USER_GUIDE.md"),
        "docs/PRODUCTION_READINESS_ASSESSMENT.md": _read("docs/PRODUCTION_READINESS_ASSESSMENT.md"),
        "docs/EXECUTIVE_CODE_SUMMARY.md": _read("docs/EXECUTIVE_CODE_SUMMARY.md"),
    }

    missing = [path for path, content in docs.items() if "91/100" not in content]

    assert missing == []


def test_99_gate_is_external_evidence_gated() -> None:
    assessment = _read("docs/PRODUCTION_READINESS_ASSESSMENT.md")
    improvements = _read("ROADMAP_IMPROVEMENTS.md")

    for content in (assessment, improvements):
        assert "99/100 Premium Robust Production Gate" in content
        assert "Do not mark it done from local tests alone" in content or "не трябва да се отбелязва само от локални тестове" in content
        lowered = content.lower()
        for required in (
            "production",
            "cutover",
            "role",
            "netfleet",
            "security",
            "accessibility",
            "monitored",
        ):
            assert required in lowered


def test_executive_summary_records_current_quality_evidence() -> None:
    summary = _read("docs/EXECUTIVE_CODE_SUMMARY.md")

    assert "`make qa-premium` passed" in summary
    assert "`make smoke-live APP_URL=http://127.0.0.1:8001` passed" in summary
    assert "160 pytest cases" in summary
    assert "13 Playwright" in summary
    assert "91/100 за контролиран вътрешен pilot" in summary


def test_all_markdown_docs_explain_no_regression_discipline() -> None:
    docs = [
        "README.md",
        "ROADMAP.md",
        "ROADMAP_IMPROVEMENTS.md",
        "docs/PRODUCTION_USER_GUIDE.md",
        "docs/ROLE_USER_FLOWS.md",
        "docs/UI_UX_COMPLIANCE_AUDIT.md",
        "docs/EXECUTIVE_CODE_SUMMARY.md",
        "docs/PRODUCTION_READINESS_ASSESSMENT.md",
    ]

    missing = []
    for path in docs:
        content = _read(path).lower()
        if not (("silent" in content or "тих" in content) and ("noisy" in content or "шум" in content)):
            missing.append(path)

    assert missing == []


def test_github_actions_are_current_and_hardened_for_dependabot() -> None:
    workflows = {
        ".github/workflows/production-gates.yml": _read(".github/workflows/production-gates.yml"),
        ".github/workflows/tests.yml": _read(".github/workflows/tests.yml"),
    }
    combined = "\n".join(workflows.values())

    assert "actions/checkout@v4" not in combined
    assert "actions/setup-python@v5" not in combined
    assert "actions/checkout@v6" in combined
    assert "actions/setup-python@v6" in combined
    assert "persist-credentials: false" in workflows[".github/workflows/production-gates.yml"]


def test_dev_dependency_pins_include_dependabot_fixes() -> None:
    requirements_dev = _read("requirements-dev.txt")

    assert "pytest==9.0.3" in requirements_dev
    assert "filelock==3.20.3" in requirements_dev
    assert "requests==2.33.0" in requirements_dev
    assert "pytest==8.3.5" not in requirements_dev
    assert "filelock==3.19.1" not in requirements_dev
    assert "requests==2.32.5" not in requirements_dev


def test_executive_route_and_migration_stats_match_code() -> None:
    summary = _read("docs/EXECUTIVE_CODE_SUMMARY.md")
    route_declarations = 0
    for path in [ROOT / "app.py", *sorted((ROOT / "routers").glob("*.py"))]:
        route_declarations += len(
            re.findall(r"@(?:router|app)\.(?:get|post|put|delete|patch)\b", path.read_text())
        )
    migration_count = len(list((ROOT / "alembic" / "versions").glob("*.py")))

    assert f"| FastAPI route declarations | {route_declarations} |" in summary
    assert f"| Alembic migrations | {migration_count} |" in summary
