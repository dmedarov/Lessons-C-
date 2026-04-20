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
    assert "await quickBookReservation();" in app_js
    assert 'name: "reservation-transition"' in app_js
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
    assert "toggleHidden(els.quickBookPanel, !authenticated || adminMode);" in app_js
    assert '"quickBook.createdTitle": "Бързата заявка е подадена"' in i18n_js
    assert ".quick-book .btn" in styles


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
    assert "toggleHidden(els.smartPrefillPanel, !authenticated || adminMode || !state.reservationPreferences?.available);" in app_js
    assert '"smartPrefill.hint": "Обичайно: {car}, около {hour}:00, за {duration} мин."' in i18n_js
    assert ".smart-prefill .action-btn" in styles


def test_status_bar_reports_free_cars_not_only_active_cars() -> None:
    app_js = _read("static/app.js")
    for template in ("templates/index.html", "templates/admin.html"):
        html = _read(template)
        assert '<span class="stat-card__label">Свободни коли</span>' in html
    assert "const availableCars = Math.max(activeCars - activeTrips, 0);" in app_js
    assert 'kpiAvailable.querySelector(".stat-card__value").textContent = availableCars;' in app_js


def test_current_trip_hero_promotes_active_or_next_trip() -> None:
    html = _read("templates/index.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert 'id="currentTripHero" aria-labelledby="currentTripTitle"' in html
    assert "function currentTripCandidate()" in app_js
    assert "function renderCurrentTripHero()" in app_js
    assert 'data-primary-trip-action="true"' in app_js
    assert 'primaryAction = active ? "return" : "start"' in app_js
    assert 'renderCurrentTripHero();' in app_js
    assert '"trip.hero.activeEyebrow": "Твоята кола"' in i18n_js
    assert ".current-trip-hero" in styles
    assert ".current-trip-hero__actions .btn" in styles


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
    assert 't("decisionRail.eyebrow")' in app_js
    assert '"decisionRail.approveAll": "Одобри всички"' in i18n_js
    assert '"decisionRail.emptyCopy": "Опашката е чиста.' in i18n_js
    assert ".decision-rail__actions .btn" in styles
    assert ".decision-card__actions .action-btn" in styles


def test_fleet_pulse_promotes_admin_executive_insights() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert 'id="fleetPulse" aria-labelledby="fleetPulseTitle" aria-live="polite"' in html
    assert html.index('id="fleetPulse"') < html.index('id="reservationsDeck"')
    assert "pulseReservations: []" in app_js
    assert "telemetry: []" in app_js
    assert "function loadFleetPulseReservations()" in app_js
    assert "function loadTelemetry()" in app_js
    assert "function loadPickupTelemetry()" in app_js
    assert 'apiFetch("/reservations?limit=500"' in app_js
    assert 'apiFetch("/cars/telemetry/latest"' in app_js
    assert 'apiFetch(`/cars/${candidate.car_id}/telemetry/latest`' in app_js
    assert "function renderFleetPulse()" in app_js
    assert "function mostBookedCar(reservations, cars)" in app_js
    assert "function telemetryByPlate()" in app_js
    assert 'const overviewReservations = state.currentRole === "fleet_admin" ? state.pulseReservations : state.reservations;' in app_js
    assert 'const adminReservations = state.pulseReservations;' in app_js
    assert '"fleetPulse.title": "Оперативен пулс"' in i18n_js
    assert '"fleetPulse.busiestCar": "Най-натоварена кола"' in i18n_js
    assert '"fleetPulse.telemetry": "GPS сигнали"' in i18n_js
    assert '"pickup.title": "Къде да вземеш колата"' in i18n_js
    assert '"telemetry.coordinates": "{lat}, {lon}"' in i18n_js
    assert ".fleet-pulse__grid" in styles
    assert ".car-card__telemetry" in styles
    assert ".pickup-location" in styles
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
    assert '"fleetPulse.telemetryNotConfigured": "NetFleet ключът не е включен в runtime средата."' in i18n_js


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
