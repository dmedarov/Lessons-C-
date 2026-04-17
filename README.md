# Lessons-C- / Car Pool Reservation API

Чист, модулен пример за резервация на пул от служебни автомобили — FastAPI + SQLite, контейнеризиран с Docker. Фокус върху реалистична сигурност и чист код.

## Какво прави

- Роли: `employee` и `fleet_admin` (login с парола → bearer token).
- Автомобили: добавяне, активиране/деактивиране (само admin).
- Резервации: създаване, approve / reject / cancel workflow.
- Защита от застъпващи се резервации в рамките на една транзакция.
- Audit log за всяко действие по резервация.
- Пагинация при списъка с резервации.
- `health` endpoint за Docker healthcheck.

## Бърз старт

```bash
SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
docker compose up --build
```

- `http://localhost:8000/` — UI
- `http://localhost:8000/docs` — Swagger UI
- `http://localhost:8000/health`

> В `dev` режим (`APP_ENV=dev`) ако не подадеш `SECRET_KEY`, приложението генерира временен ключ — токените няма да оцелеят след рестарт. За prod `SECRET_KEY` е задължителен.

## Архитектура

```
app.py              # FastAPI factory + lifespan
config.py           # Настройки от env (SECRET_KEY, DB_PATH, TOKEN_TTL_SECONDS)
db.py               # SQLite connection, schema, transaction helper, seed
security.py         # HMAC-подписани токени, PBKDF2 пароли, auth deps
schemas.py          # Pydantic request/response модели
routers/
  auth.py           # POST /auth/login
  cars.py           # /cars + deactivate/activate (admin)
  reservations.py   # /reservations + approve/reject/cancel
templates/index.html
tests/test_app.py
conftest.py         # путва project root в sys.path
```

## Login

- `POST /auth/login` → `{access_token, user, role, expires_in}`
- Demo потребители (паролите се hash-ват при първо стартиране):
  - `admin / admin123` → `fleet_admin`
  - `ivan / employee123` → `employee`
- Всеки защитен endpoint очаква `Authorization: Bearer <token>`.
- Токените са **HMAC-SHA256 подписани** с `SECRET_KEY` и имат `exp` (по подразбиране 1 час).

## Правила

- `POST /cars`, `POST /cars/{id}/deactivate`, `POST /cars/{id}/activate` — само `fleet_admin`.
- `POST /reservations` — всеки логнат потребител. Резервацията се записва на името на логнатия (не може да се прави „от името на колега").
- `POST /reservations/{id}/approve`/`reject` — само `fleet_admin`.
- `POST /reservations/{id}/cancel` — admin за всички, employee само за собствените си.
- `GET /reservations` — изисква auth. Employee вижда само собствените си; admin вижда всички. Поддържа `car_id`, `status_filter`, `mine`, `limit`, `offset`.

## Архитектурни решения

1. **Подписани токени** — HMAC-SHA256 над compact JSON payload. Няма външни dependencies.
2. **PBKDF2-SHA256 пароли** (200k итерации) със соли per-user. Само stdlib.
3. **Изолация на записа** — `BEGIN IMMEDIATE` + явен `COMMIT`/`ROLLBACK` през `transaction()` context manager.
4. **Индекс `idx_reservations_car_time`** — ускорява проверката за overlap.
5. **CHECK constraints** на `role` и `status` в SQLite — fail-fast при невалидна стойност.
6. **`datetime.now(timezone.utc)`** — без deprecated `utcnow()`, всичко е timezone-aware.
7. **Lifespan handler** вместо deprecated `@app.on_event`.
8. **Audit log** — всяко действие по резервация се логва с actor + reason.
9. **Docker non-root user** + slim base image + HEALTHCHECK.

## Тестове

```bash
pip install -r requirements-dev.txt
pytest -q
```

Покриват: login, 401/403 матрица, workflow на одобрение, overlap, cancel permissions, deactivate, видимост на списъка per role.

## Ограничения на този пример

- SQLite — ок за single-instance, за multi-writer/production премини на PostgreSQL + Alembic.
- Refresh token-и няма — клиентът прави нов login след `expires_in`.
- Rate limiting и CORS са извън скоупа.

## План за развитие

Виж `ROADMAP.md`.
