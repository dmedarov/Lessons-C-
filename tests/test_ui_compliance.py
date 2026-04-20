from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def test_notification_lists_are_polite_live_regions() -> None:
    for template in ("templates/index.html", "templates/admin.html"):
        html = _read(template)
        assert 'id="notificationsList" aria-live="polite" aria-relevant="additions text"' in html


def test_admin_calendar_glyph_buttons_have_accessible_names() -> None:
    html = _read("templates/admin.html")
    assert 'id="monthPrev" type="button" aria-label="Предишен месец"' in html
    assert 'id="monthNext" type="button" aria-label="Следващ месец"' in html


def test_dialog_helpers_restore_focus_to_trigger() -> None:
    app_js = _read("static/app.js")
    assert app_js.count("const returnFocusTo = document.activeElement instanceof HTMLElement") == 2
    assert app_js.count("returnFocusTo?.focus();") == 2


def test_dialog_helpers_expose_modal_names_and_descriptions() -> None:
    app_js = _read("static/app.js")
    assert app_js.count('dialog.setAttribute("aria-labelledby", titleId);') == 2
    assert app_js.count('dialog.setAttribute("aria-describedby", descriptionId);') == 2
    assert app_js.count('dialog.setAttribute("aria-modal", "true");') == 2
    assert app_js.count("copy.id = descriptionId;") == 2
    assert 'role="alert" aria-live="polite"' in app_js


def test_field_errors_are_programmatically_associated() -> None:
    app_js = _read("static/app.js")
    assert 'inputNode.setAttribute("aria-invalid", "true");' in app_js
    assert 'inputNode.setAttribute("aria-describedby", `${id}Error`);' in app_js
    assert 'inputNode.removeAttribute("aria-describedby");' in app_js


def test_mobile_rail_respects_safe_area() -> None:
    styles = _read("static/styles.css")
    assert "padding-bottom: calc(88px + env(safe-area-inset-bottom));" in styles
    assert "bottom: max(8px, env(safe-area-inset-bottom));" in styles


def test_message_alerts_use_theme_classes_not_inline_colors() -> None:
    app_js = _read("static/app.js")
    styles = _read("static/styles.css")
    assert 'els.message.classList.add(type === "success" ? "alert-strip--success" : "alert-strip--error");' in app_js
    assert "els.message.style.borderColor" not in app_js
    assert "els.message.style.background" not in app_js
    assert "els.message.style.color" not in app_js
    assert ".alert-strip--success" in styles
    assert ".alert-strip--error" in styles


def test_ui_dates_use_day_month_year_and_24h_time() -> None:
    app_js = _read("static/app.js")
    assert "dateStyle" not in app_js
    assert "timeStyle" not in app_js
    assert "hour12" not in app_js
    assert 'return `${day}.${month}.${year}, ${hours}:${minutes}`;' in app_js
    assert 'return `${weekday}, ${formatDateTime(date).split(",")[0]}`;' in app_js


def test_reject_dialogs_require_reason_and_mark_invalid_field() -> None:
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert app_js.count('textarea name="reason" rows="3" required') == 3
    assert app_js.count('fieldName: "reason"') == 3
    assert 'targetField.setAttribute("aria-invalid", "true");' in app_js
    assert 'targetField.setAttribute("aria-describedby", errorId);' in app_js
    assert 'targetField.focus();' in app_js
    assert '"admin.rejectReasonRequired": "Добави причина за отказа, преди да продължиш."' in i18n_js
    assert 'textarea[aria-invalid="true"]' in styles


def test_dialog_validation_can_target_the_specific_invalid_field() -> None:
    app_js = _read("static/app.js")
    assert 'form.elements[error.fieldName] || fields[0]' in app_js
    assert 'fieldName: "newPassword"' in app_js
    assert 'fieldName: "startTime"' in app_js
    assert app_js.count('fieldName: "endTime"') == 2


def test_cancel_dialog_requires_reason_before_destructive_action() -> None:
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    assert "function cancelReservationDialog(id)" in app_js
    assert 'title: t("reservation.cancelTitle", { id })' in app_js
    assert 'readValue: (form) => ({ note: form.elements.reason.value.trim() })' in app_js
    assert 'reservation.cancelReasonRequired' in app_js
    assert 'payload = await cancelReservationDialog(id);' in app_js
    assert '"reservation.cancelReasonRequired": "Добави причина за отмяната, преди да продължиш."' in i18n_js


def test_intent_driven_summary_exposes_one_primary_next_action() -> None:
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    for template in ("templates/index.html", "templates/admin.html"):
        html = _read(template)
        assert 'id="nextSignalActions" aria-label="Следващ ход"' in html
    assert "function setIntentActions(actions = [])" in app_js
    assert 'data-primary-intent="true"' in app_js
    assert 'name: "review-pending", labelKey: "intent.action.reviewPending", primary: true' in app_js
    assert 'name: "book-now", labelKey: "intent.action.bookNow", primary: true' in app_js
    assert 'name: "focus-reservation", labelKey: "intent.action.viewTrip", primary: true' in app_js
    assert "await quickBookReservation();" in app_js
    assert 'name: "reservation-transition"' not in app_js
    assert "function handleIntentAction(button)" in app_js
    assert "function focusReservationRow(id, action = null)" in app_js
    assert '"intent.employeeFreeTitle": "Свободен режим"' in i18n_js
    assert ".summary-card__actions .btn" in styles
    assert "min-height: 44px;" in styles


def test_one_tap_booking_is_available_without_form_scanning() -> None:
    html = _read("templates/index.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert 'id="quickBookPanel"' in html
    assert 'id="quickBookBtn"' in html
    assert html.index('id="quickBookPanel"') < html.index('id="reservationForm"')
    assert "function quickBookReservation()" in app_js
    assert 'apiFetch("/reservations/quick-book"' in app_js
    assert "toggleHidden(els.quickBookPanel, !authenticated || operationalMode);" in app_js
    assert '"quickBook.createdTitle": "Бързата заявка е подадена"' in i18n_js
    assert ".quick-book .btn" in styles
    assert "overflow-wrap: anywhere;" in styles


def test_smart_prefill_keeps_manual_booking_predictive() -> None:
    html = _read("templates/index.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert 'id="smartPrefillPanel"' in html
    assert 'id="smartPrefillBtn"' in html
    assert html.index('id="smartPrefillPanel"') < html.index('id="reservationForm"')
    assert "function loadReservationPreferences()" in app_js
    assert 'apiFetch("/reservations/preferences"' in app_js
    assert "function applySmartPrefill()" in app_js
    assert "function nextPreferredSlot(hour, durationMinutes)" in app_js
    assert "toggleHidden(els.smartPrefillPanel, !authenticated || operationalMode || !state.reservationPreferences?.available);" in app_js
    assert '"smartPrefill.hint": "Обичайно: {car}, около {hour}:00, за {duration} мин."' in i18n_js
    assert ".smart-prefill .action-btn" in styles


def test_status_bar_reports_free_cars_not_only_active_cars() -> None:
    app_js = _read("static/app.js")
    for template in ("templates/index.html", "templates/admin.html"):
        html = _read(template)
        assert '<span class="stat-card__label">Свободни коли</span>' in html
    assert "Math.max(activeCars - activeTrips, 0)" in app_js


def test_public_overview_feeds_pre_login_status_bar() -> None:
    app_js = _read("static/app.js")
    assert "publicOverview: null" in app_js
    assert "function loadPublicOverview()" in app_js
    assert 'apiFetch("/public/overview")' in app_js
    assert "const publicOverview = !state.token ? state.publicOverview : null;" in app_js
    assert "publicOverview?.pending_requests" in app_js
    assert "publicOverview?.active_trips" in app_js
    assert "publicOverview?.available_cars" in app_js
    assert 'kpiAvailable.querySelector(".stat-card__value").textContent = availableCars;' in app_js


def test_public_calendar_feeds_pre_login_calendar_without_private_details() -> None:
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    assert "publicCalendar: []" in app_js
    assert "function loadPublicCalendar()" in app_js
    assert 'apiFetch(`/public/calendar?${publicCalendarParams().toString()}`)' in app_js
    assert "if (!state.token) return state.publicCalendar;" in app_js
    assert "const calendarItems = calendarSourceItems();" in app_js
    assert "const label = item.plate_number || (car ? car.plate_number" in app_js
    assert "calendar.publicContext" in app_js
    assert '"calendar.publicDetails": "Влез, за да видиш заявител, цел и действия."' in i18n_js


def test_current_trip_hero_promotes_active_or_next_trip() -> None:
    html = _read("templates/index.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert 'id="currentTripHero" aria-labelledby="currentTripTitle"' in html
    assert "function currentTripCandidate()" in app_js
    assert "function renderCurrentTripHero()" in app_js
    assert 'data-trip-focus-action="true"' in app_js
    assert 'data-intent-action="focus-reservation"' in app_js
    assert 'primaryAction = active ? "return" : "start"' not in app_js
    assert 'renderCurrentTripHero();' in app_js
    assert '"trip.hero.activeEyebrow": "Твоята кола"' in i18n_js
    assert "рецепция; там отбелязват старта" in i18n_js
    assert "рецепция приключва lifecycle-а" in i18n_js
    assert ".current-trip-hero" in styles
    assert ".current-trip-hero__actions .btn" in styles


def test_employee_requests_are_prioritized_before_calendar_and_inbox() -> None:
    html = _read("templates/index.html")
    app_js = _read("static/app.js")

    assert 'status: surface === "admin" ? "pending" : "open"' in app_js
    assert 'href="#reservationsDeck">Към основното съдържание' in html
    assert html.index('href="#reservationsDeck">Курсове') < html.index('href="#calendarStudio">Календар')
    assert html.index('href="#reservationsDeck">Моите заявки') < html.index('href="#reservationPanel">Нова заявка')
    assert html.index('id="reservationPanel"') < html.index('id="notificationDeck"')
    assert html.index('id="reservationsDeck"') < html.index('id="calendarStudio"')
    assert html.index('id="calendarStudio"') < html.index('id="fleetDeck"')
    assert 'data-status="open" aria-pressed="true">Текущи' in html
    assert 'guidanceCard: document.getElementById("guidanceCard")' in app_js
    assert "toggleHidden(els.guidanceCard, authenticated);" in app_js
    assert 'state.status !== "all" && state.status !== "open"' in app_js
    assert 'data.items.filter((item) => !["returned", "rejected", "cancelled"].includes(item.status))' in app_js


def test_read_notifications_are_hidden_from_calm_default_inbox() -> None:
    app_js = _read("static/app.js")

    assert "const visibleNotifications = state.notifications.filter((item) => !item.read_at);" in app_js
    assert "const hiddenReadCount = state.notifications.length - visibleNotifications.length;" in app_js
    assert "Прочетените са прибрани, за да не стоят като шум." in app_js
    assert "прочетени уведомления са прибрани от този изглед." in app_js
    assert "visibleNotifications.forEach((item) => {" in app_js


def test_lifecycle_permissions_are_role_separated_in_ui() -> None:
    app_js = _read("static/app.js")
    router = _read("routers/reservations.py")

    assert "function canApproveReservations()" in app_js
    assert "function canManageTripHandoff()" in app_js
    assert 'if (item.status === "pending" && canApprove)' in app_js
    assert 'if (item.status === "approved" && canReception)' in app_js
    assert 'if (item.status === "checked_out" && canReception)' in app_js
    assert 'if (item.status === "approved" && (canAdmin || isOwner))' not in app_js
    assert 'if (item.status === "checked_out" && (canAdmin || isOwner))' not in app_js
    assert app_js.count('name: "reservation-transition"') == 0
    assert 'auth: AuthContext = Depends(require_employee),' in router
    assert 'auth: AuthContext = Depends(require_approver),' in router
    assert 'auth: AuthContext = Depends(require_reception),' in router


def test_role_specific_surfaces_hide_irrelevant_work() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")

    assert '<option value="fleet_approver">Одобряващ</option>' in html
    assert '<option value="fleet_reception">Рецепция ключове</option>' in html
    assert 'toggleHidden(els.reservationPanel, !authenticated || operationalMode);' in app_js
    assert 'toggleHidden(els.userCreatePanel, !authenticated || !fullAdmin || !adminSurface);' in app_js
    assert "state.status = defaultStatusForRole(user.role);" in app_js
    assert '"role.fleet_approver": "Одобряващ"' in i18n_js
    assert '"role.fleet_reception": "Рецепция ключове"' in i18n_js
    assert '"intent.receptionApprovedTitle": "{count} курса чакат ключове"' in i18n_js


def test_admin_decision_rail_promotes_pending_queue_before_table() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert 'id="decisionRail" aria-labelledby="decisionRailTitle" aria-live="polite"' in html
    assert html.index('id="decisionRail"') < html.index('id="bulkActionBar"')
    assert "function renderDecisionRail()" in app_js
    assert 'const visible = pendingItems.slice(0, 3);' in app_js
    assert 'data-decision-rail-select-all' in app_js
    assert 'setAllPendingReservationsSelected(true);' in app_js
    assert 'bulkReservationDecision("approve").catch' in app_js
    assert 'data-decision-card="${item.id}"' in app_js
    assert "requesterGsmLine(item)" in app_js
    assert 't("decisionRail.eyebrow")' in app_js
    assert '"decisionRail.approveAll": "Одобри всички"' in i18n_js
    assert '"decisionRail.emptyCopy": "Опашката е чиста.' in i18n_js
    assert ".decision-rail__actions .btn" in styles
    assert ".decision-card__actions .action-btn" in styles


def test_reception_rail_promotes_key_handoff_before_table() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")

    assert 'id="receptionRail" aria-labelledby="receptionRailTitle" aria-live="polite"' in html
    assert html.index('id="decisionRail"') < html.index('id="receptionRail"') < html.index('id="reservationsTimeline"')
    assert "receptionRail: document.getElementById(\"receptionRail\")" in app_js
    assert "handoffTelemetry: {}" in app_js
    assert "handoffTelemetry: false" in app_js
    assert "function renderReceptionRail()" in app_js
    assert "const showRail = canManageTripHandoff() && surface === \"admin\" && state.token;" in app_js
    assert "function receptionRailItems()" in app_js
    assert "function loadHandoffTelemetry()" in app_js
    assert 'apiFetch(`/cars/${carId}/telemetry/latest`' in app_js
    assert "state.handoffTelemetry[item.car_id]" in app_js
    assert "telemetryLocationBlock(handoffTelemetry)" in app_js
    assert "state.pulseReservations" in app_js
    assert "if (!handoffItems.length && isFullAdmin())" in app_js
    assert 'data-reception-card="${item.id}"' in app_js
    assert 'data-reservation-action="${action}"' in app_js
    assert "requesterGsmLine(item)" in app_js
    assert 'action = isActive ? "return" : "start"' in app_js
    assert 't("receptionRail.eyebrow")' in app_js
    assert '"receptionRail.emptyTitle": "Няма коли за предаване или връщане"' in i18n_js
    assert '"receptionRail.copy": "Първо предай или приеми ключове и документи.' in i18n_js


def test_reception_calendar_uses_operational_snapshot_not_table_filter() -> None:
    app_js = _read("static/app.js")

    assert "function calendarSourceItems()" in app_js
    assert "if (!state.token) return state.publicCalendar;" in app_js
    assert "if (!isOperationalRole()) return state.reservations;" in app_js
    assert 'state.currentRole === "fleet_reception" ? ["approved", "checked_out"]' in app_js
    assert '["pending", "approved", "checked_out"]' in app_js
    assert "const calendarItems = calendarSourceItems();" in app_js


def test_authenticated_reservation_surfaces_show_requester_gsm_without_public_leak() -> None:
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    router = _read("routers/reservations.py")
    app_py = _read("app.py")

    assert "requester.gsm_number AS requester_gsm_number" in router
    assert "LEFT JOIN users requester ON requester.id = r.created_by_id" in router
    assert "function requesterGsmLine(item)" in app_js
    assert "if (!state.token) return \"\";" in app_js
    assert 'const number = item.requester_gsm_number || t("reservation.requesterGsmMissing");' in app_js
    assert 't("reservation.requesterGsm", { number })' in app_js
    assert '"reservation.requesterGsm": "GSM: {number}"' in i18n_js
    assert '"reservation.requesterGsmMissing": "не е въведен"' in i18n_js
    assert "const requesterGsm = requesterGsmLine(item);" in app_js
    assert "requester_gsm_number" not in app_py
    assert "renderCalendar();\n    renderDayTimeline();" in app_js


def test_employee_is_redirected_away_from_admin_surface() -> None:
    index_html = _read("templates/index.html")
    app_js = _read("static/app.js")

    assert '<a class="hidden" href="/admin" data-operational-link>Admin</a>' in index_html
    assert 'operationalLinks: document.querySelectorAll("[data-operational-link]")' in app_js
    assert "function employeeBlockedFromAdminSurface(user)" in app_js
    assert 'return surface === "admin" && user?.role === "employee";' in app_js
    assert 'sessionStorage.setItem("fleetflow.employeeAdminDenied", "1");' in app_js
    assert 'window.location.replace("/");' in app_js
    assert "const allowed = await loadMe();" in app_js
    assert "if (!allowed) return;" in app_js
    assert "const canContinue = await restoreSessionFromCookie();" in app_js
    assert "if (!canContinue) return;" in app_js
    assert "els.operationalLinks.forEach((link) => toggleHidden(link, employeeAdminDenied || !authenticated || !operationalMode));" in app_js


def test_reservation_timeline_is_primary_before_table() -> None:
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    for template in ("templates/index.html", "templates/admin.html"):
        html = _read(template)
        assert 'id="reservationsTimeline" aria-labelledby="reservationsTimelineTitle" aria-live="polite"' in html
        assert html.index('id="reservationsTimeline"') < html.index('class="table-wrap"')
    assert "function renderReservationFlow(cars, canBulk)" in app_js
    assert "function reservationFlowCard(item, car, canBulk)" in app_js
    assert 'data-reservation-card="${item.id}"' in app_js
    assert 'data-reservation-select="${item.id}"' in app_js
    assert 'document.querySelector(`[data-reservation-card="${id}"]`)' in app_js
    assert "renderReservationFlow(cars, canBulk);" in app_js
    assert '"reservationFlow.title": "Курсовете като времева линия"' in i18n_js
    assert '"reservationFlow.copy": "Първо виж статуса, периода и следващото действие.' in i18n_js
    assert ".reservation-flow-card__actions" in styles
    assert ".reservation-flow-card__rail" in styles


def test_playwright_e2e_harness_is_documented_and_separate_from_unit_suite() -> None:
    makefile = _read("Makefile")
    pyproject = _read("pyproject.toml")
    requirements = _read("requirements-dev.txt")
    e2e = _read("e2e/test_browser_smoke.py")
    gitignore = _read(".gitignore")

    assert "testpaths = [\"tests\"]" in pyproject
    assert "playwright==1.58.0" in requirements
    assert "test-e2e:" in makefile
    assert "$(PYTHON) -m pytest e2e -q || test $$? -eq 5" in makefile
    assert "E2E_ARTIFACT_DIR" in e2e
    assert "employee-desktop.png" in e2e
    assert "admin-desktop.png" in e2e
    assert "employee-mobile.png" in e2e
    assert "test-results/" in gitignore


def test_fleet_pulse_promotes_admin_executive_insights() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert 'id="fleetPulse" aria-labelledby="fleetPulseTitle" aria-live="polite"' in html
    assert html.index('id="fleetPulse"') < html.index('id="reservationsDeck"')
    assert "pulseReservations: []" in app_js
    assert "intelligencePulse: null" in app_js
    assert "telemetry: []" in app_js
    assert "function loadFleetPulseReservations()" in app_js
    assert "function loadFleetIntelligencePulse()" in app_js
    assert "function loadTelemetry()" in app_js
    assert "function loadPickupTelemetry()" in app_js
    assert 'apiFetch("/reservations?limit=500"' in app_js
    assert 'apiFetch("/admin/intelligence/pulse"' in app_js
    assert 'apiFetch("/cars/telemetry/latest"' in app_js
    assert 'apiFetch(`/cars/${candidate.car_id}/telemetry/latest`' in app_js
    assert "function renderFleetPulse()" in app_js
    assert "function mostBookedCar(reservations, cars)" in app_js
    assert "function telemetryByPlate()" in app_js
    assert "const overviewReservations = isOperationalRole() ? state.pulseReservations : state.reservations;" in app_js
    assert 'const adminReservations = state.pulseReservations;' in app_js
    assert '"fleetPulse.title": "Оперативен пулс"' in i18n_js
    assert '"fleetPulse.busiestCar": "Най-натоварена кола"' in i18n_js
    assert '"fleetPulse.telemetry": "Свеж GPS сигнал"' in i18n_js
    assert '"fleetPulse.insightsLabel": "Оперативни insight-и"' in i18n_js
    assert "function hasNewReservationSignal(previousIds)" in app_js
    assert "await loadPickupTelemetry();" in app_js
    assert "const activeFleetPlates = new Set(" in app_js
    assert "const fleetTelemetryCount = state.telemetry.filter" in app_js
    assert 'value: state.telemetryConfigured ? `${fleetTelemetryCount}/${fleetTelemetryTotal}` : "—"' in app_js
    assert '"pickup.title": "Къде да вземеш колата"' in i18n_js
    assert '"pickup.notConfigured": "GPS локацията още не е включена. Администратор може да добави NetFleet ключ."' in i18n_js
    assert '"pickup.unavailable": "GPS локацията временно не е налична. Провери по-късно или попитай рецепция."' in i18n_js
    assert "function isFreshTelemetry(item, maxAgeMinutes = 60)" in app_js
    assert "function telemetryFreshnessMarkup(item)" in app_js
    assert '&& isFreshTelemetry(item)' in app_js
    assert '"telemetry.coordinates": "Координати: {lat}, {lon}"' in i18n_js
    assert '"telemetry.updated": "Последно видяна: {time}"' in i18n_js
    assert '"telemetry.freshnessStale": "Остарял сигнал: преди {minutes} мин. Потвърди с рецепция."' in i18n_js
    assert ".fleet-pulse__grid" in styles
    assert ".fleet-pulse__insight" in styles
    assert ".car-card__telemetry" in styles
    assert ".pickup-location" in styles
    assert ".telemetry-freshness--fresh" in styles
    assert ".telemetry-freshness--stale" in styles
    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in styles


def test_netfleet_secret_stays_out_of_browser_facing_ui() -> None:
    browser_files = [
        "templates/index.html",
        "templates/admin.html",
        "static/app.js",
        "static/i18n.js",
        "static/styles.css",
    ]
    for path in browser_files:
        content = _read(path)
        assert "NETFLEET_API_KEY" not in content
        assert "api-key" not in content
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    assert 'apiFetch(`/cars/${candidate.car_id}/telemetry/latest`' in app_js
    assert '"pickup.title": "Къде да вземеш колата"' in i18n_js
    assert '"pickup.notConfigured": "GPS локацията още не е включена. Администратор може да добави NetFleet ключ."' in i18n_js
    assert '"pickup.unavailable": "GPS локацията временно не е налична. Провери по-късно или попитай рецепция."' in i18n_js
    assert '"fleetPulse.telemetryNotConfigured": "NetFleet ключът още не е добавен."' in i18n_js
    assert '"telemetry.freshnessCaution": "Провери с рецепция: сигналът е от преди {minutes} мин."' in i18n_js


def test_admin_netfleet_key_can_be_configured_without_displaying_current_secret() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")

    assert 'id="netfleetForm"' in html
    assert 'id="netfleetApiKey"' in html
    assert 'type="password"' in html
    assert "Ключът не се показва обратно след запис." in html
    assert "function loadNetfleetConfig()" in app_js
    assert "function handleNetfleetConfigUpdate(event)" in app_js
    assert 'apiFetch("/cars/telemetry/config"' in app_js
    assert 'body: JSON.stringify({ api_key: els.netfleetApiKey.value.trim() })' in app_js
    assert 'els.netfleetForm.reset();' in app_js
    assert '"netfleet.configuredUi": "Конфигуриран през Admin UI. Последна промяна: {time}."' in i18n_js
    assert '"netfleet.notConfigured": "Не е конфигуриран.' in i18n_js


def test_admin_user_form_supports_gsm_number() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")

    assert 'id="newGsmNumber"' in html
    assert 'type="tel"' in html
    assert "GSM номер" in html
    assert "newGsmNumber: document.getElementById" in app_js
    assert "gsm_number: els.newGsmNumber?.value.trim() || null" in app_js
    assert 'user.gsm": "GSM: {number}"' in i18n_js


def test_admin_production_readiness_panel_is_present_and_secret_safe() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")

    assert 'id="productionReadinessPanel"' in html
    assert 'id="productionReadinessSummary"' in html
    assert 'id="productionReadinessList"' in html
    assert "function loadProductionReadiness()" in app_js
    assert "function renderProductionReadiness()" in app_js
    assert "function readinessCountsText(failed, warnings)" in app_js
    assert 'apiFetch("/ops/readiness"' in app_js
    assert '"readiness.notReady": "Има блокери преди live"' in i18n_js
    assert '"readiness.warnings.one": "{count} бележка"' in i18n_js
    assert ".readiness-item--fail span" in styles
    assert "SECRET_KEY" not in html
    assert "POSTGRES_PASSWORD" not in html
