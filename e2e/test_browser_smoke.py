from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
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


@pytest.fixture()
def server(tmp_path: Path) -> Iterator[str]:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "dev",
            "DB_PATH": str(tmp_path / "fleet.db"),
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


def _browser_contrast_failures(page: Page) -> list[str]:
    failures = page.evaluate(
        """
        () => {
          const root = document.documentElement;

          function parseColor(value) {
            const probe = document.createElement("span");
            probe.style.color = value;
            probe.style.position = "absolute";
            probe.style.pointerEvents = "none";
            probe.style.visibility = "hidden";
            document.body.appendChild(probe);
            const raw = getComputedStyle(probe).color;
            probe.remove();
            const match = raw.match(/rgba?\\(([^)]+)\\)/);
            if (!match) throw new Error(`Cannot parse color: ${value}`);
            const parts = match[1].split(",").map((part) => Number(part.trim()));
            return { r: parts[0], g: parts[1], b: parts[2], a: Number.isFinite(parts[3]) ? parts[3] : 1 };
          }

          function composite(top, bottom) {
            const alpha = top.a + bottom.a * (1 - top.a);
            return {
              r: (top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / alpha,
              g: (top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / alpha,
              b: (top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / alpha,
              a: alpha,
            };
          }

          function luminance(color) {
            const channels = [color.r, color.g, color.b].map((channel) => {
              const normalized = channel / 255;
              return normalized <= 0.03928
                ? normalized / 12.92
                : Math.pow((normalized + 0.055) / 1.055, 2.4);
            });
            return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
          }

          function ratio(foreground, background) {
            const fg = luminance(foreground);
            const bg = luminance(background);
            return (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05);
          }

          function themePairs(theme) {
            root.setAttribute("data-theme", theme);
            const styles = getComputedStyle(root);
            const token = (name) => styles.getPropertyValue(name).trim();
            const background = parseColor(token("--bg-bottom"));
            const surface = composite(parseColor(token("--surface")), background);
            const surfaceStrong = composite(parseColor(token("--surface-strong")), background);
            const warningSoft = composite(parseColor(token("--warning-soft")), background);
            const successSoft = composite(parseColor(token("--success-soft")), background);
            const dangerSoft = composite(parseColor(token("--danger-soft")), background);
            const infoSoft = composite(parseColor(token("--info-soft")), background);

            return [
              [`${theme} ink on translucent surface`, token("--ink"), surface, 4.5],
              [`${theme} muted on strong surface`, token("--muted"), surfaceStrong, 4.5],
              [`${theme} primary button`, "#ffffff", token("--brand"), 4.5],
              [`${theme} focus ring on surface`, token("--brand"), surfaceStrong, 3.0],
              [`${theme} pending status`, token("--warning"), warningSoft, 4.5],
              [`${theme} approved status`, token("--success"), successSoft, 4.5],
              [`${theme} rejected status`, token("--danger"), dangerSoft, 4.5],
              [`${theme} checked-out status`, token("--brand-strong"), infoSoft, 4.5],
            ];
          }

          const failures = [];
          for (const [name, foregroundValue, backgroundValue, minimum] of [
            ...themePairs("light"),
            ...themePairs("dark"),
          ]) {
            const actual = ratio(
              parseColor(foregroundValue),
              typeof backgroundValue === "string" ? parseColor(backgroundValue) : backgroundValue,
            );
            if (actual < minimum) {
              failures.push(`${name}: ${actual.toFixed(2)} < ${minimum}`);
            }
          }
          root.setAttribute("data-theme", "light");
          return failures;
        }
        """
    )
    assert isinstance(failures, list)
    return [str(item) for item in failures]


def _create_reservation_via_api(
    server: str,
    token: str,
    car_id: int,
    start: datetime,
    purpose: str,
    duration_hours: int = 1,
) -> dict:
    data = _api_json(
        server,
        "/reservations",
        "POST",
        token,
        {
            "car_id": car_id,
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=duration_hours)).isoformat(),
            "purpose": purpose,
        },
    )
    assert isinstance(data, dict)
    return data


def _seed_pending_reservation(server: str, car_index: int = 3) -> dict:
    admin_token = _api_login(server, "admin", "AdminPass123")
    employee_token = _api_login(server, "ivan", "IvanPass123")
    cars_response = _api_json(server, "/cars", token=admin_token)
    assert isinstance(cars_response, dict)
    start = (datetime.now().astimezone() + timedelta(days=1)).replace(
        hour=10 + car_index,
        minute=0,
        second=0,
        microsecond=0,
    )
    return _create_reservation_via_api(
        server,
        employee_token,
        cars_response["items"][car_index]["id"],
        start,
        f"E2E pending role smoke {car_index}",
    )


def test_public_orientation_surface(browser: Browser, server: str, artifact_dir: Path) -> None:
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    page = context.new_page()
    page.goto(f"{server}/", wait_until="domcontentloaded")
    expect(page.locator("#kpiPending .stat-card__value")).to_have_text("0", timeout=10_000)
    expect(page.locator("#kpiActive .stat-card__value")).to_have_text("0")
    expect(page.locator("#kpiAvailable .stat-card__value")).to_have_text("5")
    expect(page.locator("#calendarStudio")).to_be_visible()
    page.screenshot(path=artifact_dir / "public-mobile.png", full_page=True)

    page.goto(f"{server}/admin", wait_until="domcontentloaded")
    expect(page.locator("#kpiAvailable .stat-card__value")).to_have_text("5", timeout=10_000)
    expect(page.locator("#sessionPanel")).to_be_hidden()
    context.close()


def test_browser_computed_contrast_guard(browser: Browser, server: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        page = context.new_page()
        page.goto(f"{server}/", wait_until="domcontentloaded")
        expect(page.locator("#loginPanel")).to_be_visible(timeout=10_000)
        assert _browser_contrast_failures(page) == []
    finally:
        context.close()


def test_employee_quick_booking_surface(browser: Browser, server: str, artifact_dir: Path) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    _login(page, server, "/", "ivan", "IvanPass123")
    expect(page.locator("#quickBookBtn")).to_be_visible()
    expect(page.locator('[data-status="open"]')).to_have_attribute("aria-pressed", "true")
    page.locator("#quickBookBtn").click()
    expect(page.locator("#messageTitle")).to_contain_text("Бързата заявка", timeout=10_000)
    expect(page.locator("#reservationsTimeline .reservation-flow-card")).to_have_count(1)
    expect(page.locator("#guidanceCard")).to_be_hidden()
    assert _timeline_is_before_table(page)
    assert _element_is_before(page, "#reservationsDeck", "#calendarStudio")
    assert _element_is_before(page, "#reservationPanel", "#notificationDeck")
    page.screenshot(path=artifact_dir / "employee-desktop.png", full_page=True)
    context.close()


def test_employee_cannot_stay_on_admin_surface(browser: Browser, server: str) -> None:
    admin_token = _api_login(server, "admin", "AdminPass123")
    _api_json(
        server,
        "/users",
        "POST",
        admin_token,
        {
            "username": "guardemployee",
            "display_name": "Guard Employee",
            "password": "GuardEmployeePass123",
            "role": "employee",
        },
    )
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.goto(f"{server}/admin", wait_until="domcontentloaded")
    page.locator("#username").fill("guardemployee")
    page.locator("#password").fill("GuardEmployeePass123")
    expect(page.locator("#username")).to_have_value("guardemployee")
    page.locator("#loginBtn").click()
    expect(page).to_have_url(f"{server}/", timeout=10_000)
    expect(page.locator("body[data-surface='employee']")).to_be_attached()
    expect(page.locator("#sessionModePill")).to_contain_text("Служител", timeout=10_000)
    expect(page.locator("[data-operational-link]")).to_be_hidden()
    context.close()


def test_approver_decision_surface(browser: Browser, server: str, artifact_dir: Path) -> None:
    admin_token = _api_login(server, "admin", "AdminPass123")
    _api_json(
        server,
        "/users",
        "POST",
        admin_token,
        {
            "username": "approver",
            "display_name": "Approver Desk",
            "password": "ApproverPass123",
            "role": "fleet_approver",
        },
    )
    _seed_pending_reservation(server)

    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    _login(page, server, "/admin", "approver", "ApproverPass123")
    expect(page.locator("#decisionRail")).to_be_visible(timeout=10_000)
    expect(page.locator("#decisionRail")).to_contain_text("Одобри")
    expect(page.locator("#usersDeck")).to_be_hidden()
    expect(page.locator("#netfleetPanel")).to_be_hidden()
    expect(page.locator("#receptionRail")).to_be_hidden()
    page.screenshot(path=artifact_dir / "approver-desktop.png", full_page=True)
    context.close()


def test_admin_control_surface(browser: Browser, server: str, artifact_dir: Path) -> None:
    _seed_pending_reservation(server)

    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    _login(page, server, "/admin", "admin", "AdminPass123")
    expect(page.locator("#fleetPulse")).to_contain_text("Свеж GPS сигнал", timeout=10_000)
    expect(page.locator("#fleetPulse")).not_to_contain_text("GPS сигнали")
    expect(page.locator("#netfleetPanel")).to_be_visible()
    expect(page.locator("#netfleetApiKey")).to_have_attribute("type", "password")
    expect(page.locator("#decisionRail")).to_be_visible()
    expect(page.locator("#reservationsTimeline .reservation-flow-card")).to_have_count(1)
    expect(page.locator("#guidanceCard")).to_be_hidden()
    assert _timeline_is_before_table(page)
    page.screenshot(path=artifact_dir / "admin-desktop.png", full_page=True)
    context.close()


def test_employee_mobile_calendar_surface(browser: Browser, server: str, artifact_dir: Path) -> None:
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    page = context.new_page()
    _login(page, server, "/", "maria", "MariaPass123")
    button_box = page.locator("#quickBookBtn").bounding_box()
    panel_box = page.locator("#quickBookPanel").bounding_box()
    assert button_box and panel_box
    assert button_box["x"] >= panel_box["x"]
    assert button_box["x"] + button_box["width"] <= panel_box["x"] + panel_box["width"] + 1
    expect(page.locator(".mobile-day-card")).to_be_visible(timeout=10_000)
    expect(page.locator(".mobile-rail")).to_be_visible()
    expect(page.locator("#reservationsTimeline")).to_be_visible()
    page.screenshot(path=artifact_dir / "employee-mobile.png", full_page=True)
    context.close()


def test_reception_handoff_calendar_surface(browser: Browser, server: str, artifact_dir: Path) -> None:
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
