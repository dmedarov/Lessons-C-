# Lessons-C- / Car Pool Reservation API

Чист, модулен пример за резервация на пул от служебни автомобили — FastAPI, Docker и dual-database setup за SQLite в dev и PostgreSQL в production. Фокус върху реалистична сигурност, работещ контейнер и удобен вътрешен UI за служители и fleet admin.

## Какво прави

- Роли: `employee` и `fleet_admin` (login с парола → bearer token).
- Автомобили: добавяне, активиране/деактивиране (само admin).
- Резервации: създаване, approve / reject / cancel workflow.
- Защита от застъпващи се резервации в рамките на една транзакция.
- Audit log за всяко действие по резервация.
- Пагинация при списъка с резервации.
- `health` endpoint за Docker healthcheck.
- Responsive dashboard UI без външни CDN зависимости.
- Бърз operational overview: активни коли, pending/approved заявки, следващи курсове.
- Ясни status тагове, филтри и действия в контекста на всеки запис.
- Реален месечен календарен изглед за планиране и натоварване по дни.
- PostgreSQL-ready режим чрез `DATABASE_URL`.

## Бърз старт

1. Подготви `.env` файл:

```bash
cp .env.example .env
```

2. Сложи реален secret в `.env`, например:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

3. Стартирай контейнера:

```bash
docker compose up --build -d
```

- `http://localhost:8000/` — UI
- `http://localhost:8000/docs` — Swagger UI
- `http://localhost:8000/health`

Спиране:

```bash
docker compose down
```

> За production остави `APP_ENV=prod` и използвай дълъг случаен `SECRET_KEY`. Ако искаш бърза dev среда, можеш да смениш `APP_ENV=dev` в `.env`.

## Production с PostgreSQL

1. Попълни `.env` с реални стойности за `SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` и `DATABASE_URL`.

2. Стартирай production-ready стека:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build -d
```

3. Спиране:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml down
```

## Архитектура

```
app.py              # FastAPI factory + lifespan
config.py           # Настройки от env (SECRET_KEY, DB_PATH, DATABASE_URL, TOKEN_TTL_SECONDS)
db.py               # SQLite/PostgreSQL adapters, schema, transaction helper, dev seed
security.py         # HMAC-подписани токени, PBKDF2 пароли, auth deps
schemas.py          # Pydantic request/response модели
routers/
  auth.py           # POST /auth/login
  cars.py           # /cars + deactivate/activate (admin)
  reservations.py   # /reservations + approve/reject/cancel
templates/index.html
static/
tests/test_app.py
conftest.py         # путва project root в sys.path
docker-compose.postgres.yml
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
9. **Docker multi-stage build** + non-root user + HEALTHCHECK.
10. **Local static assets** — UI-то не зависи от външна CDN връзка.
11. **Role-aware dashboard** — employee вижда бърз booking flow, admin вижда и контрол на наличността.
12. **Dual backend strategy** — SQLite за лек dev старт, PostgreSQL чрез `DATABASE_URL` за production.
13. **Demo users only in dev** — production startup не seed-ва примерни акаунти.

## Тестове

```bash
pip install -r requirements-dev.txt
pytest -q
```

Покриват: login, 401/403 матрица, workflow на одобрение, overlap, cancel permissions, deactivate, видимост на списъка per role.

## Ограничения на този пример

- PostgreSQL режимът е готов за контейнерен production setup, но schema migration история все още липсва; следващата стъпка е Alembic.
- Refresh token-и няма — клиентът прави нов login след `expires_in`.
- Rate limiting и CORS са извън скоупа.

## План за развитие

Виж `ROADMAP.md`.
