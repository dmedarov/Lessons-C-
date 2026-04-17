# Roadmap: Car Pool Reservation App

## Vision
Леко и надеждно вътрешно приложение за резервации на служебни автомобили с ясна проследимост, роли и минимални конфликти.

## Фаза 1 (Стабилизиране) — 1-2 седмици

### 1) Качество и тестове
- Добавяне на автоматични тестове:
  - unit тестове за валидации (времеви интервали, duplicate car),
  - integration тестове за API endpoint-и,
  - конкурентни тестове за конфликтни резервации.
- Добавяне на `pytest` и тестов pipeline в GitHub Actions.

### 2) Наблюдаемост
- Структурирани логове (JSON) + request ID.
- Ясни HTTP грешки с консистентен формат.
- Базови метрики (брой заявки, latency, 4xx/5xx).

### 3) DX (Developer Experience)
- `Makefile` цели (`make run`, `make test`, `make lint`).
- `.env.example` и конфигурируеми настройки (DB_PATH, log level).

## Фаза 2 (Сигурност и достъп) — 2-3 седмици

### 1) Аутентикация/авторизация
- JWT login.
- Роли: `employee`, `fleet_admin`.
- Ограничаване на действията (само admin добавя/деактивира автомобили).

### 2) Валидации и бизнес правила
- Забрана за резервации в миналото.
- Максимална продължителност на резервация (напр. 24 часа).
- Blackout периоди (сервиз/ремонт).

### 3) Одит и проследимост
- Audit trail: кой и кога създава/редактира/отменя резервация.
- Soft delete за резервации и автомобили.

## Фаза 3 (Скалируемост) — 2-4 седмици

### 1) База данни
- Миграция SQLite -> PostgreSQL.
- Alembic миграции и rollback стратегия.

### 2) API стабилност
- Версиониране (`/api/v1`).
- Rate limiting за write endpoint-и.
- Idempotency key за POST `/reservations`.

### 3) UI подобрения
- Календарен изглед (седмица/ден).
- Филтри по служител, период, автомобил.
- „Моите резервации“ + бутон за отмяна.

## Фаза 4 (Продукция и операции) — 1-2 седмици

### 1) CI/CD
- Автоматичен build + тест + scan на image.
- Tag-ване на версии и release notes.

### 2) Надеждност
- Backup/restore план за DB.
- Runbook за инциденти.
- Health/readiness checks за оркестратор.

### 3) Security hardening
- Dependabot / safety scan.
- CSP/secure headers за UI.
- Secrets management (не в git).

## Suggested backlog (първи 10 задачи)
1. Добави `pytest` + 8 базови теста.
2. Добави GitHub Action за тестове.
3. Въведи Pydantic model за грешки (единен error format).
4. Добави cancel endpoint за резервации.
5. Добави JWT login endpoint.
6. Добави role middleware/dependency.
7. Добави поле `status` за резервация (`active/cancelled`).
8. Добави audit таблица.
9. Подготви PostgreSQL compose профил.
10. Добави календарен UI компонент.
