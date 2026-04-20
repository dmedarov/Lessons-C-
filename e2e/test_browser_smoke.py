from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
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
