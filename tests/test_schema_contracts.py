from __future__ import annotations

import re
import sqlite3
from collections import Counter

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.routing import APIRoute

import app
import db


def _table_name(statement: str) -> str | None:
    match = re.search(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-z_]+)",
        statement,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _column_names(statement: str) -> set[str]:
    body_start = statement.find("(")
    body_end = statement.rfind(")")
    if body_start == -1 or body_end == -1 or body_end <= body_start:
        return set()

    columns: set[str] = set()
    for raw_line in statement[body_start + 1 : body_end].splitlines():
        line = raw_line.strip().rstrip(",")
        if not line:
            continue
        first_token = line.split(maxsplit=1)[0].strip('"')
        if first_token.upper().split("(", 1)[0] in {
            "CONSTRAINT",
            "PRIMARY",
            "FOREIGN",
            "CHECK",
            "UNIQUE",
        }:
            continue
        columns.add(first_token)
    return columns


def _table_contract(schema: list[str]) -> dict[str, set[str]]:
    return {
        table_name: _column_names(statement)
        for statement in schema
        if (table_name := _table_name(statement))
    }


def test_fastapi_routes_have_unique_method_path_pairs() -> None:
    pairs: list[tuple[str, str]] = []
    for route in app.app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            pairs.append((method, route.path))

    duplicates = {pair: count for pair, count in Counter(pairs).items() if count > 1}

    assert duplicates == {}


def test_sqlite_bootstrap_schema_executes_cleanly() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        for statement in db.SQLITE_SCHEMA:
            conn.execute(statement)

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
    finally:
        conn.close()

    assert {
        "users",
        "refresh_tokens",
        "cars",
        "reservations",
        "audit_log",
        "notifications",
        "notification_deliveries",
        "user_audit_log",
        "car_blackouts",
        "app_settings",
        "car_assignments",
    }.issubset(tables)


def test_sqlite_and_postgres_bootstrap_schema_contracts_match() -> None:
    sqlite_contract = _table_contract(db.SQLITE_SCHEMA)
    postgres_contract = _table_contract(db.POSTGRES_SCHEMA)

    assert sqlite_contract.keys() == postgres_contract.keys()
    assert sqlite_contract == postgres_contract


def test_runtime_upgrade_columns_exist_in_bootstrap_schemas() -> None:
    contract = _table_contract(db.SQLITE_SCHEMA)

    assert {"checked_out_at", "returned_at"}.issubset(contract["reservations"])
    assert {"email", "gsm_number"}.issubset(contract["users"])
    assert {"notes"}.issubset(contract["cars"])


def test_alembic_has_single_head_revision() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["20260420_0009"]
