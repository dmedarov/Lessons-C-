const state = {
  token: null,
  currentRole: null,
  currentUser: null,
  carFilter: "active",
  scope: "smart",
  status: "all",
  cars: [],
  reservations: [],
  calendarDate: startOfMonth(new Date()),
  selectedDateKey: dateKey(new Date()),
};

const els = {
  loginForm: document.getElementById("loginForm"),
  logoutBtn: document.getElementById("logoutBtn"),
  username: document.getElementById("username"),
  password: document.getElementById("password"),
  sessionBadge: document.getElementById("sessionBadge"),
  heroCaption: document.getElementById("heroCaption"),
  carForm: document.getElementById("carForm"),
  reservationForm: document.getElementById("reservationForm"),
  carId: document.getElementById("carId"),
  startTime: document.getElementById("startTime"),
  endTime: document.getElementById("endTime"),
  purpose: document.getElementById("purpose"),
  carsGrid: document.getElementById("carsGrid"),
  reservationsTableBody: document.getElementById("reservationsTableBody"),
  agendaList: document.getElementById("agendaList"),
  overviewStats: document.getElementById("overviewStats"),
  carPanel: document.getElementById("carPanel"),
  reservationPanel: document.getElementById("reservationPanel"),
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
};

const fieldErrorIds = ["username", "password", "plate", "model", "carId", "startTime", "endTime", "purpose"];

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

function clearErrors() {
  fieldErrorIds.forEach((id) => {
    const node = document.getElementById(`${id}Error`);
    const input = document.getElementById(id);
    if (node) {
      node.textContent = "";
    }
    if (input) {
      input.removeAttribute("aria-invalid");
    }
  });
}

function setFieldError(id, message) {
  const node = document.getElementById(`${id}Error`);
  const input = document.getElementById(id);
  if (node) {
    node.textContent = message;
  }
  if (input) {
    input.setAttribute("aria-invalid", "true");
  }
}

function showMessage(title, text, type = "error", details = []) {
  els.message.classList.remove("hidden");
  els.messageTitle.textContent = title;
  els.messageText.textContent = text;
  els.message.style.borderColor = type === "success" ? "rgba(30, 130, 76, 0.18)" : "rgba(202, 60, 87, 0.18)";
  els.message.style.background = type === "success" ? "rgba(239, 251, 244, 0.92)" : "rgba(255, 242, 246, 0.92)";
  els.message.style.color = type === "success" ? "#19683d" : "#a52c47";
  els.messageList.innerHTML = "";
  details.forEach((detail) => {
    const li = document.createElement("li");
    li.textContent = detail;
    els.messageList.appendChild(li);
  });
  els.message.focus();
}

function hideMessage() {
  els.message.classList.add("hidden");
  els.messageList.innerHTML = "";
}

function setSession(role, user, token) {
  state.currentRole = role;
  state.currentUser = user;
  state.token = token;

  if (!token) {
    els.sessionBadge.className = "status-pill status-pill--muted";
    els.sessionBadge.textContent = "Не сте влезли";
    els.heroCaption.textContent = "Влез с профил, за да управляваш резервации, календар и наличности.";
    els.carPanel.style.display = "none";
    els.reservationPanel.style.display = "block";
    return;
  }

  els.sessionBadge.className = `status-pill ${role === "fleet_admin" ? "status-pill--admin" : "status-pill--employee"}`;
  els.sessionBadge.textContent = `${user} · ${role === "fleet_admin" ? "fleet_admin" : "employee"}`;
  els.heroCaption.textContent =
    role === "fleet_admin"
      ? "Admin режимът показва пълната месечна картина, чакащите заявки и моментен контрол върху флота."
      : "Employee режимът е фокусиран върху бързо планиране по дни и ясно проследяване на собствените заявки.";
  els.carPanel.style.display = role === "fleet_admin" ? "block" : "none";
  els.reservationPanel.style.display = "block";
}

function formatDateTime(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("bg-BG", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDayLabel(key) {
  return new Intl.DateTimeFormat("bg-BG", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(localDateFromKey(key));
}

function formatMonthLabel(value) {
  return new Intl.DateTimeFormat("bg-BG", {
    month: "long",
    year: "numeric",
  }).format(value);
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
  return `<span class="status-tag status-tag--${status}">${status}</span>`;
}

function calendarPill(item, car) {
  const label = car ? `${car.plate_number}` : `Car ${item.car_id}`;
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

function setSelectedDate(key) {
  state.selectedDateKey = key;
  const selected = localDateFromKey(key);
  const now = new Date();
  if (selected >= new Date(now.getFullYear(), now.getMonth(), now.getDate())) {
    const start = new Date(selected.getFullYear(), selected.getMonth(), selected.getDate(), 9, 0, 0, 0);
    const end = new Date(selected.getFullYear(), selected.getMonth(), selected.getDate(), 11, 0, 0, 0);
    els.startTime.value = localInputValue(start);
    els.endTime.value = localInputValue(end);
    els.endTime.min = els.startTime.value;
  }
  renderCalendar();
  renderDayTimeline();
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
      setSession(null, null, null);
      showMessage("Сесията е изтекла", "Моля, влез отново.", "error");
    }
    throw new Error(data?.detail || "Неуспешна заявка към сървъра.");
  }
  return data;
}

function updateOverview() {
  const activeCars = state.cars.filter((car) => car.active).length;
  const pending = state.reservations.filter((item) => item.status === "pending").length;
  const approved = state.reservations.filter((item) => item.status === "approved").length;
  const mine =
    state.currentRole === "fleet_admin"
      ? state.reservations.filter((item) => item.employee_name === state.currentUser).length
      : state.reservations.length;

  [activeCars, pending, approved, mine].forEach((value, index) => {
    const node = els.overviewStats.querySelectorAll(".stat-card__value")[index];
    if (node) {
      node.textContent = value;
    }
  });
}

function renderCars() {
  const carsToShow = state.cars.filter((car) => (state.carFilter === "active" ? car.active : true));
  els.carsGrid.innerHTML = "";

  if (!carsToShow.length) {
    els.carsGrid.innerHTML = `
      <article class="empty-state">
        <strong>Няма автомобили за този филтър.</strong>
        <p>Смени изгледа или добави нов автомобил като fleet admin.</p>
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
        <span class="status-tag ${car.active ? "status-tag--approved" : "status-tag--cancelled"}">${car.active ? "активен" : "неактивен"}</span>
      </div>
      <p class="mini-note">${car.active ? "Наличен за нови заявки." : "Скрит от нови резервации."}</p>
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
  els.carId.innerHTML = cars.length
    ? cars.map((car) => `<option value="${car.id}">${car.plate_number} · ${car.model}</option>`).join("")
    : `<option value="">Няма активни автомобили</option>`;
}

function reservationActions(item) {
  const actions = [];
  const canAdmin = state.currentRole === "fleet_admin";
  if (item.status === "pending" && canAdmin) {
    actions.push(`<button class="action-btn action-btn--approve" type="button" data-decision="approve" data-id="${item.id}">Approve</button>`);
    actions.push(`<button class="action-btn action-btn--reject" type="button" data-decision="reject" data-id="${item.id}">Reject</button>`);
  }
  if (["pending", "approved"].includes(item.status) && state.token) {
    actions.push(`<button class="action-btn action-btn--cancel" type="button" data-cancel-id="${item.id}">Cancel</button>`);
  }
  return actions.join("");
}

function renderReservations() {
  const cars = carMap();
  els.reservationsTableBody.innerHTML = "";

  if (!state.token) {
    els.reservationsTableBody.innerHTML = `<tr><td colspan="7" class="muted">Влез в системата, за да видиш резервациите.</td></tr>`;
    return;
  }

  if (!state.reservations.length) {
    els.reservationsTableBody.innerHTML = `<tr><td colspan="7" class="muted">Няма резервации за текущия изглед.</td></tr>`;
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
      <td>
        <strong>${item.purpose || "Без описание"}</strong>
        <div class="muted">${item.decision_reason || "Без решение/коментар"}</div>
      </td>
      <td><div class="table-actions">${reservationActions(item)}</div></td>
    `;
    els.reservationsTableBody.appendChild(row);
  });
}

function renderAgenda() {
  const cars = carMap();
  const items = [...state.reservations]
    .filter((item) => ["pending", "approved"].includes(item.status))
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
    .slice(0, 5);

  els.agendaList.innerHTML = "";
  if (!items.length) {
    els.agendaList.innerHTML = `
      <article class="empty-state">
        <strong>Няма предстоящи курсове.</strong>
        <p>Когато има активни заявки, те ще се покажат тук.</p>
      </article>
    `;
    return;
  }

  items.forEach((item) => {
    const car = cars.get(item.car_id);
    const card = document.createElement("article");
    card.className = "agenda-item";
    card.innerHTML = `
      <div class="agenda-item__head">
        <div>
          <strong>${car ? `${car.plate_number} · ${car.model}` : `Car ${item.car_id}`}</strong>
          <p class="muted">${item.employee_name}</p>
        </div>
        ${statusTag(item.status)}
      </div>
      <p>${formatDateTime(item.start_time)} → ${formatDateTime(item.end_time)}</p>
      <p>${item.purpose || "Без уточнена цел"}</p>
    `;
    els.agendaList.appendChild(card);
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
        <span class="calendar-day__count">${items.length ? `${items.length} booking${items.length > 1 ? "s" : ""}` : ""}</span>
      </div>
      <div class="calendar-day__list">
        ${items
          .slice(0, 3)
          .map((item) => {
            const car = cars.get(item.car_id);
            return calendarPill(item, car);
          })
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
    els.selectedDateMeta.textContent = "Няма резервации за избрания ден. Ако денят е бъдещ, можеш да го използваш като старт за нова заявка.";
    els.dayTimeline.innerHTML = `
      <article class="empty-state">
        <strong>Спокоен ден.</strong>
        <p>Няма заетост в този ден за текущия изглед.</p>
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

async function loadCars() {
  const query = state.currentRole === "fleet_admin" ? "?active_only=false" : "";
  const data = await apiFetch(`/cars${query}`);
  state.cars = data.items;
  renderCars();
  renderCarSelect();
  updateOverview();
  renderCalendar();
  renderDayTimeline();
}

async function loadReservations() {
  if (!state.token) {
    state.reservations = [];
    renderReservations();
    renderAgenda();
    updateOverview();
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
  renderAgenda();
  updateOverview();
  renderCalendar();
  renderDayTimeline();
}

async function refreshData() {
  try {
    hideMessage();
    await loadCars();
    await loadReservations();
  } catch (error) {
    showMessage("Неуспешно зареждане", error.message);
  }
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

function validateCarForm() {
  clearErrors();
  let valid = true;
  if (!document.getElementById("plate").value.trim()) {
    setFieldError("plate", "Регистрационният номер е задължителен.");
    valid = false;
  }
  if (!document.getElementById("model").value.trim()) {
    setFieldError("model", "Моделът е задължителен.");
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

async function handleLogin(event) {
  event.preventDefault();
  if (!validateLoginForm()) {
    showMessage("Има проблем", "Поправи маркираните полета преди вход.");
    return;
  }

  try {
    const data = await apiFetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: els.username.value.trim(),
        password: els.password.value,
      }),
    });
    setSession(data.role, data.user, data.access_token);
    showMessage("Успешен вход", `Добре дошъл, ${data.user}.`, "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешен вход", error.message);
  }
}

function handleLogout() {
  setSession(null, null, null);
  clearErrors();
  els.loginForm.reset();
  showMessage("Сесията приключи", "Излязохте успешно.", "success");
  refreshData();
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
        plate_number: document.getElementById("plate").value.trim(),
        model: document.getElementById("model").value.trim(),
      }),
    });
    els.carForm.reset();
    showMessage("Автомобилът е добавен", "Флотът е обновен.", "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешно добавяне", error.message);
  }
}

async function handleReservationCreate(event) {
  event.preventDefault();
  if (!state.token) {
    showMessage("Липсва сесия", "Първо влез в системата.");
    return;
  }
  if (!validateReservationForm()) {
    showMessage("Има проблем", "Поправи данните за резервацията.");
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
    showMessage("Заявката е подадена", "Резервацията е записана като pending.", "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешна резервация", error.message);
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

async function takeDecision(id, action) {
  try {
    await apiFetch(`/reservations/${id}/${action}`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        reason: `${action === "approve" ? "Approved" : "Rejected"} via FleetFlow UI`,
      }),
    });
    showMessage("Статусът е обновен", `Резервация #${id} е ${action === "approve" ? "одобрена" : "отказана"}.`, "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешно решение", error.message);
  }
}

async function cancelReservation(id) {
  try {
    await apiFetch(`/reservations/${id}/cancel`, {
      method: "POST",
      headers: authHeaders(),
    });
    showMessage("Резервацията е отменена", `Резервация #${id} е отменена.`, "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешна отмяна", error.message);
  }
}

function wireToolbar(buttons, key, callback) {
  buttons.forEach((button) => {
    button.addEventListener("click", async () => {
      buttons.forEach((item) => item.classList.remove("chip--active"));
      button.classList.add("chip--active");
      state[key] = button.dataset[key];
      await callback();
    });
  });
}

function initDefaults() {
  els.startTime.min = nextLocalSlot(0);
  els.endTime.min = nextLocalSlot(30);
  els.startTime.value = nextLocalSlot(30);
  els.endTime.value = nextLocalSlot(120);
  setSession(null, null, null);
  renderCars();
  renderReservations();
  renderAgenda();
  renderCalendar();
  renderDayTimeline();
  updateOverview();
}

els.loginForm.addEventListener("submit", handleLogin);
els.logoutBtn.addEventListener("click", handleLogout);
els.carForm.addEventListener("submit", handleCarCreate);
els.reservationForm.addEventListener("submit", handleReservationCreate);

els.startTime.addEventListener("change", () => {
  els.endTime.min = els.startTime.value || nextLocalSlot(30);
});

els.monthPrev.addEventListener("click", () => {
  state.calendarDate = addMonths(state.calendarDate, -1);
  renderCalendar();
});

els.monthNext.addEventListener("click", () => {
  state.calendarDate = addMonths(state.calendarDate, 1);
  renderCalendar();
});

els.todayFocus.addEventListener("click", () => {
  state.calendarDate = startOfMonth(new Date());
  setSelectedDate(dateKey(new Date()));
});

document.querySelectorAll("[data-demo-user]").forEach((button) => {
  button.addEventListener("click", () => {
    els.username.value = button.dataset.demoUser;
    els.password.value = button.dataset.demoPass;
    els.loginForm.requestSubmit();
  });
});

wireToolbar(document.querySelectorAll("[data-car-filter]"), "carFilter", loadCars);
wireToolbar(document.querySelectorAll("[data-scope]"), "scope", loadReservations);
wireToolbar(document.querySelectorAll("[data-status]"), "status", loadReservations);

document.addEventListener("click", (event) => {
  const toggleButton = event.target.closest("[data-toggle-car]");
  const decisionButton = event.target.closest("[data-decision]");
  const cancelButton = event.target.closest("[data-cancel-id]");
  const calendarButton = event.target.closest("[data-date-key]");

  if (toggleButton) {
    toggleCar(Number(toggleButton.dataset.toggleCar));
  }
  if (decisionButton) {
    takeDecision(Number(decisionButton.dataset.id), decisionButton.dataset.decision);
  }
  if (cancelButton) {
    cancelReservation(Number(cancelButton.dataset.cancelId));
  }
  if (calendarButton) {
    setSelectedDate(calendarButton.dataset.dateKey);
  }
});

initDefaults();
refreshData();
