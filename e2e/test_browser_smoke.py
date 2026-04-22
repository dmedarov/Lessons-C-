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
            "LOGIN_RATE_LIMIT_ATTEMPTS": "100",
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


def _layout_density_failures(page: Page) -> list[str]:
    failures = page.evaluate(
        """
        () => {
          const failures = [];
          const tolerance = 2;
          const root = document.documentElement;
          const body = document.body;
          if (root.scrollWidth > window.innerWidth + tolerance) {
            failures.push(`document overflow: ${root.scrollWidth} > ${window.innerWidth}`);
          }
          if (body.scrollWidth > window.innerWidth + tolerance) {
            failures.push(`body overflow: ${body.scrollWidth} > ${window.innerWidth}`);
          }

          function visible(el) {
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return (
              style.display !== "none" &&
              style.visibility !== "hidden" &&
              !el.hidden &&
              rect.width > 0 &&
              rect.height > 0
            );
          }

          for (const el of document.querySelectorAll("button, a.btn, .chip")) {
            if (!visible(el)) continue;
            if (el.matches(".calendar-day")) continue;
            if (el.scrollWidth > el.clientWidth + tolerance) {
              failures.push(`control text overflow: ${el.textContent.trim().slice(0, 48)}`);
            }
            if (el.getBoundingClientRect().height < 40) {
              failures.push(`control target under 40px: ${el.textContent.trim().slice(0, 48)}`);
            }
          }

          const candidates = [...document.querySelectorAll([
            ".glass-card",
            ".summary-card",
            ".stat-card",
            ".reservation-flow-card",
            ".decision-card",
            ".fleet-pulse__item",
            ".pickup-location",
          ].join(","))].filter(visible);

          for (let i = 0; i < candidates.length; i += 1) {
            for (let j = i + 1; j < candidates.length; j += 1) {
              const a = candidates[i];
              const b = candidates[j];
              if (a.contains(b) || b.contains(a)) continue;
              const ar = a.getBoundingClientRect();
              const br = b.getBoundingClientRect();
              const xOverlap = Math.max(0, Math.min(ar.right, br.right) - Math.max(ar.left, br.left));
              const yOverlap = Math.max(0, Math.min(ar.bottom, br.bottom) - Math.max(ar.top, br.top));
              const overlapArea = xOverlap * yOverlap;
              if (overlapArea > 16) {
                failures.push(
                  `module overlap: ${a.id || a.className} / ${b.id || b.className}`
                );
              }
            }
          }

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


def _seed_reception_work(server: str) -> dict:
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
    return {
        "base_start": base_start,
        "approved_reservation": approved_reservation,
        "active_reservation": active_reservation,
    }


def test_public_orientation_surface(browser: Browser, server: str, artifact_dir: Path) -> None:
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    page = context.new_page()
    page.goto(f"{server}/", wait_until="domcontentloaded")
    expect(page.locator("#kpiPending .stat-card__value")).to_have_text("0", timeout=10_000)
    expect(page.locator("#kpiActive .stat-card__value")).to_have_text("0")
    expect(page.locator("#kpiAvailable .stat-card__value")).to_have_text("5")
    expect(page.locator("#calendarStudio")).to_be_visible()
    expect(page.locator("body")).not_to_contain_text("calendar.calmDayTitle")
    expect(page.locator("body")).not_to_contain_text("calendar.nextBusyDay")
    expect(page.locator("body")).not_to_contain_text("Текстът не е наличен")
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
    expect(page.locator("#requestOutcome")).to_contain_text("чака одобрение", timeout=10_000)
    expect(page.locator("#requestOutcome")).to_contain_text("Не е нужно да натискаш отново")
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
    expect(page.locator("#reservationPanel")).to_be_visible()
    expect(page.locator("[data-operational-link]")).to_be_hidden()
    page.goto(f"{server}/admin", wait_until="domcontentloaded")
    expect(page).to_have_url(f"{server}/", timeout=10_000)
    expect(page.locator("body[data-surface='employee']")).to_be_attached()
    expect(page.locator("#sessionModePill")).to_contain_text("Служител", timeout=10_000)
    expect(page.locator("#reservationPanel")).to_be_visible()
    context.close()


def test_operational_roles_login_to_admin_surface_first(browser: Browser, server: str) -> None:
    admin_token = _api_login(server, "admin", "AdminPass123")
    _api_json(
        server,
        "/users",
        "POST",
        admin_token,
        {
            "username": "firstapprover",
            "display_name": "First Approver",
            "password": "FirstApprover123",
            "role": "fleet_approver",
        },
    )
    _api_json(
        server,
        "/users",
        "POST",
        admin_token,
        {
            "username": "firstreception",
            "display_name": "First Reception",
            "password": "FirstReception123",
            "role": "fleet_reception",
        },
    )

    scenarios = [
        ("admin", "AdminPass123", "Администратор"),
        ("firstapprover", "FirstApprover123", "Одобряващ"),
        ("firstreception", "FirstReception123", "Рецепция ключове"),
    ]
    for username, password, role_label in scenarios:
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.goto(f"{server}/", wait_until="domcontentloaded")
        expect(page.locator("#loginPanel")).to_be_visible(timeout=10_000)
        page.locator("#username").fill(username)
        page.locator("#password").fill(password)
        with page.expect_response(lambda response: response.url.endswith("/auth/me"), timeout=10_000) as me_info:
            with page.expect_response(lambda response: response.url.endswith("/auth/login") and response.status == 200):
                page.locator("#loginBtn").click()
        me_response = me_info.value
        assert me_response.status == 200
        expect(page).to_have_url(f"{server}/admin", timeout=10_000)
        expect(page.locator("body[data-surface='admin']")).to_be_attached()
        expect(page.locator("#sessionModePill")).to_contain_text(role_label, timeout=10_000)
        expect(page.locator("#reservationsDeck")).to_be_visible()
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
    flow_checkbox = page.locator("#reservationsTimeline [data-reservation-select]").first
    table_checkbox = page.locator("#reservationsTableBody [data-reservation-select]").first
    expect(flow_checkbox).to_be_visible()
    flow_checkbox.focus()
    page.keyboard.press("Space")
    expect(flow_checkbox).to_be_checked()
    expect(table_checkbox).to_be_checked()
    expect(page.locator("#bulkActionBar")).to_be_visible()
    expect(page.locator("#bulkSelectedCount")).to_contain_text("1 избрани")
    expect(page.locator("#reservationsTimeline .reservation-flow-card.is-selected")).to_have_count(1)
    page.screenshot(path=artifact_dir / "approver-keyboard-bulk-selection.png", full_page=True)
    page.screenshot(path=artifact_dir / "approver-desktop.png", full_page=True)
    context.close()


def test_approver_reject_flow_updates_employee_view(browser: Browser, server: str, artifact_dir: Path) -> None:
    admin_token = _api_login(server, "admin", "AdminPass123")
    users = _api_json(server, "/users", token=admin_token)
    assert isinstance(users, list)
    ivan = next(user for user in users if user["username"] == "ivan")
    _api_json(
        server,
        f"/users/{ivan['id']}/contact",
        "PUT",
        admin_token,
        {"gsm_number": "+359889001122", "reason": "Approver flow GSM evidence"},
    )
    _api_json(
        server,
        "/users",
        "POST",
        admin_token,
        {
            "username": "rejectapprover",
            "display_name": "Reject Approver",
            "password": "RejectApprover123",
            "role": "fleet_approver",
        },
    )
    _seed_pending_reservation(server, car_index=2)

    approver_context = browser.new_context(viewport={"width": 1280, "height": 900})
    approver_page = approver_context.new_page()
    _login(approver_page, server, "/admin", "rejectapprover", "RejectApprover123")
    decision_card = approver_page.locator("#decisionRail .decision-card").filter(has_text="E2E pending role smoke 2")
    expect(decision_card).to_be_visible(timeout=10_000)
    expect(decision_card).to_contain_text("GSM: +359889001122")
    decision_card.locator('[data-reservation-action="reject"]').click()
    dialog = approver_page.locator("dialog[open]")
    expect(dialog.locator("textarea[name='reason']")).to_be_focused()
    dialog.get_by_role("button", name="Откажи").click()
    expect(dialog.locator("[data-dialog-error]")).to_contain_text("Добави причина", timeout=10_000)
    dialog.locator("textarea[name='reason']").fill("Нужна е друга кола за същия слот.")
    dialog.get_by_role("button", name="Откажи").click()
    expect(approver_page.locator("#messageTitle")).to_contain_text("Lifecycle е обновен", timeout=10_000)
    approver_page.screenshot(path=artifact_dir / "approver-reject-with-gsm.png", full_page=True)
    approver_context.close()

    employee_context = browser.new_context(viewport={"width": 1024, "height": 900})
    employee_page = employee_context.new_page()
    _login(employee_page, server, "/", "ivan", "IvanPass123")
    employee_page.locator('[data-status="all"]').click()
    expect(employee_page.locator("#reservationsTimeline")).to_contain_text("Отказана", timeout=10_000)
    expect(employee_page.locator("#reservationsTimeline")).to_contain_text("E2E pending role smoke 2")
    employee_page.screenshot(path=artifact_dir / "employee-rejected-request.png", full_page=True)
    employee_context.close()


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


def test_admin_user_contact_correction_flow(browser: Browser, server: str, artifact_dir: Path) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    _login(page, server, "/admin", "admin", "AdminPass123")

    users_deck = page.locator("#usersDeck")
    expect(users_deck).to_be_visible(timeout=10_000)
    maria_card = page.locator(".user-card").filter(has_text="Maria Petrova")
    expect(maria_card).to_be_visible()
    maria_card.get_by_role("button", name="Контакт").click()

    dialog = page.locator("dialog[open]")
    expect(dialog).to_contain_text("Контакт за Maria Petrova")
    dialog.locator('input[name="email"]').fill("maria.production@example.com")
    dialog.locator('input[name="gsmNumber"]').fill("+359881112233")
    dialog.locator('textarea[name="reason"]').fill("Production contact verification")
    dialog.get_by_role("button", name="Запази").click()

    expect(page.locator("#message")).to_contain_text("Контактът е обновен", timeout=10_000)
    maria_card = page.locator(".user-card").filter(has_text="Maria Petrova")
    expect(maria_card).to_contain_text("maria.production@example.com")
    expect(maria_card).to_contain_text("GSM номер")
    expect(maria_card).to_contain_text("+359881112233")
    maria_card.get_by_role("button", name="Покажи audit").click()
    expect(maria_card).to_contain_text("Контакт обновен", timeout=10_000)
    page.screenshot(path=artifact_dir / "admin-contact-correction.png", full_page=True)
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
    _seed_reception_work(server)

    reception = browser.new_context(viewport={"width": 1440, "height": 1000})
    reception_page = reception.new_page()
    _login(reception_page, server, "/admin", "reception", "ReceptionPass123")
    expect(reception_page.locator("#dayTimeline")).to_contain_text("Следващият запис", timeout=10_000)
    reception_page.get_by_role("button", name="Виж този ден").click()
    expect(reception_page.locator('[data-status="approved"]')).to_have_attribute("aria-pressed", "true")
    expect(reception_page.locator("#receptionRail")).to_be_visible(timeout=10_000)
    expect(reception_page.locator("#receptionRail")).to_contain_text("Започни курс")
    expect(reception_page.locator("#receptionRail")).to_contain_text("Върни автомобил")
    expect(reception_page.locator("#receptionRail")).to_contain_text("Къде да вземеш колата", timeout=10_000)
    expect(reception_page.locator("#receptionRail")).to_contain_text("GPS локацията още не е включена")
    expect(reception_page.locator("#dayTimeline")).to_contain_text("Одобрена", timeout=10_000)
    expect(reception_page.locator("#dayTimeline")).to_contain_text("Активен курс")
    expect(reception_page.locator("#usersDeck")).to_be_hidden()
    board_box = reception_page.locator(".calendar-board").bounding_box()
    panel_box = reception_page.locator(".day-panel").bounding_box()
    assert board_box and panel_box
    assert panel_box["y"] > board_box["y"] + board_box["height"] - 1
    reception_page.screenshot(path=artifact_dir / "reception-desktop.png", full_page=True)
    reception.close()


def test_reception_start_and_return_flow(browser: Browser, server: str, artifact_dir: Path) -> None:
    _seed_reception_work(server)

    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    _login(page, server, "/admin", "reception", "ReceptionPass123")
    approved_card = page.locator("#receptionRail .reception-card").filter(has_text="Reception approved calendar smoke")
    expect(approved_card).to_be_visible(timeout=10_000)
    expect(approved_card).to_contain_text("Къде да вземеш колата")
    approved_card.locator('[data-reservation-action="start"]').click()
    expect(page.locator("#messageTitle")).to_contain_text("Lifecycle е обновен", timeout=10_000)

    page.locator('[data-status="checked_out"]').click()
    active_card = page.locator("#receptionRail .reception-card").filter(has_text="Reception approved calendar smoke")
    expect(active_card).to_be_visible(timeout=10_000)
    expect(active_card).to_contain_text("Активен курс")
    active_card.locator('[data-reservation-action="return"]').click()
    dialog = page.locator("dialog[open]")
    expect(dialog).to_contain_text("Потвърди връщането")
    dialog.get_by_role("button", name="Върни автомобил").click()
    expect(page.locator("#messageTitle")).to_contain_text("Lifecycle е обновен", timeout=10_000)

    page.locator('[data-status="returned"]').click()
    expect(page.locator("#reservationsTimeline")).to_contain_text("Върната", timeout=10_000)
    expect(page.locator("#reservationsTimeline")).to_contain_text("Reception approved calendar smoke")
    page.screenshot(path=artifact_dir / "reception-start-return-flow.png", full_page=True)
    context.close()


def test_reception_overdue_return_next_signal(browser: Browser, server: str, artifact_dir: Path) -> None:
    seed = _seed_reception_work(server)
    _seed_pending_reservation(server, car_index=0)
    fixed_now = int((seed["base_start"] + timedelta(hours=4)).timestamp() * 1000)

    def overdue_context():
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.add_init_script(
            script=f"""
            (() => {{
              const fixedNow = {fixed_now};
              const RealDate = Date;
              class FleetFlowMockDate extends RealDate {{
                constructor(...args) {{
                  if (args.length === 0) return new RealDate(fixedNow);
                  return new RealDate(...args);
                }}
                static now() {{ return fixedNow; }}
              }}
              FleetFlowMockDate.UTC = RealDate.UTC;
              FleetFlowMockDate.parse = RealDate.parse;
              FleetFlowMockDate.prototype = RealDate.prototype;
              window.Date = FleetFlowMockDate;
            }})();
            """
        )
        return context

    admin_context = overdue_context()
    admin_page = admin_context.new_page()
    _login(admin_page, server, "/admin", "admin", "AdminPass123")
    expect(admin_page.locator("#nextSignalTitle")).to_contain_text("чака връщане", timeout=10_000)
    expect(admin_page.locator("#nextSignalCopy")).to_contain_text("Срокът е изтекъл")
    admin_page.screenshot(path=artifact_dir / "admin-overdue-return-signal.png", full_page=True)
    admin_context.close()

    context = overdue_context()
    page = context.new_page()
    _login(page, server, "/admin", "reception", "ReceptionPass123")
    expect(page.locator("#nextSignalTitle")).to_contain_text("чака връщане", timeout=10_000)
    expect(page.locator("#nextSignalCopy")).to_contain_text("Срокът е изтекъл")
    expect(page.locator("#receptionRail")).to_contain_text("просрочено от")
    page.screenshot(path=artifact_dir / "reception-overdue-return-signal.png", full_page=True)
    context.close()


def test_responsive_density_evidence_across_roles(browser: Browser, server: str, artifact_dir: Path) -> None:
    admin_token = _api_login(server, "admin", "AdminPass123")
    _api_json(
        server,
        "/users",
        "POST",
        admin_token,
        {
            "username": "densityapprover",
            "display_name": "Density Approver",
            "password": "DensityApprover123",
            "role": "fleet_approver",
        },
    )
    _seed_pending_reservation(server, car_index=2)
    _seed_reception_work(server)

    scenarios = [
        ("public", "/", None, None, 390),
        ("public", "/", None, None, 768),
        ("employee", "/", "ivan", "IvanPass123", 390),
        ("approver", "/admin", "densityapprover", "DensityApprover123", 768),
        ("reception", "/admin", "reception", "ReceptionPass123", 768),
        ("admin", "/admin", "admin", "AdminPass123", 1024),
        ("admin", "/admin", "admin", "AdminPass123", 1440),
    ]

    for name, path, username, password, width in scenarios:
        context = browser.new_context(viewport={"width": width, "height": 940}, is_mobile=width <= 430)
        page = context.new_page()
        if username and password:
            _login(page, server, path, username, password)
        else:
            page.goto(f"{server}{path}", wait_until="domcontentloaded")
            expect(page.locator("#loginPanel")).to_be_visible(timeout=10_000)
        page.wait_for_timeout(350)
        failures = _layout_density_failures(page)
        page.screenshot(path=artifact_dir / f"density-{name}-{width}.png", full_page=False)
        context.close()
        assert failures == [], f"{name} {width}px: {failures}"


def test_destructive_action_keyboard_recovery(browser: Browser, server: str, artifact_dir: Path) -> None:
    admin_token = _api_login(server, "admin", "AdminPass123")
    _api_json(
        server,
        "/users",
        "POST",
        admin_token,
        {
            "username": "destructiveapprover",
            "display_name": "Destructive Approver",
            "password": "DestructiveApprover123",
            "role": "fleet_approver",
        },
    )
    _seed_pending_reservation(server, car_index=1)
    _seed_reception_work(server)

    approver_context = browser.new_context(viewport={"width": 1024, "height": 900})
    approver_page = approver_context.new_page()
    _login(approver_page, server, "/admin", "destructiveapprover", "DestructiveApprover123")
    reject_button = approver_page.locator('#decisionRail [data-reservation-action="reject"]').first
    expect(reject_button).to_be_visible(timeout=10_000)
    reject_button.focus()
    approver_page.keyboard.press("Enter")
    dialog = approver_page.locator("dialog[open]")
    expect(dialog).to_be_visible()
    expect(dialog.locator("textarea[name='reason']")).to_be_focused()
    dialog.locator("button.btn--primary").press("Enter")
    expect(dialog.locator("[data-dialog-error]")).to_contain_text("Добави причина", timeout=10_000)
    expect(dialog.locator("textarea[name='reason']")).to_have_attribute("aria-invalid", "true")
    expect(dialog.locator("textarea[name='reason']")).to_be_focused()
    approver_page.screenshot(path=artifact_dir / "destructive-reject-recovery.png", full_page=True)
    dialog.locator("textarea[name='reason']").fill("Няма свободен автомобил за този прозорец.")
    dialog.locator("button.btn--primary").press("Enter")
    expect(approver_page.locator("#messageTitle")).to_contain_text("Lifecycle е обновен", timeout=10_000)
    approver_context.close()

    reception_context = browser.new_context(viewport={"width": 1024, "height": 900})
    reception_page = reception_context.new_page()
    _login(reception_page, server, "/admin", "reception", "ReceptionPass123")
    return_button = reception_page.locator('#receptionRail [data-reservation-action="return"]').first
    expect(return_button).to_be_visible(timeout=10_000)
    return_button.focus()
    reception_page.keyboard.press("Enter")
    return_dialog = reception_page.locator("dialog[open]")
    expect(return_dialog).to_be_visible()
    expect(return_dialog.locator("button.btn--primary")).to_be_focused()
    reception_page.screenshot(path=artifact_dir / "destructive-return-confirmation.png", full_page=True)
    reception_page.keyboard.press("Escape")
    expect(return_dialog).to_be_hidden()
    expect(return_button).to_be_focused()
    reception_context.close()


def test_admin_destructive_configuration_keyboard_recovery(
    browser: Browser, server: str, artifact_dir: Path
) -> None:
    admin_token = _api_login(server, "admin", "AdminPass123")
    candidate = _api_json(
        server,
        "/users",
        "POST",
        admin_token,
        {
            "username": "destructiveconfig",
            "display_name": "Destructive Config",
            "password": "DestructiveConfig123",
            "role": "employee",
        },
    )
    assert isinstance(candidate, dict)
    cars_response = _api_json(server, "/cars", token=admin_token)
    assert isinstance(cars_response, dict)
    cars = cars_response["items"]
    blackout_start = (datetime.now().astimezone() + timedelta(days=3)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    _api_json(
        server,
        f"/cars/{cars[0]['id']}/blackouts",
        "POST",
        admin_token,
        {
            "kind": "maintenance",
            "start_time": blackout_start.isoformat(),
            "end_time": (blackout_start + timedelta(hours=2)).isoformat(),
            "reason": "Keyboard recovery evidence",
        },
    )

    context = browser.new_context(viewport={"width": 1280, "height": 1000})
    page = context.new_page()
    _login(page, server, "/admin", "admin", "AdminPass123")

    deactivate_button = page.locator(
        f'[data-user-action="deactivate"][data-user-id="{candidate["id"]}"]'
    )
    expect(deactivate_button).to_be_visible(timeout=10_000)
    deactivate_button.focus()
    page.keyboard.press("Enter")
    deactivate_dialog = page.locator("dialog[open]")
    expect(deactivate_dialog).to_be_visible()
    expect(deactivate_dialog.locator("button.btn--primary")).to_be_focused()
    page.screenshot(path=artifact_dir / "destructive-user-deactivate-confirmation.png", full_page=True)
    page.keyboard.press("Escape")
    expect(deactivate_dialog).to_be_hidden()
    expect(deactivate_button).to_be_focused()

    role_button = page.locator(f'[data-user-role="{candidate["id"]}"]')
    role_button.focus()
    page.keyboard.press("Enter")
    role_dialog = page.locator("dialog[open]")
    expect(role_dialog).to_be_visible()
    expect(role_dialog.locator("select[name='role']")).to_be_focused()
    role_dialog.locator("select[name='role']").select_option("fleet_reception")
    role_dialog.locator("button.btn--primary").press("Enter")
    expect(role_dialog.locator("[data-dialog-error]")).to_contain_text("Добави причина", timeout=10_000)
    expect(role_dialog.locator("textarea[name='reason']")).to_have_attribute("aria-invalid", "true")
    expect(role_dialog.locator("textarea[name='reason']")).to_be_focused()
    page.screenshot(path=artifact_dir / "destructive-role-change-recovery.png", full_page=True)
    role_dialog.locator("textarea[name='reason']").fill("Роля рецепция за тест на ключове.")
    role_dialog.locator("button.btn--primary").press("Enter")
    expect(page.locator("#messageTitle")).to_contain_text("Ролята е обновена", timeout=10_000)

    page.locator("#handoffUserId").select_option(str(candidate["id"]))
    handoff_submit = page.locator('#handoffForm button[type="submit"]')
    handoff_submit.focus()
    page.keyboard.press("Enter")
    expect(page.locator("#handoffReason")).to_have_attribute("aria-invalid", "true")
    expect(page.locator("#handoffReason")).to_be_focused()
    page.screenshot(path=artifact_dir / "destructive-handoff-recovery.png", full_page=True)
    page.locator("#handoffReason").fill("Проверка на admin continuity без реално прехвърляне.")
    handoff_submit.focus()
    page.keyboard.press("Enter")
    handoff_dialog = page.locator("dialog[open]")
    expect(handoff_dialog).to_be_visible()
    expect(handoff_dialog.locator("button.btn--primary")).to_be_focused()
    page.screenshot(path=artifact_dir / "destructive-handoff-confirmation.png", full_page=True)
    page.keyboard.press("Escape")
    expect(handoff_dialog).to_be_hidden()
    expect(handoff_submit).to_be_focused()

    blackout_button = page.locator("[data-blackout-disable]").first
    expect(blackout_button).to_be_visible(timeout=10_000)
    blackout_button.focus()
    page.keyboard.press("Enter")
    blackout_dialog = page.locator("dialog[open]")
    expect(blackout_dialog).to_be_visible()
    expect(blackout_dialog.locator("button.btn--primary")).to_be_focused()
    page.screenshot(path=artifact_dir / "destructive-blackout-deactivate-confirmation.png", full_page=True)
    page.keyboard.press("Escape")
    expect(blackout_dialog).to_be_hidden()
    expect(blackout_button).to_be_focused()
    context.close()
