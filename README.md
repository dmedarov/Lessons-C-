# Lessons-C- / Car Pool Reservation API

Чист, модулен пример за управление на pool car процес в компания — FastAPI, Docker, real auth/user management, role-aware UI и dual-database setup за SQLite в dev и PostgreSQL в production. Продуктовата цел вече е **calm operations assistant for internal mobility**: по-малко UI шум, един основен ход на surface и ясна следваща стъпка.

## Какво прави

- Роли: `employee` и `fleet_admin` (login с парола -> short-lived bearer token + HttpOnly refresh cookie).
- Автомобили: добавяне, активиране/деактивиране (само admin).
- Blackout windows за service/maintenance по автомобил.
- Резервации: employee request/cancel, admin approve / reject / start active trip / return lifecycle.
- Защита от застъпващи се резервации в рамките на една транзакция.
- Audit log за всяко действие по резервация.
- In-app notifications за ключови lifecycle събития.
- Outbound notifications към email, Slack и Teams, когато са конфигурирани.
- Bootstrap flow за първия `fleet_admin`, без demo users в production.
- User management: създаване, activate/deactivate, password change и guarded admin handoff.
- Пагинация при списъка с резервации.
- `health` endpoint за Docker healthcheck.
- `health/ready` endpoint за production readiness probe към базата.
- Responsive dashboard UI без външни CDN зависимости.
- Отделна admin страница за approvals, users, blackout windows и continuity actions.
- Batch approve/reject UX за pending заявки: checkbox selection, action bar и partial-failure summary.
- Error-prevention dialogs: reject действията изискват конкретна причина, а custom dialog validation фокусира точното грешно поле.
- Cancel действията вече изискват причина в UI и я записват в reservation audit trail.
- Refresh-token rotation: UI-то подновява access token-а тихо при 401, а logout ревокира refresh cookie-то.
- Бърз operational overview: активни коли, pending заявки, активни курсове и непрочетени нотификации.
- Loading skeleton-и и submit busy states за основните форми и панели.
- Ясни status тагове, филтри и действия в контекста на всеки запис.
- Intent-driven summary: началният operational слой показва следващия най-важен ход според режима.
- One-tap booking: employee може да подаде pending заявка за най-близката свободна активна кола без ръчно попълване.
- Smart prefill: employee формата предлага обичайната кола, час и продължителност от последните резервации.
- Current Trip Hero: активната или следваща одобрена резервация излиза като основен hero блок; employee вижда статус/място за взимане, а admin управлява start/return lifecycle.
- Employee UX priority: след login заявките/lifecycle са преди календара, формата за нова заявка е преди inbox-а, а обучителните карти се скриват, за да няма UI шум.
- Calm default inbox/listing: employee default филтърът е **Текущи**, така че върнатите/отказаните/отменените не стоят в оперативния поток; прочетените нотификации се прибират от inbox-а.
- Admin Decision Rail: `/admin` започва с най-спешните pending заявки, директни approve/reject действия и bulk approve, преди таблицата.
- Timeline-first reservations: employee/admin виждат lifecycle cards преди таблицата, с директни действия и secondary table fallback.
- Fleet Pulse: `/admin` показва executive strip с активни курсове, освобождаване до 1 час, pending решения, най-натоварена кола и `X/Y` GPS позиции само за активните коли във FleetFlow.
- NetFleet telemetry: server-side proxy за последни GPS координати по регистрационен номер; API ключът стои само в runtime `.env` или admin-managed DB setting и не стига до browser-а.
- Admin production readiness panel: `/ops/readiness` проверява live blockers без да показва secret-и, пароли или connection string.
- Pickup location: служителят вижда къде да вземе колата само за своя одобрена/активна резервация.
- Status bar-ът показва чакащи, активни курсове и реално свободни коли (активни коли минус активни курсове).
- Реален месечен календарен изглед за планиране и натоварване по дни.
- Mobile day calendar mode под 768px, с предишен/следващ ден и бързо резервиране.
- PostgreSQL-ready режим чрез `DATABASE_URL`.
- Alembic baseline за versioned schema migrations.

## Бърз старт за development

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
- `http://localhost:8000/admin` — Admin UI
- `http://localhost:8000/docs` — Swagger UI
- `http://localhost:8000/health`

В стандартния Docker dev режим (`APP_ENV=dev`) се seed-ват локални тестови акаунти и реалният pool списък от 5 автомобила. Ако тези потребители вече съществуват, паролите им се ресетват при старт на контейнера:

- `admin` / `AdminPass123` — `fleet_admin`
- `ivan` / `IvanPass123` — `employee`
- `maria` / `MariaPass123` — `employee`

Pool автомобили:

- `CA1330PT` — HYUNDAI i30 Wagon
- `CA6945TB` — HYUNDAI i30 Wagon
- `CA6946TB` — HYUNDAI i30 Wagon
- `CA6947TB` — HYUNDAI i20
- `CB2426BH` — HYUNDAI i20

За production остави `APP_ENV=prod` и `DEV_SEED_DEMO_DATA=false`. Тогава няма demo акаунти и UI-то ще поиска да създадеш първия `fleet_admin`.

Спиране:

```bash
docker compose down
```

> За production използвай дълъг случаен `SECRET_KEY`, конкретен `CORS_ALLOW_ORIGINS` и реална PostgreSQL база.

## Production setup simplification

Production flow-ът е умишлено кратък:

```bash
git clone <repo>
cd <repo>
make setup
make prod
```

Това е всичко за първо стартиране.

`make setup`:

- създава `.env` от `.env.example`, ако още няма такъв файл;
- генерира автоматично `SECRET_KEY` с 48-byte random secret;
- генерира автоматично `POSTGRES_PASSWORD` с 32-byte random password;
- обновява `DATABASE_URL`, така че паролата в него да съвпада с реалния
  `POSTGRES_PASSWORD`;
- не презаписва съществуващ `.env`, за да не счупи работеща инсталация.

`make prod`:

- build-ва production image-а;
- стартира PostgreSQL + FleetFlow app през `docker-compose.postgres.yml`;
- използва pin-нат PostgreSQL major image
  (`POSTGRES_IMAGE`, default `postgres:16`), защото
  `latest` може да направи несъвместим major upgrade на съществуващ volume;
- изпълнява Alembic миграциите преди старта на приложението;
- оставя UI-то на `http://localhost:${APP_PORT:-8000}`.

Преди live deployment смени поне:

```env
CORS_ALLOW_ORIGINS=https://your-real-domain.example
```

GPS сигналите могат да се включат по два начина:

1. Препоръчано за оператори: влез като `fleet_admin`, отвори `/admin` и в панела **GPS сигнали / NetFleet ключ** постави ключа еднократно или при промяна. Текущият ключ не се показва обратно в UI.
2. Fallback за инфраструктура: добави ключа в runtime `.env` файла:

```env
NETFLEET_API_KEY=your-netfleet-company-api-key
```

Ако използваш `.env`, рестартирай stack-а с `make prod` или `docker compose ... up -d --build`. Не добавяй реалния ключ в `README`, source файлове, tests или frontend assets.

Ако порт `8000` е зает, задай например:

```env
APP_PORT=8001
```

Преди live cutover пусни:

```bash
make prod-check
```

Тази проверка не стартира контейнери. Тя валидира, че `.env` е в production
режим, secret-ите са генерирани, `DATABASE_URL` използва същата PostgreSQL
парола, `DEV_SEED_DEMO_DATA=false`, а `CORS_ALLOW_ORIGINS` вече е реалният
домейн вместо wildcard/example стойност. Проверява и PostgreSQL image-ът да не
е `latest`. Празен NetFleet ключ е само warning, защото може да се добави
по-късно от Admin UI.

Потребителската production инструкция е в
[`docs/PRODUCTION_USER_GUIDE.md`](docs/PRODUCTION_USER_GUIDE.md). Тя описва
първо пускане, bootstrap token, NetFleet настройка, admin-owned pool процеса и
минималната live проверка преди реална употреба.

Полезни production команди:

```bash
make logs   # app logs, включително bootstrap token при fresh install
make down   # спира production/dev compose контейнерите
make prod-check # проверява .env преди live cutover
make prod-backup # създава PostgreSQL backup в backups/
make prod-restore-drill BACKUP=backups/fleetflow-....dump # dry-run restore в отделен project
make test   # pytest suite
make test-e2e # optional Playwright browser smoke
```

Преди първа реална употреба и преди всяка production миграция направи
`make prod-backup`, после `make prod-restore-drill BACKUP=<backup-file>`. Drill
командата възстановява dump-а в отделен Docker project
`fleetflow_restore_drill`, проверява `alembic_version` и не пипа production
volume-а. Подробната операторска инструкция е в
[`docs/PRODUCTION_USER_GUIDE.md`](docs/PRODUCTION_USER_GUIDE.md).

## Bootstrap token при fresh production install

В production (`APP_ENV=prod`) първият `fleet_admin` не може да се създаде
само от отворен UI. При старт, ако още няма администратор, приложението
генерира еднократен bootstrap token, валиден 30 минути, и го отпечатва в
логовете.

1. Стартирай stack-а:

```bash
make prod
```

2. Вземи token-а:

```bash
make logs
```

Търси блок като:

```text
FleetFlow bootstrap token (valid 30 min, one-shot):
  <token>
Pass as X-Bootstrap-Token header to POST /auth/bootstrap-admin.
```

3. Отвори `/` или `/admin`, попълни първия администратор и постави token-а в
полето **Bootstrap token**.

Token-ът е one-shot: след успешно създаване на първия `fleet_admin` вече не
може да се използва. Ако изтече преди да го използваш, рестартирай app
контейнера и вземи нов token от логовете:

```bash
docker compose -f docker-compose.postgres.yml restart car-pool
make logs
```

## Production с PostgreSQL — ръчен вариант

Препоръчаният път е `make setup && make prod`. Ако все пак искаш ръчен flow:

1. Попълни `.env` с реални стойности за `SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` и `DATABASE_URL`.
   Остави `POSTGRES_IMAGE` pin-нат към major версия, например `postgres:16`.
2. Ако искаш външни нотификации, попълни и `SMTP_*`, `SLACK_WEBHOOK_URL`, `TEAMS_WEBHOOK_URL`.
   Ако искаш live координати, добави ключа през `/admin` или попълни `NETFLEET_API_KEY` в `.env`; `NETFLEET_BASE_URL`
   по подразбиране е `https://api.netfleet.bg:8080`.
   Ако порт `8000` е зает, задай `APP_PORT=8001` или друг свободен порт в `.env`.

3. Стартирай production-ready стека:

```bash
docker compose -f docker-compose.postgres.yml up --build -d
```

Този flow вече изпълнява `alembic upgrade head` преди старта на приложението.

4. Спиране:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml down
```

## Архитектура

```
app.py              # FastAPI factory + lifespan
app_settings.py     # DB-backed runtime settings for admin-managed secrets such as NetFleet
config.py           # Настройки от env (SECRET_KEY, DB_PATH, DATABASE_URL, TOKEN_TTL_SECONDS, REFRESH_TOKEN_TTL_SECONDS, CORS/rate limits, NetFleet)
db.py               # SQLite/PostgreSQL adapters, schema bootstrap, runtime compatibility upgrades
netfleet_service.py # Server-side NetFleet GPS telemetry client; ключът не стига до browser-а
production_readiness.py # shared prod checks for make prod-check and /ops/readiness
security.py         # HMAC-подписани токени, PBKDF2 пароли, auth deps
schemas.py          # Pydantic request/response модели
routers/
  auth.py           # setup-status, bootstrap-admin, login, refresh, logout, auth/me
  cars.py           # /cars + deactivate/activate + blackout windows
  notifications.py  # user notification inbox
  ops.py            # admin-only production readiness preflight
  reservations.py   # /reservations + suggest/quick-book/preferences + approve/reject/start/return/cancel
  users.py          # user management + password change + admin handoff
notifications_service.py  # in-app + outbound notification delivery
alembic/            # versioned DB migrations
templates/index.html
static/
scripts/prod_check.py # .env readiness guard преди live cutover
scripts/backup_postgres.sh # PostgreSQL custom-format backup helper
scripts/restore_postgres_drill.sh # isolated restore validation helper
tests/test_app.py
e2e/test_browser_smoke.py  # optional Playwright browser smoke + screenshots
conftest.py         # путва project root в sys.path
docker-compose.postgres.yml
```

## Login и setup

- `GET /auth/setup-status` → показва дали има активен `fleet_admin`.
- `POST /auth/bootstrap-admin` → създава първия администратор, само когато още няма такъв.
- `POST /auth/login` → `{access_token, user, role, expires_in}` + `fleetflow_refresh` HttpOnly cookie.
- `POST /auth/refresh` → върти refresh token-а от cookie-то и връща нов short-lived access token.
- `POST /auth/logout` → ревокира текущия refresh token и изчиства cookie-то.
- `GET /auth/me` → връща текущия user context.
- `GET /health/ready` → публичен readiness probe, който проверява DB връзката.
- `GET /ops/readiness` → само `fleet_admin`; връща production preflight статус без secret values.
- Всеки защитен endpoint очаква `Authorization: Bearer <token>`.
- Токените са **HMAC-SHA256 подписани** с `SECRET_KEY`, имат `exp` и се re-bind-ват към live user state при всяка заявка.
- Access token-ът по подразбиране живее 1 час (`TOKEN_TTL_SECONDS=3600`), а refresh cookie-то 14 дни (`REFRESH_TOKEN_TTL_SECONDS=1209600`). Refresh token-ите се пазят само като SHA-256 hash в DB, въртят се при всяко `/auth/refresh` извикване и replay на стар refresh token ревокира активната refresh верига за user-а.

## Правила

- `POST /cars`, `POST /cars/{id}/deactivate`, `POST /cars/{id}/activate` — само `fleet_admin`.
- `GET /cars/telemetry/config` и `PUT /cars/telemetry/config` — само `fleet_admin`; записва/сменя NetFleet ключ без да връща текущата стойност.
- `GET /cars/telemetry/latest` — само `fleet_admin`; връща последните NetFleet GPS събития, ако ключът е конфигуриран.
- `GET /cars/{id}/telemetry/latest` — admin или employee със собствена одобрена/активна резервация за тази кола.
- `GET /users`, `POST /users`, `POST /users/{id}/activate`, `POST /users/{id}/deactivate` — само `fleet_admin`.
- `POST /users/{id}/handoff-admin` — guarded admin handoff към друг активен user.
- `POST /users/me/password` — логнат потребител, със задължителна текуща парола.
- `POST /cars/{id}/blackouts`, `GET /cars/{id}/blackouts`, `POST /cars/blackouts/{id}/deactivate` — blackout management за service/maintenance.
- `POST /reservations` — всеки логнат потребител. Резервацията се записва на името на логнатия (не може да се прави „от името на колега").
- `GET /reservations/suggest` и `POST /reservations/quick-book` — employee quick-booking за най-близката свободна активна кола през същите conflict/blackout guardrails.
- `GET /reservations/preferences` — employee smart prefill от последните 10 собствени резервации.
- `POST /reservations/{id}/approve`/`reject` — само `fleet_admin`.
- `POST /reservations/{id}/start` и `POST /reservations/{id}/return` — само `fleet_admin`.
- `POST /reservations/{id}/cancel` — admin за всички, employee само за собствените си.
- `GET /reservations` — изисква auth. Employee вижда само собствените си; admin вижда всички. Поддържа `car_id`, `status_filter`, `mine`, `limit`, `offset`.
- `GET /notifications`, `POST /notifications/{id}/read`, `POST /notifications/read-all` — личен inbox на текущия user.

## Архитектурни решения

1. **Подписани токени** — HMAC-SHA256 над compact JSON payload.
2. **PBKDF2-SHA256 пароли** (200k итерации) със соли per-user.
3. **Live auth rebinding** — role промени и deactivation влизат в сила веднага.
4. **Изолация на записа** — `BEGIN IMMEDIATE` + явен `COMMIT`/`ROLLBACK` през `transaction()` context manager.
5. **Lifecycle without UI guesswork** — API връща operational status като `pending`, `approved`, `checked_out`, `returned`.
6. **Audit log + notification layer** — решенията и transitions са traceable и видими.
7. **Outbound delivery is best-effort** — SMTP/Slack/Teams fail-ове се логват отделно и не блокират operational flow.
8. **Admin continuity** — handoff flow позволява атомично предаване на admin ownership.
9. **Maintenance guardrails** — blackout window блокира конфликтна резервация преди запис.
10. **`datetime.now(timezone.utc)`** — timezone-aware навсякъде.
11. **Lifespan handler** вместо deprecated `@app.on_event`.
12. **Docker multi-stage build** + non-root user + HEALTHCHECK.
13. **Local static assets** — UI-то не зависи от външна CDN връзка.
14. **Role-separated dashboard** — employee и admin имат различни работни повърхности.
15. **Dual backend strategy** — SQLite за лек dev старт, PostgreSQL чрез `DATABASE_URL` за production.
16. **Alembic baseline** — production schema changes вече имат versioned migration path.
17. **Dev-only seed** — deterministic тестови акаунти само в `APP_ENV=dev` + `DEV_SEED_DEMO_DATA=true`.
18. **Auth rate limiting** — in-memory brute-force guard за login и bootstrap endpoints.
19. **Refresh-token rotation** — short-lived access tokens + HttpOnly refresh cookie, replay protection и explicit logout invalidation.
20. **UI error prevention** — destructive reject/cancel flows пазят задължителна причина, показват inline грешка и маркират конкретното поле с `aria-invalid`.
21. **Admin-owned lifecycle** — служителите заявяват и отменят свои заявки; само admin отбелязва активен курс и върната кола.
22. **Production cutover check** — `make prod-check` валидира `.env` за real origin, generated secrets, matching `DATABASE_URL`, pinned PostgreSQL image, disabled demo seed и production mode.
23. **Secret-safe readiness UI** — admin вижда blockers/warnings за live без да получава сурови secret-и, пароли или connection string.
24. **Backup before migration** — production backup и restore drill са Make targets, а backup файловете са извън git.

## Тестове

```bash
pip install -r requirements-dev.txt
make test
```

Browser-level UI/UX smoke тестът е отделен от бързия unit/static suite, за да
не прави всеки локален run зависим от Chromium:

```bash
python -m playwright install chromium
make test-e2e
```

За handoff screenshots:

```bash
E2E_ARTIFACT_DIR=test-results/e2e make test-e2e
```

`make test-e2e` стартира fresh FastAPI server с временна SQLite база, логва
employee/admin demo users, проверява one-tap booking, timeline-first cards,
Admin Decision Rail, Fleet Pulse copy и mobile calendar, после записва:
`employee-desktop.png`, `admin-desktop.png` и `employee-mobile.png`.
`test-results/` е игнориран от git.

Последна локална проверка за request-first/admin-lifecycle/production-readiness пакета:
`pytest -q` -> 121 passed, targeted UI/API/production readiness pack -> 32 passed,
`node --check static/app.js`, `node --check static/i18n.js`,
`PYTHONPYCACHEPREFIX=/tmp/fleetflow-pycache .venv/bin/python -m py_compile production_readiness.py routers/ops.py scripts/prod_check.py app.py schemas.py`,
и `E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
-> 1 passed. `make prod-check` fail-fast-ва без `.env`, както трябва за clean
repo. Старият `fleetflow_test` stack беше премахнат, Docker image-ът беше
rebuild-нат, PostgreSQL compose мина с pin-нат `postgres:16`, `/health` върна
`{"status":"ok"}`, `/health/ready` върна `{"status":"ready","database":"postgres"}`
и актуалният `fleetflow_prod_smoke-car-pool-1` е healthy на `8001`. Backup
drill доказателството мина: backup към `/tmp/fleetflow-backups/...dump` и
restore в изолиран `fleetflow_restore_drill` project с проверен
`alembic_version`.

Покриват: login, 401/403 матрица, workflow на одобрение, overlap, cancel permissions, deactivate, видимост на списъка per role.

Допълнително покриват:
- bootstrap-admin flow
- създаване на users от admin
- password change
- lifecycle start/return
- admin-only start/return authorization and employee UI without lifecycle transition buttons
- notifications visibility и `read-all`
- admin handoff
- blackout windows
- outbound dispatch hook
- сценарий с 2 users + 1 admin, включително какво вижда вторият user
- dev seed reset на тестовите акаунти
- login rate limiting
- refresh-token rotation, replay protection и logout invalidation
- UI compliance guardrails: live regions, dialog focus return, exact invalid-field targeting, intent-driven next actions, current trip hero, theme-aware alerts, safe-area mobile nav и задължителни reject/cancel reasons
- NetFleet service normalization/unconfigured states и frontend guardrail, че `NETFLEET_API_KEY` не изтича към browser-facing файлове
- admin-managed NetFleet key flow: status, add/change, admin-only access и server-side usage without returning the secret
- one-tap booking suggestion/create flow и smart prefill preferences за обичайна кола/час/продължителност
- timeline-first reservation cards before the secondary table, including lifecycle actions and admin pending selection

## Alembic migrations

Локално:

```bash
alembic upgrade head
```

Нова revision:

```bash
alembic revision -m "describe change"
```

## Ограничения на този пример

- Няма UI за управление на активни sessions по устройства; logout ревокира текущия refresh token, а replay защита чисти активната refresh верига за user-а.
- Rate limiting-ът е in-memory и е подходящ за single-container deployment; за multi-instance production го изнеси към Redis, API gateway или WAF.
- Следващата production/UI стъпка е операторска дисциплина плюс browser evidence: PostgreSQL migration smoke, backup/restore playbook, structured JSON logs, `make prod-check` в release checklist и Playwright screenshots/e2e за `/`, `/admin`, mobile calendar и reject/bulk flows.

## План за развитие

Виж `ROADMAP.md`.
