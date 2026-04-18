const bg = {
  "action.approve": "Одобри",
  "action.reject": "Откажи",
  "action.cancel": "Отмени",
  "action.startTrip": "Започни курс",
  "action.returnCar": "Върни автомобил",
  "action.deactivate": "Деактивирай",
  "action.activate": "Активирай",
  "action.handoff": "Прехвърли",
  "action.confirm": "Потвърди",
  "action.keep": "Остави",
  "action.close": "Затвори",
  "action.markRead": "Маркирай като прочетено",
  "status.pending": "Чака одобрение",
  "status.approved": "Одобрена",
  "status.rejected": "Отказана",
  "status.checked_out": "Активен курс",
  "status.returned": "Върната",
  "status.cancelled": "Отменена",
  "status.active": "Активен",
  "status.inactive": "Неактивен",
  "status.read": "прочетено",
  "status.new": "ново",
  "role.employee": "Служител",
  "role.fleet_admin": "Администратор",
  "calendar.records.one": "{count} запис",
  "calendar.records.many": "{count} записа",
  "calendar.noEvents": "Няма lifecycle събития за този ден в текущия изглед.",
  "calendar.selectedTotal": "Общо {count} запис(а) за избрания ден.",
  "conflict.idleTitle": "Проверка за заетост",
  "conflict.idleBody": "Избери автомобил, начало и край, за да видиш конфликти предварително.",
  "conflict.loadingTitle": "Проверявам прозореца",
  "conflict.loadingBody": "Сравнявам избрания слот с активни резервации и blackout-и.",
  "conflict.clearTitle": "Прозорецът изглежда свободен",
  "conflict.clearBody": "Няма намерени конфликти за избрания автомобил и интервал.",
  "conflict.errorTitle": "Проверката не успя",
  "conflict.warningTitle": "Има {count} конфликт(а)",
  "conflict.reservation": "Резервация #{id}: {start} -> {end}",
  "conflict.blackout": "{kind}: {start} -> {end}",
  "conflict.adminDetail": "{employee} · {purpose}",
  "conflict.noPurpose": "без уточнена цел",
  "blackout.kind.service": "Сервиз",
  "blackout.kind.maintenance": "Поддръжка",
  "blackout.kind.inspection": "Преглед",
  "blackout.kind.blocked": "Блокиран прозорец",
  "confirm.title": "Потвърждение",
  "confirm.reject": "Сигурен ли си, че искаш да откажеш тази заявка?",
  "confirm.cancel": "Сигурен ли си, че искаш да отмениш тази резервация?",
  "confirm.return": "Потвърди връщането само ако автомобилът реално е върнат.",
  "confirm.deactivateUser": "Деактивирането спира достъпа на този потребител веднага.",
  "confirm.deactivateCar": "Деактивирането ще извади автомобила от нови заявки.",
  "confirm.handoff": "Потвърди admin handoff. Това променя административния достъп.",
  "confirm.blackoutDeactivate": "Потвърди деактивиране на този blackout прозорец.",
  "message.lifecycleSuccess": "Резервация #{id} премина през действие „{action}“.",
  "audit.approvedViaUi": "Одобрено през FleetFlow интерфейса",
  "audit.rejectedViaUi": "Отказано през FleetFlow интерфейса",
  "audit.tripStartedViaUi": "Курсът е започнат през FleetFlow интерфейса",
  "audit.vehicleReturnedViaUi": "Автомобилът е върнат през FleetFlow интерфейса",
  "entity.unknownCar": "Неизвестен автомобил",
  "entity.car": "Автомобил {id}",
  "ui.initialSetup": "Начална настройка",
  "ui.waitingLogin": "Очаква вход",
  "ui.adminReady": "Административен режим",
  "ui.employeeReady": "Работен режим",
};

function interpolate(template, vars = {}) {
  return template.replace(/\{(\w+)\}/g, (_match, key) => String(vars[key] ?? ""));
}

function t(key, vars = {}) {
  const template = bg[key] || key;
  return interpolate(template, vars);
}

function pluralRecord(count) {
  return t(count === 1 ? "calendar.records.one" : "calendar.records.many", { count });
}

window.FleetFlowI18n = {
  bg,
  pluralRecord,
  t,
};
