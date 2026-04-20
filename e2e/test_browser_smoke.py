from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

import pytest

playwright_sync = pytest.importorskip(
    "playwright.sync_api",
    reason="Install browser deps with `python -m pip install -r requirements-dev.txt && python -m playwright install chromium`.",
)
from playwright.sync_api import Browser, Error as PlaywrightError, Page, expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + 20
    last_error: Exception | None = None
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            pytest.fail(f"e2e server exited early with {process.returncode}\n{output}")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001 - surface startup diagnostics below.
            last_error = exc
        time.sleep(0.25)
    output = process.stdout.read() if process.stdout else ""
    pytest.fail(f"e2e server did not become healthy: {last_error}\n{output}")


@pytest.fixture(scope="session")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "dev",
            "DB_PATH": str(tmp_path_factory.mktemp("fleetflow-e2e") / "fleet.db"),
            "DEV_SEED_DEMO_DATA": "true",
            "SECRET_KEY": "fleetflow-e2e-secret-key",
            "TOKEN_TTL_SECONDS": "3600",
            "LOGIN_RATE_LIMIT_ATTEMPTS": "20",
        }
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_health(base_url, process)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except PlaywrightError as exc:
            pytest.skip(f"Chromium is not installed for Playwright: {exc}")
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture()
def artifact_dir(tmp_path: Path) -> Path:
    directory = Path(os.getenv("E2E_ARTIFACT_DIR", tmp_path / "screenshots"))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _login(page: Page, base_url: str, path: str, username: str, password: str) -> None:
    page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
    page.locator("#username").fill(username)
    page.locator("#password").fill(password)
    page.locator("#loginBtn").click()
    expect(page.locator("#sessionPanel")).to_be_visible(timeout=10_000)
    expect(page.locator("#summaryDeck")).to_be_visible()


def _api_json(base_url: str, path: str, method: str = "GET", token: str | None = None, payload: dict | None = None) -> dict | list:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _api_login(base_url: str, username: str, password: str) -> str:
    data = _api_json(base_url, "/auth/login", "POST", payload={"username": username, "password": password})
    assert isinstance(data, dict)
    return str(data["access_token"])


def _timeline_is_before_table(page: Page) -> bool:
    return bool(
        page.evaluate(
            """
            () => {
              const timeline = document.querySelector("#reservationsTimeline");
              const table = document.querySelector("#reservationsDeck .table-wrap");
              return Boolean(
                timeline &&
                table &&
                (timeline.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING)
              );
            }
            """
        )
    )


def _element_is_before(page: Page, first_selector: str, second_selector: str) -> bool:
    return bool(
        page.evaluate(
            """
            ([firstSelector, secondSelector]) => {
              const first = document.querySelector(firstSelector);
              const second = document.querySelector(secondSelector);
              return Boolean(
                first &&
                second &&
                (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING)
              );
            }
            """,
            [first_selector, second_selector],
        )
    )


def test_premium_employee_admin_and_mobile_surfaces(
    browser: Browser,
    server: str,
    artifact_dir: Path,
) -> None:
    prelogin = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    prelogin_page = prelogin.new_page()
    prelogin_page.goto(f"{server}/", wait_until="domcontentloaded")
    expect(prelogin_page.locator("#kpiPending .stat-card__value")).to_have_text("0", timeout=10_000)
    expect(prelogin_page.locator("#kpiActive .stat-card__value")).to_have_text("0")
    expect(prelogin_page.locator("#kpiAvailable .stat-card__value")).to_have_text("5")
    prelogin_page.goto(f"{server}/admin", wait_until="domcontentloaded")
    expect(prelogin_page.locator("#kpiAvailable .stat-card__value")).to_have_text("5", timeout=10_000)
    prelogin.close()

    employee = browser.new_context(viewport={"width": 1440, "height": 1000})
    employee_page = employee.new_page()
    _login(employee_page, server, "/", "ivan", "IvanPass123")
    expect(employee_page.locator("#quickBookBtn")).to_be_visible()
    expect(employee_page.locator('[data-status="open"]')).to_have_attribute("aria-pressed", "true")
    employee_page.locator("#quickBookBtn").click()
    expect(employee_page.locator("#messageTitle")).to_contain_text("Бързата заявка", timeout=10_000)
    expect(employee_page.locator("#reservationsTimeline .reservation-flow-card")).to_have_count(1)
    expect(employee_page.locator("#guidanceCard")).to_be_hidden()
    assert _timeline_is_before_table(employee_page)
    assert _element_is_before(employee_page, "#reservationsDeck", "#calendarStudio")
    assert _element_is_before(employee_page, "#reservationPanel", "#notificationDeck")
    employee_page.screenshot(path=artifact_dir / "employee-desktop.png", full_page=True)
    employee.close()

    admin = browser.new_context(viewport={"width": 1440, "height": 1000})
    admin_page = admin.new_page()
    _login(admin_page, server, "/admin", "admin", "AdminPass123")
    expect(admin_page.locator("#fleetPulse")).to_contain_text("Коли с GPS позиция", timeout=10_000)
    expect(admin_page.locator("#fleetPulse")).not_to_contain_text("GPS сигнали")
    expect(admin_page.locator("#netfleetPanel")).to_be_visible()
    expect(admin_page.locator("#netfleetApiKey")).to_have_attribute("type", "password")
    expect(admin_page.locator("#decisionRail")).to_be_visible()
    expect(admin_page.locator("#reservationsTimeline .reservation-flow-card")).to_have_count(1)
    expect(admin_page.locator("#guidanceCard")).to_be_hidden()
    assert _timeline_is_before_table(admin_page)
    admin_page.screenshot(path=artifact_dir / "admin-desktop.png", full_page=True)
    admin.close()

    mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    mobile_page = mobile.new_page()
    _login(mobile_page, server, "/", "maria", "MariaPass123")
    button_box = mobile_page.locator("#quickBookBtn").bounding_box()
    panel_box = mobile_page.locator("#quickBookPanel").bounding_box()
    assert button_box and panel_box
    assert button_box["x"] >= panel_box["x"]
    assert button_box["x"] + button_box["width"] <= panel_box["x"] + panel_box["width"] + 1
    expect(mobile_page.locator(".mobile-day-card")).to_be_visible(timeout=10_000)
    expect(mobile_page.locator(".mobile-rail")).to_be_visible()
    expect(mobile_page.locator("#reservationsTimeline")).to_be_visible()
    mobile_page.screenshot(path=artifact_dir / "employee-mobile.png", full_page=True)
    mobile.close()

    admin_token = _api_login(server, "admin", "AdminPass123")
    ivan_token = _api_login(server, "ivan", "IvanPass123")
    maria_token = _api_login(server, "maria", "MariaPass123")
    _api_json(
        server,
        "/users",
        "POST",
        admin_token,
        {
            "username": "reception",
            "display_name": "Reception Desk",
            "password": "ReceptionPass123",
            "role": "fleet_reception",
        },
    )
    reception_token = _api_login(server, "reception", "ReceptionPass123")
    cars_response = _api_json(server, "/cars", token=admin_token)
    assert isinstance(cars_response, dict)
    cars = cars_response["items"]
    base_start = (datetime.now().astimezone() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

    approved_reservation = _api_json(
        server,
        "/reservations",
        "POST",
        ivan_token,
        {
            "car_id": cars[3]["id"],
            "start_time": base_start.isoformat(),
            "end_time": (base_start + timedelta(hours=1)).isoformat(),
            "purpose": "Reception approved calendar smoke",
        },
    )
    active_reservation = _api_json(
        server,
        "/reservations",
        "POST",
        maria_token,
        {
            "car_id": cars[4]["id"],
            "start_time": (base_start + timedelta(hours=2)).isoformat(),
            "end_time": (base_start + timedelta(hours=3)).isoformat(),
            "purpose": "Reception active calendar smoke",
        },
    )
    assert isinstance(approved_reservation, dict)
    assert isinstance(active_reservation, dict)
    _api_json(server, f"/reservations/{approved_reservation['id']}/approve", "POST", admin_token, {})
    _api_json(server, f"/reservations/{active_reservation['id']}/approve", "POST", admin_token, {})
    _api_json(server, f"/reservations/{active_reservation['id']}/start", "POST", reception_token, {"note": "Keys handed over"})

    reception = browser.new_context(viewport={"width": 1440, "height": 1000})
    reception_page = reception.new_page()
    _login(reception_page, server, "/admin", "reception", "ReceptionPass123")
    reception_page.evaluate("dateKey => setSelectedDate(dateKey)", base_start.date().isoformat())
    expect(reception_page.locator('[data-status="approved"]')).to_have_attribute("aria-pressed", "true")
    expect(reception_page.locator("#receptionRail")).to_be_visible(timeout=10_000)
    expect(reception_page.locator("#receptionRail")).to_contain_text("Започни курс")
    expect(reception_page.locator("#receptionRail")).to_contain_text("Върни автомобил")
    expect(reception_page.locator("#dayTimeline")).to_contain_text("Одобрена", timeout=10_000)
    expect(reception_page.locator("#dayTimeline")).to_contain_text("Активен курс")
    expect(reception_page.locator("#usersDeck")).to_be_hidden()
    reception_page.screenshot(path=artifact_dir / "reception-desktop.png", full_page=True)
    reception.close()
