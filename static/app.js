const state = {
  token: null,
  currentRole: null,
  currentUser: null,
  carFilter: "active",
  scope: "smart",
  status: "all",
  cars: [],
  reservations: [],
};

const els = {
  loginForm: document.getElementById("loginForm"),
  logoutBtn: document.getElementById("logoutBtn"),
  username: document.getElementById("username"),
  password: document.getElementById("password"),
  loginBtn: document.getElementById("loginBtn"),
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
};

const fieldErrorIds = [
  "username",
  "password",
  "plate",
  "model",
  "carId",
  "startTime",
  "endTime",
  "purpose",
];

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
  els.message.style.borderColor = type === "success" ? "rgba(45, 106, 79, 0.22)" : "rgba(159, 45, 45, 0.22)";
  els.message.style.background = type === "success" ? "rgba(239, 250, 244, 0.96)" : "rgba(255, 241, 238, 0.96)";
  els.message.style.color = type === "success" ? "#20533c" : "#6d2222";
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
    els.heroCaption.textContent = "Влез с профил, за да управляваш резервации и наличности.";
    els.carPanel.style.display = "none";
    els.reservationPanel.style.display = "block";
    return;
  }

  els.sessionBadge.className = `status-pill ${role === "fleet_admin" ? "status-pill--admin" : "status-pill--employee"}`;
  els.sessionBadge.textContent = `${user} · ${role === "fleet_admin" ? "fleet_admin" : "employee"}`;
  els.heroCaption.textContent =
    role === "fleet_admin"
      ? "Admin изгледът показва целия флот, чакащите заявки и контроли за активиране."
      : "Employee изгледът е фокусиран върху бързо подаване на заявка и проследяване на собствените резервации.";
  els.carPanel.style.display = role === "fleet_admin" ? "block" : "none";
  els.reservationPanel.style.display = "block";
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("bg-BG", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function nextLocalSlot(minutesFromNow = 30) {
  const date = new Date(Date.now() + minutesFromNow * 60 * 1000);
  date.setSeconds(0, 0);
  return date.toISOString().slice(0, 16);
}

function toIso(localValue) {
  return localValue ? new Date(localValue).toISOString() : null;
}

function statusTag(status) {
  return `<span class="status-tag status-tag--${status}">${status}</span>`;
}

function carMap() {
  return new Map(state.cars.map((car) => [car.id, car]));
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
      showMessage("Сесията е невалидна", "Моля, влез отново.", "error");
    }
    const detail = data?.detail || "Неуспешна заявка към сървъра.";
    throw new Error(detail);
  }

  return data;
}

function updateOverview() {
  const totalCars = state.cars.length;
  const activeCars = state.cars.filter((car) => car.active).length;
  const pending = state.reservations.filter((item) => item.status === "pending").length;
  const approved = state.reservations.filter((item) => item.status === "approved").length;
  const mine =
    state.currentRole === "fleet_admin"
      ? state.reservations.filter((item) => item.employee_name === state.currentUser).length
      : state.reservations.length;

  const values = [activeCars || totalCars, pending, approved, mine];
  [...els.overviewStats.querySelectorAll(".stat-card__value")].forEach((node, index) => {
    node.textContent = values[index] ?? 0;
  });
}

function renderCars() {
  els.carsGrid.innerHTML = "";
  const carsToShow = state.cars.filter((car) => (state.carFilter === "active" ? car.active : true));

  if (!carsToShow.length) {
    els.carsGrid.innerHTML = `
      <article class="empty-state">
        <div>
          <strong>Няма автомобили за този филтър.</strong>
          <p>Смени изгледа или добави нов автомобил като admin.</p>
        </div>
      </article>
    `;
    return;
  }

  carsToShow.forEach((car) => {
    const card = document.createElement("article");
    card.className = "car-card";
    const activeLabel = car.active ? "Активен" : "Неактивен";
    card.innerHTML = `
      <div class="car-card__meta">
        <div>
          <h3 class="car-card__title">${car.model}</h3>
          <p class="car-card__plate">${car.plate_number}</p>
        </div>
        <span class="status-tag ${car.active ? "status-tag--approved" : "status-tag--cancelled"}">${activeLabel}</span>
      </div>
      <p class="mini-note">ID #${car.id} · ${car.active ? "Готов за нови заявки" : "Скрит от нови резервации"}</p>
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
  const activeCars = state.cars.filter((car) => car.active);
  if (!activeCars.length) {
    els.carId.innerHTML = `<option value="">Няма активни автомобили</option>`;
    return;
  }

  els.carId.innerHTML = activeCars
    .map((car) => `<option value="${car.id}">${car.plate_number} · ${car.model}</option>`)
    .join("");
}

function reservationActions(item) {
  const canAdmin = state.currentRole === "fleet_admin";
  const actions = [];

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
  els.reservationsTableBody.innerHTML = "";
  const cars = carMap();

  if (!state.token) {
    els.reservationsTableBody.innerHTML = `
      <tr>
        <td colspan="7" class="muted">Влез в системата, за да видиш резервациите.</td>
      </tr>
    `;
    els.agendaList.innerHTML = `
      <article class="empty-state">
        <div>
          <strong>Няма активна сесия.</strong>
          <p>След вход ще видиш следващите курсове и статуса им.</p>
        </div>
      </article>
    `;
    return;
  }

  if (!state.reservations.length) {
    els.reservationsTableBody.innerHTML = `
      <tr>
        <td colspan="7" class="muted">Няма резервации за избраните филтри.</td>
      </tr>
    `;
  } else {
    state.reservations.forEach((item) => {
      const car = cars.get(item.car_id);
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>#${item.id}</td>
        <td>
          <strong>${car ? car.plate_number : `Car ${item.car_id}`}</strong>
          <div class="muted">${car ? car.model : "Неизвестен автомобил"}</div>
        </td>
        <td>
          <strong>${item.employee_name}</strong>
          <div class="muted">${item.created_by_id === undefined ? "" : `User #${item.created_by_id}`}</div>
        </td>
        <td>
          <strong>${formatDate(item.start_time)}</strong>
          <div class="muted">до ${formatDate(item.end_time)}</div>
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

  const agendaItems = [...state.reservations]
    .filter((item) => item.status === "approved" || item.status === "pending")
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
    .slice(0, 4);

  if (!agendaItems.length) {
    els.agendaList.innerHTML = `
      <article class="empty-state">
        <div>
          <strong>Няма предстоящи курсове.</strong>
          <p>Подай първата заявка и тя ще се появи тук.</p>
        </div>
      </article>
    `;
    return;
  }

  els.agendaList.innerHTML = agendaItems
    .map((item) => {
      const car = cars.get(item.car_id);
      return `
        <article class="agenda-item">
          <div class="agenda-item__head">
            <div>
              <strong>${car ? `${car.plate_number} · ${car.model}` : `Car ${item.car_id}`}</strong>
              <span class="muted">${item.employee_name}</span>
            </div>
            ${statusTag(item.status)}
          </div>
          <p>${formatDate(item.start_time)} → ${formatDate(item.end_time)}</p>
          <p>${item.purpose || "Без уточнена причина"}</p>
        </article>
      `;
    })
    .join("");
}

async function loadCars() {
  const query = state.currentRole === "fleet_admin" ? "?active_only=false" : "";
  const data = await apiFetch(`/cars${query}`);
  state.cars = data.items;
  renderCars();
  renderCarSelect();
  updateOverview();
}

async function loadReservations() {
  if (!state.token) {
    state.reservations = [];
    renderReservations();
    updateOverview();
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
  updateOverview();
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
  const plate = document.getElementById("plate").value.trim();
  const model = document.getElementById("model").value.trim();

  if (!plate) {
    setFieldError("plate", "Регистрационният номер е задължителен.");
    valid = false;
  }
  if (!model) {
    setFieldError("model", "Моделът е задължителен.");
    valid = false;
  }
  return valid;
}

function validateReservationForm() {
  clearErrors();
  let valid = true;
  const carId = els.carId.value;
  const start = els.startTime.value;
  const end = els.endTime.value;
  const now = Date.now();

  if (!carId) {
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
    els.reservationForm.reset();
    els.startTime.value = nextLocalSlot(30);
    els.endTime.value = nextLocalSlot(120);
    showMessage("Заявката е подадена", "Резервацията е записана като pending.", "success");
    await refreshData();
  } catch (error) {
    showMessage("Неуспешна резервация", error.message);
  }
}

async function toggleCar(carId) {
  const car = state.cars.find((item) => item.id === carId);
  if (!car) return;

  const action = car.active ? "deactivate" : "activate";
  try {
    await apiFetch(`/cars/${carId}/${action}`, {
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
  updateOverview();
}

els.loginForm.addEventListener("submit", handleLogin);
els.logoutBtn.addEventListener("click", handleLogout);
els.carForm.addEventListener("submit", handleCarCreate);
els.reservationForm.addEventListener("submit", handleReservationCreate);

els.startTime.addEventListener("change", () => {
  els.endTime.min = els.startTime.value || nextLocalSlot(30);
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

  if (toggleButton) {
    toggleCar(Number(toggleButton.dataset.toggleCar));
  }
  if (decisionButton) {
    takeDecision(Number(decisionButton.dataset.id), decisionButton.dataset.decision);
  }
  if (cancelButton) {
    cancelReservation(Number(cancelButton.dataset.cancelId));
  }
});

initDefaults();
refreshData();
