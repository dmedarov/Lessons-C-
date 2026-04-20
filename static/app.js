function t(key, vars = {}) {
  return window.FleetFlowI18n?.t(key, vars) || key;
}

function pluralRecord(count) {
  return window.FleetFlowI18n?.pluralRecord(count) || `${count} запис(а)`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

const surface = document.body.dataset.surface || "employee";
const operationalRoles = new Set(["fleet_admin", "fleet_approver", "fleet_reception"]);

const state = {
  token: null,
  hasAdmin: true,
  surface,
  currentRole: null,
  currentUser: null,
  carFilter: "active",
  scope: "smart",
  status: surface === "admin" ? "pending" : "open",
  reservationSearch: "",
  reservationStartDate: "",
  reservationEndDate: "",
  notificationPollId: null,
  cars: [],
  reservations: [],
  pulseReservations: [],
  publicOverview: null,
  publicCalendar: [],
  notifications: [],
  telemetry: [],
  telemetryConfigured: false,
  intelligencePulse: null,
  netfleetConfig: null,
  productionReadiness: null,
  pickupTelemetry: null,
  reservationPreferences: null,
  users: [],
  userAudit: {},
  blackouts: [],
  loading: {
    cars: false,
    reservations: false,
    pulseReservations: false,
    publicOverview: false,
    publicCalendar: false,
    intelligencePulse: false,
    notifications: false,
    telemetry: false,
    netfleetConfig: false,
    productionReadiness: false,
    pickupTelemetry: false,
    preferences: false,
    users: false,
    blackouts: false,
  },
  selectedReservationIds: new Set(),
  conflictPreview: {
    requested: false,
    loading: false,
    error: null,
    items: [],
    requestId: 0,
  },
  calendarDate: startOfMonth(new Date()),
  selectedDateKey: dateKey(new Date()),
};

const els = {
  bootstrapForm: document.getElementById("bootstrapForm"),
  bootstrapUsername: document.getElementById("bootstrapUsername"),
  bootstrapDisplayName: document.getElementById("bootstrapDisplayName"),
  bootstrapPassword: document.getElementById("bootstrapPassword"),
  bootstrapToken: document.getElementById("bootstrapToken"),
  setupPanel: document.getElementById("setupPanel"),
  loginPanel: document.getElementById("loginPanel"),
  sessionPanel: document.getElementById("sessionPanel"),
  loginForm: document.getElementById("loginForm"),
  logoutBtn: document.getElementById("logoutBtn"),
  logoutBtnSecondary: document.getElementById("logoutBtnSecondary"),
  username: document.getElementById("username"),
  password: document.getElementById("password"),
  sessionBadge: document.getElementById("sessionBadge"),
  notificationBadge: document.getElementById("notificationBadge"),
  sessionTitle: document.getElementById("sessionTitle"),
  sessionModePill: document.getElementById("sessionModePill"),
  sessionMeta: document.getElementById("sessionMeta"),
  heroCaption: document.getElementById("heroCaption"),
  guidanceCard: document.getElementById("guidanceCard"),
  reservationForm: document.getElementById("reservationForm"),
  quickBookPanel: document.getElementById("quickBookPanel"),
  quickBookBtn: document.getElementById("quickBookBtn"),
  quickBookHint: document.getElementById("quickBookHint"),
  smartPrefillPanel: document.getElementById("smartPrefillPanel"),
  smartPrefillBtn: document.getElementById("smartPrefillBtn"),
  smartPrefillHint: document.getElementById("smartPrefillHint"),
  passwordForm: document.getElementById("passwordForm"),
  userForm: document.getElementById("userForm"),
  carForm: document.getElementById("carForm"),
  netfleetForm: document.getElementById("netfleetForm"),
  netfleetApiKey: document.getElementById("netfleetApiKey"),
  netfleetConfigStatus: document.getElementById("netfleetConfigStatus"),
  productionReadinessPanel: document.getElementById("productionReadinessPanel"),
  productionReadinessSummary: document.getElementById("productionReadinessSummary"),
  productionReadinessList: document.getElementById("productionReadinessList"),
  reservationPanel: document.getElementById("reservationPanel"),
  passwordPanel: document.getElementById("passwordPanel"),
  userCreatePanel: document.getElementById("userCreatePanel"),
  carPanel: document.getElementById("carPanel"),
  usersDeck: document.getElementById("usersDeck"),
  summaryDeck: document.getElementById("summaryDeck"),
  markAllReadBtn: document.getElementById("markAllReadBtn"),
  notificationsList: document.getElementById("notificationsList"),
  usersGrid: document.getElementById("usersGrid"),
  carId: document.getElementById("carId"),
  startTime: document.getElementById("startTime"),
  endTime: document.getElementById("endTime"),
  conflictPreview: document.getElementById("conflictPreview"),
  purpose: document.getElementById("purpose"),
  currentPassword: document.getElementById("currentPassword"),
  newPassword: document.getElementById("newPassword"),
  newUsername: document.getElementById("newUsername"),
  newDisplayName: document.getElementById("newDisplayName"),
  newGsmNumber: document.getElementById("newGsmNumber"),
  newRole: document.getElementById("newRole"),
  newUserPassword: document.getElementById("newUserPassword"),
  handoffForm: document.getElementById("handoffForm"),
  handoffUserId: document.getElementById("handoffUserId"),
  handoffReason: document.getElementById("handoffReason"),
  handoffDemoteSelf: document.getElementById("handoffDemoteSelf"),
  blackoutForm: document.getElementById("blackoutForm"),
  blackoutCarId: document.getElementById("blackoutCarId"),
  blackoutKind: document.getElementById("blackoutKind"),
  blackoutStartTime: document.getElementById("blackoutStartTime"),
  blackoutEndTime: document.getElementById("blackoutEndTime"),
  blackoutReason: document.getElementById("blackoutReason"),
  blackoutsList: document.getElementById("blackoutsList"),
  plate: document.getElementById("plate"),
  model: document.getElementById("model"),
  carsGrid: document.getElementById("carsGrid"),
  reservationsTableBody: document.getElementById("reservationsTableBody"),
  reservationsTimeline: document.getElementById("reservationsTimeline"),
  decisionRail: document.getElementById("decisionRail"),
  receptionRail: document.getElementById("receptionRail"),
  fleetPulse: document.getElementById("fleetPulse"),
  overviewStats: document.getElementById("overviewStats"),
  currentTripHero: document.getElementById("currentTripHero"),
  message: document.getElementById("message"),
  messageTitle: document.getElementById("messageTitle"),
  messageText: document.getElementById("messageText"),
  messageList: document.getElementById("messageList"),
  calendarGrid: document.getElementById("calendarGrid"),
  calendarMonthLabel: document.getElementById("calendarMonthLabel"),
  selectedDateLabel: document.getElementById("selectedDateLabel"),
  selectedDateMeta: document.getElementById("selectedDateMeta"),
  dayTimeline: document.getElementById("dayTimeline"),
  monthPrev: document.getElementById("monthPrev"),
  monthNext: document.getElementById("monthNext"),
  todayFocus: document.getElementById("todayFocus"),
  modeHeading: document.getElementById("modeHeading"),
  modeCopy: document.getElementById("modeCopy"),
  nextSignalTitle: document.getElementById("nextSignalTitle"),
  nextSignalCopy: document.getElementById("nextSignalCopy"),
  nextSignalActions: document.getElementById("nextSignalActions"),
  reservationSearch: document.getElementById("reservationSearch"),
  reservationStartDate: document.getElementById("reservationStartDate"),
  reservationEndDate: document.getElementById("reservationEndDate"),
  clearReservationFiltersBtn: document.getElementById("clearReservationFiltersBtn"),
  exportReservationsBtn: document.getElementById("exportReservationsBtn"),
  bulkActionBar: document.getElementById("bulkActionBar"),
  bulkSelectedCount: document.getElementById("bulkSelectedCount"),
  bulkSelectAll: document.getElementById("bulkSelectAll"),
  bulkClearBtn: document.getElementById("bulkClearBtn"),
  bulkApproveBtn: document.getElementById("bulkApproveBtn"),
  bulkRejectBtn: document.getElementById("bulkRejectBtn"),
};

function isFullAdmin() {
  return state.currentRole === "fleet_admin";
}

function canApproveReservations() {
  return ["fleet_admin", "fleet_approver"].includes(state.currentRole);
}

function canManageTripHandoff() {
  return ["fleet_admin", "fleet_reception"].includes(state.currentRole);
}

function isOperationalRole() {
  return operationalRoles.has(state.currentRole);
}

function roleBadgeClass(role = state.currentRole) {
  if (role === "fleet_admin") return "status-pill--admin";
  if (role === "fleet_approver") return "status-pill--admin";
  if (role === "fleet_reception") return "status-pill--muted";
  return "status-pill--employee";
}

function defaultStatusForRole(role = state.currentRole) {
  if (surface !== "admin") return "open";
  if (role === "fleet_reception") return "approved";
  if (role === "fleet_admin" || role === "fleet_approver") return "pending";
  return "open";
}

const fieldErrorIds = [
  "bootstrapUsername",
  "bootstrapDisplayName",
  "bootstrapPassword",
  "username",
  "password",
  "carId",
  "startTime",
  "endTime",
  "purpose",
  "currentPassword",
  "newPassword",
  "newUsername",
  "newDisplayName",
  "newGsmNumber",
  "newUserPassword",
  "plate",
  "model",
  "netfleetApiKey",
];

let conflictPreviewTimer = null;
let reservationFilterTimer = null;
const mobileCalendarMedia = window.matchMedia("(max-width: 767px)");

function startOfMonth(value) {
  return new Date(value.getFullYear(), value.getMonth(), 1);
}

function addMonths(value, amount) {
  return new Date(value.getFullYear(), value.getMonth() + amount, 1);
}

function addDays(value, amount) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate() + amount);
}

function dateKey(value) {
  return [
    value.getFullYear(),
    String(value.getMonth() + 1).padStart(2, "0"),
    String(value.getDate()).padStart(2, "0"),
  ].join("-");
}

function localDateFromKey(key) {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function authHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  return headers;
}

function toggleHidden(node, hidden) {
  if (!node) return;
  node.classList.toggle("hidden", hidden);
}

function bind(node, eventName, handler) {
  if (!node) return;
  node.addEventListener(eventName, handler);
}

function setLoading(section, value) {
  state.loading[section] = value;
}

function skeletonCards(count = 3) {
  return Array.from({ length: count }, () => `<article class="skeleton-card" aria-hidden="true">
    <span class="skeleton skeleton--title"></span>
    <span class="skeleton skeleton--line"></span>
    <span class="skeleton skeleton--line skeleton--short"></span>
  </article>`).join("");
}

function skeletonTableRow(colspan) {
  return `<tr class="skeleton-row" aria-hidden="true"><td colspan="${colspan}">
    <span class="skeleton skeleton--line"></span>
    <span class="skeleton skeleton--line skeleton--short"></span>
  </td></tr>`;
}

function setSubmitBusy(form, busyLabel = t("form.submit.loading")) {
  const submitButton = form?.querySelector('button[type="submit"]');
  if (!submitButton) {
    return () => {};
  }
  const originalText = submitButton.textContent;
  submitButton.disabled = true;
  submitButton.dataset.loading = "true";
  submitButton.textContent = busyLabel;
  return () => {
    submitButton.disabled = false;
    submitButton.dataset.loading = "false";
    submitButton.textContent = originalText;
  };
}

function confirmAction(message, confirmLabel = t("action.confirm")) {
  if (!("HTMLDialogElement" in window)) {
    return Promise.resolve(window.confirm(message));
  }

  return new Promise((resolve) => {
    const returnFocusTo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = document.createElement("dialog");
    const titleId = `confirm-title-${Date.now()}`;
    const descriptionId = `confirm-description-${Date.now()}`;
    dialog.className = "confirm-dialog";
    dialog.setAttribute("aria-labelledby", titleId);
    dialog.setAttribute("aria-describedby", descriptionId);
    dialog.setAttribute("aria-modal", "true");

    const title = document.createElement("h2");
    title.id = titleId;
    title.textContent = t("confirm.title");

    const copy = document.createElement("p");
    copy.id = descriptionId;
    copy.textContent = message;

    const actions = document.createElement("div");
    actions.className = "confirm-dialog__actions";

    const cancelButton = document.createElement("button");
    cancelButton.className = "btn btn--ghost";
    cancelButton.type = "button";
    cancelButton.textContent = t("action.keep");

    const confirmButton = document.createElement("button");
    confirmButton.className = "btn btn--primary";
    confirmButton.type = "button";
    confirmButton.textContent = confirmLabel;

    const close = (confirmed) => {
      dialog.close();
      dialog.remove();
      returnFocusTo?.focus();
      resolve(confirmed);
    };

    cancelButton.addEventListener("click", () => close(false));
    confirmButton.addEventListener("click", () => close(true));
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      close(false);
    });

    actions.append(cancelButton, confirmButton);
    dialog.append(title, copy, actions);
    document.body.appendChild(dialog);
    dialog.showModal();
    confirmButton.focus();
  });
}

function userDialog({ title, body, confirmLabel, renderFields, readValue, validate }) {
  if (!("HTMLDialogElement" in window)) {
    return Promise.resolve(null);
  }

  return new Promise((resolve) => {
    const returnFocusTo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = document.createElement("dialog");
    const titleId = `user-dialog-title-${Date.now()}`;
    const descriptionId = `user-dialog-description-${Date.now()}`;
    const errorId = `user-dialog-error-${Date.now()}`;
    dialog.className = "confirm-dialog user-admin-dialog";
    dialog.setAttribute("aria-labelledby", titleId);
    dialog.setAttribute("aria-describedby", descriptionId);
    dialog.setAttribute("aria-modal", "true");

    const heading = document.createElement("h2");
    heading.id = titleId;
    heading.textContent = title;

    const copy = document.createElement("p");
    copy.id = descriptionId;
    copy.textContent = body;

    const form = document.createElement("form");
    form.className = "stack";
    form.method = "dialog";
    form.setAttribute("aria-describedby", errorId);
    form.innerHTML = `${renderFields()}<small class="field__error" id="${errorId}" data-dialog-error role="alert" aria-live="polite"></small>`;

    const actions = document.createElement("div");
    actions.className = "confirm-dialog__actions";

    const cancelButton = document.createElement("button");
    cancelButton.className = "btn btn--ghost";
    cancelButton.type = "button";
    cancelButton.textContent = t("action.keep");

    const confirmButton = document.createElement("button");
    confirmButton.className = "btn btn--primary";
    confirmButton.type = "submit";
    confirmButton.textContent = confirmLabel;

    const close = (value) => {
      dialog.close();
      dialog.remove();
      returnFocusTo?.focus();
      resolve(value);
    };

    cancelButton.addEventListener("click", () => close(null));
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      close(null);
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const value = readValue(form);
      const error = validate ? validate(value) : null;
      const fields = form.querySelectorAll("input, select, textarea");
      fields.forEach((field) => {
        field.removeAttribute("aria-invalid");
        if (field.getAttribute("aria-describedby") === errorId) {
          field.removeAttribute("aria-describedby");
        }
      });
      if (error) {
        const message = typeof error === "string" ? error : error.message;
        const targetField =
          typeof error === "string" ? fields[0] : form.elements[error.fieldName] || fields[0];
        form.querySelector("[data-dialog-error]").textContent = message;
        if (targetField instanceof HTMLElement) {
          targetField.setAttribute("aria-invalid", "true");
          targetField.setAttribute("aria-describedby", errorId);
          targetField.focus();
        }
        return;
      }
      close(value);
    });

    actions.append(cancelButton, confirmButton);
    form.appendChild(actions);
    dialog.append(heading, copy, form);
    document.body.appendChild(dialog);
    dialog.showModal();
    form.querySelector("input, select, textarea")?.focus();
  });
}

function resetPasswordDialog(user) {
  return userDialog({
    title: t("admin.resetPasswordTitle", { name: user.display_name }),
    body: t("admin.resetPasswordBody"),
    confirmLabel: t("action.resetPassword"),
    renderFields: () => `
      <label class="field">
        <span>${t("admin.passwordLabel")}</span>
        <input name="newPassword" type="password" autocomplete="new-password" />
      </label>
      <label class="field">
        <span>${t("admin.reasonLabel")}</span>
        <textarea name="reason" rows="3"></textarea>
      </label>
    `,
    readValue: (form) => ({
      new_password: form.elements.newPassword.value,
      reason: form.elements.reason.value.trim() || null,
    }),
    validate: (value) =>
      value.new_password.length < 8 ? { message: t("admin.passwordTooShort"), fieldName: "newPassword" } : null,
  });
}

function editBlackoutDialog(blackout) {
  const startLocal = localInputValue(new Date(blackout.start_time));
  const endLocal = localInputValue(new Date(blackout.end_time));
  return userDialog({
    title: t("admin.editBlackoutTitle", { id: blackout.id }),
    body: t("admin.editBlackoutBody"),
    confirmLabel: t("action.save"),
    renderFields: () => `
      <label class="field">
        <span>${t("admin.blackoutKindLabel")}</span>
        <select name="kind">
          <option value="maintenance" ${blackout.kind === "maintenance" ? "selected" : ""}>${t("blackout.kind.maintenance")}</option>
          <option value="service" ${blackout.kind === "service" ? "selected" : ""}>${t("blackout.kind.service")}</option>
          <option value="inspection" ${blackout.kind === "inspection" ? "selected" : ""}>${t("blackout.kind.inspection")}</option>
          <option value="blocked" ${blackout.kind === "blocked" ? "selected" : ""}>${t("blackout.kind.blocked")}</option>
        </select>
      </label>
      <label class="field">
        <span>Начало</span>
        <input name="startTime" type="datetime-local" value="${startLocal}" />
      </label>
      <label class="field">
        <span>Край</span>
        <input name="endTime" type="datetime-local" value="${endLocal}" />
      </label>
      <label class="field">
        <span>Причина</span>
        <textarea name="reason" rows="3">${escapeHtml(blackout.reason || "")}</textarea>
      </label>
    `,
    readValue: (form) => ({
      kind: form.elements.kind.value,
      start_time: toIso(form.elements.startTime.value),
      end_time: toIso(form.elements.endTime.value),
      reason: form.elements.reason.value.trim() || null,
    }),
    validate: (value) => {
      if (!value.start_time) return { message: "Въведи начало.", fieldName: "startTime" };
      if (!value.end_time) return { message: "Въведи край.", fieldName: "endTime" };
      if (new Date(value.end_time) <= new Date(value.start_time)) {
        return { message: "Краят трябва да е след началото.", fieldName: "endTime" };
      }
      return null;
    },
  });
}

function roleChangeDialog(user) {
  return userDialog({
    title: t("admin.changeRoleTitle", { name: user.display_name }),
    body: t("admin.changeRoleBody"),
    confirmLabel: t("action.changeRole"),
    renderFields: () => `
      <label class="field">
        <span>${t("admin.roleLabel")}</span>
        <select name="role">
          <option value="employee" ${user.role === "employee" ? "selected" : ""}>${t("role.employee")}</option>
          <option value="fleet_approver" ${user.role === "fleet_approver" ? "selected" : ""}>${t("role.fleet_approver")}</option>
          <option value="fleet_reception" ${user.role === "fleet_reception" ? "selected" : ""}>${t("role.fleet_reception")}</option>
          <option value="fleet_admin" ${user.role === "fleet_admin" ? "selected" : ""}>${t("role.fleet_admin")}</option>
        </select>
      </label>
      <label class="field">
        <span>${t("admin.reasonLabel")}</span>
        <textarea name="reason" rows="3"></textarea>
      </label>
    `,
    readValue: (form) => ({
      role: form.elements.role.value,
      reason: form.elements.reason.value.trim() || null,
    }),
  });
}

function cancelReservationDialog(id) {
  return userDialog({
    title: t("reservation.cancelTitle", { id }),
    body: t("reservation.cancelBody"),
    confirmLabel: t("action.cancel"),
    renderFields: () => `
      <label class="field">
        <span>${t("reservation.cancelReasonLabel")}</span>
        <textarea name="reason" rows="3" required placeholder="${t("reservation.cancelReasonPlaceholder")}"></textarea>
      </label>
    `,
    readValue: (form) => ({ note: form.elements.reason.value.trim() }),
    validate: (value) =>
      !value.note ? { message: t("reservation.cancelReasonRequired"), fieldName: "reason" } : null,
  });
}

function clearErrors() {
  fieldErrorIds.forEach((id) => {
    const errorNode = document.getElementById(`${id}Error`);
    const inputNode = document.getElementById(id);
    if (errorNode) {
      errorNode.textContent = "";
    }
    if (inputNode) {
      inputNode.removeAttribute("aria-invalid");
      if (inputNode.getAttribute("aria-describedby") === `${id}Error`) {
        inputNode.removeAttribute("aria-describedby");
      }
    }
  });
}

function setFieldError(id, message) {
  const errorNode = document.getElementById(`${id}Error`);
  const inputNode = document.getElementById(id);
  if (errorNode) {
    errorNode.textContent = message;
  }
  if (inputNode) {
    inputNode.setAttribute("aria-invalid", "true");
    inputNode.setAttribute("aria-describedby", `${id}Error`);
  }
}

function showMessage(title, text, type = "error", details = []) {
  els.message.classList.remove("hidden", "alert-strip--success", "alert-strip--error");
  els.message.classList.add(type === "success" ? "alert-strip--success" : "alert-strip--error");
  els.messageTitle.textContent = title;
  els.messageText.textContent = text;
  els.messageList.innerHTML = "";
  details.forEach((detail) => {
    const item = document.createElement("li");
    item.textContent = detail;
    els.messageList.appendChild(item);
  });
  els.message.focus();
}

function hideMessage() {
  els.message.classList.add("hidden");
  els.messageList.innerHTML = "";
}

function formatDateTime(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("bg-BG", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function formatTelemetryTime(value) {
  if (!value) return "—";
  const raw = String(value);
  const normalized = raw.includes("T") ? raw : `${raw.replace(" ", "T")}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? raw : formatDateTime(date.toISOString());
}

function formatCoordinate(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(5) : "—";
}

function formatMonthLabel(value) {
  return new Intl.DateTimeFormat("bg-BG", { month: "long", year: "numeric" }).format(value);
}

function formatDayLabel(key) {
  return new Intl.DateTimeFormat("bg-BG", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(localDateFromKey(key));
}

function nextLocalSlot(minutesFromNow = 30) {
  const date = new Date(Date.now() + minutesFromNow * 60 * 1000);
  date.setSeconds(0, 0);
  return date.toISOString().slice(0, 16);
}

function toIso(localValue) {
  return localValue ? new Date(localValue).toISOString() : null;
}

function dateFilterIso(dateValue, endOfDay = false) {
  if (!dateValue) return null;
  const date = new Date(`${dateValue}T00:00:00`);
  if (endOfDay) {
    date.setDate(date.getDate() + 1);
  }
  return date.toISOString();
}

function localInputValue(date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function statusTag(status) {
  return `<span class="status-tag status-tag--${status}">${t(`status.${status}`)}</span>`;
}

function lifecycleLabel(status) {
  return t(`status.${status}`);
}

function lifecycleMeter(item) {
  const flow = ["pending", "approved", "checked_out", "returned"];
  const currentIndex = flow.indexOf(item.status);
  if (currentIndex === -1) {
    return `
      <div class="lifecycle-meter lifecycle-meter--terminal" aria-label="Lifecycle статус: ${lifecycleLabel(item.status)}">
        <span class="lifecycle-step lifecycle-step--current">
          <span class="lifecycle-step__dot" aria-hidden="true"></span>
          <span>${lifecycleLabel(item.status)}</span>
        </span>
      </div>
    `;
  }

  return `
    <ol class="lifecycle-meter" aria-label="Lifecycle статус: ${lifecycleLabel(item.status)}">
      ${flow
        .map((status, index) => {
          const stepClass =
            index < currentIndex
              ? "lifecycle-step--complete"
              : index === currentIndex
                ? "lifecycle-step--current"
                : "lifecycle-step--upcoming";
          const currentAttr = index === currentIndex ? ' aria-current="step"' : "";
          return `
            <li class="lifecycle-step ${stepClass}"${currentAttr}>
              <span class="lifecycle-step__dot" aria-hidden="true"></span>
              <span>${lifecycleLabel(status)}</span>
            </li>
          `;
        })
        .join("")}
    </ol>
  `;
}

function calendarPill(item, car) {
  const label = item.plate_number || (car ? car.plate_number : `Car ${item.car_id}`);
  return `<span class="calendar-pill calendar-pill--${item.status}">${escapeHtml(label)}</span>`;
}

function carMap() {
  return new Map(state.cars.map((car) => [car.id, car]));
}

function telemetryByPlate() {
  return new Map(state.telemetry.map((item) => [String(item.plate_number || "").trim().toUpperCase(), item]));
}

function calendarSourceItems() {
  if (!state.token) return state.publicCalendar;
  if (!isOperationalRole()) return state.reservations;
  const source = state.pulseReservations.length || state.loading.pulseReservations ? state.pulseReservations : state.reservations;
  const currentStatuses =
    state.currentRole === "fleet_reception" ? ["approved", "checked_out"] : ["pending", "approved", "checked_out"];
  return source.filter((item) => currentStatuses.includes(item.status));
}

function dayMap() {
  const map = new Map();
  const calendarItems = calendarSourceItems();
  calendarItems.forEach((item) => {
    const key = dateKey(new Date(item.start_time));
    const list = map.get(key) || [];
    list.push(item);
    map.set(key, list);
  });
  return map;
}

function conflictDateKeys() {
  const keys = new Set();
  state.conflictPreview.items.forEach((item) => {
    const start = new Date(item.start_time);
    const end = new Date(item.end_time);
    const cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    const final = new Date(end.getFullYear(), end.getMonth(), end.getDate());
    while (cursor <= final) {
      keys.add(dateKey(cursor));
      cursor.setDate(cursor.getDate() + 1);
    }
  });
  return keys;
}

async function parseJsonResponse(response) {
  let data = null;
  try {
    data = await response.json();
  } catch (_error) {
    data = null;
  }
  return data;
}

async function refreshAccessToken() {
  const response = await fetch("/auth/refresh", {
    method: "POST",
    credentials: "same-origin",
  });
  const data = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(data?.detail || "Сесията изтече.");
  }
  state.token = data.access_token;
  state.currentRole = data.role;
  if (state.currentUser) {
    state.currentUser = {
      ...state.currentUser,
      display_name: data.user,
      role: data.role,
    };
  }
  renderShell();
  startNotificationPolling();
  return data.access_token;
}

function shouldAttemptRefresh(url, options, response) {
  if (response.status !== 401 || options.skipRefresh) {
    return false;
  }
  return !["/auth/login", "/auth/bootstrap-admin", "/auth/refresh", "/auth/logout"].includes(url);
}

async function apiFetch(url, options = {}) {
  const { skipRefresh: _skipRefresh, ...fetchOptions } = options;
  const requestOptions = {
    credentials: "same-origin",
    ...fetchOptions,
  };
  const response = await fetch(url, requestOptions);
  let data = await parseJsonResponse(response);

  if (!response.ok) {
    if (shouldAttemptRefresh(url, options, response)) {
      try {
        await refreshAccessToken();
        const retryHeaders = {
          ...(requestOptions.headers || {}),
          ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
        };
        const retryResponse = await fetch(url, {
          ...requestOptions,
          headers: retryHeaders,
        });
        data = await parseJsonResponse(retryResponse);
        if (retryResponse.ok) {
          return data;
        }
        if (retryResponse.status === 401) {
          setSession(null, null);
        }
        throw new Error(data?.detail || "Неуспешна заявка към сървъра.");
      } catch (refreshError) {
        setSession(null, null);
        throw refreshError;
      }
    }
    if (response.status === 401) {
      setSession(null, null);
    }
    throw new Error(data?.detail || "Неуспешна заявка към сървъра.");
  }
  return data;
}

function setSession(user, token) {
  state.currentUser = user;
  state.currentRole = user ? user.role : null;
  state.token = token;
  if (user && token) {
    state.status = defaultStatusForRole(user.role);
    state.scope = operationalRoles.has(user.role) ? "all" : "smart";
    updateToolbarPressedStates(document.querySelectorAll("[data-status]"), "status");
    updateToolbarPressedStates(document.querySelectorAll("[data-scope]"), "scope");
  }
  if (user && token) {
    startNotificationPolling();
  } else {
    stopNotificationPolling();
  }
  renderShell();
}

function startNotificationPolling() {
  if (state.notificationPollId) return;
  state.notificationPollId = window.setInterval(async () => {
    if (!state.token) return;
    try {
      const previousIds = new Set(state.notifications.map((item) => item.id));
      await loadNotifications();
      if (hasNewReservationSignal(previousIds)) {
        await loadReservations();
        await loadPickupTelemetry();
        updateSummary();
      }
      updateOverview();
    } catch (error) {
      console.warn("Notification polling failed", error);
    }
  }, 30000);
}

function stopNotificationPolling() {
  if (!state.notificationPollId) return;
  window.clearInterval(state.notificationPollId);
  state.notificationPollId = null;
}

function renderShell() {
  const authenticated = Boolean(state.token && state.currentUser);
  const fullAdmin = isFullAdmin();
  const operationalMode = isOperationalRole();
  const adminSurface = state.surface === "admin";

  toggleHidden(els.setupPanel, state.hasAdmin || authenticated);
  toggleHidden(els.loginPanel, !state.hasAdmin || authenticated);
  toggleHidden(els.sessionPanel, !authenticated);
  toggleHidden(els.logoutBtn, !authenticated);
  toggleHidden(els.reservationPanel, !authenticated || operationalMode);
  toggleHidden(els.quickBookPanel, !authenticated || operationalMode);
  toggleHidden(els.smartPrefillPanel, !authenticated || operationalMode || !state.reservationPreferences?.available);
  toggleHidden(els.passwordPanel, !authenticated);
  toggleHidden(els.summaryDeck, !authenticated);
  toggleHidden(els.guidanceCard, authenticated);
  toggleHidden(els.userCreatePanel, !authenticated || !fullAdmin || !adminSurface);
  toggleHidden(els.carPanel, !authenticated || !fullAdmin || !adminSurface);
  toggleHidden(els.netfleetForm?.closest(".glass-card"), !authenticated || !fullAdmin || !adminSurface);
  toggleHidden(els.productionReadinessPanel, !authenticated || !fullAdmin || !adminSurface);
  toggleHidden(els.usersDeck, !authenticated || !fullAdmin || !adminSurface);
  toggleHidden(els.handoffForm?.closest(".glass-card"), !authenticated || !fullAdmin || !adminSurface);
  toggleHidden(els.blackoutForm?.closest(".glass-card"), !authenticated || !fullAdmin || !adminSurface);
  toggleHidden(els.blackoutsList?.closest(".glass-card"), !authenticated || !fullAdmin || !adminSurface);

  if (!state.hasAdmin && !authenticated) {
    els.sessionBadge.className = "status-pill status-pill--muted";
    els.sessionBadge.textContent = t("ui.initialSetup");
    return;
  }

  if (!authenticated) {
    els.sessionBadge.className = "status-pill status-pill--muted";
    els.sessionBadge.textContent = t("ui.waitingLogin");
    return;
  }

  const roleClass = roleBadgeClass();
  els.sessionBadge.className = `status-pill ${roleClass}`;
  els.sessionBadge.textContent = `${state.currentUser.display_name} · ${t(`role.${state.currentRole}`)}`;
  els.sessionTitle.textContent = operationalMode ? t(`ui.${state.currentRole}Ready`) : t("ui.employeeReady");
  els.sessionModePill.className = `status-pill ${roleClass}`;
  els.sessionModePill.textContent = t(`role.${state.currentRole}`);
  els.sessionMeta.textContent = `${state.currentUser.display_name} (${state.currentUser.username})`;
  if (els.heroCaption) {
    if (fullAdmin) {
      els.heroCaption.textContent = adminSurface
        ? "Admin страницата събира настройки, потребители, флот и пълен lifecycle контрол."
        : "За административни настройки отвори отделната Admin страница от горната навигация.";
    } else if (state.currentRole === "fleet_approver") {
      els.heroCaption.textContent = "Approver режимът показва чакащите заявки и решенията, без настройки и ключове.";
    } else if (state.currentRole === "fleet_reception") {
      els.heroCaption.textContent = "Reception режимът показва одобрените и активните курсове за ключове, документи и връщане.";
    } else {
      els.heroCaption.textContent = "Employee режимът показва само собствените ти заявки, нотификации и следващото практично действие.";
    }
  }
}

function hasNewReservationSignal(previousIds) {
  const lifecycleKinds = new Set([
    "reservation_decision",
    "reservation_cancelled",
    "trip_started",
    "trip_returned",
  ]);
  return state.notifications.some(
    (item) => item.reservation_id && lifecycleKinds.has(item.kind) && !previousIds.has(item.id)
  );
}

function updateOverview() {
  const overviewReservations = isOperationalRole() ? state.pulseReservations : state.reservations;
  const publicOverview = !state.token ? state.publicOverview : null;
  const activeCars = publicOverview?.active_cars ?? state.cars.filter((car) => car.active).length;
  const pending = publicOverview?.pending_requests ?? overviewReservations.filter((item) => item.status === "pending").length;
  const activeTrips = publicOverview?.active_trips ?? overviewReservations.filter((item) => item.status === "checked_out").length;
  const availableCars = publicOverview?.available_cars ?? Math.max(activeCars - activeTrips, 0);

  const kpiPending = document.getElementById("kpiPending");
  const kpiActive = document.getElementById("kpiActive");
  const kpiAvailable = document.getElementById("kpiAvailable");

  if (kpiPending) {
    kpiPending.querySelector(".stat-card__value").textContent = pending;
    kpiPending.classList.toggle("stat-card--urgent", pending > 0);
  }
  if (kpiActive) {
    kpiActive.querySelector(".stat-card__value").textContent = activeTrips;
    kpiActive.classList.toggle("stat-card--active-trips", activeTrips > 0);
  }
  if (kpiAvailable) {
    kpiAvailable.querySelector(".stat-card__value").textContent = availableCars;
    kpiAvailable.classList.toggle("stat-card--available", availableCars > 0);
  }
  renderFleetPulse();
}

function mostBookedCar(reservations, cars) {
  const counts = new Map();
  reservations
    .filter((item) => ["pending", "approved", "checked_out"].includes(item.status))
    .forEach((item) => counts.set(item.car_id, (counts.get(item.car_id) || 0) + 1));
  const [carId, count] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0] || [];
  if (!carId) return { label: t("fleetPulse.noBusiestCar"), count: 0 };
  const car = cars.get(carId);
  return {
    label: car ? `${car.plate_number} · ${car.model}` : t("entity.car", { id: carId }),
    count,
  };
}

function renderFleetPulse() {
  if (!els.fleetPulse) return;
  const showPulse = isFullAdmin() && surface === "admin" && state.token;
  toggleHidden(els.fleetPulse, !showPulse);
  if (!showPulse) {
    els.fleetPulse.innerHTML = "";
    return;
  }

  if (state.loading.pulseReservations || state.loading.intelligencePulse || state.loading.cars || state.loading.telemetry) {
    els.fleetPulse.innerHTML = `
      <div class="fleet-pulse__header">
        <div>
          <p class="panel__eyebrow">${escapeHtml(t("fleetPulse.eyebrow"))}</p>
          <h2 id="fleetPulseTitle">${escapeHtml(t("fleetPulse.loadingTitle"))}</h2>
        </div>
      </div>
      ${skeletonCards(1)}
    `;
    return;
  }

  const now = new Date();
  const oneHourFromNow = new Date(now.getTime() + 60 * 60 * 1000);
  const cars = carMap();
  const activeFleetPlates = new Set(
    state.cars
      .filter((car) => car.active)
      .map((car) => String(car.plate_number || "").trim().toUpperCase())
      .filter(Boolean)
  );
  const activeTrips = state.pulseReservations.filter((item) => item.status === "checked_out");
  const pending = state.pulseReservations.filter((item) => item.status === "pending").length;
  const intelligence = state.intelligencePulse;
  const releasingSoon = activeTrips.filter((item) => {
    const end = new Date(item.end_time);
    return end > now && end <= oneHourFromNow;
  }).length;
  const busiestCar = mostBookedCar(state.pulseReservations, cars);
  const fleetTelemetryCount = state.telemetry.filter((item) =>
    activeFleetPlates.has(String(item.plate_number || "").trim().toUpperCase())
  ).length;
  const fleetTelemetryTotal = activeFleetPlates.size || state.cars.filter((car) => car.active).length;

  const items = [
    {
      label: t("fleetPulse.activeTrips"),
      value: intelligence?.active_trips ?? activeTrips.length,
      detail: t(activeTrips.length ? "fleetPulse.activeTripsDetail" : "fleetPulse.activeTripsClear"),
    },
    {
      label: t("fleetPulse.releasingSoon"),
      value: releasingSoon,
      detail: t(releasingSoon ? "fleetPulse.releasingSoonDetail" : "fleetPulse.releasingSoonClear"),
    },
    {
      label: t("fleetPulse.pending"),
      value: intelligence?.pending_requests ?? pending,
      detail: t(pending ? "fleetPulse.pendingDetail" : "fleetPulse.pendingClear"),
    },
    {
      label: t("fleetPulse.busiestCar"),
      value: intelligence?.busiest_car || busiestCar.label,
      detail: busiestCar.count
        ? t("fleetPulse.busiestCarDetail", { count: busiestCar.count })
        : t("fleetPulse.busiestCarClear"),
    },
    {
      label: t("fleetPulse.telemetry"),
      value: state.telemetryConfigured ? `${fleetTelemetryCount}/${fleetTelemetryTotal}` : "—",
      detail: t(state.telemetryConfigured
        ? (fleetTelemetryCount ? "fleetPulse.telemetryDetail" : "fleetPulse.telemetryEmpty")
        : "fleetPulse.telemetryNotConfigured", {
          count: fleetTelemetryCount,
          total: fleetTelemetryTotal,
        }),
    },
  ];

  els.fleetPulse.innerHTML = `
    <div class="fleet-pulse__header">
      <div>
        <p class="panel__eyebrow">${escapeHtml(t("fleetPulse.eyebrow"))}</p>
        <h2 id="fleetPulseTitle">${escapeHtml(t("fleetPulse.title"))}</h2>
        <p class="section-copy">${escapeHtml(t("fleetPulse.copy"))}</p>
      </div>
    </div>
    <div class="fleet-pulse__grid">
      ${items.map((item) => `
        <article class="fleet-pulse__item">
          <span>${escapeHtml(item.label)}</span>
          <strong>${escapeHtml(item.value)}</strong>
          <p>${escapeHtml(item.detail)}</p>
        </article>
      `).join("")}
    </div>
    ${intelligence?.insights?.length ? `
      <div class="fleet-pulse__insights" aria-label="${escapeHtml(t("fleetPulse.insightsLabel"))}">
        ${intelligence.insights.map((insight) => `
          <article class="fleet-pulse__insight" data-severity="${escapeHtml(insight.severity || "info")}">
            <strong>${escapeHtml(insight.title)}</strong>
            <p>${escapeHtml(insight.body)}</p>
          </article>
        `).join("")}
      </div>
    ` : ""}
  `;
}

function renderNetfleetConfig() {
  if (!els.netfleetConfigStatus) return;
  const config = state.netfleetConfig;
  if (state.loading.netfleetConfig) {
    els.netfleetConfigStatus.textContent = t("netfleet.loading");
    return;
  }
  if (!config?.configured) {
    els.netfleetConfigStatus.textContent = t("netfleet.notConfigured");
    return;
  }
  if (config.source === "database") {
    els.netfleetConfigStatus.textContent = t("netfleet.configuredUi", {
      time: formatDateTime(config.updated_at),
    });
    return;
  }
  els.netfleetConfigStatus.textContent = t("netfleet.configuredRuntime");
}

function readinessStatusClass(status) {
  if (status === "pass") return "readiness-item--pass";
  if (status === "warn") return "readiness-item--warn";
  return "readiness-item--fail";
}

function readinessCountsText(failed, warnings) {
  const blockerText = t(failed === 1 ? "readiness.blockers.one" : "readiness.blockers.many", { count: failed });
  const warningText = t(warnings === 1 ? "readiness.warnings.one" : "readiness.warnings.many", { count: warnings });
  return `${blockerText} · ${warningText}`;
}

function renderProductionReadiness() {
  if (!els.productionReadinessSummary || !els.productionReadinessList) return;
  if (state.loading.productionReadiness) {
    els.productionReadinessSummary.innerHTML = `<span class="status-pill status-pill--muted">${escapeHtml(t("readiness.loading"))}</span>`;
    els.productionReadinessList.innerHTML = skeletonCards(2);
    return;
  }

  const data = state.productionReadiness;
  if (!data) {
    els.productionReadinessSummary.innerHTML = `<span class="status-pill status-pill--muted">${escapeHtml(t("readiness.unavailable"))}</span>`;
    els.productionReadinessList.innerHTML = "";
    return;
  }

  const failed = data.items.filter((item) => item.status === "fail").length;
  const warnings = data.items.filter((item) => item.status === "warn").length;
  const summaryKey = data.ready ? (warnings ? "readiness.readyWithWarnings" : "readiness.ready") : "readiness.notReady";
  const summaryClass = data.ready ? (warnings ? "readiness-summary--warn" : "readiness-summary--pass") : "readiness-summary--fail";

  els.productionReadinessSummary.className = `readiness-summary ${summaryClass}`;
  els.productionReadinessSummary.innerHTML = `
    <strong>${escapeHtml(t(summaryKey))}</strong>
    <span>${escapeHtml(readinessCountsText(failed, warnings))}</span>
  `;
  els.productionReadinessList.innerHTML = data.items.map((item) => `
    <article class="readiness-item ${readinessStatusClass(item.status)}">
      <div>
        <strong>${escapeHtml(item.label)}</strong>
        <p>${escapeHtml(item.detail)}</p>
      </div>
      <span>${escapeHtml(t(`readiness.status.${item.status}`))}</span>
    </article>
  `).join("");
}

function updateNotificationBadge() {
  if (!els.notificationBadge) return;
  const unread = state.notifications.filter((item) => !item.read_at).length;
  els.notificationBadge.textContent = unread > 99 ? "99+" : String(unread);
  els.notificationBadge.classList.toggle("hidden", !unread);
  els.notificationBadge.classList.toggle("notification-badge--pulse", unread > 0);
}

function setIntentActions(actions = []) {
  if (!els.nextSignalActions) return;
  toggleHidden(els.nextSignalActions, !actions.length);
  els.nextSignalActions.innerHTML = actions
    .map((action, index) => {
      const classes = action.primary ? "btn btn--primary" : "btn btn--ghost";
      const reservationId = action.reservationId ? ` data-reservation-id="${action.reservationId}"` : "";
      const reservationAction = action.reservationAction
        ? ` data-reservation-action-target="${action.reservationAction}"`
        : "";
      return `<button class="${classes}" type="button" data-intent-action="${action.name}"${reservationId}${reservationAction} ${index === 0 ? 'data-primary-intent="true"' : ""}>${escapeHtml(t(action.labelKey))}</button>`;
    })
    .join("");
}

function updateSummary() {
  if (!state.currentUser) {
    els.modeHeading.textContent = "Влез в системата";
    els.modeCopy.textContent = "След login ще видиш или личен operational desk, или глобален административен изглед.";
    els.nextSignalTitle.textContent = "Очаква setup";
    els.nextSignalCopy.textContent = state.hasAdmin
      ? "Влез с наличен профил, за да заредиш данните."
      : "Създай първия fleet admin, за да инициализираш системата.";
    setIntentActions([]);
    return;
  }

  if (isOperationalRole()) {
    const adminReservations = state.pulseReservations;
    const pending = adminReservations.filter((item) => item.status === "pending").length;
    const approved = adminReservations.filter((item) => item.status === "approved").length;
    const activeTrips = adminReservations.filter((item) => item.status === "checked_out").length;
    const adminSurface = state.surface === "admin";
    if (isFullAdmin()) {
      els.modeHeading.textContent = adminSurface ? "Admin control surface" : "Admin on employee desk";
      els.modeCopy.textContent = adminSurface
        ? "Пълен контрол за настройки, флот, потребители и lifecycle."
        : "Това е общият desk. За потребители, handoff и blackout-и използвай отделната Admin страница.";
    } else if (state.currentRole === "fleet_approver") {
      els.modeHeading.textContent = "Approver workspace";
      els.modeCopy.textContent = "Фокус само върху заявките за решение. Няма настройки, флот конфигурация или ключове.";
    } else {
      els.modeHeading.textContent = "Reception workspace";
      els.modeCopy.textContent = "Фокус върху реалното предаване и връщане: ключове, документи и активни курсове.";
    }
    if (canApproveReservations() && pending) {
      els.nextSignalTitle.textContent = t("intent.adminDecisionTitle", { count: pending });
      els.nextSignalCopy.textContent = t("intent.adminDecisionCopy");
      setIntentActions([
        { name: "review-pending", labelKey: "intent.action.reviewPending", primary: true },
        ...(isFullAdmin() ? [{ name: "view-fleet", labelKey: "intent.action.viewFleet" }] : []),
      ]);
      return;
    }
    if (canManageTripHandoff() && approved) {
      els.nextSignalTitle.textContent = t("intent.receptionApprovedTitle", { count: approved });
      els.nextSignalCopy.textContent = t("intent.receptionApprovedCopy");
      setIntentActions([
        { name: "view-handoffs", labelKey: "intent.action.viewHandoffs", primary: true },
        ...(isFullAdmin() ? [{ name: "view-fleet", labelKey: "intent.action.viewFleet" }] : []),
      ]);
      return;
    }
    if (canManageTripHandoff() && activeTrips) {
      els.nextSignalTitle.textContent = t("intent.receptionActiveTitle", { count: activeTrips });
      els.nextSignalCopy.textContent = t("intent.receptionActiveCopy");
      setIntentActions([
        { name: "view-active-trips", labelKey: "intent.action.viewActiveTrips", primary: true },
        ...(isFullAdmin() ? [{ name: "view-fleet", labelKey: "intent.action.viewFleet" }] : []),
      ]);
      return;
    }
    els.nextSignalTitle.textContent = t("intent.adminCalmTitle");
    els.nextSignalCopy.textContent = t("intent.adminCalmCopy");
    setIntentActions(isFullAdmin() ? [{ name: "view-fleet", labelKey: "intent.action.viewFleet", primary: true }] : []);
    return;
  }

  const activeTrip = state.reservations.find((item) => item.status === "checked_out");
  const nextApproved = [...state.reservations]
    .filter((item) => item.status === "approved")
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))[0];

  els.modeHeading.textContent = "Employee workspace";
  els.modeCopy.textContent = "Личен изглед с ясна история на заявките, активните курсове и нотификациите, които те касаят.";
  if (activeTrip) {
    els.nextSignalTitle.textContent = t("intent.employeeActiveTitle");
    els.nextSignalCopy.textContent = t("intent.employeeActiveCopy", { end: formatDateTime(activeTrip.end_time) });
    setIntentActions([
      { name: "focus-reservation", labelKey: "intent.action.viewTrip", primary: true, reservationId: activeTrip.id },
    ]);
    return;
  }
  if (nextApproved) {
    els.nextSignalTitle.textContent = t("intent.employeeApprovedTitle");
    els.nextSignalCopy.textContent = t("intent.employeeApprovedCopy", { start: formatDateTime(nextApproved.start_time) });
    setIntentActions([
      { name: "focus-reservation", labelKey: "intent.action.viewTrip", primary: true, reservationId: nextApproved.id },
    ]);
    return;
  }
  els.nextSignalTitle.textContent = t("intent.employeeFreeTitle");
  els.nextSignalCopy.textContent = t("intent.employeeFreeCopy");
  setIntentActions([
    { name: "book-now", labelKey: "intent.action.bookNow", primary: true },
    { name: "view-my-trips", labelKey: "intent.action.viewMyTrips" },
  ]);
}

function currentTripCandidate() {
  if (isOperationalRole()) return null;
  const activeTrip = state.reservations.find((item) => item.status === "checked_out");
  if (activeTrip) return activeTrip;
  return [...state.reservations]
    .filter((item) => item.status === "approved")
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))[0] || null;
}

function renderCurrentTripHero() {
  if (!els.currentTripHero) return;
  const item = state.currentUser ? currentTripCandidate() : null;
  toggleHidden(els.currentTripHero, !item);
  if (!item) {
    els.currentTripHero.innerHTML = "";
    return;
  }

  const car = carMap().get(item.car_id);
  const carLabel = car ? `${car.plate_number} · ${car.model}` : t("entity.car", { id: item.car_id });
  const active = item.status === "checked_out";
  const purpose = item.purpose
    ? `<p class="current-trip-hero__purpose">${escapeHtml(t("trip.hero.reason", { purpose: item.purpose }))}</p>`
    : "";
  const pickup = state.pickupTelemetry && state.pickupTelemetry.carId === item.car_id ? state.pickupTelemetry : null;
  const pickupMarkup = state.loading.pickupTelemetry
    ? `<div class="pickup-location"><strong>${escapeHtml(t("pickup.loading"))}</strong></div>`
    : pickup?.item
      ? `
        <div class="pickup-location">
          <strong>${escapeHtml(t("pickup.title"))}</strong>
          <span>${escapeHtml(t("telemetry.coordinates", {
            lat: formatCoordinate(pickup.item.latitude),
            lon: formatCoordinate(pickup.item.longitude),
          }))}</span>
          <span>${escapeHtml(t("telemetry.updated", { time: formatTelemetryTime(pickup.item.utc_time) }))}</span>
          ${pickup.item.latitude != null && pickup.item.longitude != null ? `<a class="ghost-link ghost-link--compact" href="https://www.google.com/maps?q=${encodeURIComponent(`${pickup.item.latitude},${pickup.item.longitude}`)}" target="_blank" rel="noreferrer">${escapeHtml(t("pickup.mapLink"))}</a>` : ""}
        </div>
      `
      : pickup?.configured
        ? `<div class="pickup-location"><strong>${escapeHtml(t("pickup.title"))}</strong><span>${escapeHtml(t("pickup.noSignal"))}</span></div>`
        : pickup?.error
          ? `<div class="pickup-location"><strong>${escapeHtml(t("pickup.title"))}</strong><span>${escapeHtml(t("pickup.unavailable"))}</span></div>`
          : pickup
            ? `<div class="pickup-location"><strong>${escapeHtml(t("pickup.title"))}</strong><span>${escapeHtml(t("pickup.notConfigured"))}</span></div>`
        : "";

  els.currentTripHero.innerHTML = `
    <div class="current-trip-hero__content">
      <p class="panel__eyebrow">${escapeHtml(t(active ? "trip.hero.activeEyebrow" : "trip.hero.approvedEyebrow"))}</p>
      <h2 id="currentTripTitle">${escapeHtml(t(active ? "trip.hero.activeTitle" : "trip.hero.approvedTitle", { car: carLabel }))}</h2>
      <p class="current-trip-hero__time">${escapeHtml(t("trip.hero.window", {
        start: formatDateTime(item.start_time),
        end: formatDateTime(item.end_time),
      }))}</p>
      <p class="section-copy">${escapeHtml(t(active ? "trip.hero.activeCopy" : "trip.hero.approvedCopy"))}</p>
      ${purpose}
      ${pickupMarkup}
    </div>
    <div class="current-trip-hero__aside">
      <span class="status-tag status-tag--${item.status}">${escapeHtml(t("trip.hero.status", { status: lifecycleLabel(item.status) }))}</span>
      <div class="current-trip-hero__actions">
        <button class="btn btn--primary" type="button" data-intent-action="focus-reservation" data-reservation-id="${item.id}" data-trip-focus-action="true">
          ${escapeHtml(t("intent.action.viewTrip"))}
        </button>
      </div>
    </div>
  `;
}

function renderNotifications() {
  els.notificationsList.innerHTML = "";

  if (!state.token) {
    els.notificationsList.innerHTML = `
      <article class="empty-state">
        <strong>Няма активна сесия.</strong>
        <p>След вход тук ще виждаш само важните operational събития за теб.</p>
      </article>
    `;
    return;
  }

  if (state.loading.notifications) {
    els.notificationsList.innerHTML = skeletonCards(3);
    return;
  }

  const visibleNotifications = state.notifications.filter((item) => !item.read_at);
  const hiddenReadCount = state.notifications.length - visibleNotifications.length;

  if (!visibleNotifications.length) {
    els.notificationsList.innerHTML = `
      <article class="empty-state">
        <strong>Тихо табло.</strong>
        <p>${
          hiddenReadCount
            ? "Няма нови уведомления. Прочетените са прибрани, за да не стоят като шум."
            : "В момента няма нови уведомления за текущия потребител."
        }</p>
      </article>
    `;
    updateNotificationBadge();
    return;
  }

  visibleNotifications.forEach((item) => {
    const card = document.createElement("article");
    card.className = "notification-card";
    card.innerHTML = `
      <div class="notification-card__head">
        <strong>${escapeHtml(item.title)}</strong>
        <span class="status-pill status-pill--employee">${t("status.new")}</span>
      </div>
      <p>${escapeHtml(item.body)}</p>
      <div class="notification-card__foot">
        <span class="muted">${formatDateTime(item.created_at)}</span>
        <button class="action-btn action-btn--toggle" type="button" data-notification-read="${item.id}">${t("action.markRead")}</button>
      </div>
    `;
    els.notificationsList.appendChild(card);
  });
  if (hiddenReadCount) {
    const note = document.createElement("p");
    note.className = "muted notification-card__hidden-note";
    note.textContent = `${hiddenReadCount} прочетени уведомления са прибрани от този изглед.`;
    els.notificationsList.appendChild(note);
  }
  updateNotificationBadge();
}

function renderUsers() {
  if (!els.usersGrid) return;
  els.usersGrid.innerHTML = "";

  if (!isFullAdmin()) {
    return;
  }

  if (state.loading.users) {
    els.usersGrid.innerHTML = skeletonCards(3);
    return;
  }

  if (!state.users.length) {
    els.usersGrid.innerHTML = `
      <article class="empty-state">
        <strong>Няма потребители.</strong>
        <p>Създай първите employee акаунти от панела вляво.</p>
      </article>
    `;
    return;
  }

  state.users.forEach((user) => {
    const card = document.createElement("article");
    card.className = "user-card";
    const isSelf = state.currentUser && user.id === state.currentUser.id;
    const auditItems = state.userAudit[user.id] || [];
    const auditMarkup = state.userAudit[user.id]
      ? `
        <div class="user-audit">
          ${
            auditItems.length
              ? auditItems
                  .map(
                    (item) => `
                      <article class="user-audit__item">
                        <strong>${escapeHtml(t("admin.auditBy", {
                          action: t(`audit.${item.action}`),
                          actor: item.actor_display_name,
                        }))}</strong>
                        <span>${formatDateTime(item.at)}</span>
                        ${item.reason ? `<p>${escapeHtml(t("admin.auditReason", { reason: item.reason }))}</p>` : ""}
                      </article>
                    `
                  )
                  .join("")
              : `<p class="muted">${t("admin.auditEmpty")}</p>`
          }
        </div>
      `
      : "";
    card.innerHTML = `
      <div class="user-card__head">
        <div>
          <strong>${escapeHtml(user.display_name)}</strong>
          <p class="muted">${escapeHtml(user.username)}</p>
        </div>
        <span class="status-pill ${roleBadgeClass(user.role)}">${t(`role.${user.role}`)}</span>
      </div>
      <div class="user-card__meta">
        <span class="status-tag ${user.active ? "status-tag--approved" : "status-tag--cancelled"}">${t(user.active ? "status.active" : "status.inactive")}</span>
        ${user.email ? `<span class="muted">${escapeHtml(user.email)}</span>` : ""}
        ${user.gsm_number ? `<span class="muted">${escapeHtml(t("user.gsm", { number: user.gsm_number }))}</span>` : ""}
        <span class="muted">създаден: ${formatDateTime(user.created_at)}</span>
      </div>
      <div class="car-card__actions">
        ${
          user.active
            ? `<button class="action-btn action-btn--toggle" type="button" data-user-action="deactivate" data-user-id="${user.id}" ${isSelf ? "data-self=true" : ""}>${t("action.deactivate")}</button>`
            : `<button class="action-btn action-btn--toggle" type="button" data-user-action="activate" data-user-id="${user.id}">${t("action.activate")}</button>`
        }
        ${
          !isSelf && user.active
            ? `<button class="action-btn action-btn--approve" type="button" data-handoff-candidate="${user.id}">${t("action.handoff")}</button>`
            : ""
        }
        <button class="action-btn action-btn--toggle" type="button" data-user-role="${user.id}">${t("action.changeRole")}</button>
        <button class="action-btn action-btn--toggle" type="button" data-user-reset="${user.id}" ${user.active ? "" : "disabled"}>${t("action.resetPassword")}</button>
        <button class="action-btn action-btn--toggle" type="button" data-user-audit="${user.id}">${t("action.loadAudit")}</button>
      </div>
      ${auditMarkup}
    `;
    els.usersGrid.appendChild(card);
  });
}

function renderCars() {
  const carsToShow = state.cars.filter((car) => (state.carFilter === "active" ? car.active : true));
  const telemetry = telemetryByPlate();
  els.carsGrid.innerHTML = "";

  if (state.loading.cars) {
    els.carsGrid.innerHTML = skeletonCards(4);
    return;
  }

  if (!carsToShow.length) {
    els.carsGrid.innerHTML = `
      <article class="empty-state">
        <strong>Няма автомобили за този изглед.</strong>
        <p>${isFullAdmin() ? "Регистрирай автомобил или смени филтъра." : "Изчакай fleet admin да добави наличност."}</p>
      </article>
    `;
    return;
  }

  carsToShow.forEach((car) => {
    const card = document.createElement("article");
    card.className = "car-card";
    const gps = telemetry.get(String(car.plate_number || "").trim().toUpperCase());
    const telemetryMarkup = gps
      ? `
        <div class="car-card__telemetry">
          <strong>${escapeHtml(t("telemetry.latest"))}</strong>
          <span>${escapeHtml(t("telemetry.coordinates", {
            lat: formatCoordinate(gps.latitude),
            lon: formatCoordinate(gps.longitude),
          }))}</span>
          <span>${escapeHtml(t("telemetry.speed", { speed: gps.speed ?? "—" }))}</span>
          <span>${escapeHtml(t("telemetry.updated", { time: formatTelemetryTime(gps.utc_time) }))}</span>
          ${gps.latitude != null && gps.longitude != null ? `<a class="ghost-link ghost-link--compact" href="https://www.google.com/maps?q=${encodeURIComponent(`${gps.latitude},${gps.longitude}`)}" target="_blank" rel="noreferrer">${escapeHtml(t("telemetry.mapLink"))}</a>` : ""}
        </div>
      `
      : "";
    card.innerHTML = `
      <div class="car-card__meta">
        <div>
          <strong class="car-card__title">${escapeHtml(car.model)}</strong>
          <p class="car-card__plate">${escapeHtml(car.plate_number)}</p>
        </div>
        <span class="status-tag ${car.active ? "status-tag--approved" : "status-tag--cancelled"}">${t(car.active ? "status.active" : "status.inactive")}</span>
      </div>
      <p class="mini-note">${car.active ? "Наличен за нови заявки." : "Изваден от нови резервации."}</p>
      ${isFullAdmin() ? telemetryMarkup : ""}
      ${
        isFullAdmin()
          ? `<div class="car-card__notes">
              <textarea class="notes-textarea" data-car-notes-id="${car.id}" rows="2"
                placeholder="${escapeHtml(t("car.notesPlaceholder"))}">${escapeHtml(car.notes || "")}</textarea>
              <button class="action-btn action-btn--notes" type="button" data-save-car-notes="${car.id}">${t("action.saveNotes")}</button>
            </div>`
          : car.notes
            ? `<p class="car-note-hint">${escapeHtml(t("car.noteHint", { notes: car.notes }))}</p>`
            : ""
      }
      <div class="car-card__actions">
        ${
          isFullAdmin()
            ? `<button class="action-btn action-btn--toggle" type="button" data-toggle-car="${car.id}">
                ${t(car.active ? "action.deactivate" : "action.activate")}
              </button>`
            : ""
        }
      </div>
    `;
    els.carsGrid.appendChild(card);
  });
}

function renderCarSelect() {
  const cars = state.cars.filter((car) => car.active);
  const markup = cars.length
    ? cars.map((car) => `<option value="${car.id}">${escapeHtml(car.plate_number)} · ${escapeHtml(car.model)}</option>`).join("")
    : `<option value="">Няма активни автомобили</option>`;
  if (els.carId) {
    els.carId.innerHTML = markup;
  }
  if (els.blackoutCarId) {
    els.blackoutCarId.innerHTML = markup;
  }
}

function renderConflictPreview() {
  if (!els.conflictPreview) return;

  const preview = state.conflictPreview;
  els.conflictPreview.className = "conflict-preview";

  if (!state.token || !preview.requested) {
    els.conflictPreview.classList.add("conflict-preview--idle");
    els.conflictPreview.innerHTML = `
      <strong>${t("conflict.idleTitle")}</strong>
      <span>${t("conflict.idleBody")}</span>
    `;
    renderCalendar();
    return;
  }

  if (preview.loading) {
    els.conflictPreview.classList.add("conflict-preview--loading");
    els.conflictPreview.innerHTML = `
      <strong>${t("conflict.loadingTitle")}</strong>
      <span>${t("conflict.loadingBody")}</span>
    `;
    renderCalendar();
    return;
  }

  if (preview.error) {
    els.conflictPreview.classList.add("conflict-preview--warning");
    els.conflictPreview.innerHTML = `
      <strong>${t("conflict.errorTitle")}</strong>
      <span>${escapeHtml(preview.error)}</span>
    `;
    renderCalendar();
    return;
  }

  if (!preview.items.length) {
    els.conflictPreview.classList.add("conflict-preview--clear");
    els.conflictPreview.innerHTML = `
      <strong>${t("conflict.clearTitle")}</strong>
      <span>${t("conflict.clearBody")}</span>
    `;
    renderCalendar();
    return;
  }

  els.conflictPreview.classList.add("conflict-preview--warning");
  const items = preview.items
    .map((item) => {
      if (item.type === "blackout") {
        return `<li>${escapeHtml(t("conflict.blackout", {
          kind: t(`blackout.kind.${item.kind}`),
          start: formatDateTime(item.start_time),
          end: formatDateTime(item.end_time),
        }))}</li>`;
      }
      const detail = item.employee_name
        ? `<small>${escapeHtml(t("conflict.adminDetail", {
            employee: item.employee_name,
            purpose: item.purpose || t("conflict.noPurpose"),
          }))}</small>`
        : "";
      return `<li>${escapeHtml(t("conflict.reservation", {
        id: item.id,
        start: formatDateTime(item.start_time),
        end: formatDateTime(item.end_time),
      }))}${detail}</li>`;
    })
    .join("");

  const latestEnd = preview.items.reduce((max, item) => {
    const end = new Date(item.end_time);
    return end > max ? end : max;
  }, new Date(0));
  const requestedDuration = els.endTime?.value && els.startTime?.value
    ? new Date(els.endTime.value) - new Date(els.startTime.value)
    : 2 * 60 * 60 * 1000;
  const suggestedStart = latestEnd;
  const suggestedEnd = new Date(latestEnd.getTime() + requestedDuration);
  const slotKey = `${suggestedStart.toISOString()}|${suggestedEnd.toISOString()}`;

  els.conflictPreview.innerHTML = `
    <strong>${t("conflict.warningTitle", { count: preview.items.length })}</strong>
    <ul>${items}</ul>
    <div class="conflict-suggestion">
      <span>${t("conflict.nextSlot", { start: formatDateTime(suggestedStart), end: formatDateTime(suggestedEnd) })}</span>
      <button class="action-btn action-btn--approve" type="button" data-apply-slot="${escapeHtml(slotKey)}">${t("conflict.applySlot")}</button>
    </div>
  `;
  renderCalendar();
}

function renderBlackouts() {
  if (!els.blackoutsList) return;
  els.blackoutsList.innerHTML = "";

  if (!isFullAdmin()) {
    els.blackoutsList.innerHTML = `
      <article class="empty-state">
        <strong>Blackout-и са видими само за admin.</strong>
      </article>
    `;
    return;
  }

  if (state.loading.blackouts) {
    els.blackoutsList.innerHTML = skeletonCards(3);
    return;
  }

  if (!state.blackouts.length) {
    els.blackoutsList.innerHTML = `
      <article class="empty-state">
        <strong>Няма активни blackout-и.</strong>
        <p>Когато автомобил е в сервиз или поддръжка, прозорецът ще се появи тук.</p>
      </article>
    `;
    return;
  }

  const cars = carMap();
  state.blackouts.forEach((item) => {
    const car = cars.get(item.car_id);
    const card = document.createElement("article");
    card.className = "notification-card";
    card.innerHTML = `
      <div class="notification-card__head">
        <strong>${escapeHtml(car ? `${car.plate_number} · ${car.model}` : `Car ${item.car_id}`)}</strong>
        <span class="status-tag status-tag--returned">${escapeHtml(item.kind)}</span>
      </div>
      <p>${escapeHtml(item.reason || "Без конкретизирана причина")}</p>
      <div class="notification-card__foot">
        <span class="muted">${formatDateTime(item.start_time)} → ${formatDateTime(item.end_time)}</span>
        ${item.active ? `
          <button class="action-btn" type="button" data-blackout-edit="${item.id}">${t("action.editBlackout")}</button>
          <button class="action-btn action-btn--toggle" type="button" data-blackout-disable="${item.id}">${t("action.deactivate")}</button>
        ` : ""}
      </div>
    `;
    els.blackoutsList.appendChild(card);
  });
}

function renderHandoffCandidates() {
  if (!els.handoffUserId) return;
  const options = state.users
    .filter((user) => user.active && (!state.currentUser || user.id !== state.currentUser.id))
    .map((user) => `<option value="${user.id}">${escapeHtml(user.display_name)} · ${t(`role.${user.role}`)}</option>`)
    .join("");
  els.handoffUserId.innerHTML = options || `<option value="">Няма подходящ потребител</option>`;
}

function bulkSelectionEnabled() {
  return surface === "admin" && canApproveReservations();
}

function pendingReservationIds() {
  return new Set(state.reservations.filter((item) => item.status === "pending").map((item) => item.id));
}

function syncBulkSelection() {
  if (!bulkSelectionEnabled()) {
    state.selectedReservationIds.clear();
    return;
  }
  const pendingIds = pendingReservationIds();
  state.selectedReservationIds.forEach((id) => {
    if (!pendingIds.has(id)) {
      state.selectedReservationIds.delete(id);
    }
  });
}

function renderBulkActionBar() {
  if (!els.bulkActionBar) return;

  syncBulkSelection();
  const selectedCount = state.selectedReservationIds.size;
  const pendingIds = pendingReservationIds();
  toggleHidden(els.bulkActionBar, !bulkSelectionEnabled() || selectedCount === 0);

  if (els.bulkSelectedCount) {
    els.bulkSelectedCount.textContent = t("bulk.selected", { count: selectedCount });
  }
  if (els.bulkSelectAll) {
    els.bulkSelectAll.checked = pendingIds.size > 0 && selectedCount === pendingIds.size;
    els.bulkSelectAll.indeterminate = selectedCount > 0 && selectedCount < pendingIds.size;
    els.bulkSelectAll.disabled = !bulkSelectionEnabled() || pendingIds.size === 0 || state.loading.reservations;
  }
  [els.bulkApproveBtn, els.bulkRejectBtn, els.bulkClearBtn].forEach((button) => {
    if (button) {
      button.disabled = selectedCount === 0 || state.loading.reservations;
    }
  });
}

function setReservationSelected(id, selected) {
  if (selected) {
    state.selectedReservationIds.add(id);
  } else {
    state.selectedReservationIds.delete(id);
  }
  renderBulkActionBar();
}

function setAllPendingReservationsSelected(selected) {
  state.selectedReservationIds.clear();
  if (selected) {
    pendingReservationIds().forEach((id) => state.selectedReservationIds.add(id));
  }
  renderReservations();
}

function focusReservationRow(id, action = null) {
  const row = document.querySelector(`[data-reservation-card="${id}"]`) || document.querySelector(`[data-reservation-row="${id}"]`);
  if (!row) return;
  row.scrollIntoView({ behavior: "smooth", block: "center" });
  row.tabIndex = -1;
  const target = action ? row.querySelector(`[data-reservation-action="${action}"]`) : row;
  window.setTimeout(() => (target || row).focus(), 180);
}

function focusReservationForm() {
  els.reservationForm?.scrollIntoView({ behavior: "smooth", block: "start" });
  window.setTimeout(() => (els.carId || els.startTime || els.reservationForm)?.focus(), 180);
}

function nextPreferredSlot(hour, durationMinutes) {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hour, 0, 0, 0);
  if (start <= now) {
    start.setDate(start.getDate() + 1);
  }
  const end = new Date(start.getTime() + durationMinutes * 60 * 1000);
  return { start, end };
}

function renderSmartPrefill() {
  if (!els.smartPrefillPanel) return;
  const available = Boolean(state.token && !isOperationalRole() && state.reservationPreferences?.available);
  toggleHidden(els.smartPrefillPanel, !available);
  if (!available) return;
  const prefs = state.reservationPreferences;
  if (els.smartPrefillHint) {
    els.smartPrefillHint.textContent = t("smartPrefill.hint", {
      car: `${prefs.plate_number} · ${prefs.model}`,
      hour: String(prefs.start_hour).padStart(2, "0"),
      duration: prefs.duration_minutes,
    });
  }
}

function applySmartPrefill() {
  const prefs = state.reservationPreferences;
  if (!prefs?.available) return;
  const slot = nextPreferredSlot(prefs.start_hour, prefs.duration_minutes);
  if (els.carId) els.carId.value = String(prefs.car_id);
  if (els.startTime) els.startTime.value = localInputValue(slot.start);
  if (els.endTime) els.endTime.value = localInputValue(slot.end);
  scheduleConflictPreview();
  focusReservationForm();
  showMessage(t("smartPrefill.appliedTitle"), t("smartPrefill.appliedBody"), "success");
}

async function handleIntentAction(button) {
  const action = button.dataset.intentAction;
  const reservationId = Number(button.dataset.reservationId || 0);
  const reservationActionTarget = button.dataset.reservationActionTarget || null;

  if (action === "reservation-transition" && reservationId && reservationActionTarget) {
    await reservationAction(reservationId, reservationActionTarget);
    return;
  }
  if (action === "focus-reservation" && reservationId) {
    focusReservationRow(reservationId, reservationActionTarget);
    return;
  }
  if (action === "book-now") {
    await quickBookReservation();
    return;
  }
  if (action === "view-my-trips") {
    state.scope = "mine";
    updateToolbarPressedStates(document.querySelectorAll("[data-scope]"), "scope");
    await loadReservations();
    document.getElementById("reservationsDeck")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  if (action === "review-pending" || action === "view-active-trips" || action === "view-handoffs") {
    state.status = action === "review-pending" ? "pending" : action === "view-handoffs" ? "approved" : "checked_out";
    updateToolbarPressedStates(document.querySelectorAll("[data-status]"), "status");
    await loadReservations();
    const railTarget = action === "review-pending" ? els.decisionRail : els.receptionRail;
    (railTarget && !railTarget.classList.contains("hidden") ? railTarget : document.getElementById("reservationsDeck"))
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => {
      const target =
        action === "review-pending"
          ? els.bulkSelectAll || document.querySelector('[data-reservation-action="approve"]')
          : action === "view-handoffs"
            ? document.querySelector('[data-reservation-action="start"]')
            : document.querySelector('[data-reservation-action="return"]');
      target?.focus();
    }, 180);
    return;
  }
  if (action === "view-fleet") {
    document.getElementById("fleetDeck")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function reservationContext(item) {
  const details = [];
  if (item.purpose) {
    details.push(`<strong>${escapeHtml(item.purpose)}</strong>`);
  }
  if (item.decided_by_name) {
    const key = item.status === "rejected" ? "reservation.rejectedBy" : "reservation.decidedBy";
    details.push(`<div class="muted">${escapeHtml(t(key, { name: item.decided_by_name }))}</div>`);
  }
  if (item.decision_reason) {
    details.push(`<div class="muted">${escapeHtml(item.decision_reason)}</div>`);
  }
  if (item.checked_out_at) {
    details.push(`<div class="muted">Старт: ${formatDateTime(item.checked_out_at)}</div>`);
  }
  if (item.returned_at) {
    details.push(`<div class="muted">Върнат: ${formatDateTime(item.returned_at)}</div>`);
  }
  return details.join("");
}

function reservationActions(item) {
  const actions = [];
  const canApprove = canApproveReservations();
  const canReception = canManageTripHandoff();
  const isOwner = state.currentUser && item.created_by_id === state.currentUser.id;

  if (item.status === "pending" && canApprove) {
    actions.push(`<button class="action-btn action-btn--approve" type="button" data-reservation-action="approve" data-id="${item.id}" aria-label="${t("action.approve")} резервация #${item.id}">${t("action.approve")}</button>`);
    actions.push(`<button class="action-btn action-btn--reject" type="button" data-reservation-action="reject" data-id="${item.id}" aria-label="${t("action.reject")} резервация #${item.id}">${t("action.reject")}</button>`);
  }
  if (item.status === "approved" && canReception) {
    actions.push(`<button class="action-btn action-btn--toggle" type="button" data-reservation-action="start" data-id="${item.id}" aria-label="${t("action.startTrip")} за резервация #${item.id}">${t("action.startTrip")}</button>`);
  }
  if (item.status === "checked_out" && canReception) {
    actions.push(`<button class="action-btn action-btn--toggle" type="button" data-reservation-action="return" data-id="${item.id}" aria-label="${t("action.returnCar")} за резервация #${item.id}">${t("action.returnCar")}</button>`);
  }
  if (["pending", "approved"].includes(item.status) && (isFullAdmin() || isOwner)) {
    actions.push(`<button class="action-btn action-btn--cancel" type="button" data-reservation-action="cancel" data-id="${item.id}" aria-label="${t("action.cancel")} резервация #${item.id}">${t("action.cancel")}</button>`);
  }
  return actions.join("");
}

function reservationFlowEmptyMessage() {
  if (!state.token) return t("reservationFlow.loginCopy");
  if (isOperationalRole()) return t(`reservationFlow.empty.${state.currentRole}`);
  return t("reservationFlow.emptyEmployee");
}

function reservationFlowCard(item, car, canBulk) {
  const selectable = canBulk && item.status === "pending";
  const context = reservationContext(item) || `<span class="muted">${escapeHtml(t("reservationFlow.noContext"))}</span>`;
  const actions = reservationActions(item);
  const carLabel = car ? `${car.plate_number} · ${car.model}` : t("entity.car", { id: item.car_id });
  return `
    <article class="reservation-flow-card" data-reservation-card="${item.id}" data-reservation-status="${item.status}">
      <div class="reservation-flow-card__rail" aria-hidden="true"></div>
      <div class="reservation-flow-card__body">
        <div class="reservation-flow-card__top">
          <div class="reservation-flow-card__identity">
            ${selectable ? `
              <input
                class="reservation-flow-card__select"
                type="checkbox"
                data-reservation-select="${item.id}"
                aria-label="Избери резервация #${item.id}"
                ${state.selectedReservationIds.has(item.id) ? "checked" : ""}
              />
            ` : ""}
            <div>
              <p class="panel__eyebrow">${escapeHtml(t("reservationFlow.itemEyebrow", { id: item.id }))}</p>
              <h3>${escapeHtml(carLabel)}</h3>
              <p class="reservation-flow-card__meta">${escapeHtml(item.employee_name)} · ${formatDateTime(item.start_time)} → ${formatDateTime(item.end_time)}</p>
            </div>
          </div>
          ${statusTag(item.status)}
        </div>
        <div class="reservation-flow-card__lifecycle">
          ${lifecycleMeter(item)}
        </div>
        <div class="reservation-flow-card__context">
          ${context}
        </div>
        <div class="reservation-flow-card__actions">
          ${actions || `<span class="muted">${escapeHtml(t("reservationFlow.noAction"))}</span>`}
        </div>
      </div>
    </article>
  `;
}

function renderReservationFlow(cars, canBulk) {
  if (!els.reservationsTimeline) return;

  if (!state.token) {
    els.reservationsTimeline.innerHTML = `
      <div class="reservation-flow__header">
        <div>
          <p class="panel__eyebrow">${escapeHtml(t("reservationFlow.eyebrow"))}</p>
          <h3 id="reservationsTimelineTitle">${escapeHtml(t("reservationFlow.title"))}</h3>
          <p class="section-copy">${escapeHtml(reservationFlowEmptyMessage())}</p>
        </div>
      </div>
    `;
    return;
  }

  if (state.loading.reservations) {
    els.reservationsTimeline.innerHTML = `
      <div class="reservation-flow__header">
        <div>
          <p class="panel__eyebrow">${escapeHtml(t("reservationFlow.eyebrow"))}</p>
          <h3 id="reservationsTimelineTitle">${escapeHtml(t("reservationFlow.loadingTitle"))}</h3>
          <p class="section-copy">${escapeHtml(t("reservationFlow.loadingCopy"))}</p>
        </div>
      </div>
      <div class="reservation-flow__list">${skeletonCards(3)}</div>
    `;
    return;
  }

  if (!state.reservations.length) {
    els.reservationsTimeline.innerHTML = `
      <div class="reservation-flow__header">
        <div>
          <p class="panel__eyebrow">${escapeHtml(t("reservationFlow.eyebrow"))}</p>
          <h3 id="reservationsTimelineTitle">${escapeHtml(t("reservationFlow.emptyTitle"))}</h3>
          <p class="section-copy">${escapeHtml(reservationFlowEmptyMessage())}</p>
        </div>
      </div>
    `;
    return;
  }

  const sorted = [...state.reservations].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
  els.reservationsTimeline.innerHTML = `
    <div class="reservation-flow__header">
      <div>
        <p class="panel__eyebrow">${escapeHtml(t("reservationFlow.eyebrow"))}</p>
        <h3 id="reservationsTimelineTitle">${escapeHtml(t("reservationFlow.title"))}</h3>
        <p class="section-copy">${escapeHtml(t("reservationFlow.copy"))}</p>
      </div>
      <span class="status-pill status-pill--muted">${escapeHtml(pluralRecord(sorted.length))}</span>
    </div>
    <div class="reservation-flow__list">
      ${sorted.map((item) => reservationFlowCard(item, cars.get(item.car_id), canBulk)).join("")}
    </div>
  `;
}

function renderDecisionRail() {
  if (!els.decisionRail) return;
  const showRail = canApproveReservations() && surface === "admin" && state.token;
  toggleHidden(els.decisionRail, !showRail);
  if (!showRail) {
    els.decisionRail.innerHTML = "";
    return;
  }

  if (state.loading.reservations) {
    els.decisionRail.innerHTML = `
      <div>
        <p class="panel__eyebrow">${escapeHtml(t("decisionRail.eyebrow"))}</p>
        <h3 id="decisionRailTitle">${escapeHtml(t("decisionRail.loadingTitle"))}</h3>
      </div>
      ${skeletonCards(2)}
    `;
    return;
  }

  const cars = carMap();
  const pendingItems = state.reservations
    .filter((item) => item.status === "pending")
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
  const visible = pendingItems.slice(0, 3);
  const extraCount = Math.max(pendingItems.length - visible.length, 0);

  if (!pendingItems.length) {
    els.decisionRail.innerHTML = `
      <div>
        <p class="panel__eyebrow">${escapeHtml(t("decisionRail.eyebrow"))}</p>
        <h3 id="decisionRailTitle">${escapeHtml(t("decisionRail.emptyTitle"))}</h3>
        <p class="section-copy">${escapeHtml(t("decisionRail.emptyCopy"))}</p>
      </div>
    `;
    return;
  }

  els.decisionRail.innerHTML = `
    <div class="decision-rail__header">
      <div>
        <p class="panel__eyebrow">${escapeHtml(t("decisionRail.eyebrow"))}</p>
        <h3 id="decisionRailTitle">${escapeHtml(t("decisionRail.title", { count: pendingItems.length }))}</h3>
        <p class="section-copy">${escapeHtml(t("decisionRail.copy"))}</p>
      </div>
      <div class="decision-rail__actions">
        <button class="btn btn--primary" type="button" data-decision-rail-select-all>${escapeHtml(t("decisionRail.approveAll"))}</button>
        <button class="btn btn--ghost" type="button" data-intent-action="review-pending">${escapeHtml(t("intent.action.reviewPending"))}</button>
      </div>
    </div>
    <div class="decision-rail__list">
      ${visible.map((item) => {
        const car = cars.get(item.car_id);
        const carLabel = car ? `${car.plate_number} · ${car.model}` : t("entity.car", { id: item.car_id });
        return `
          <article class="decision-card" data-decision-card="${item.id}">
            <div>
              <strong>${escapeHtml(item.employee_name)}</strong>
              <p>${escapeHtml(carLabel)}</p>
              <span class="muted">${formatDateTime(item.start_time)} → ${formatDateTime(item.end_time)}</span>
              ${item.purpose ? `<p class="decision-card__purpose">${escapeHtml(item.purpose)}</p>` : ""}
            </div>
            <div class="decision-card__actions">
              <button class="action-btn action-btn--approve" type="button" data-reservation-action="approve" data-id="${item.id}" aria-label="${t("action.approve")} резервация #${item.id}">${t("action.approve")}</button>
              <button class="action-btn action-btn--reject" type="button" data-reservation-action="reject" data-id="${item.id}" aria-label="${t("action.reject")} резервация #${item.id}">${t("action.reject")}</button>
            </div>
          </article>
        `;
      }).join("")}
    </div>
    ${extraCount ? `<p class="muted decision-rail__more">${escapeHtml(t("decisionRail.more", { count: extraCount }))}</p>` : ""}
  `;
}

function receptionRailItems() {
  const source = isOperationalRole() ? state.pulseReservations : state.reservations;
  return [...source]
    .filter((item) => ["approved", "checked_out"].includes(item.status))
    .sort((a, b) => {
      const aTime = new Date(a.status === "checked_out" ? a.end_time : a.start_time);
      const bTime = new Date(b.status === "checked_out" ? b.end_time : b.start_time);
      if (a.status !== b.status) return a.status === "approved" ? -1 : 1;
      return aTime - bTime;
    });
}

function renderReceptionRail() {
  if (!els.receptionRail) return;
  const showRail = canManageTripHandoff() && surface === "admin" && state.token;
  toggleHidden(els.receptionRail, !showRail);
  if (!showRail) {
    els.receptionRail.innerHTML = "";
    return;
  }

  if (state.loading.pulseReservations || state.loading.reservations) {
    els.receptionRail.innerHTML = `
      <div>
        <p class="panel__eyebrow">${escapeHtml(t("receptionRail.eyebrow"))}</p>
        <h3 id="receptionRailTitle">${escapeHtml(t("receptionRail.loadingTitle"))}</h3>
      </div>
      ${skeletonCards(2)}
    `;
    return;
  }

  const cars = carMap();
  const handoffItems = receptionRailItems();
  const visible = handoffItems.slice(0, 4);
  const extraCount = Math.max(handoffItems.length - visible.length, 0);

  if (!handoffItems.length && isFullAdmin()) {
    toggleHidden(els.receptionRail, true);
    els.receptionRail.innerHTML = "";
    return;
  }

  if (!handoffItems.length) {
    els.receptionRail.innerHTML = `
      <div>
        <p class="panel__eyebrow">${escapeHtml(t("receptionRail.eyebrow"))}</p>
        <h3 id="receptionRailTitle">${escapeHtml(t("receptionRail.emptyTitle"))}</h3>
        <p class="section-copy">${escapeHtml(t("receptionRail.emptyCopy"))}</p>
      </div>
    `;
    return;
  }

  els.receptionRail.innerHTML = `
    <div class="decision-rail__header">
      <div>
        <p class="panel__eyebrow">${escapeHtml(t("receptionRail.eyebrow"))}</p>
        <h3 id="receptionRailTitle">${escapeHtml(t("receptionRail.title", { count: handoffItems.length }))}</h3>
        <p class="section-copy">${escapeHtml(t("receptionRail.copy"))}</p>
      </div>
      <div class="decision-rail__actions">
        <button class="btn btn--primary" type="button" data-intent-action="view-handoffs">${escapeHtml(t("intent.action.viewHandoffs"))}</button>
        <button class="btn btn--ghost" type="button" data-intent-action="view-active-trips">${escapeHtml(t("intent.action.viewActiveTrips"))}</button>
      </div>
    </div>
    <div class="decision-rail__list">
      ${visible.map((item) => {
        const car = cars.get(item.car_id);
        const carLabel = car ? `${car.plate_number} · ${car.model}` : t("entity.car", { id: item.car_id });
        const isActive = item.status === "checked_out";
        const action = isActive ? "return" : "start";
        const label = isActive ? t("action.returnCar") : t("action.startTrip");
        const timeKey = isActive ? "receptionRail.returnBy" : "receptionRail.startAt";
        const timeValue = isActive ? item.end_time : item.start_time;
        return `
          <article class="decision-card reception-card" data-reception-card="${item.id}">
            <div>
              <strong>${escapeHtml(carLabel)}</strong>
              <p>${escapeHtml(item.employee_name)} · ${escapeHtml(t(timeKey, { time: formatDateTime(timeValue) }))}</p>
              <span class="status-pill ${isActive ? "status-pill--warning" : "status-pill--success"}">${escapeHtml(t(`status.${item.status}`))}</span>
              ${item.purpose ? `<p class="decision-card__purpose">${escapeHtml(item.purpose)}</p>` : ""}
            </div>
            <div class="decision-card__actions">
              <button class="action-btn action-btn--toggle" type="button" data-reservation-action="${action}" data-id="${item.id}" aria-label="${label} за резервация #${item.id}">${escapeHtml(label)}</button>
            </div>
          </article>
        `;
      }).join("")}
    </div>
    ${extraCount ? `<p class="muted decision-rail__more">${escapeHtml(t("receptionRail.more", { count: extraCount }))}</p>` : ""}
  `;
}

function renderReservations() {
  const cars = carMap();
  const canBulk = bulkSelectionEnabled();
  const colspan = canBulk ? 8 : 7;
  els.reservationsTableBody.innerHTML = "";
  renderReservationFlow(cars, canBulk);

  if (!state.token) {
    state.selectedReservationIds.clear();
    renderBulkActionBar();
    renderDecisionRail();
    renderReceptionRail();
    renderReservationFlow(cars, canBulk);
    els.reservationsTableBody.innerHTML = `<tr><td colspan="${colspan}" class="muted">Влез в системата, за да видиш operational потока.</td></tr>`;
    return;
  }

  if (state.loading.reservations) {
    renderBulkActionBar();
    renderDecisionRail();
    renderReceptionRail();
    renderReservationFlow(cars, canBulk);
    els.reservationsTableBody.innerHTML = `${skeletonTableRow(colspan)}${skeletonTableRow(colspan)}${skeletonTableRow(colspan)}`;
    return;
  }

  if (!state.reservations.length) {
    state.selectedReservationIds.clear();
    renderBulkActionBar();
    renderDecisionRail();
    renderReceptionRail();
    renderReservationFlow(cars, canBulk);
    els.reservationsTableBody.innerHTML = `<tr><td colspan="${colspan}" class="muted">${isFullAdmin() ? "Няма резервации за текущия изглед." : "Нямаш видими резервации за текущия изглед."}</td></tr>`;
    return;
  }

  syncBulkSelection();
  renderReservationFlow(cars, canBulk);
  state.reservations.forEach((item) => {
    const car = cars.get(item.car_id);
    const selectable = canBulk && item.status === "pending";
    const row = document.createElement("tr");
    row.dataset.reservationRow = String(item.id);
    row.dataset.reservationStatus = item.status;
    row.innerHTML = `
      ${
        canBulk
          ? `<td data-label="Избор" class="select-cell">
              ${
                selectable
                  ? `<input type="checkbox" data-reservation-select="${item.id}" aria-label="Избери резервация #${item.id}" ${state.selectedReservationIds.has(item.id) ? "checked" : ""} />`
                  : ""
              }
            </td>`
          : ""
      }
      <td data-label="ID">#${item.id}</td>
      <td data-label="Автомобил">
        <strong>${escapeHtml(car ? car.plate_number : t("entity.car", { id: item.car_id }))}</strong>
        <div class="muted">${escapeHtml(car ? car.model : t("entity.unknownCar"))}</div>
      </td>
      <td data-label="Заявител"><strong>${escapeHtml(item.employee_name)}</strong></td>
      <td data-label="Период">
        <strong>${formatDateTime(item.start_time)}</strong>
        <div class="muted">до ${formatDateTime(item.end_time)}</div>
      </td>
      <td data-label="Статус">${statusTag(item.status)}</td>
      <td data-label="Контекст">
        <div class="status-stack">
          ${lifecycleMeter(item)}
          ${reservationContext(item) || '<span class="muted">Без допълнителен контекст</span>'}
        </div>
      </td>
      <td data-label="Действия"><div class="table-actions">${reservationActions(item)}</div></td>
    `;
    els.reservationsTableBody.appendChild(row);
  });
  renderBulkActionBar();
  renderDecisionRail();
  renderReceptionRail();
}

function renderCalendar() {
  const monthStart = startOfMonth(state.calendarDate);
  const cars = carMap();
  const days = dayMap();
  const conflictKeys = conflictDateKeys();
  const todayKey = dateKey(new Date());

  if (mobileCalendarMedia.matches) {
    const selected = localDateFromKey(state.selectedDateKey);
    const selectedItems = (days.get(state.selectedDateKey) || []).sort(
      (a, b) => new Date(a.start_time) - new Date(b.start_time)
    );
    els.calendarMonthLabel.textContent = formatMonthLabel(startOfMonth(selected));
    els.calendarGrid.classList.add("calendar-grid--mobile");
    els.calendarGrid.innerHTML = `
      <article class="mobile-day-card ${conflictKeys.has(state.selectedDateKey) ? "mobile-day-card--conflict" : ""}">
        <div class="mobile-day-card__nav">
          <button class="segmented__btn" type="button" data-mobile-day-shift="-1" aria-label="${t("calendar.previousDay")}">‹</button>
          <div>
            <p class="panel__eyebrow">${t("calendar.mobileHint")}</p>
            <h3>${formatDayLabel(state.selectedDateKey)}</h3>
          </div>
          <button class="segmented__btn" type="button" data-mobile-day-shift="1" aria-label="${t("calendar.nextDay")}">›</button>
        </div>
        <div class="mobile-day-card__meta">
          <span class="status-pill ${state.selectedDateKey === todayKey ? "status-pill--admin" : "status-pill--muted"}">
            ${state.selectedDateKey === todayKey ? "Днес" : pluralRecord(selectedItems.length)}
          </span>
          <span class="muted">${selectedItems.length ? t("calendar.selectedTotal", { count: selectedItems.length }) : t("calendar.noEvents")}</span>
        </div>
        <div class="calendar-day__list">
          ${
            selectedItems.length
              ? selectedItems.map((item) => calendarPill(item, cars.get(item.car_id))).join("")
              : `<span class="muted">Няма записи за този ден.</span>`
          }
        </div>
        <button class="btn btn--primary" type="button" data-mobile-book-day="${state.selectedDateKey}">${t("action.bookThisDay")}</button>
      </article>
    `;
    return;
  }

  const firstDay = new Date(monthStart);
  const weekday = (firstDay.getDay() + 6) % 7;
  firstDay.setDate(firstDay.getDate() - weekday);
  const monthIndex = monthStart.getMonth();

  els.calendarMonthLabel.textContent = formatMonthLabel(monthStart);
  els.calendarGrid.classList.remove("calendar-grid--mobile");
  els.calendarGrid.innerHTML = "";

  for (let index = 0; index < 42; index += 1) {
    const current = new Date(firstDay);
    current.setDate(firstDay.getDate() + index);
    const key = dateKey(current);
    const items = (days.get(key) || []).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    const visibleItems = items.slice(0, 3);
    const hiddenCount = Math.max(items.length - visibleItems.length, 0);
    const button = document.createElement("button");
    button.type = "button";
    button.className = [
      "calendar-day",
      current.getMonth() !== monthIndex ? "calendar-day--outside" : "",
      key === todayKey ? "calendar-day--today" : "",
      key === state.selectedDateKey ? "calendar-day--selected" : "",
      conflictKeys.has(key) ? "calendar-day--conflict" : "",
    ]
      .filter(Boolean)
      .join(" ");
    button.dataset.dateKey = key;
    button.setAttribute("aria-pressed", key === state.selectedDateKey ? "true" : "false");
    button.setAttribute(
      "aria-label",
      `${formatDayLabel(key)} · ${items.length ? pluralRecord(items.length) : "няма записи"}`
    );
    button.innerHTML = `
      <div class="calendar-day__head">
        <span class="calendar-day__number">${current.getDate()}</span>
        <span class="calendar-day__count">${items.length ? pluralRecord(items.length) : ""}</span>
      </div>
      <div class="calendar-day__list">
        ${visibleItems
          .map((item) => calendarPill(item, cars.get(item.car_id)))
          .join("")}
        ${hiddenCount ? `<span class="calendar-more">+${hiddenCount} още</span>` : ""}
      </div>
    `;
    els.calendarGrid.appendChild(button);
  }
}

function renderDayTimeline() {
  const cars = carMap();
  const selectedItems = [...(dayMap().get(state.selectedDateKey) || [])].sort(
    (a, b) => new Date(a.start_time) - new Date(b.start_time)
  );
  els.selectedDateLabel.textContent = formatDayLabel(state.selectedDateKey);
  els.dayTimeline.innerHTML = "";

  if (!selectedItems.length) {
    els.selectedDateMeta.textContent = t("calendar.noEvents");
    els.dayTimeline.innerHTML = `
      <article class="empty-state">
        <strong>Спокоен ден.</strong>
        <p>Няма заявки или курсове в избрания ден.</p>
      </article>
    `;
    return;
  }

  els.selectedDateMeta.textContent = t("calendar.selectedTotal", { count: selectedItems.length });

  selectedItems.forEach((item) => {
    const car = cars.get(item.car_id);
    const publicCarLabel = item.plate_number
      ? `${item.plate_number}${item.model ? ` · ${item.model}` : ""}`
      : null;
    const carLabel = publicCarLabel || (car ? `${car.plate_number} · ${car.model}` : t("entity.car", { id: item.car_id }));
    const contextLine = state.token
      ? escapeHtml(item.employee_name)
      : escapeHtml(t("calendar.publicContext"));
    const purposeLine = state.token
      ? escapeHtml(item.purpose || "Без уточнена цел")
      : escapeHtml(t("calendar.publicDetails"));
    const card = document.createElement("article");
    card.className = "timeline-item";
    card.innerHTML = `
      <div class="timeline-item__top">
        <div>
          <strong>${escapeHtml(carLabel)}</strong>
          <p class="muted">${contextLine}</p>
        </div>
        ${statusTag(item.status)}
      </div>
      <p>${formatDateTime(item.start_time)} → ${formatDateTime(item.end_time)}</p>
      ${lifecycleMeter(item)}
      <p>${purposeLine}</p>
    `;
    els.dayTimeline.appendChild(card);
  });
}

function setSelectedDate(key) {
  state.selectedDateKey = key;
  const selected = localDateFromKey(key);
  state.calendarDate = startOfMonth(selected);
  const today = new Date();
  if (els.startTime && els.endTime && selected >= new Date(today.getFullYear(), today.getMonth(), today.getDate())) {
    const start = new Date(selected.getFullYear(), selected.getMonth(), selected.getDate(), 9, 0, 0, 0);
    const end = new Date(selected.getFullYear(), selected.getMonth(), selected.getDate(), 11, 0, 0, 0);
    els.startTime.value = localInputValue(start);
    els.endTime.value = localInputValue(end);
    els.endTime.min = els.startTime.value;
  }
  renderCalendar();
  renderDayTimeline();
  if (els.carId) {
    scheduleConflictPreview();
  }
}

async function loadSetupStatus() {
  const data = await apiFetch("/auth/setup-status");
  state.hasAdmin = data.has_admin;
  renderShell();
}

async function loadMe() {
  if (!state.token) return;
  const me = await apiFetch("/auth/me", { headers: authHeaders() });
  setSession(me, state.token);
}

async function loadCars() {
  const query = isFullAdmin() ? "?active_only=false" : "";
  setLoading("cars", true);
  renderCars();
  try {
    const data = await apiFetch(`/cars${query}`);
    state.cars = data.items;
    renderCarSelect();
    await loadBlackouts();
  } finally {
    setLoading("cars", false);
    renderCars();
  }
}

function syncReservationFiltersFromInputs() {
  if (!els.reservationSearch) return;
  state.reservationSearch = els.reservationSearch.value;
  state.reservationStartDate = els.reservationStartDate?.value || "";
  state.reservationEndDate = els.reservationEndDate?.value || "";
}

function reservationQueryParams() {
  syncReservationFiltersFromInputs();
  const params = new URLSearchParams();
  if (state.status !== "all" && state.status !== "open") {
    params.set("status_filter", state.status);
  }
  if (isOperationalRole() && state.scope === "mine") {
    params.set("mine", "true");
  }
  if (state.reservationSearch.trim()) {
    params.set("search", state.reservationSearch.trim());
  }
  if (state.reservationStartDate) {
    params.set("start", dateFilterIso(state.reservationStartDate));
  }
  if (state.reservationEndDate) {
    params.set("end", dateFilterIso(state.reservationEndDate, true));
  }
  return params;
}

async function applyReservationFilters() {
  await loadReservations();
  updateOverview();
  updateSummary();
}

function scheduleReservationFilterRefresh() {
  clearTimeout(reservationFilterTimer);
  reservationFilterTimer = setTimeout(() => {
    applyReservationFilters().catch((error) => {
      showMessage("Филтърът не успя", error.message);
    });
  }, 250);
}

async function clearReservationFilters() {
  if (els.reservationSearch) {
    els.reservationSearch.value = "";
  }
  if (els.reservationStartDate) {
    els.reservationStartDate.value = "";
  }
  if (els.reservationEndDate) {
    els.reservationEndDate.value = "";
  }
  state.reservationSearch = "";
  state.reservationStartDate = "";
  state.reservationEndDate = "";
  clearTimeout(reservationFilterTimer);
  try {
    await applyReservationFilters();
  } catch (error) {
    showMessage("Филтърът не успя", error.message);
  }
}

async function loadReservations() {
  if (!state.token) {
    state.reservations = [];
    renderReservations();
    await loadPublicCalendar();
    return;
  }

  const params = reservationQueryParams();
  const suffix = params.toString() ? `?${params.toString()}` : "";
  setLoading("reservations", true);
  renderReservations();
  renderCalendar();
  renderDayTimeline();
  try {
    const data = await apiFetch(`/reservations${suffix}`, { headers: authHeaders() });
    state.reservations =
      state.status === "open"
        ? data.items.filter((item) => !["returned", "rejected", "cancelled"].includes(item.status))
        : data.items;
  } finally {
    setLoading("reservations", false);
    renderReservations();
    renderCalendar();
    renderDayTimeline();
  }
}

async function loadFleetPulseReservations() {
  if (!state.token || !isOperationalRole()) {
    state.pulseReservations = [];
    renderFleetPulse();
    renderReceptionRail();
    renderCalendar();
    renderDayTimeline();
    return;
  }

  setLoading("pulseReservations", true);
  renderFleetPulse();
  renderReceptionRail();
  renderCalendar();
  renderDayTimeline();
  try {
    const data = await apiFetch("/reservations?limit=500", { headers: authHeaders() });
    state.pulseReservations = data.items;
  } finally {
    setLoading("pulseReservations", false);
    renderFleetPulse();
    renderReceptionRail();
    renderCalendar();
    renderDayTimeline();
  }
}

async function loadPublicOverview() {
  setLoading("publicOverview", true);
  try {
    state.publicOverview = await apiFetch("/public/overview");
  } catch (error) {
    state.publicOverview = null;
    console.warn("Public overview failed", error);
  } finally {
    setLoading("publicOverview", false);
    updateOverview();
  }
}

function publicCalendarParams() {
  const monthStart = startOfMonth(state.calendarDate);
  const firstDay = new Date(monthStart);
  const weekday = (firstDay.getDay() + 6) % 7;
  firstDay.setDate(firstDay.getDate() - weekday);
  const lastDay = addDays(firstDay, 42);
  const params = new URLSearchParams();
  params.set("start", firstDay.toISOString());
  params.set("end", lastDay.toISOString());
  return params;
}

async function loadPublicCalendar() {
  if (state.token) {
    state.publicCalendar = [];
    renderCalendar();
    renderDayTimeline();
    return;
  }

  setLoading("publicCalendar", true);
  renderCalendar();
  renderDayTimeline();
  try {
    const data = await apiFetch(`/public/calendar?${publicCalendarParams().toString()}`);
    state.publicCalendar = data.items || [];
  } catch (error) {
    state.publicCalendar = [];
    console.warn("Public calendar failed", error);
  } finally {
    setLoading("publicCalendar", false);
    renderCalendar();
    renderDayTimeline();
  }
}

async function loadFleetIntelligencePulse() {
  if (!state.token || !isFullAdmin()) {
    state.intelligencePulse = null;
    renderFleetPulse();
    return;
  }

  setLoading("intelligencePulse", true);
  renderFleetPulse();
  try {
    state.intelligencePulse = await apiFetch("/admin/intelligence/pulse", { headers: authHeaders() });
  } catch (error) {
    state.intelligencePulse = null;
    console.warn("Fleet intelligence pulse failed", error);
  } finally {
    setLoading("intelligencePulse", false);
    renderFleetPulse();
  }
}

async function loadTelemetry() {
  if (!state.token || !isFullAdmin()) {
    state.telemetry = [];
    state.telemetryConfigured = false;
    renderFleetPulse();
    renderCars();
    return;
  }

  setLoading("telemetry", true);
  renderFleetPulse();
  try {
    const data = await apiFetch("/cars/telemetry/latest", { headers: authHeaders() });
    state.telemetryConfigured = Boolean(data.configured);
    state.telemetry = data.items || [];
  } catch (error) {
    state.telemetry = [];
    state.telemetryConfigured = false;
    console.warn("NetFleet telemetry failed", error);
  } finally {
    setLoading("telemetry", false);
    renderFleetPulse();
    renderCars();
  }
}

async function loadNetfleetConfig() {
  if (!state.token || !isFullAdmin()) {
    state.netfleetConfig = null;
    renderNetfleetConfig();
    return;
  }

  setLoading("netfleetConfig", true);
  renderNetfleetConfig();
  try {
    state.netfleetConfig = await apiFetch("/cars/telemetry/config", { headers: authHeaders() });
  } catch (error) {
    state.netfleetConfig = null;
    console.warn("NetFleet config failed", error);
  } finally {
    setLoading("netfleetConfig", false);
    renderNetfleetConfig();
  }
}

async function loadProductionReadiness() {
  if (!state.token || !isFullAdmin()) {
    state.productionReadiness = null;
    renderProductionReadiness();
    return;
  }

  setLoading("productionReadiness", true);
  renderProductionReadiness();
  try {
    state.productionReadiness = await apiFetch("/ops/readiness", { headers: authHeaders() });
  } catch (error) {
    state.productionReadiness = null;
    console.warn("Production readiness failed", error);
  } finally {
    setLoading("productionReadiness", false);
    renderProductionReadiness();
  }
}

async function loadReservationPreferences() {
  if (!state.token || isOperationalRole()) {
    state.reservationPreferences = null;
    renderSmartPrefill();
    return;
  }

  setLoading("preferences", true);
  try {
    state.reservationPreferences = await apiFetch("/reservations/preferences", { headers: authHeaders() });
  } catch (error) {
    state.reservationPreferences = null;
    console.warn("Reservation preferences failed", error);
  } finally {
    setLoading("preferences", false);
    renderSmartPrefill();
  }
}

async function loadPickupTelemetry() {
  const candidate = currentTripCandidate();
  if (!state.token || !candidate) {
    state.pickupTelemetry = null;
    renderCurrentTripHero();
    return;
  }

  setLoading("pickupTelemetry", true);
  renderCurrentTripHero();
  try {
    const data = await apiFetch(`/cars/${candidate.car_id}/telemetry/latest`, { headers: authHeaders() });
    state.pickupTelemetry = {
      carId: candidate.car_id,
      configured: Boolean(data.configured),
      item: data.item || null,
    };
  } catch (error) {
    state.pickupTelemetry = {
      carId: candidate.car_id,
      configured: false,
      item: null,
      error: true,
    };
    console.warn("Pickup telemetry failed", error);
  } finally {
    setLoading("pickupTelemetry", false);
    renderCurrentTripHero();
  }
}

async function downloadCsv(url, filename) {
  const response = await fetch(url, { headers: authHeaders() });
  if (!response.ok) {
    let detail = "Неуспешна заявка към сървъра.";
    try {
      const data = await response.json();
      detail = data?.detail || detail;
    } catch (_error) {
      // CSV failures are not guaranteed to return JSON.
    }
    if (response.status === 401) {
      setSession(null, null);
    }
    throw new Error(detail);
  }

  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

async function exportReservationsCsv() {
  const params = reservationQueryParams();
  const suffix = params.toString() ? `?${params.toString()}` : "";
  try {
    await downloadCsv(`/reservations/export.csv${suffix}`, "fleetflow-reservations.csv");
    showMessage("CSV файлът е готов", "Експортът следва текущите филтри на таблицата.", "success");
  } catch (error) {
    showMessage("Експортът не успя", error.message);
  }
}

async function loadNotifications() {
  if (!state.token) {
    state.notifications = [];
    renderNotifications();
    updateNotificationBadge();
    return;
  }
  setLoading("notifications", true);
  renderNotifications();
  try {
    state.notifications = await apiFetch("/notifications", { headers: authHeaders() });
  } finally {
    setLoading("notifications", false);
    renderNotifications();
    updateNotificationBadge();
  }
}

async function loadUsers() {
  if (!isFullAdmin()) {
    state.users = [];
    renderUsers();
    renderHandoffCandidates();
    return;
  }
  setLoading("users", true);
  renderUsers();
  try {
    state.users = await apiFetch("/users", { headers: authHeaders() });
    renderHandoffCandidates();
  } finally {
    setLoading("users", false);
    renderUsers();
    renderHandoffCandidates();
  }
}

async function loadBlackouts() {
  if (!isFullAdmin() || !state.cars.length) {
    state.blackouts = [];
    renderBlackouts();
    return;
  }

  setLoading("blackouts", true);
  renderBlackouts();
  try {
    const requests = state.cars.map((car) =>
      apiFetch(`/cars/${car.id}/blackouts`, { headers: authHeaders() }).then((items) =>
        items.map((item) => ({ ...item, car_id: car.id }))
      )
    );
    const batches = await Promise.all(requests);
    state.blackouts = batches.flat();
  } finally {
    setLoading("blackouts", false);
    renderBlackouts();
  }
}

function resetConflictPreview() {
  state.conflictPreview = {
    requested: false,
    loading: false,
    error: null,
    items: [],
    requestId: state.conflictPreview.requestId + 1,
  };
  renderConflictPreview();
}

async function loadConflictPreview() {
  if (!state.token || !els.carId?.value || !els.startTime?.value || !els.endTime?.value) {
    resetConflictPreview();
    return;
  }

  const start = new Date(els.startTime.value);
  const end = new Date(els.endTime.value);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end <= start) {
    resetConflictPreview();
    return;
  }

  const requestId = state.conflictPreview.requestId + 1;
  state.conflictPreview = {
    requested: true,
    loading: true,
    error: null,
    items: [],
    requestId,
  };
  renderConflictPreview();

  const params = new URLSearchParams({
    car_id: els.carId.value,
    start: toIso(els.startTime.value),
    end: toIso(els.endTime.value),
  });

  try {
    const data = await apiFetch(`/reservations/conflicts?${params.toString()}`, {
      headers: authHeaders(),
    });
    if (state.conflictPreview.requestId !== requestId) return;
    state.conflictPreview = {
      requested: true,
      loading: false,
      error: null,
      items: data.items || [],
      requestId,
    };
  } catch (error) {
    if (state.conflictPreview.requestId !== requestId) return;
    state.conflictPreview = {
      requested: true,
      loading: false,
      error: error.message,
      items: [],
      requestId,
    };
  }
  renderConflictPreview();
}

function scheduleConflictPreview() {
  if (conflictPreviewTimer) {
    window.clearTimeout(conflictPreviewTimer);
  }
  conflictPreviewTimer = window.setTimeout(loadConflictPreview, 250);
}

async function refreshData() {
  try {
    hideMessage();
    await loadCars();
    await Promise.all([
      loadReservations(),
      loadFleetPulseReservations(),
      loadPublicOverview(),
      loadFleetIntelligencePulse(),
      loadNetfleetConfig(),
      loadProductionReadiness(),
      loadTelemetry(),
      loadReservationPreferences(),
      loadNotifications(),
      loadUsers(),
    ]);
    await loadPickupTelemetry();
    updateOverview();
    updateSummary();
    renderCurrentTripHero();
  } catch (error) {
    showMessage("Неуспешно зареждане", error.message);
  }
}

function validateBootstrapForm() {
  clearErrors();
  let valid = true;
  if (!els.bootstrapUsername.value.trim()) {
    setFieldError("bootstrapUsername", "Въведи потребител.");
    valid = false;
  }
  if (!els.bootstrapDisplayName.value.trim()) {
    setFieldError("bootstrapDisplayName", "Въведи име.");
    valid = false;
  }
  if (!els.bootstrapPassword.value || els.bootstrapPassword.value.length < 8) {
    setFieldError("bootstrapPassword", "Паролата трябва да е поне 8 символа.");
    valid = false;
  }
  return valid;
}

function validateLoginForm() {
  clearErrors();
  let valid = true;
  if (!els.username.value.trim()) {
    setFieldError("username", "Въведи потребител.");
    valid = false;
  }
  if (!els.password.value) {
    setFieldError("password", "Въведи парола.");
    valid = false;
  }
  return valid;
}

function validateReservationForm() {
  clearErrors();
  let valid = true;
  const start = els.startTime.value;
  const end = els.endTime.value;
  const now = Date.now();

  if (!els.carId.value) {
    setFieldError("carId", "Избери автомобил.");
    valid = false;
  }
  if (!start) {
    setFieldError("startTime", "Въведи начало.");
    valid = false;
  }
  if (!end) {
    setFieldError("endTime", "Въведи край.");
    valid = false;
  }
  if (start && new Date(start).getTime() <= now) {
    setFieldError("startTime", "Началото трябва да е в бъдещето.");
    valid = false;
  }
  if (start && end && new Date(end) <= new Date(start)) {
    setFieldError("endTime", "Краят трябва да е след началото.");
    valid = false;
  }
  return valid;
}

function validatePasswordForm() {
  clearErrors();
  let valid = true;
  if (!els.currentPassword.value) {
    setFieldError("currentPassword", "Въведи текущата парола.");
    valid = false;
  }
  if (!els.newPassword.value || els.newPassword.value.length < 8) {
    setFieldError("newPassword", "Новата парола трябва да е поне 8 символа.");
    valid = false;
  }
  return valid;
}

function validateUserForm() {
  clearErrors();
  let valid = true;
  if (!els.newUsername.value.trim()) {
    setFieldError("newUsername", "Въведи потребител.");
    valid = false;
  }
  if (!els.newDisplayName.value.trim()) {
    setFieldError("newDisplayName", "Въведи име.");
    valid = false;
  }
  if (!els.newUserPassword.value || els.newUserPassword.value.length < 8) {
    setFieldError("newUserPassword", "Началната парола трябва да е поне 8 символа.");
    valid = false;
  }
  if (els.newGsmNumber?.value.trim() && els.newGsmNumber.value.trim().length > 32) {
    setFieldError("newGsmNumber", "GSM номерът трябва да е до 32 символа.");
    valid = false;
  }
  return valid;
}

function validateCarForm() {
  clearErrors();
  let valid = true;
  if (!els.plate.value.trim()) {
    setFieldError("plate", "Регистрационният номер е задължителен.");
    valid = false;
  }
  if (!els.model.value.trim()) {
    setFieldError("model", "Моделът е задължителен.");
    valid = false;
  }
  return valid;
}

async function loginWith(username, password) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  state.token = data.access_token;
  await loadMe();
  await refreshData();
  showMessage("Успешен вход", `Добре дошъл, ${state.currentUser.display_name}.`, "success");
}

async function handleBootstrap(event) {
  event.preventDefault();
  if (!validateBootstrapForm()) {
    showMessage("Има проблем", "Поправи данните за първия администратор.");
    return;
  }

  const payload = {
    username: els.bootstrapUsername.value.trim(),
    display_name: els.bootstrapDisplayName.value.trim(),
    password: els.bootstrapPassword.value,
  };
  const headers = { "Content-Type": "application/json" };
  const bootstrapToken = els.bootstrapToken?.value?.trim();
  if (bootstrapToken) {
    headers["X-Bootstrap-Token"] = bootstrapToken;
  }

  const releaseSubmit = setSubmitBusy(event.currentTarget);
  try {
    await apiFetch("/auth/bootstrap-admin", {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    state.hasAdmin = true;
    await loginWith(payload.username, payload.password);
  } catch (error) {
    showMessage("Setup не успя", error.message);
  } finally {
    releaseSubmit();
  }
}

async function handleLogin(event) {
  event.preventDefault();
  if (!validateLoginForm()) {
    showMessage("Има проблем", "Поправи полетата за вход.");
    return;
  }

  const releaseSubmit = setSubmitBusy(event.currentTarget);
  try {
    await loginWith(els.username.value.trim(), els.password.value);
  } catch (error) {
    showMessage("Неуспешен вход", error.message);
  } finally {
    releaseSubmit();
  }
}

async function handleLogout() {
  if (state.token) {
    try {
      await apiFetch("/auth/logout", {
        method: "POST",
        credentials: "same-origin",
        skipRefresh: true,
      });
    } catch (error) {
      console.warn("Logout request failed", error);
    }
  }
  setSession(null, null);
  state.notifications = [];
  state.reservations = [];
  state.pulseReservations = [];
  state.publicCalendar = [];
  await loadPublicOverview();
  await loadPublicCalendar();
  state.telemetry = [];
  state.telemetryConfigured = false;
  state.intelligencePulse = null;
  state.netfleetConfig = null;
  state.pickupTelemetry = null;
  state.reservationPreferences = null;
  state.users = [];
  state.userAudit = {};
  state.blackouts = [];
  state.selectedReservationIds.clear();
  els.loginForm.reset();
  resetConflictPreview();
  renderNotifications();
  updateNotificationBadge();
  renderReservations();
  renderCurrentTripHero();
  renderDecisionRail();
  renderReceptionRail();
  renderFleetPulse();
  renderNetfleetConfig();
  renderSmartPrefill();
  renderUsers();
  renderBlackouts();
  renderHandoffCandidates();
  updateOverview();
  updateSummary();
  showMessage("Сесията приключи", "Излязохте успешно.", "success");
}

async function handleReservationCreate(event) {
  event.preventDefault();
  if (!validateReservationForm()) {
    showMessage("Има проблем", "Поправи данните за заявката.");
    return;
  }

  const releaseSubmit = setSubmitBusy(event.currentTarget);
  try {
    await apiFetch("/reservations", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        car_id: Number(els.carId.value),
        start_time: toIso(els.startTime.value),
        end_time: toIso(els.endTime.value),
        purpose: els.purpose.value.trim() || null,
      }),
    });
    els.purpose.value = "";
    showMessage("Заявката е подадена", "Резервацията е записана като pending.", "success");
    await refreshData();
    scheduleConflictPreview();
  } catch (error) {
    showMessage("Неуспешна заявка", error.message);
  } finally {
    releaseSubmit();
  }
}

async function quickBookReservation() {
  if (!state.token) return;
  const button = els.quickBookBtn;
  const originalText = button?.textContent;
  if (button) {
    button.disabled = true;
    button.dataset.loading = "true";
    button.textContent = t("quickBook.loading");
  }
  if (els.quickBookHint) {
    els.quickBookHint.textContent = t("quickBook.searching");
  }
  try {
    const reservation = await apiFetch("/reservations/quick-book", {
      method: "POST",
      headers: authHeaders(),
    });
    const suggestion = reservation.quick_suggestion || {};
    const car = suggestion.plate_number
      ? `${suggestion.plate_number} · ${suggestion.model}`
      : t("entity.car", { id: reservation.car_id });
    if (els.quickBookHint) {
      els.quickBookHint.textContent = t("quickBook.createdHint", {
        car,
        start: formatDateTime(reservation.start_time),
        end: formatDateTime(reservation.end_time),
      });
    }
    showMessage(
      t("quickBook.createdTitle"),
      t("quickBook.createdBody", {
        car,
        start: formatDateTime(reservation.start_time),
      }),
      "success",
    );
    await refreshData();
  } catch (error) {
    if (els.quickBookHint) {
      els.quickBookHint.textContent = t("quickBook.failedHint");
    }
    showMessage(t("quickBook.failedTitle"), error.message);
    focusReservationForm();
  } finally {
    if (button) {
      button.disabled = false;
      button.dataset.loading = "false";
      button.textContent = originalText || t("quickBook.button");
    }
  }
}

async function handlePasswordChange(event) {
  event.preventDefault();
  if (!validatePasswordForm()) {
    showMessage("Има проблем", "Поправи полетата за смяна на парола.");
    return;
  }

  const releaseSubmit = setSubmitBusy(event.currentTarget);
  try {
    await apiFetch("/users/me/password", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        current_password: els.currentPassword.value,
        new_password: els.newPassword.value,
      }),
    });
    els.passwordForm.reset();
    showMessage("Паролата е обновена", "Новата парола е активна.", "success");
  } catch (error) {
    showMessage("Неуспешна смяна", error.message);
  } finally {
    releaseSubmit();
  }
}

function validateNetfleetForm() {
  clearErrors();
  const value = els.netfleetApiKey?.value.trim() || "";
  if (value.length < 16) {
    setFieldError("netfleetApiKey", t("netfleet.keyTooShort"));
    return false;
  }
  return true;
}

async function handleNetfleetConfigUpdate(event) {
  event.preventDefault();
  if (!validateNetfleetForm()) {
    showMessage(t("netfleet.invalidTitle"), t("netfleet.invalidBody"));
    return;
  }

  const releaseSubmit = setSubmitBusy(event.currentTarget);
  try {
    state.netfleetConfig = await apiFetch("/cars/telemetry/config", {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ api_key: els.netfleetApiKey.value.trim() }),
    });
    els.netfleetForm.reset();
    renderNetfleetConfig();
    showMessage(t("netfleet.savedTitle"), t("netfleet.savedBody"), "success");
    await loadTelemetry();
  } catch (error) {
    showMessage(t("netfleet.saveFailedTitle"), error.message);
  } finally {
    releaseSubmit();
  }
}

async function handleUserCreate(event) {
  event.preventDefault();
  if (!validateUserForm()) {
    showMessage("Има проблем", "Поправи данните за новия потребител.");
    return;
  }

  const releaseSubmit = setSubmitBusy(event.currentTarget);
  try {
    await apiFetch("/users", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        username: els.newUsername.value.trim(),
        display_name: els.newDisplayName.value.trim(),
        password: els.newUserPassword.value,
        role: els.newRole.value,
        email: document.getElementById("newEmail")?.value.trim() || null,
        gsm_number: els.newGsmNumber?.value.trim() || null,
      }),
    });
    els.userForm.reset();
    showMessage("Потребителят е създаден", "Списъкът с потребители е обновен.", "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешно създаване", error.message);
  } finally {
    releaseSubmit();
  }
}

async function handleCarCreate(event) {
  event.preventDefault();
  if (!validateCarForm()) {
    showMessage("Има проблем", "Поправи данните за автомобила.");
    return;
  }

  const releaseSubmit = setSubmitBusy(event.currentTarget);
  try {
    await apiFetch("/cars", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        plate_number: els.plate.value.trim(),
        model: els.model.value.trim(),
      }),
    });
    els.carForm.reset();
    showMessage("Автомобилът е регистриран", "Флотът е обновен.", "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешна регистрация", error.message);
  } finally {
    releaseSubmit();
  }
}

async function handleHandoff(event) {
  event.preventDefault();
  if (!els.handoffUserId || !els.handoffUserId.value) {
    showMessage("Липсва потребител", "Избери активен потребител за admin handoff.");
    return;
  }

  const confirmed = await confirmAction(t("confirm.handoff"), t("action.handoff"));
  if (!confirmed) return;

  const releaseSubmit = setSubmitBusy(event.currentTarget);
  try {
    const data = await apiFetch(`/users/${Number(els.handoffUserId.value)}/handoff-admin`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        demote_self: Boolean(els.handoffDemoteSelf?.checked),
        reason: els.handoffReason?.value?.trim() || null,
      }),
    });
    showMessage(
      "Admin ownership е обновен",
      `${data.next_admin.display_name} вече има admin достъп.`,
      "success"
    );
    if (els.handoffForm) {
      els.handoffForm.reset();
    }
    await refreshData();
  } catch (error) {
    showMessage("Неуспешен handoff", error.message);
  } finally {
    releaseSubmit();
  }
}

async function handleBlackoutCreate(event) {
  event.preventDefault();
  if (!els.blackoutCarId?.value || !els.blackoutStartTime?.value || !els.blackoutEndTime?.value) {
    showMessage("Непълни данни", "Избери автомобил и blackout интервал.");
    return;
  }

  const releaseSubmit = setSubmitBusy(event.currentTarget);
  try {
    await apiFetch(`/cars/${Number(els.blackoutCarId.value)}/blackouts`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        kind: els.blackoutKind?.value || "maintenance",
        start_time: toIso(els.blackoutStartTime.value),
        end_time: toIso(els.blackoutEndTime.value),
        reason: els.blackoutReason?.value?.trim() || null,
      }),
    });
    if (els.blackoutForm) {
      els.blackoutForm.reset();
    }
    showMessage("Blackout е добавен", "Автомобилът вече е блокиран за този интервал.", "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешен blackout", error.message);
  } finally {
    releaseSubmit();
  }
}

async function toggleCar(carId) {
  const car = state.cars.find((item) => item.id === carId);
  if (!car) return;

  if (car.active) {
    const confirmed = await confirmAction(t("confirm.deactivateCar"), t("action.deactivate"));
    if (!confirmed) return;
  }

  try {
    await apiFetch(`/cars/${carId}/${car.active ? "deactivate" : "activate"}`, {
      method: "POST",
      headers: authHeaders(),
    });
    showMessage("Флотът е обновен", `${car.plate_number} е ${car.active ? "деактивиран" : "активиран"}.`, "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешна промяна", error.message);
  }
}

async function toggleUser(userId, action) {
  if (action === "deactivate") {
    const confirmed = await confirmAction(t("confirm.deactivateUser"), t("action.deactivate"));
    if (!confirmed) return;
  }

  try {
    await apiFetch(`/users/${userId}/${action}`, {
      method: "POST",
      headers: authHeaders(),
    });
    showMessage("Потребителят е обновен", "Списъкът с потребители е актуализиран.", "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешна промяна", error.message);
  }
}

async function resetUserPassword(userId) {
  const user = state.users.find((item) => item.id === userId);
  if (!user) return;

  const payload = await resetPasswordDialog(user);
  if (!payload) return;

  try {
    await apiFetch(`/users/${userId}/reset-password`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    showMessage("Паролата е обновена", t("admin.passwordResetSuccess", { name: user.display_name }), "success");
    await loadUserAudit(userId);
  } catch (error) {
    showMessage("Неуспешен reset", error.message);
  }
}

async function changeUserRole(userId) {
  const user = state.users.find((item) => item.id === userId);
  if (!user) return;

  const payload = await roleChangeDialog(user);
  if (!payload || payload.role === user.role) return;

  try {
    await apiFetch(`/users/${userId}/role`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    showMessage("Ролята е обновена", t("admin.roleChangeSuccess", { name: user.display_name }), "success");
    await refreshData();
    await loadUserAudit(userId);
  } catch (error) {
    showMessage("Неуспешна смяна на роля", error.message);
  }
}

async function loadUserAudit(userId) {
  try {
    state.userAudit[userId] = await apiFetch(`/users/${userId}/audit`, { headers: authHeaders() });
    renderUsers();
  } catch (error) {
    showMessage("Audit историята не се зареди", error.message);
  }
}

async function deactivateBlackout(blackoutId) {
  const confirmed = await confirmAction(t("confirm.blackoutDeactivate"), t("action.deactivate"));
  if (!confirmed) return;

  try {
    await apiFetch(`/cars/blackouts/${blackoutId}/deactivate`, {
      method: "POST",
      headers: authHeaders(),
    });
    showMessage("Blackout е обновен", "Прозорецът вече е неактивен.", "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешна промяна", error.message);
  }
}

async function handleBlackoutEdit(blackoutId) {
  const blackout = state.blackouts.find((b) => b.id === blackoutId);
  if (!blackout) return;

  const payload = await editBlackoutDialog(blackout);
  if (!payload) return;

  try {
    await apiFetch(`/cars/${blackout.car_id}/blackouts/${blackoutId}`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    showMessage("Blackout е обновен", "Прозорецът е обновен успешно.", "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешна промяна", error.message);
  }
}

async function saveCarNotes(carId) {
  const textarea = document.querySelector(`[data-car-notes-id="${carId}"]`);
  const notes = textarea ? textarea.value.trim() || null : null;

  try {
    const updated = await apiFetch(`/cars/${carId}/notes`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({ notes }),
    });
    // Update in-memory so employee note hint re-renders correctly
    const car = state.cars.find((c) => c.id === carId);
    if (car) car.notes = updated.notes ?? null;
    showMessage("Бележките са запазени", `${updated.plate_number} — бележката е обновена.`, "success");
  } catch (error) {
    showMessage("Неуспешно запазване", error.message);
  }
}

async function sendTestNotification() {
  try {
    const result = await apiFetch("/notifications/test", {
      method: "POST",
      headers: authHeaders(),
    });
    const channelLines = result.channels
      .map((ch) => {
        const status = t(`notification.channel${ch.status.charAt(0).toUpperCase() + ch.status.slice(1).replace("_", "")}`) || ch.status;
        return `${ch.name}: ${status}${ch.error ? ` — ${ch.error}` : ""}`;
      })
      .join("\n");
    showMessage(t("notification.testTitle"), `${t("notification.testSuccess")}\n\n${channelLines}`, "success");
    await loadNotifications();
  } catch (error) {
    showMessage(t("notification.testTitle"), error.message);
  }
}

function bulkResultDetails(results) {
  return results
    .filter((item) => item.status === "skipped" || item.error)
    .map((item) => `#${item.id}: ${item.error || item.status}`);
}

async function bulkReservationDecision(action) {
  const ids = [...state.selectedReservationIds];
  if (!ids.length) {
    showMessage("Няма избор", t("bulk.noSelection"));
    return;
  }

  let payload = { ids, reason: t(action === "approve" ? "audit.approvedViaUi" : "audit.rejectedViaUi") };
  if (action === "approve") {
    const confirmed = await confirmAction(t("confirm.bulkApprove", { count: ids.length }), t("action.bulkApprove"));
    if (!confirmed) return;
  } else {
    const result = await userDialog({
      title: t("action.bulkReject"),
      body: t("confirm.bulkReject"),
      confirmLabel: t("action.bulkReject"),
      renderFields: () => `
        <label class="field">
          <span>${t("admin.rejectReasonLabel")}</span>
          <textarea name="reason" rows="3" required placeholder="${t("conflict.noPurpose")}"></textarea>
        </label>
      `,
      readValue: (form) => ({ reason: form.elements.reason.value.trim() }),
      validate: (value) =>
        !value.reason ? { message: t("admin.rejectReasonRequired"), fieldName: "reason" } : null,
    });
    if (!result) return;
    payload = { ids, reason: result.reason };
  }

  const button = action === "approve" ? els.bulkApproveBtn : els.bulkRejectBtn;
  const originalText = button?.textContent;
  if (button) {
    button.disabled = true;
    button.textContent = t("form.submit.loading");
  }

  try {
    const response = await apiFetch(`/reservations/bulk-${action}`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    const messageKey = action === "approve" ? "bulk.approveSuccess" : "bulk.rejectSuccess";
    const details = bulkResultDetails(response.results || []);
    showMessage(
      "Batch lifecycle е обновен",
      t(messageKey, { succeeded: response.succeeded, failed: response.failed }),
      response.failed ? "error" : "success",
      details
    );
    state.selectedReservationIds.clear();
    await refreshData();
  } catch (error) {
    showMessage("Batch действието не успя", error.message);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = originalText;
    }
    renderBulkActionBar();
  }
}

async function reservationAction(id, action) {
  if (action === "reject") {
    const result = await userDialog({
      title: t("admin.rejectTitle", { id }),
      body: t("admin.rejectBody"),
      confirmLabel: t("action.reject"),
      renderFields: () => `
        <label class="field">
          <span>${t("admin.rejectReasonLabel")}</span>
          <textarea name="reason" rows="3" required placeholder="${t("conflict.noPurpose")}"></textarea>
        </label>
      `,
      readValue: (form) => ({ reason: form.elements.reason.value.trim() }),
      validate: (value) =>
        !value.reason ? { message: t("admin.rejectReasonRequired"), fieldName: "reason" } : null,
    });
    if (!result) return;
    try {
      await apiFetch(`/reservations/${id}/reject`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(result),
      });
      showMessage("Lifecycle е обновен", t("message.lifecycleSuccess", { id, action: t("action.reject") }), "success");
      await refreshData();
    } catch (error) {
      showMessage("Неуспешно действие", error.message);
    }
    return;
  }

  let payload = null;
  if (action === "cancel") {
    payload = await cancelReservationDialog(id);
    if (!payload) return;
  }

  const confirmationByAction = {
    return: [t("confirm.return"), t("action.returnCar")],
  };
  if (confirmationByAction[action]) {
    const [message, label] = confirmationByAction[action];
    const confirmed = await confirmAction(message, label);
    if (!confirmed) return;
  }

  payload =
    payload ||
    (action === "approve"
      ? { reason: t("audit.approvedViaUi") }
      : action === "start"
          ? { note: t("audit.tripStartedViaUi") }
          : action === "return"
            ? { note: t("audit.vehicleReturnedViaUi") }
            : null);

  try {
    await apiFetch(`/reservations/${id}/${action}`, {
      method: "POST",
      headers: authHeaders(),
      body: payload ? JSON.stringify(payload) : undefined,
    });
    const actionLabel =
      {
        approve: t("action.approve"),
        reject: t("action.reject"),
        start: t("action.startTrip"),
        return: t("action.returnCar"),
        cancel: t("action.cancel"),
      }[action] || action;
    showMessage("Lifecycle е обновен", t("message.lifecycleSuccess", { id, action: actionLabel }), "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешно действие", error.message);
  }
}

async function markNotificationRead(notificationId) {
  try {
    await apiFetch(`/notifications/${notificationId}/read`, {
      method: "POST",
      headers: authHeaders(),
    });
    await loadNotifications();
    updateOverview();
  } catch (error) {
    showMessage("Неуспешно обновяване", error.message);
  }
}

async function markAllRead() {
  if (!state.token) return;
  try {
    await apiFetch("/notifications/read-all", {
      method: "POST",
      headers: authHeaders(),
    });
    await loadNotifications();
    updateOverview();
  } catch (error) {
    showMessage("Неуспешно обновяване", error.message);
  }
}

function updateToolbarPressedStates(buttons, key) {
  buttons.forEach((button) => {
    const active = button.dataset[key] === state[key];
    button.classList.toggle("chip--active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

function wireToolbar(buttons, key, callback) {
  updateToolbarPressedStates(buttons, key);
  buttons.forEach((button) => {
    button.addEventListener("click", async () => {
      state[key] = button.dataset[key];
      updateToolbarPressedStates(buttons, key);
      await callback();
      updateSummary();
      updateOverview();
      renderCurrentTripHero();
    });
  });
}

function initDefaults() {
  if (els.startTime) {
    els.startTime.min = nextLocalSlot(0);
    els.endTime.min = nextLocalSlot(30);
    els.startTime.value = nextLocalSlot(30);
    els.endTime.value = nextLocalSlot(120);
  }
  if (els.blackoutStartTime) {
    els.blackoutStartTime.value = nextLocalSlot(30);
  }
  if (els.blackoutEndTime) {
    els.blackoutEndTime.value = nextLocalSlot(180);
  }
  renderShell();
  renderNotifications();
  renderUsers();
  renderBlackouts();
  renderHandoffCandidates();
  renderCars();
  renderCarSelect();
  renderReservations();
  renderCurrentTripHero();
  renderCalendar();
  renderDayTimeline();
  renderConflictPreview();
  renderSmartPrefill();
  renderNetfleetConfig();
  renderProductionReadiness();
  updateOverview();
  updateSummary();
}

bind(els.bootstrapForm, "submit", handleBootstrap);
bind(els.loginForm, "submit", handleLogin);
bind(els.logoutBtn, "click", handleLogout);
bind(els.logoutBtnSecondary, "click", handleLogout);
bind(els.reservationForm, "submit", handleReservationCreate);
bind(els.quickBookBtn, "click", quickBookReservation);
bind(els.smartPrefillBtn, "click", applySmartPrefill);
bind(els.passwordForm, "submit", handlePasswordChange);
bind(els.userForm, "submit", handleUserCreate);
bind(els.carForm, "submit", handleCarCreate);
bind(els.netfleetForm, "submit", handleNetfleetConfigUpdate);
bind(els.handoffForm, "submit", handleHandoff);
bind(els.blackoutForm, "submit", handleBlackoutCreate);
bind(els.markAllReadBtn, "click", markAllRead);

bind(els.startTime, "change", () => {
  els.endTime.min = els.startTime.value || nextLocalSlot(30);
  scheduleConflictPreview();
});
bind(els.startTime, "input", scheduleConflictPreview);
bind(els.endTime, "change", scheduleConflictPreview);
bind(els.endTime, "input", scheduleConflictPreview);
bind(els.carId, "change", scheduleConflictPreview);
bind(els.reservationSearch, "input", scheduleReservationFilterRefresh);
bind(els.reservationStartDate, "change", scheduleReservationFilterRefresh);
bind(els.reservationEndDate, "change", scheduleReservationFilterRefresh);
bind(els.clearReservationFiltersBtn, "click", clearReservationFilters);
bind(els.exportReservationsBtn, "click", exportReservationsCsv);
bind(els.bulkClearBtn, "click", () => {
  state.selectedReservationIds.clear();
  renderReservations();
});
bind(els.bulkApproveBtn, "click", () => bulkReservationDecision("approve"));
bind(els.bulkRejectBtn, "click", () => bulkReservationDecision("reject"));
bind(els.bulkSelectAll, "change", (event) => {
  setAllPendingReservationsSelected(event.currentTarget.checked);
});

bind(els.monthPrev, "click", () => {
  if (mobileCalendarMedia.matches) {
    setSelectedDate(dateKey(addDays(localDateFromKey(state.selectedDateKey), -1)));
    if (!state.token) loadPublicCalendar().catch((error) => console.warn("Public calendar failed", error));
    return;
  }
  state.calendarDate = addMonths(state.calendarDate, -1);
  if (!state.token) {
    loadPublicCalendar().catch((error) => console.warn("Public calendar failed", error));
  } else {
    renderCalendar();
  }
});

bind(els.monthNext, "click", () => {
  if (mobileCalendarMedia.matches) {
    setSelectedDate(dateKey(addDays(localDateFromKey(state.selectedDateKey), 1)));
    if (!state.token) loadPublicCalendar().catch((error) => console.warn("Public calendar failed", error));
    return;
  }
  state.calendarDate = addMonths(state.calendarDate, 1);
  if (!state.token) {
    loadPublicCalendar().catch((error) => console.warn("Public calendar failed", error));
  } else {
    renderCalendar();
  }
});

bind(els.todayFocus, "click", () => {
  state.calendarDate = startOfMonth(new Date());
  setSelectedDate(dateKey(new Date()));
  if (!state.token) loadPublicCalendar().catch((error) => console.warn("Public calendar failed", error));
});

wireToolbar(document.querySelectorAll("[data-car-filter]"), "carFilter", loadCars);
wireToolbar(document.querySelectorAll("[data-scope]"), "scope", loadReservations);
wireToolbar(document.querySelectorAll("[data-status]"), "status", loadReservations);

if (mobileCalendarMedia.addEventListener) {
  mobileCalendarMedia.addEventListener("change", renderCalendar);
} else if (mobileCalendarMedia.addListener) {
  mobileCalendarMedia.addListener(renderCalendar);
}

document.addEventListener("change", (event) => {
  const reservationCheckbox = event.target.closest("[data-reservation-select]");
  if (reservationCheckbox) {
    setReservationSelected(Number(reservationCheckbox.dataset.reservationSelect), reservationCheckbox.checked);
  }
});

document.addEventListener("click", (event) => {
  const calendarButton = event.target.closest("[data-date-key]");
  const toggleCarButton = event.target.closest("[data-toggle-car]");
  const reservationButton = event.target.closest("[data-reservation-action]");
  const notificationButton = event.target.closest("[data-notification-read]");
  const userButton = event.target.closest("[data-user-action]");
  const userResetButton = event.target.closest("[data-user-reset]");
  const userRoleButton = event.target.closest("[data-user-role]");
  const userAuditButton = event.target.closest("[data-user-audit]");
  const blackoutButton = event.target.closest("[data-blackout-disable]");
  const blackoutEditButton = event.target.closest("[data-blackout-edit]");
  const saveCarNotesButton = event.target.closest("[data-save-car-notes]");
  const testNotificationButton = event.target.closest("[data-test-notification]");
  const handoffButton = event.target.closest("[data-handoff-candidate]");
  const applySlotButton = event.target.closest("[data-apply-slot]");
  const mobileDayShiftButton = event.target.closest("[data-mobile-day-shift]");
  const mobileBookDayButton = event.target.closest("[data-mobile-book-day]");
  const intentButton = event.target.closest("[data-intent-action]");
  const decisionRailSelectAllButton = event.target.closest("[data-decision-rail-select-all]");

  if (decisionRailSelectAllButton) {
    setAllPendingReservationsSelected(true);
    bulkReservationDecision("approve").catch((error) => showMessage(t("action.bulkApprove"), error.message));
    return;
  }
  if (intentButton) {
    handleIntentAction(intentButton).catch((error) => showMessage("Следващият ход не успя", error.message));
  }
  if (applySlotButton) {
    const [start, end] = applySlotButton.dataset.applySlot.split("|");
    if (els.startTime && els.endTime) {
      els.startTime.value = localInputValue(new Date(start));
      els.endTime.value = localInputValue(new Date(end));
      scheduleConflictPreview();
    }
  }
  if (calendarButton) {
    setSelectedDate(calendarButton.dataset.dateKey);
  }
  if (mobileDayShiftButton) {
    const amount = Number(mobileDayShiftButton.dataset.mobileDayShift);
    setSelectedDate(dateKey(addDays(localDateFromKey(state.selectedDateKey), amount)));
  }
  if (mobileBookDayButton) {
    setSelectedDate(mobileBookDayButton.dataset.mobileBookDay);
    els.reservationForm?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  if (toggleCarButton) {
    toggleCar(Number(toggleCarButton.dataset.toggleCar));
  }
  if (reservationButton) {
    reservationAction(Number(reservationButton.dataset.id), reservationButton.dataset.reservationAction);
  }
  if (notificationButton) {
    markNotificationRead(Number(notificationButton.dataset.notificationRead));
  }
  if (userButton) {
    toggleUser(Number(userButton.dataset.userId), userButton.dataset.userAction);
  }
  if (userResetButton) {
    resetUserPassword(Number(userResetButton.dataset.userReset));
  }
  if (userRoleButton) {
    changeUserRole(Number(userRoleButton.dataset.userRole));
  }
  if (userAuditButton) {
    loadUserAudit(Number(userAuditButton.dataset.userAudit));
  }
  if (blackoutButton) {
    deactivateBlackout(Number(blackoutButton.dataset.blackoutDisable));
  }
  if (blackoutEditButton) {
    handleBlackoutEdit(Number(blackoutEditButton.dataset.blackoutEdit));
  }
  if (saveCarNotesButton) {
    saveCarNotes(Number(saveCarNotesButton.dataset.saveCarNotes));
  }
  if (testNotificationButton) {
    sendTestNotification();
  }
  if (handoffButton && els.handoffUserId) {
    els.handoffUserId.value = handoffButton.dataset.handoffCandidate;
    showMessage("Handoff кандидат е избран", "Прегледай настройките и потвърди прехвърлянето.", "success");
  }
});

async function initialize() {
  initDefaults();
  await loadSetupStatus();
  await refreshData();
}

initialize();
