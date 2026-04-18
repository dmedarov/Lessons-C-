const state = {
  token: null,
  hasAdmin: true,
  surface: document.body.dataset.surface || "employee",
  currentRole: null,
  currentUser: null,
  carFilter: "active",
  scope: "smart",
  status: "all",
  cars: [],
  reservations: [],
  notifications: [],
  users: [],
  blackouts: [],
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

function localInputValue(date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function statusTag(status) {
  return `<span class="status-tag status-tag--${status}">${status.replace("_", " ")}</span>`;
}

function calendarPill(item, car) {
  const label = car ? car.plate_number : `Car ${item.car_id}`;
  return `<span class="calendar-pill calendar-pill--${item.status}">${label}</span>`;
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
  renderShell();
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
    els.sessionBadge.textContent = "Initial setup";
    return;
  }

  if (!authenticated) {
    els.sessionBadge.className = "status-pill status-pill--muted";
    els.sessionBadge.textContent = "Очаква login";
    return;
  }

  const isAdmin = state.currentRole === "fleet_admin";
  els.sessionBadge.className = `status-pill ${isAdmin ? "status-pill--admin" : "status-pill--employee"}`;
  els.sessionBadge.textContent = `${state.currentUser.display_name} · ${isAdmin ? "fleet_admin" : "employee"}`;
  els.sessionTitle.textContent = isAdmin ? "Admin command ready" : "Employee workspace ready";
  els.sessionModePill.className = `status-pill ${isAdmin ? "status-pill--admin" : "status-pill--employee"}`;
  els.sessionModePill.textContent = isAdmin ? "fleet_admin" : "employee";
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
  const unread = state.notifications.filter((item) => !item.read_at).length;

  [activeCars, pending, activeTrips, unread].forEach((value, index) => {
    const node = els.overviewStats.querySelectorAll(".stat-card__value")[index];
    if (node) {
      node.textContent = value;
    }
  });
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
    els.nextSignalCopy.textContent = `Следващият ти слот започва ${formatDateTime(nextApproved.start_time)}. Когато вземеш автомобила, маркирай го като active trip.`;
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
        <strong>${item.title}</strong>
        ${item.read_at ? `<span class="status-pill status-pill--muted">read</span>` : `<span class="status-pill status-pill--employee">new</span>`}
      </div>
      <p>${item.body}</p>
      <div class="notification-card__foot">
        <span class="muted">${formatDateTime(item.created_at)}</span>
        ${item.read_at ? "" : `<button class="action-btn action-btn--toggle" type="button" data-notification-read="${item.id}">Маркирай като прочетено</button>`}
      </div>
    `;
    els.notificationsList.appendChild(card);
  });
}

function renderUsers() {
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
    card.innerHTML = `
      <div class="user-card__head">
        <div>
          <strong>${user.display_name}</strong>
          <p class="muted">${user.username}</p>
        </div>
        <span class="status-pill ${user.role === "fleet_admin" ? "status-pill--admin" : "status-pill--employee"}">${user.role}</span>
      </div>
      <div class="user-card__meta">
        <span class="status-tag ${user.active ? "status-tag--approved" : "status-tag--cancelled"}">${user.active ? "active" : "inactive"}</span>
        <span class="muted">създаден: ${formatDateTime(user.created_at)}</span>
      </div>
      <div class="car-card__actions">
        ${
          user.active
            ? `<button class="action-btn action-btn--toggle" type="button" data-user-action="deactivate" data-user-id="${user.id}" ${isSelf ? "data-self=true" : ""}>Деактивирай</button>`
            : `<button class="action-btn action-btn--toggle" type="button" data-user-action="activate" data-user-id="${user.id}">Активирай</button>`
        }
        ${
          !isSelf && user.active
            ? `<button class="action-btn action-btn--approve" type="button" data-handoff-candidate="${user.id}">Handoff</button>`
            : ""
        }
      </div>
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
          <strong class="car-card__title">${car.model}</strong>
          <p class="car-card__plate">${car.plate_number}</p>
        </div>
        <span class="status-tag ${car.active ? "status-tag--approved" : "status-tag--cancelled"}">${car.active ? "active" : "inactive"}</span>
      </div>
      <p class="mini-note">${car.active ? "Наличен за нови заявки." : "Изваден от нови резервации."}</p>
      <div class="car-card__actions">
        ${
          state.currentRole === "fleet_admin"
            ? `<button class="action-btn action-btn--toggle" type="button" data-toggle-car="${car.id}">
                ${car.active ? "Деактивирай" : "Активирай"}
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
    ? cars.map((car) => `<option value="${car.id}">${car.plate_number} · ${car.model}</option>`).join("")
    : `<option value="">Няма активни автомобили</option>`;
  if (els.carId) {
    els.carId.innerHTML = markup;
  }
  if (els.blackoutCarId) {
    els.blackoutCarId.innerHTML = markup;
  }
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
        <strong>${car ? `${car.plate_number} · ${car.model}` : `Car ${item.car_id}`}</strong>
        <span class="status-tag status-tag--returned">${item.kind}</span>
      </div>
      <p>${item.reason || "Без конкретизирана причина"}</p>
      <div class="notification-card__foot">
        <span class="muted">${formatDateTime(item.start_time)} → ${formatDateTime(item.end_time)}</span>
        ${item.active ? `<button class="action-btn action-btn--toggle" type="button" data-blackout-disable="${item.id}">Деактивирай</button>` : ""}
      </div>
    `;
    els.blackoutsList.appendChild(card);
  });
}

function renderHandoffCandidates() {
  if (!els.handoffUserId) return;
  const options = state.users
    .filter((user) => user.active && (!state.currentUser || user.id !== state.currentUser.id))
    .map((user) => `<option value="${user.id}">${user.display_name} · ${user.role}</option>`)
    .join("");
  els.handoffUserId.innerHTML = options || `<option value="">Няма подходящ потребител</option>`;
}

function reservationContext(item) {
  const details = [];
  if (item.purpose) {
    details.push(`<strong>${item.purpose}</strong>`);
  }
  if (item.decision_reason) {
    details.push(`<div class="muted">${item.decision_reason}</div>`);
  }
  if (item.checked_out_at) {
    details.push(`<div class="muted">Start: ${formatDateTime(item.checked_out_at)}</div>`);
  }
  if (item.returned_at) {
    details.push(`<div class="muted">Return: ${formatDateTime(item.returned_at)}</div>`);
  }
  return details.join("");
}

function reservationActions(item) {
  const actions = [];
  const canAdmin = state.currentRole === "fleet_admin";
  const isOwner = state.currentUser && item.created_by_id === state.currentUser.id;

  if (item.status === "pending" && canAdmin) {
    actions.push(`<button class="action-btn action-btn--approve" type="button" data-reservation-action="approve" data-id="${item.id}">Approve</button>`);
    actions.push(`<button class="action-btn action-btn--reject" type="button" data-reservation-action="reject" data-id="${item.id}">Reject</button>`);
  }
  if (item.status === "approved" && (canAdmin || isOwner)) {
    actions.push(`<button class="action-btn action-btn--toggle" type="button" data-reservation-action="start" data-id="${item.id}">Start trip</button>`);
  }
  if (item.status === "checked_out" && (canAdmin || isOwner)) {
    actions.push(`<button class="action-btn action-btn--toggle" type="button" data-reservation-action="return" data-id="${item.id}">Return car</button>`);
  }
  if (["pending", "approved"].includes(item.status) && (canAdmin || isOwner)) {
    actions.push(`<button class="action-btn action-btn--cancel" type="button" data-reservation-action="cancel" data-id="${item.id}">Cancel</button>`);
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
      <td>#${item.id}</td>
      <td>
        <strong>${car ? car.plate_number : `Car ${item.car_id}`}</strong>
        <div class="muted">${car ? car.model : "Неизвестен автомобил"}</div>
      </td>
      <td><strong>${item.employee_name}</strong></td>
      <td>
        <strong>${formatDateTime(item.start_time)}</strong>
        <div class="muted">до ${formatDateTime(item.end_time)}</div>
      </td>
      <td>${statusTag(item.status)}</td>
      <td>${reservationContext(item) || '<span class="muted">Без допълнителен контекст</span>'}</td>
      <td><div class="table-actions">${reservationActions(item)}</div></td>
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

  els.calendarMonthLabel.textContent = formatMonthLabel(monthStart);
  els.calendarGrid.innerHTML = "";

  for (let index = 0; index < 42; index += 1) {
    const current = new Date(firstDay);
    current.setDate(firstDay.getDate() + index);
    const key = dateKey(current);
    const items = (days.get(key) || []).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    const button = document.createElement("button");
    button.type = "button";
    button.className = [
      "calendar-day",
      current.getMonth() !== monthIndex ? "calendar-day--outside" : "",
      key === todayKey ? "calendar-day--today" : "",
      key === state.selectedDateKey ? "calendar-day--selected" : "",
    ]
      .filter(Boolean)
      .join(" ");
    button.dataset.dateKey = key;
    button.innerHTML = `
      <div class="calendar-day__head">
        <span class="calendar-day__number">${current.getDate()}</span>
        <span class="calendar-day__count">${items.length ? `${items.length} record${items.length > 1 ? "s" : ""}` : ""}</span>
      </div>
      <div class="calendar-day__list">
        ${items
          .slice(0, 3)
          .map((item) => calendarPill(item, cars.get(item.car_id)))
          .join("")}
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
    els.selectedDateMeta.textContent = "Няма lifecycle събития за този ден в текущия изглед.";
    els.dayTimeline.innerHTML = `
      <article class="empty-state">
        <strong>Спокоен ден.</strong>
        <p>Няма заявки или курсове в избрания ден.</p>
      </article>
    `;
    return;
  }

  els.selectedDateMeta.textContent = `Общо ${selectedItems.length} запис(а) за избрания ден.`;

  selectedItems.forEach((item) => {
    const car = cars.get(item.car_id);
    const card = document.createElement("article");
    card.className = "timeline-item";
    card.innerHTML = `
      <div class="timeline-item__top">
        <div>
          <strong>${car ? `${car.plate_number} · ${car.model}` : `Car ${item.car_id}`}</strong>
          <p class="muted">${item.employee_name}</p>
        </div>
        ${statusTag(item.status)}
      </div>
      <p>${formatDateTime(item.start_time)} → ${formatDateTime(item.end_time)}</p>
      <p>${item.purpose || "Без уточнена цел"}</p>
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

async function loadReservations() {
  if (!state.token) {
    state.reservations = [];
    renderReservations();
    renderCalendar();
    renderDayTimeline();
    return;
  }

  const params = new URLSearchParams();
  if (state.status !== "all") {
    params.set("status_filter", state.status);
  }
  if (state.currentRole === "fleet_admin" && state.scope === "mine") {
    params.set("mine", "true");
  }

  const suffix = params.toString() ? `?${params.toString()}` : "";
  const data = await apiFetch(`/reservations${suffix}`, { headers: authHeaders() });
  state.reservations = data.items;
  renderReservations();
  renderCalendar();
  renderDayTimeline();
}

async function loadNotifications() {
  if (!state.token) {
    state.notifications = [];
    renderNotifications();
    return;
  }
  state.notifications = await apiFetch("/notifications", { headers: authHeaders() });
  renderNotifications();
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
  state.blackouts = [];
  els.loginForm.reset();
  renderNotifications();
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
    els.reservationForm.reset();
    els.startTime.value = nextLocalSlot(30);
    els.endTime.value = nextLocalSlot(120);
    showMessage("Заявката е подадена", "Резервацията е записана като pending.", "success");
    await refreshData();
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
    await apiFetch("/users", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        username: els.newUsername.value.trim(),
        display_name: els.newDisplayName.value.trim(),
        password: els.newUserPassword.value,
        role: els.newRole.value,
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

async function deactivateBlackout(blackoutId) {
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

async function reservationAction(id, action) {
  const payload =
    action === "approve"
      ? { reason: "Approved via FleetFlow UI" }
      : action === "reject"
        ? { reason: "Rejected via FleetFlow UI" }
        : action === "start"
          ? { note: "Trip started via FleetFlow UI" }
          : action === "return"
            ? { note: "Vehicle returned via FleetFlow UI" }
            : null;

  try {
    await apiFetch(`/reservations/${id}/${action}`, {
      method: "POST",
      headers: authHeaders(),
      body: payload ? JSON.stringify(payload) : undefined,
    });
    showMessage("Lifecycle е обновен", `Резервация #${id} премина през действие "${action}".`, "success");
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

function wireToolbar(buttons, key, callback) {
  buttons.forEach((button) => {
    button.addEventListener("click", async () => {
      buttons.forEach((item) => item.classList.remove("chip--active"));
      button.classList.add("chip--active");
      state[key] = button.dataset[key];
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
});

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
  const blackoutButton = event.target.closest("[data-blackout-disable]");
  const handoffButton = event.target.closest("[data-handoff-candidate]");

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
  if (blackoutButton) {
    deactivateBlackout(Number(blackoutButton.dataset.blackoutDisable));
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
