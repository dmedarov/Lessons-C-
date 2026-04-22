from __future__ import annotations

import re
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


def test_static_assets_are_cache_busted_in_templates() -> None:
    app_py = _read("app.py")
    assert 'response.headers["Cache-Control"] = "no-cache, must-revalidate"' in app_py
    assert "NO_CACHE_ASSET_EXTENSIONS" in app_py
    for template in ("templates/index.html", "templates/admin.html"):
        html = _read(template)
        assert "/static/styles.css?v=20260422-next-focus" in html
        assert "/static/i18n.js?v=20260422-next-focus" in html
        assert "/static/app.js?v=20260422-next-focus" in html
        assert "/static/theme.js?v=20260422-next-focus" in html
        assert 'src="/static/i18n.js"' not in html
        assert 'src="/static/app.js"' not in html


def test_premium_visual_system_avoids_decorative_orbs() -> None:
    styles = _read("static/styles.css")
    assert "radial-gradient" not in styles
    assert ".hero__primary::before" not in styles
    assert ".hero__primary::after" not in styles
    assert "no decorative orbs" in styles


def test_cnsys_brand_mark_is_visible_without_adding_nav_noise() -> None:
    styles = _read("static/styles.css")
    for template in ("templates/index.html", "templates/admin.html"):
        html = _read(template)
        assert '<span class="brand__company">CNSYS</span>' in html
    assert ".brand__company" in styles


def test_i18n_literal_keys_are_defined_and_missing_keys_do_not_render_raw_keys() -> None:
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    defined_keys = set(re.findall(r'"([^"]+)"\s*:', i18n_js))
    literal_t_keys = set(re.findall(r'(?<![A-Za-z0-9_.$])t\("([^"`]+)"', app_js))
    missing = sorted(literal_t_keys - defined_keys)
    assert missing == []
    assert "const template = bg[key];" in i18n_js
    assert "return missingTranslationFallback;" in i18n_js
    assert "bg[key] || key" not in i18n_js
    assert 'window.FleetFlowI18n?.t(key, vars) || "Текстът се зарежда"' in app_js


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
    assert "form.noValidate = true;" in app_js
    assert app_js.count('textarea name="reason" rows="3" required') == 3
    assert app_js.count('fieldName: "reason"') >= 3
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


def test_admin_handoff_and_role_change_require_reasons() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    assert 'id="handoffUserIdError"' in html
    assert 'id="handoffReasonError"' in html
    assert "function validateHandoffForm()" in app_js
    assert "function focusFirstFieldError(ids = fieldErrorIds)" in app_js
    assert 'setFieldError("handoffUserId", t("admin.handoffUserRequired"))' in app_js
    assert 'setFieldError("handoffReason", t("admin.handoffReasonRequired"))' in app_js
    assert 'showMessage("Има проблем", "Поправи данните за admin handoff.")' in app_js
    assert 'focusFirstFieldError(["handoffUserId", "handoffReason"])' in app_js
    assert 't("admin.roleChangeReasonRequired")' in app_js
    assert '"admin.roleChangeReasonRequired": "Добави причина за смяната на роля."' in i18n_js
    assert '"admin.handoffReasonRequired": "Добави причина за admin handoff."' in i18n_js


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
    admin_html = _read("templates/admin.html")
    assert 'id="nextFocusCard"' in admin_html
    assert 'id="nextSignalBadge"' in admin_html
    assert 'id="nextSignalInsights"' in admin_html
    assert admin_html.index('id="nextFocusCard"') < admin_html.index('id="modeCard"')
    assert "function setIntentActions(actions = [])" in app_js
    assert "function setNextFocusBadge(label = \"\", tone = \"muted\")" in app_js
    assert "function setNextFocusInsights(items = [])" in app_js
    assert "function nextFocusSupportActions()" in app_js
    assert "function setNextFocusState({ badgeKey, badgeTone = \"muted\", title, copy, insights = [], actions = [] })" in app_js
    assert "function operationalNextFocusInsights({ pending, approved, overdueReturns, activeTrips })" in app_js
    assert 'data-primary-intent="true"' in app_js
    assert 'name: "review-pending", labelKey: "intent.action.reviewPending", primary: true' in app_js
    assert 'name: "view-readiness", labelKey: "intent.action.viewReadiness"' in app_js
    assert 'name: "book-now", labelKey: "intent.action.bookNow", primary: true' in app_js
    assert 'name: "focus-reservation", labelKey: "intent.action.viewTrip", primary: true' in app_js
    assert "await quickBookReservation();" in app_js
    assert 'name: "reservation-transition"' not in app_js
    assert "function handleIntentAction(button)" in app_js
    assert "function focusReservationRow(id, action = null)" in app_js
    assert '"intent.employeeFreeTitle": "Свободен режим"' in i18n_js
    assert '"intent.employeePendingTitle": "Заявката чака одобрение"' in i18n_js
    assert 'title: t("intent.employeePendingTitle")' in app_js
    assert '"ui.surface.controlTower": "Control Tower"' in i18n_js
    assert '"ui.surface.decisionDesk": "Decision Desk"' in i18n_js
    assert '"ui.surface.handoffDesk": "Handoff Desk"' in i18n_js
    assert '"ui.surface.employeeDesk": "Моят курс / Нова заявка"' in i18n_js
    assert '"summary.nextFocus.badge.decide": "Решение"' in i18n_js
    assert '"summary.nextFocus.badge.readiness": "Live"' in i18n_js
    assert '"summary.nextFocus.readinessFailInsight": "{count} live блокера остават отворени."' in i18n_js
    assert '"summary.nextFocus.readinessBlockersTitle": "{count} блокера преди live"' in i18n_js
    assert '"intent.action.viewReadiness": "Готовност за live"' in i18n_js
    assert 'els.modeHeading.textContent = t("ui.surface.employeeDesk");' in app_js
    assert ".summary-card--hero" in styles
    assert ".summary-card__header" in styles
    assert ".summary-insight-list" in styles
    assert ".summary-card__actions .btn" in styles
    assert "min-height: 44px;" in styles


def test_one_tap_booking_is_available_without_form_scanning() -> None:
    html = _read("templates/index.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert 'id="suggestedBookingHero" aria-labelledby="suggestedBookingTitle"' in html
    assert html.index('id="suggestedBookingHero"') < html.index('id="reservationsDeck"')
    assert 'id="quickBookPanel"' in html
    assert 'id="quickBookBtn"' in html
    assert 'id="requestOutcome" role="status" aria-live="polite"' in html
    assert html.index('id="quickBookPanel"') < html.index('id="reservationForm"')
    assert "function quickBookReservation()" in app_js
    assert "function renderSuggestedBookingHero()" in app_js
    assert "function loadSuggestedBooking()" in app_js
    assert 'state.suggestedBooking = await apiFetch("/reservations/suggest", { headers: authHeaders() });' in app_js
    assert "function employeeOpenReservation()" in app_js
    assert "function showRequestOutcome(reservation" in app_js
    assert 'showRequestOutcome(reservation, { source: "quick", carLabel: car });' in app_js
    assert 'showRequestOutcome(reservation, { source: "manual" });' in app_js
    assert 'if (action === "edit-suggestion")' in app_js
    assert 'apiFetch("/reservations/quick-book"' in app_js
    assert "toggleHidden(els.quickBookPanel, !authenticated || operationalMode);" in app_js
    assert '"quickBook.createdTitle": "Бързата заявка е подадена"' in i18n_js
    assert '"suggestedBooking.title": "Нямаш активен курс"' in i18n_js
    assert '"requestOutcome.nextStep": "Следващият ход е при одобряващия. Не е нужно да натискаш отново."' in i18n_js
    assert ".suggested-booking-hero" in styles
    assert ".request-outcome" in styles
    assert ".quick-book .btn" in styles
    assert "overflow-wrap: anywhere;" in styles


def test_outbound_notification_status_is_admin_only_and_actionable() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")

    assert 'id="outboundNotificationStatus" role="status" aria-live="polite"' in html
    assert "function renderOutboundNotificationStatus()" in app_js
    assert 'testNotificationBtn: document.querySelector("[data-test-notification]")' in app_js
    assert "toggleHidden(els.testNotificationBtn, !authenticated || !fullAdmin || !adminSurface);" in app_js
    assert 'els.outboundNotificationStatus.className = "outbound-status hidden";' in app_js
    assert '"outbound.inAppOnlyCopy": "Добави SMTP за персонални email-и или Teams webhook за shared operational канал."' in i18n_js
    assert '"outbound.readyCopy": "SMTP праща към email-а на получателя; Teams е shared канал. Тествай преди live."' in i18n_js
    assert ".outbound-status--ready" in styles
    assert ".outbound-status--warn" in styles


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
        assert '<span class="stat-card__label">Чака вземане</span>' in html
    assert "Math.max(activeCars - approved - activeTrips, 0)" in app_js
    assert 'const approved = publicOverview?.approved_handoffs' in app_js


def test_public_overview_feeds_pre_login_status_bar() -> None:
    app_js = _read("static/app.js")
    assert "publicOverview: null" in app_js
    assert "function loadPublicOverview()" in app_js
    assert 'apiFetch("/public/overview")' in app_js
    assert "const publicOverview = !state.token ? state.publicOverview : null;" in app_js
    assert "publicOverview?.pending_requests" in app_js
    assert "publicOverview?.approved_handoffs" in app_js
    assert "publicOverview?.active_trips" in app_js
    assert "publicOverview?.available_cars" in app_js
    assert 'kpiApproved.querySelector(".stat-card__value").textContent = approved;' in app_js
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
    assert "function isAwaitingPickup(item)" in app_js
    assert "function presentationStatusKey(item)" in app_js
    assert "function renderCurrentTripHero()" in app_js
    assert 'data-trip-focus-action="true"' in app_js
    assert 'data-intent-action="focus-reservation"' in app_js
    assert 'primaryAction = active ? "return" : "start"' not in app_js
    assert 'renderCurrentTripHero();' in app_js
    assert '"trip.hero.activeEyebrow": "Твоята кола"' in i18n_js
    assert '"trip.hero.awaitingPickupEyebrow": "Чака вземане"' in i18n_js
    assert '"status.awaiting_pickup": "Чака вземане"' in i18n_js
    assert "рецепция; там отбелязват старта" in i18n_js
    assert "още не е отбелязала предаването" in i18n_js
    assert "рецепция приключва lifecycle-а" in i18n_js
    assert ".current-trip-hero" in styles
    assert ".current-trip-hero__actions .btn" in styles


def test_car_cards_show_operational_state_not_just_pool_flag() -> None:
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")

    assert "function operationalReservationSource()" in app_js
    assert "function presentationStatusState(status)" in app_js
    assert "function carOperationalState(car, reservations = operationalReservationSource())" in app_js
    assert '"car.state.available": "Свободна"' in i18n_js
    assert '"car.stateNote.awaiting_pickup": "Курсът е одобрен, но колата още чака вземане от рецепция."' in i18n_js
    assert ".status-tag--available" in styles
    assert "const reservations = operationalReservationSource();" in app_js
    assert "carOperationalState(car, reservations)" in app_js
    assert "function rerenderOperationalSurfaces()" in app_js
    assert "renderFleetPulse();\n  renderReceptionRail();\n  renderCars();\n  renderCalendar();\n  renderDayTimeline();" in app_js
    assert "function applyPulseReservations(items = [])" in app_js


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
    assert '"intent.receptionApprovedTitle.one": "{count} курс чака ключове"' in i18n_js
    assert '"intent.receptionOverdueReturnTitle.many": "{count} курса чакат връщане"' in i18n_js
    assert 'receptionTitle("receptionOverdueReturnTitle", overdueReturns)' in app_js
    assert app_js.index("if (canManageTripHandoff() && overdueReturns)") < app_js.index(
        "if (canApproveReservations() && pending)"
    )
    assert app_js.index("if (canManageTripHandoff() && overdueReturns)") < app_js.index(
        "if (canManageTripHandoff() && approved)"
    )


def test_admin_decision_rail_promotes_pending_queue_before_table() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert 'id="decisionRail" aria-labelledby="decisionRailTitle" aria-live="polite"' in html
    assert html.index('id="decisionRail"') < html.index('id="reservationsDeck"')
    assert "function renderDecisionRail()" in app_js
    assert "function pendingDecisionItems()" in app_js
    assert "[...state.pulseReservations, ...state.reservations]" in app_js
    assert "const seen = new Set();" in app_js
    assert 'const visibleLimit = state.currentRole === "fleet_approver" ? 5 : 3;' in app_js
    assert 'data-decision-rail-select-all' in app_js
    assert 'setAllPendingReservationsSelected(true);' in app_js
    assert 'els.bulkApproveBtn?.focus();' in app_js
    assert 'data-decision-card="${item.id}"' in app_js
    assert "requesterGsmLine(item)" in app_js
    assert "decisionPurposeLine(item)" in app_js
    assert "function decisionUrgency(item)" in app_js
    assert 't("decisionRail.eyebrow")' in app_js
    assert '"decisionRail.selectAll": "Избери всички"' in i18n_js
    assert '"decisionRail.reasonMissing": "Причина: не е въведена. Провери заявителя преди решение."' in i18n_js
    assert '"decisionRail.emptyCopy": "Опашката е чиста.' in i18n_js
    assert ".decision-rail__actions .btn" in styles
    assert ".decision-card__actions .action-btn" in styles
    assert ".reservations-deck--decision-secondary .table-wrap" in styles


def test_reception_rail_promotes_key_handoff_before_table() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    styles = _read("static/styles.css")
    i18n_js = _read("static/i18n.js")

    assert 'id="receptionRail" aria-labelledby="receptionRailTitle" aria-live="polite"' in html
    assert html.index('id="decisionRail"') < html.index('id="receptionRail"') < html.index('id="reservationsDeck"')
    assert html.index('id="receptionRail"') < html.index('id="calendarStudio"')
    assert "receptionRail: document.getElementById(\"receptionRail\")" in app_js
    assert "calendarStudio: document.getElementById(\"calendarStudio\")" in app_js
    assert "handoffTelemetry: {}" in app_js
    assert "handoffTelemetry: false" in app_js
    assert "function renderReceptionRail()" in app_js
    assert "const showRail = canManageTripHandoff() && surface === \"admin\" && state.token;" in app_js
    assert "function receptionRailItems()" in app_js
    assert "function receptionRailGroups()" in app_js
    assert "function receptionCardMarkup(item, cars)" in app_js
    assert "function receptionRailSection(titleKey, emptyKey, items, cars, extraCount = 0)" in app_js
    assert "function isOverdueReturn(item)" in app_js
    assert "const aOverdue = isOverdueReturn(a);" in app_js
    assert 'overdue ? "receptionRail.overdueReturnBy"' in app_js
    assert 'status-pill--danger' in app_js
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
    assert '"reservations-deck--handoff-secondary"' in app_js
    assert '"calendar-studio--handoff-context"' in app_js
    assert 't("receptionRail.eyebrow")' in app_js
    assert ".reception-rail__stack" in styles
    assert ".reservations-deck--handoff-secondary .table-wrap" in styles
    assert "body[data-role=\"fleet_reception\"] #calendarStudio.calendar-studio--handoff-context" in styles
    assert '"receptionRail.emptyTitle": "Няма коли за предаване или връщане"' in i18n_js
    assert '"receptionRail.copy": "Първо затвори просрочените връщания, после предай ключове и документи.' in i18n_js
    assert '"receptionRail.overdueTitle": "Чака връщане"' in i18n_js
    assert '"receptionRail.handoffTitle": "Чака предаване"' in i18n_js


def test_bulk_selection_stays_synchronized_between_timeline_and_table() -> None:
    app_js = Path("static/app.js").read_text()
    styles = Path("static/styles.css").read_text()
    e2e = Path("e2e/test_browser_smoke.py").read_text()

    assert "function syncReservationSelectionControls(id)" in app_js
    assert 'document.querySelectorAll(`[data-reservation-select="${id}"]`)' in app_js
    assert 'document.querySelectorAll(`[data-reservation-card="${id}"], [data-reservation-row="${id}"]`)' in app_js
    assert 'row.classList.toggle("is-selected", state.selectedReservationIds.has(item.id));' in app_js
    assert ".reservation-flow-card.is-selected" in styles
    assert '.select-cell input[type="checkbox"]:focus-visible' in styles
    assert "approver-keyboard-bulk-selection.png" in e2e


def test_reception_calendar_uses_operational_snapshot_not_table_filter() -> None:
    app_js = _read("static/app.js")

    assert "function calendarSourceItems()" in app_js
    assert "if (!state.token) return state.publicCalendar;" in app_js
    assert "if (!isOperationalRole()) return state.reservations;" in app_js
    assert 'state.currentRole === "fleet_reception" ? ["approved", "checked_out"]' in app_js
    assert '["pending", "approved", "checked_out"]' in app_js
    assert "const calendarItems = calendarSourceItems();" in app_js


def test_calendar_expands_multi_day_items_and_keeps_range_pills_visible() -> None:
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")

    assert "function calendarItemKeys(item)" in app_js
    assert "while (cursor <= final)" in app_js
    assert "calendar_segment: calendarSegmentFor(index, keys.length)" in app_js
    assert "calendar_span_days: keys.length" in app_js
    assert "function sortCalendarItems(items)" in app_js
    assert "item.calendar_segment?.range ? 0 : 1" in app_js
    assert "const visibleItems = items.slice(0, 4);" in app_js
    assert 'calendarPill(item, cars.get(item.car_id), { compact: true })' in app_js
    assert 'aria-label="${escapeHtml(accessibleLabel)}"' in app_js
    assert "function nextBusyDateKey(fromKey)" in app_js
    assert 'data-date-key="${nextKey}"' in app_js
    assert '"calendar.nextBusyDay": "Следващият запис е на {date}."' in i18n_js
    assert '"calendar.viewNextBusyDay": "Виж този ден"' in i18n_js
    assert '"calendar.rangeStart": "начало"' in i18n_js
    assert '"calendar.rangeMiddle": "продължава"' in i18n_js
    assert '"calendar.rangeEnd": "край"' in i18n_js
    assert ".calendar-pill--range" in styles
    assert ".calendar-pill--compact" in styles
    assert ".calendar-day__list" in styles
    assert "container-type: inline-size;" in styles
    assert "@container (max-width: 920px)" in styles
    assert "width: 100%;" in styles
    assert "min-width: 0;" in styles
    assert "overflow: hidden;" in styles


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
    assert 'return window.location.pathname.startsWith("/admin") && user?.role === "employee";' in app_js
    assert "function operationalBlockedFromEmployeeSurface(user)" in app_js
    assert 'return !window.location.pathname.startsWith("/admin") && Boolean(user?.role) && user.role !== "employee";' in app_js
    assert 'sessionStorage.setItem("fleetflow.surfaceRedirectToken", state.token);' in app_js
    assert 'sessionStorage.removeItem("fleetflow.surfaceRedirectToken");' in app_js
    assert "if (state.token) return await loadMe();" in app_js
    assert 'sessionStorage.setItem("fleetflow.employeeAdminDenied", "1");' in app_js
    assert 'window.location.assign("/");' in app_js
    assert 'window.location.assign("/admin");' in app_js
    assert "redirectOperationalToAdminSurface(state.currentUser)" in app_js
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


def test_public_calendar_pills_are_text_backed_for_operational_states() -> None:
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")

    assert "const presentation = presentationStatusState(item);" in app_js
    assert "const statusText = lifecycleLabel(item);" in app_js
    assert '`${t(presentation.shortLabelKey)} · ${label}`' in app_js
    assert 'calendar-pill--${presentation.key}' in app_js
    assert ".calendar-pill--awaiting_pickup" in styles
    assert '"status.short.awaiting_pickup": "Вземане"' in i18n_js
    assert '"status.short.checked_out": "Активен"' in i18n_js


def test_calendar_legend_and_priority_distinguish_awaiting_pickup_from_active_trip() -> None:
    app_js = _read("static/app.js")
    styles = _read("static/styles.css")
    index_html = _read("templates/index.html")
    admin_html = _read("templates/admin.html")

    assert "const PRESENTATION_STATUS = {" in app_js
    assert 'awaiting_pickup: { tagClass: "approved", priority: 1 }' in app_js
    assert "const presentation = presentationStatusState(item);" in app_js
    assert "presentation.priority" in app_js
    assert "Избран ден" in index_html
    assert "Избран ден" in admin_html
    assert "чакащи одобрение, чакащи вземане, активни курсове и върнати автомобили" in index_html
    assert "чакащи одобрение, чакащи вземане, активни курсове и върнати автомобили" in admin_html
    assert "legend__dot--awaiting-pickup" in index_html
    assert "legend__dot--awaiting-pickup" in admin_html
    assert ".legend__dot--awaiting-pickup" in styles


def test_public_surface_is_simplified_before_login_without_hiding_contextual_overview() -> None:
    app_js = _read("static/app.js")
    e2e = _read("e2e/test_browser_smoke.py")

    assert 'notificationDeck: document.getElementById("notificationDeck")' in app_js
    assert 'fleetDeck: document.getElementById("fleetDeck")' in app_js
    assert "toggleHidden(els.notificationDeck, !authenticated);" in app_js
    assert "toggleHidden(els.reservationsDeck, !authenticated);" in app_js
    assert "toggleHidden(els.guidanceCard, authenticated);" in app_js
    assert "toggleHidden(els.summaryDeck, !authenticated);" in app_js
    assert "public-desktop.png" in e2e
    assert 'expect(desktop_page.locator("#notificationDeck")).to_be_hidden()' in e2e
    assert 'expect(desktop_page.locator("#reservationsDeck")).to_be_hidden()' in e2e
    assert 'expect(desktop_page.locator("#calendarGrid")).to_contain_text("Вземане ·"' in e2e


def test_operational_state_pipeline_is_single_source_for_pulse_driven_surfaces() -> None:
    app_js = _read("static/app.js")

    assert "function rerenderOperationalSurfaces()" in app_js
    assert "function applyPulseReservations(items = [])" in app_js
    assert "state.pulseReservations = items;" in app_js
    assert "rerenderOperationalSurfaces();" in app_js
    assert "setLoading(\"pulseReservations\", true);" in app_js
    assert "applyPulseReservations(data.items);" in app_js
    assert "setLoading(\"pulseReservations\", false);" in app_js


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
    assert "public-desktop.png" in e2e
    assert "admin-desktop.png" in e2e
    assert "admin-contact-correction.png" in e2e
    assert "approver-reject-with-gsm.png" in e2e
    assert "reception-start-return-flow.png" in e2e
    assert "employee-mobile.png" in e2e
    assert "test-results/" in gitignore


def test_manual_keyboard_accessibility_doc_covers_all_roles() -> None:
    doc = _read("docs/ROLE_KEYBOARD_ACCESSIBILITY.md")

    assert "Public orientation" in doc
    assert "Employee" in doc
    assert "Approver" in doc
    assert "Reception" in doc
    assert "Admin" in doc
    assert "PILOT GO" in doc
    assert "screen-reader check" in doc


def test_fleet_pulse_promotes_admin_executive_insights() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")
    assert 'id="fleetPulse" aria-labelledby="fleetPulseTitle" aria-live="polite"' in html
    assert html.index('id="fleetPulse"') < html.index('id="reservationsDeck"')
    assert html.index('id="summaryDeck"') < html.index('id="fleetPulse"') < html.index('id="productionReadinessPanel"') < html.index('id="decisionRail"')
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
    assert 'telemetryError: false' in app_js
    assert 'value: state.telemetryError ? t("fleetPulse.telemetryValueUnavailable") : state.telemetryConfigured ? `${fleetTelemetryCount}/${fleetTelemetryTotal}` : "—"' in app_js
    assert '? "fleetPulse.telemetryUnavailable"' in app_js
    assert 'let configured = state.netfleetConfig?.configured;' in app_js
    assert 'state.netfleetConfig = await apiFetch("/cars/telemetry/config", { headers: authHeaders() });' in app_js
    assert "state.telemetryError = Boolean(configured);" in app_js
    assert '"fleetPulse.telemetryValueUnavailable": "Няма връзка"' in i18n_js
    assert '"fleetPulse.telemetryUnavailable": "NetFleet е конфигуриран, но live GPS временно не отговаря."' in i18n_js
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
    schemas = _read("schemas.py")
    router = _read("routers/users.py")

    assert 'id="newGsmNumber"' in html
    assert 'type="tel"' in html
    assert "GSM номер" in html
    assert "newGsmNumber: document.getElementById" in app_js
    assert "gsm_number: els.newGsmNumber?.value.trim() || null" in app_js
    assert "function contactEditDialog(user)" in app_js
    assert 'data-user-contact="${user.id}"' in app_js
    assert "updateUserContact(Number(userContactButton.dataset.userContact))" in app_js
    assert "UserContactUpdatePayload" in schemas
    assert '@router.put("/{user_id}/contact"' in router
    assert 'user.gsm": "GSM: {number}"' in i18n_js
    assert 'audit.contact_updated": "Контакт обновен"' in i18n_js


def test_admin_user_cards_use_scannable_density_layout() -> None:
    app_js = _read("static/app.js")
    css = _read("static/styles.css")
    i18n_js = _read("static/i18n.js")

    assert 'class="user-card__signals"' in app_js
    assert 'class="user-card__action-group user-card__action-group--primary"' in app_js
    render_users_src = app_js[app_js.index("function renderUsers()") : app_js.index("function renderCars()")]
    assert 'class="car-card__actions"' not in render_users_src
    assert ".user-card__meta {\n  display: grid;" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in css
    assert "@media (max-width: 760px)" in css
    assert ".user-card__action-group .action-btn" in css
    assert '"user.contactMissing": "не е въведено"' in i18n_js


def test_admin_bulk_employee_import_supports_name_surname_gsm_source() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    schemas = _read("schemas.py")
    router = _read("routers/users.py")

    assert 'id="employeeImportPanel"' in html
    assert 'id="employeeImportText"' in html
    assert "Използват се Име + Фамилия + GSM" in html
    assert 'id="employeeImportPassword"' in html
    assert 'id="employeeImportResetPasswords"' in html
    assert 'apiFetch("/users/import-employees"' in app_js
    assert "function validateEmployeeImportForm()" in app_js
    assert "EmployeeImportPayload" in schemas
    assert "EmployeeImportResponse" in schemas
    assert '@router.post("/import-employees"' in router
    assert "role='employee'" in router
    assert "Презиме" in html


def test_admin_production_readiness_panel_is_present_and_secret_safe() -> None:
    html = _read("templates/admin.html")
    app_js = _read("static/app.js")
    i18n_js = _read("static/i18n.js")
    styles = _read("static/styles.css")

    assert 'id="productionReadinessPanel"' in html
    assert html.index('id="fleetPulse"') < html.index('id="productionReadinessPanel"') < html.index('id="decisionRail"')
    assert 'id="productionReadinessSummary"' in html
    assert 'id="productionReadinessList"' in html
    assert "function loadProductionReadiness()" in app_js
    assert "function renderProductionReadiness()" in app_js
    assert "function sortedReadinessItems(items = [])" in app_js
    assert "function readinessItemMarkup(item)" in app_js
    assert "function readinessFocusMarkup(items = [])" in app_js
    assert "function readinessCountsText(failed, warnings)" in app_js
    assert "function readinessNextStep(item)" in app_js
    assert 'apiFetch("/ops/readiness"' in app_js
    assert '"readiness.notReady": "Има блокери преди live"' in i18n_js
    assert '"readiness.focusTitle": "Най-важното сега"' in i18n_js
    assert '"readiness.focusClear": "Няма открити runtime блокери; останалите проверки са за справка."' in i18n_js
    assert '"readiness.passedToggle": "Проверени проверки ({count})"' in i18n_js
    assert '"readiness.next.cors": "Замени example/wildcard с реалния production домейн."' in i18n_js
    assert '"readiness.next.admin_redundancy": "Добави втори активен fleet_admin за continuity."' in i18n_js
    assert '"readiness.next.restore_drill": "Пусни `make prod-backup` и `make prod-restore-drill BACKUP=...`, за да има свеж restore marker."' in i18n_js
    assert '"readiness.next.notification_recipients": "Попълни липсващите user email-и или задай SMTP_TO_EMAIL като shared fallback inbox."' in i18n_js
    assert '"readiness.warnings.one": "{count} бележка"' in i18n_js
    assert ".readiness-summary__focus" in styles
    assert ".readiness-summary__focus-list" in styles
    assert ".readiness-pass-group" in styles
    assert ".readiness-pass-group__list" in styles
    assert ".readiness-item--fail span" in styles
    assert ".readiness-item__next" in styles
    assert "SECRET_KEY" not in html
    assert "POSTGRES_PASSWORD" not in html
