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

const state = {
  token: null,
  hasAdmin: true,
  surface,
  currentRole: null,
  currentUser: null,
  carFilter: "active",
  scope: "smart",
  status: surface === "admin" ? "pending" : "all",
  reservationSearch: "",
  reservationStartDate: "",
  reservationEndDate: "",
  notificationPollId: null,
  cars: [],
  reservations: [],
  notifications: [],
  users: [],
  userAudit: {},
  blackouts: [],
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
  reservationForm: document.getElementById("reservationForm"),
  passwordForm: document.getElementById("passwordForm"),
  userForm: document.getElementById("userForm"),
  carForm: document.getElementById("carForm"),
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
  overviewStats: document.getElementById("overviewStats"),
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
  reservationSearch: document.getElementById("reservationSearch"),
  reservationStartDate: document.getElementById("reservationStartDate"),
  reservationEndDate: document.getElementById("reservationEndDate"),
  clearReservationFiltersBtn: document.getElementById("clearReservationFiltersBtn"),
  exportReservationsBtn: document.getElementById("exportReservationsBtn"),
};

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
  "newUserPassword",
  "plate",
  "model",
];

let conflictPreviewTimer = null;
let reservationFilterTimer = null;

function startOfMonth(value) {
  return new Date(value.getFullYear(), value.getMonth(), 1);
}

function addMonths(value, amount) {
  return new Date(value.getFullYear(), value.getMonth() + amount, 1);
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

function confirmAction(message, confirmLabel = t("action.confirm")) {
  if (!("HTMLDialogElement" in window)) {
    return Promise.resolve(window.confirm(message));
  }

  return new Promise((resolve) => {
    const dialog = document.createElement("dialog");
    const titleId = `confirm-title-${Date.now()}`;
    dialog.className = "confirm-dialog";
    dialog.setAttribute("aria-labelledby", titleId);

    const title = document.createElement("h2");
    title.id = titleId;
    title.textContent = t("confirm.title");

    const copy = document.createElement("p");
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
    const dialog = document.createElement("dialog");
    const titleId = `user-dialog-title-${Date.now()}`;
    dialog.className = "confirm-dialog user-admin-dialog";
    dialog.setAttribute("aria-labelledby", titleId);

    const heading = document.createElement("h2");
    heading.id = titleId;
    heading.textContent = title;

    const copy = document.createElement("p");
    copy.textContent = body;

    const form = document.createElement("form");
    form.className = "stack";
    form.method = "dialog";
    form.innerHTML = `${renderFields()}<small class="field__error" data-dialog-error></small>`;

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
      if (error) {
        form.querySelector("[data-dialog-error]").textContent = error;
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
    validate: (value) => (value.new_password.length < 8 ? t("admin.passwordTooShort") : null),
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
      if (!value.start_time || !value.end_time) return "Въведи начало и край.";
      if (new Date(value.end_time) <= new Date(value.start_time)) return "Краят трябва да е след началото.";
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

function clearErrors() {
  fieldErrorIds.forEach((id) => {
    const errorNode = document.getElementById(`${id}Error`);
    const inputNode = document.getElementById(id);
    if (errorNode) {
      errorNode.textContent = "";
    }
    if (inputNode) {
      inputNode.removeAttribute("aria-invalid");
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
  }
}

function showMessage(title, text, type = "error", details = []) {
  els.message.classList.remove("hidden");
  els.messageTitle.textContent = title;
  els.messageText.textContent = text;
  els.message.style.borderColor = type === "success" ? "rgba(35, 120, 78, 0.2)" : "rgba(184, 53, 79, 0.18)";
  els.message.style.background = type === "success" ? "rgba(242, 251, 247, 0.92)" : "rgba(255, 244, 246, 0.92)";
  els.message.style.color = type === "success" ? "#165538" : "#8f2740";
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
  const label = car ? car.plate_number : `Car ${item.car_id}`;
  return `<span class="calendar-pill calendar-pill--${item.status}">${escapeHtml(label)}</span>`;
}

function carMap() {
  return new Map(state.cars.map((car) => [car.id, car]));
}

function dayMap() {
  const map = new Map();
  state.reservations.forEach((item) => {
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

async function apiFetch(url, options = {}) {
  const response = await fetch(url, options);
  let data = null;
  try {
    data = await response.json();
  } catch (_error) {
    data = null;
  }

  if (!response.ok) {
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
      await loadNotifications();
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
  const adminMode = state.currentRole === "fleet_admin";
  const adminSurface = state.surface === "admin";

  toggleHidden(els.setupPanel, state.hasAdmin || authenticated);
  toggleHidden(els.loginPanel, !state.hasAdmin || authenticated);
  toggleHidden(els.sessionPanel, !authenticated);
  toggleHidden(els.logoutBtn, !authenticated);
  toggleHidden(els.reservationPanel, !authenticated);
  toggleHidden(els.passwordPanel, !authenticated);
  toggleHidden(els.summaryDeck, !authenticated);
  toggleHidden(els.userCreatePanel, !authenticated || !adminMode || !adminSurface);
  toggleHidden(els.carPanel, !authenticated || !adminMode || !adminSurface);
  toggleHidden(els.usersDeck, !authenticated || !adminMode || !adminSurface);
  toggleHidden(els.handoffForm?.closest(".glass-card"), !authenticated || !adminMode || !adminSurface);
  toggleHidden(els.blackoutForm?.closest(".glass-card"), !authenticated || !adminMode || !adminSurface);
  toggleHidden(els.blackoutsList?.closest(".glass-card"), !authenticated || !adminMode || !adminSurface);

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

  const isAdmin = state.currentRole === "fleet_admin";
  els.sessionBadge.className = `status-pill ${isAdmin ? "status-pill--admin" : "status-pill--employee"}`;
  els.sessionBadge.textContent = `${state.currentUser.display_name} · ${t(isAdmin ? "role.fleet_admin" : "role.employee")}`;
  els.sessionTitle.textContent = isAdmin ? t("ui.adminReady") : t("ui.employeeReady");
  els.sessionModePill.className = `status-pill ${isAdmin ? "status-pill--admin" : "status-pill--employee"}`;
  els.sessionModePill.textContent = t(isAdmin ? "role.fleet_admin" : "role.employee");
  els.sessionMeta.textContent = `${state.currentUser.display_name} (${state.currentUser.username})`;
  if (els.heroCaption) {
    els.heroCaption.textContent = isAdmin
      ? adminSurface
        ? "Отделната admin страница събира approvals, blackout-и, handoff и user control на едно място."
        : "За административни действия отвори отделната Admin страница от горната навигация."
      : "Employee режимът показва само собствените ти заявки, нотификации и следващото практично действие.";
  }
}

function updateOverview() {
  const activeCars = state.cars.filter((car) => car.active).length;
  const pending = state.reservations.filter((item) => item.status === "pending").length;
  const activeTrips = state.reservations.filter((item) => item.status === "checked_out").length;

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
    kpiAvailable.querySelector(".stat-card__value").textContent = activeCars;
    kpiAvailable.classList.toggle("stat-card--available", activeCars > 0);
  }
}

function updateNotificationBadge() {
  if (!els.notificationBadge) return;
  const unread = state.notifications.filter((item) => !item.read_at).length;
  els.notificationBadge.textContent = unread > 99 ? "99+" : String(unread);
  els.notificationBadge.classList.toggle("hidden", !unread);
  els.notificationBadge.classList.toggle("notification-badge--pulse", unread > 0);
}

function updateSummary() {
  if (!state.currentUser) {
    els.modeHeading.textContent = "Влез в системата";
    els.modeCopy.textContent = "След login ще видиш или личен operational desk, или глобален административен изглед.";
    els.nextSignalTitle.textContent = "Очаква setup";
    els.nextSignalCopy.textContent = state.hasAdmin
      ? "Влез с наличен профил, за да заредиш данните."
      : "Създай първия fleet admin, за да инициализираш системата.";
    return;
  }

  const adminMode = state.currentRole === "fleet_admin";
  if (adminMode) {
    const pending = state.reservations.filter((item) => item.status === "pending").length;
    const activeTrips = state.reservations.filter((item) => item.status === "checked_out").length;
    const adminSurface = state.surface === "admin";
    els.modeHeading.textContent = adminSurface ? "Admin control surface" : "Admin on employee desk";
    els.modeCopy.textContent = adminSurface
      ? "Отделна admin страница за approvals, fleet control, blackout windows и continuity actions."
      : "Това е общият desk. За потребители, handoff и blackout-и използвай отделната Admin страница.";
    els.nextSignalTitle.textContent = pending
      ? `${pending} чакащи заявки`
      : activeTrips
        ? `${activeTrips} активни курса`
        : "Няма критични опашки";
    els.nextSignalCopy.textContent = pending
      ? "Прегледай pending редовете и вземи решение директно от таблицата."
      : activeTrips
        ? "Следи кои автомобили са в курс и кои още не са върнати."
        : "Флотът е под контрол и няма чакащи решения.";
    return;
  }

  const activeTrip = state.reservations.find((item) => item.status === "checked_out");
  const nextApproved = [...state.reservations]
    .filter((item) => item.status === "approved")
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))[0];

  els.modeHeading.textContent = "Employee workspace";
  els.modeCopy.textContent = "Личен изглед с ясна история на заявките, активните курсове и нотификациите, които те касаят.";
  if (activeTrip) {
    els.nextSignalTitle.textContent = "Имаш активен курс";
    els.nextSignalCopy.textContent = `Автомобилът е в статус active trip до ${formatDateTime(activeTrip.end_time)}. При приключване го маркирай като върнат.`;
    return;
  }
  if (nextApproved) {
    els.nextSignalTitle.textContent = "Имаш одобрена заявка";
    els.nextSignalCopy.textContent = `Следващият ти слот започва ${formatDateTime(nextApproved.start_time)}. Когато вземеш автомобила, маркирай го като активен курс.`;
    return;
  }
  els.nextSignalTitle.textContent = "Няма активен ангажимент";
  els.nextSignalCopy.textContent = "Ако ти трябва автомобил, можеш да подадеш нова заявка отляво.";
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

  if (!state.notifications.length) {
    els.notificationsList.innerHTML = `
      <article class="empty-state">
        <strong>Тихо табло.</strong>
        <p>В момента няма нови уведомления за текущия потребител.</p>
      </article>
    `;
    return;
  }

  state.notifications.forEach((item) => {
    const card = document.createElement("article");
    card.className = "notification-card";
    card.innerHTML = `
      <div class="notification-card__head">
        <strong>${escapeHtml(item.title)}</strong>
        ${item.read_at ? `<span class="status-pill status-pill--muted">${t("status.read")}</span>` : `<span class="status-pill status-pill--employee">${t("status.new")}</span>`}
      </div>
      <p>${escapeHtml(item.body)}</p>
      <div class="notification-card__foot">
        <span class="muted">${formatDateTime(item.created_at)}</span>
        ${item.read_at ? "" : `<button class="action-btn action-btn--toggle" type="button" data-notification-read="${item.id}">${t("action.markRead")}</button>`}
      </div>
    `;
    els.notificationsList.appendChild(card);
  });
  updateNotificationBadge();
}

function renderUsers() {
  if (!els.usersGrid) return;
  els.usersGrid.innerHTML = "";

  if (state.currentRole !== "fleet_admin") {
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
        <span class="status-pill ${user.role === "fleet_admin" ? "status-pill--admin" : "status-pill--employee"}">${t(`role.${user.role}`)}</span>
      </div>
      <div class="user-card__meta">
        <span class="status-tag ${user.active ? "status-tag--approved" : "status-tag--cancelled"}">${t(user.active ? "status.active" : "status.inactive")}</span>
        ${user.email ? `<span class="muted">${escapeHtml(user.email)}</span>` : ""}
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
  els.carsGrid.innerHTML = "";

  if (!carsToShow.length) {
    els.carsGrid.innerHTML = `
      <article class="empty-state">
        <strong>Няма автомобили за този изглед.</strong>
        <p>${state.currentRole === "fleet_admin" ? "Регистрирай автомобил или смени филтъра." : "Изчакай fleet admin да добави наличност."}</p>
      </article>
    `;
    return;
  }

  carsToShow.forEach((car) => {
    const card = document.createElement("article");
    card.className = "car-card";
    card.innerHTML = `
      <div class="car-card__meta">
        <div>
          <strong class="car-card__title">${escapeHtml(car.model)}</strong>
          <p class="car-card__plate">${escapeHtml(car.plate_number)}</p>
        </div>
        <span class="status-tag ${car.active ? "status-tag--approved" : "status-tag--cancelled"}">${t(car.active ? "status.active" : "status.inactive")}</span>
      </div>
      <p class="mini-note">${car.active ? "Наличен за нови заявки." : "Изваден от нови резервации."}</p>
      ${
        state.currentRole === "fleet_admin"
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
          state.currentRole === "fleet_admin"
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

  if (state.currentRole !== "fleet_admin") {
    els.blackoutsList.innerHTML = `
      <article class="empty-state">
        <strong>Blackout-и са видими само за admin.</strong>
      </article>
    `;
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
  const canAdmin = state.currentRole === "fleet_admin";
  const isOwner = state.currentUser && item.created_by_id === state.currentUser.id;

  if (item.status === "pending" && canAdmin) {
    actions.push(`<button class="action-btn action-btn--approve" type="button" data-reservation-action="approve" data-id="${item.id}" aria-label="${t("action.approve")} резервация #${item.id}">${t("action.approve")}</button>`);
    actions.push(`<button class="action-btn action-btn--reject" type="button" data-reservation-action="reject" data-id="${item.id}" aria-label="${t("action.reject")} резервация #${item.id}">${t("action.reject")}</button>`);
  }
  if (item.status === "approved" && (canAdmin || isOwner)) {
    actions.push(`<button class="action-btn action-btn--toggle" type="button" data-reservation-action="start" data-id="${item.id}" aria-label="${t("action.startTrip")} за резервация #${item.id}">${t("action.startTrip")}</button>`);
  }
  if (item.status === "checked_out" && (canAdmin || isOwner)) {
    actions.push(`<button class="action-btn action-btn--toggle" type="button" data-reservation-action="return" data-id="${item.id}" aria-label="${t("action.returnCar")} за резервация #${item.id}">${t("action.returnCar")}</button>`);
  }
  if (["pending", "approved"].includes(item.status) && (canAdmin || isOwner)) {
    actions.push(`<button class="action-btn action-btn--cancel" type="button" data-reservation-action="cancel" data-id="${item.id}" aria-label="${t("action.cancel")} резервация #${item.id}">${t("action.cancel")}</button>`);
  }
  return actions.join("");
}

function renderReservations() {
  const cars = carMap();
  els.reservationsTableBody.innerHTML = "";

  if (!state.token) {
    els.reservationsTableBody.innerHTML = `<tr><td colspan="7" class="muted">Влез в системата, за да видиш operational потока.</td></tr>`;
    return;
  }

  if (!state.reservations.length) {
    els.reservationsTableBody.innerHTML = `<tr><td colspan="7" class="muted">${state.currentRole === "fleet_admin" ? "Няма резервации за текущия изглед." : "Нямаш видими резервации за текущия изглед."}</td></tr>`;
    return;
  }

  state.reservations.forEach((item) => {
    const car = cars.get(item.car_id);
    const row = document.createElement("tr");
    row.innerHTML = `
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
}

function renderCalendar() {
  const monthStart = startOfMonth(state.calendarDate);
  const firstDay = new Date(monthStart);
  const weekday = (firstDay.getDay() + 6) % 7;
  firstDay.setDate(firstDay.getDate() - weekday);
  const monthIndex = monthStart.getMonth();
  const todayKey = dateKey(new Date());
  const days = dayMap();
  const cars = carMap();
  const conflictKeys = conflictDateKeys();

  els.calendarMonthLabel.textContent = formatMonthLabel(monthStart);
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
    const card = document.createElement("article");
    card.className = "timeline-item";
    card.innerHTML = `
      <div class="timeline-item__top">
        <div>
          <strong>${escapeHtml(car ? `${car.plate_number} · ${car.model}` : t("entity.car", { id: item.car_id }))}</strong>
          <p class="muted">${escapeHtml(item.employee_name)}</p>
        </div>
        ${statusTag(item.status)}
      </div>
      <p>${formatDateTime(item.start_time)} → ${formatDateTime(item.end_time)}</p>
      ${lifecycleMeter(item)}
      <p>${escapeHtml(item.purpose || "Без уточнена цел")}</p>
    `;
    els.dayTimeline.appendChild(card);
  });
}

function setSelectedDate(key) {
  state.selectedDateKey = key;
  const selected = localDateFromKey(key);
  const today = new Date();
  if (selected >= new Date(today.getFullYear(), today.getMonth(), today.getDate())) {
    const start = new Date(selected.getFullYear(), selected.getMonth(), selected.getDate(), 9, 0, 0, 0);
    const end = new Date(selected.getFullYear(), selected.getMonth(), selected.getDate(), 11, 0, 0, 0);
    els.startTime.value = localInputValue(start);
    els.endTime.value = localInputValue(end);
    els.endTime.min = els.startTime.value;
  }
  renderCalendar();
  renderDayTimeline();
  scheduleConflictPreview();
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
  const query = state.currentRole === "fleet_admin" ? "?active_only=false" : "";
  const data = await apiFetch(`/cars${query}`);
  state.cars = data.items;
  renderCars();
  renderCarSelect();
  await loadBlackouts();
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
  if (state.status !== "all") {
    params.set("status_filter", state.status);
  }
  if (state.currentRole === "fleet_admin" && state.scope === "mine") {
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
    renderCalendar();
    renderDayTimeline();
    return;
  }

  const params = reservationQueryParams();
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const data = await apiFetch(`/reservations${suffix}`, { headers: authHeaders() });
  state.reservations = data.items;
  renderReservations();
  renderCalendar();
  renderDayTimeline();
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
  state.notifications = await apiFetch("/notifications", { headers: authHeaders() });
  renderNotifications();
  updateNotificationBadge();
}

async function loadUsers() {
  if (state.currentRole !== "fleet_admin") {
    state.users = [];
    renderUsers();
    renderHandoffCandidates();
    return;
  }
  state.users = await apiFetch("/users", { headers: authHeaders() });
  renderUsers();
  renderHandoffCandidates();
}

async function loadBlackouts() {
  if (state.currentRole !== "fleet_admin" || !state.cars.length) {
    state.blackouts = [];
    renderBlackouts();
    return;
  }

  const requests = state.cars.map((car) =>
    apiFetch(`/cars/${car.id}/blackouts`, { headers: authHeaders() }).then((items) =>
      items.map((item) => ({ ...item, car_id: car.id }))
    )
  );
  const batches = await Promise.all(requests);
  state.blackouts = batches.flat();
  renderBlackouts();
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
    await Promise.all([loadReservations(), loadNotifications(), loadUsers()]);
    updateOverview();
    updateSummary();
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

  try {
    await apiFetch("/auth/bootstrap-admin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.hasAdmin = true;
    await loginWith(payload.username, payload.password);
  } catch (error) {
    showMessage("Setup не успя", error.message);
  }
}

async function handleLogin(event) {
  event.preventDefault();
  if (!validateLoginForm()) {
    showMessage("Има проблем", "Поправи полетата за вход.");
    return;
  }

  try {
    await loginWith(els.username.value.trim(), els.password.value);
  } catch (error) {
    showMessage("Неуспешен вход", error.message);
  }
}

function handleLogout() {
  setSession(null, null);
  state.notifications = [];
  state.reservations = [];
  state.users = [];
  state.userAudit = {};
  state.blackouts = [];
  els.loginForm.reset();
  resetConflictPreview();
  renderNotifications();
  updateNotificationBadge();
  renderReservations();
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
  }
}

async function handlePasswordChange(event) {
  event.preventDefault();
  if (!validatePasswordForm()) {
    showMessage("Има проблем", "Поправи полетата за смяна на парола.");
    return;
  }

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
  }
}

async function handleUserCreate(event) {
  event.preventDefault();
  if (!validateUserForm()) {
    showMessage("Има проблем", "Поправи данните за новия потребител.");
    return;
  }

  try {
    const newEmail = document.getElementById("newEmail");
    await apiFetch("/users", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        username: els.newUsername.value.trim(),
        display_name: els.newDisplayName.value.trim(),
        password: els.newUserPassword.value,
        role: els.newRole.value,
        email: newEmail?.value.trim() || null,
      }),
    });
    els.userForm.reset();
    showMessage("Потребителят е създаден", "Списъкът с потребители е обновен.", "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешно създаване", error.message);
  }
}

async function handleCarCreate(event) {
  event.preventDefault();
  if (!validateCarForm()) {
    showMessage("Има проблем", "Поправи данните за автомобила.");
    return;
  }

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
  }
}

async function handleBlackoutCreate(event) {
  event.preventDefault();
  if (!els.blackoutCarId?.value || !els.blackoutStartTime?.value || !els.blackoutEndTime?.value) {
    showMessage("Непълни данни", "Избери автомобил и blackout интервал.");
    return;
  }

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

async function reservationAction(id, action) {
  if (action === "reject") {
    const result = await userDialog({
      title: t("admin.rejectTitle", { id }),
      body: t("admin.rejectBody"),
      confirmLabel: t("action.reject"),
      renderFields: () => `
        <label class="field">
          <span>${t("admin.rejectReasonLabel")}</span>
          <textarea name="reason" rows="3" placeholder="${t("conflict.noPurpose")}"></textarea>
        </label>
      `,
      readValue: (form) => ({ reason: form.elements.reason.value.trim() || t("audit.rejectedViaUi") }),
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

  const confirmationByAction = {
    cancel: [t("confirm.cancel"), t("action.cancel")],
    return: [t("confirm.return"), t("action.returnCar")],
  };
  if (confirmationByAction[action]) {
    const [message, label] = confirmationByAction[action];
    const confirmed = await confirmAction(message, label);
    if (!confirmed) return;
  }

  const payload =
    action === "approve"
      ? { reason: t("audit.approvedViaUi") }
      : action === "start"
          ? { note: t("audit.tripStartedViaUi") }
          : action === "return"
            ? { note: t("audit.vehicleReturnedViaUi") }
            : null;

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
  renderCalendar();
  renderDayTimeline();
  renderConflictPreview();
  updateOverview();
  updateSummary();
}

bind(els.bootstrapForm, "submit", handleBootstrap);
bind(els.loginForm, "submit", handleLogin);
bind(els.logoutBtn, "click", handleLogout);
bind(els.logoutBtnSecondary, "click", handleLogout);
bind(els.reservationForm, "submit", handleReservationCreate);
bind(els.passwordForm, "submit", handlePasswordChange);
bind(els.userForm, "submit", handleUserCreate);
bind(els.carForm, "submit", handleCarCreate);
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

bind(els.monthPrev, "click", () => {
  state.calendarDate = addMonths(state.calendarDate, -1);
  renderCalendar();
});

bind(els.monthNext, "click", () => {
  state.calendarDate = addMonths(state.calendarDate, 1);
  renderCalendar();
});

bind(els.todayFocus, "click", () => {
  state.calendarDate = startOfMonth(new Date());
  setSelectedDate(dateKey(new Date()));
});

wireToolbar(document.querySelectorAll("[data-car-filter]"), "carFilter", loadCars);
wireToolbar(document.querySelectorAll("[data-scope]"), "scope", loadReservations);
wireToolbar(document.querySelectorAll("[data-status]"), "status", loadReservations);

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
