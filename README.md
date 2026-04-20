# Lessons-C- / Car Pool Reservation API

Чист, модулен пример за управление на pool car процес в компания — FastAPI, Docker, real auth/user management, role-aware UI и dual-database setup за SQLite в dev и PostgreSQL в production. Продуктовата цел вече е **calm operations assistant for internal mobility**: по-малко UI шум, един основен ход на surface и ясна следваща стъпка.

## Какво прави

- Роли: `employee`, `fleet_approver`, `fleet_reception` и `fleet_admin` (login с парола -> short-lived bearer token + HttpOnly refresh cookie).
- Автомобили: добавяне, активиране/деактивиране (само admin).
- Blackout windows за service/maintenance по автомобил.
- Резервации: employee request/cancel, approver approve/reject, reception start active trip / return lifecycle, admin full override.
- Защита от застъпващи се резервации в рамките на една транзакция.
- Audit log за всяко действие по резервация.
- In-app notifications за ключови lifecycle събития.
- Outbound notifications към email, Slack и Teams, когато са конфигурирани.
- Bootstrap flow за първия `fleet_admin`, без demo users в production.
- User management: създаване, activate/deactivate, password change и guarded admin handoff.
- User contacts: admin може да добавя optional email и GSM номер към потребител.
- Requester contact in requests: след login заявките показват GSM номера на заявителя, или ясно `GSM: не е въведен`, за authenticated потребителите, които вече имат право да виждат резервацията; публичният pre-login календар остава без заявител/GSM.
- Employee admin guard: employee не остава на `/admin`; Admin shortcut-ът в employee изгледа е скрит и се показва само за operational роли.
- Structured access logs: production режимът логва request id, route, status и latency като JSON.
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
- Pre-login operational overview: още преди вход hero status bar-ът показва реални агрегирани броя за чакащи одобрение, активни курсове и свободни коли.
- One-tap booking: employee може да подаде pending заявка за най-подходящата свободна активна кола без ръчно попълване.
- Fleet Intelligence Seed: quick-booking използва explainable scoring върху наличност, скорошно натоварване и user preference, вместо просто първата свободна кола.
- Assignment traceability: ръчните и quick-book резервациите записват `car_assignments` със score и причина за избора.
- Smart prefill: employee формата предлага обичайната кола, час и продължителност от последните резервации.
- Current Trip Hero: активната или следваща одобрена резервация излиза като основен hero блок; employee вижда статус/място за взимане, а reception управлява start/return lifecycle.
- Employee UX priority: след login заявките/lifecycle са преди календара, формата за нова заявка е преди inbox-а, а обучителните карти се скриват, за да няма UI шум.
- Calm default inbox/listing: employee default филтърът е **Текущи**, така че върнатите/отказаните/отменените не стоят в оперативния поток; прочетените нотификации се прибират от inbox-а.
- Role-specific operational surfaces: `/admin` показва Decision Rail за `fleet_approver`, handoff/start/return поток за `fleet_reception`, и пълен control surface само за `fleet_admin`.
- Admin Decision Rail: `/admin` започва с най-спешните pending заявки, директни approve/reject действия и bulk approve за роли с право на решение, преди таблицата.
- Reception Rail: `/admin` показва одобрените курсове за предаване и активните курсове за връщане най-горе за `fleet_reception`/`fleet_admin`, с директни start/return действия преди таблицата.
- Timeline-first reservations: employee/approver/reception/admin виждат lifecycle cards преди таблицата, с действия само според ролята и secondary table fallback.
- Role-aware calendar: operational календарът за `fleet_reception` показва approved handoffs и active returns от глобалния snapshot, независимо от филтъра на таблицата.
- Fleet Pulse: `/admin` показва executive strip с активни курсове, освобождаване до 1 час, pending решения, най-натоварена кола, `X/Y` свежи GPS позиции и compact Fleet Intelligence insight-и.
- NetFleet telemetry: server-side proxy за последни GPS координати по регистрационен номер; API ключът стои само в runtime `.env` или admin-managed DB setting и не стига до browser-а. UI показва last-seen/freshness label, за да е ясно дали локацията е надеждна за вземане на автомобила; reception вижда локация за approved/active handoff коли.
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

`LOG_FORMAT=auto` пази dev логовете четими и превключва production access
логовете към JSON. Ако искаш да форсираш формат: `LOG_FORMAT=json` или
`LOG_FORMAT=text`.

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
първо пускане, bootstrap token, NetFleet настройка, role-separated pool процеса и
минималната live проверка преди реална употреба.

Полезни production команди:

```bash
make logs   # app logs, включително bootstrap token при fresh install
make down   # спира production/dev compose контейнерите
make prod-check # проверява .env преди live cutover
make go-live-check # final gate: env + restore-drill evidence + release-check + live smoke
make prod-backup # създава PostgreSQL backup в backups/
make prod-restore-drill BACKUP=backups/fleetflow-....dump # dry-run restore в отделен project
make audit-prod # локален audit на pinned production runtime dependencies
make audit-prod-full # resolver audit за production dependencies (същият подход като CI)
make release-check # локални production gates: audit, compile, tests, JS syntax
make qa-premium # release gates + browser role smoke
make smoke-live APP_URL=http://127.0.0.1:8001 # health/ready/active admin/public overview на жив stack
make test   # pytest suite
make test-e2e # optional Playwright browser smoke
```

Преди първа реална употреба и преди всяка production миграция направи
`make prod-backup`, после `make prod-restore-drill BACKUP=<backup-file>`. Drill
командата възстановява dump-а в отделен Docker project
`fleetflow_restore_drill`, проверява `alembic_version`, не пипа production
volume-а и записва локално доказателство в игнорираната директория
`.fleetflow/restore-drill-ok.json`. `make go-live-check` отказва cutover без
свеж restore-drill marker от последните `RESTORE_DRILL_MAX_AGE_HOURS` часа
(default 168). Подробната операторска инструкция е в
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
fleet_intelligence/ # explainable scoring, derived metrics and compact admin insights
logging_config.py   # request access log formatter for text/dev and JSON/prod
netfleet_service.py # Server-side NetFleet GPS telemetry client; ключът не стига до browser-а
production_readiness.py # shared prod checks for make prod-check and /ops/readiness
security.py         # HMAC-подписани токени, PBKDF2 пароли, auth deps
schemas.py          # Pydantic request/response модели
routers/
  auth.py           # setup-status, bootstrap-admin, login, refresh, logout, auth/me
  cars.py           # /cars + deactivate/activate + blackout windows
  intelligence.py   # /admin/intelligence/pulse
  notifications.py  # user notification inbox
  ops.py            # admin-only production readiness preflight
  reservations.py   # /reservations + suggest/quick-book/preferences + approve/reject/start/return/cancel
  users.py          # user management + contacts + password change + admin handoff
notifications_service.py  # in-app + outbound notification delivery
alembic/            # versioned DB migrations
templates/index.html
static/
scripts/prod_check.py # .env readiness guard преди live cutover
scripts/go_live_check.py # final go-live gate: env, restore-drill evidence, release + live smoke
scripts/smoke_live.py # URL smoke: health, DB readiness, active admin, public overview
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
- `GET /public/overview` → публични aggregate counts за hero status bar-а преди login.
- `GET /public/calendar?start=&end=` → публични календарни слотове преди login със статус, регистрационен номер и модел; не връща заявител, цел, GPS, reservation id или действия.
- `GET /ops/readiness` → само `fleet_admin`; връща production preflight статус без secret values.
- Всеки защитен endpoint очаква `Authorization: Bearer <token>`.
- Токените са **HMAC-SHA256 подписани** с `SECRET_KEY`, имат `exp` и се re-bind-ват към live user state при всяка заявка.
- Access token-ът по подразбиране живее 1 час (`TOKEN_TTL_SECONDS=3600`), а refresh cookie-то 14 дни (`REFRESH_TOKEN_TTL_SECONDS=1209600`). Refresh token-ите се пазят само като SHA-256 hash в DB, въртят се при всяко `/auth/refresh` извикване и replay на стар refresh token ревокира активната refresh верига за user-а.

## Правила

- `POST /cars`, `POST /cars/{id}/deactivate`, `POST /cars/{id}/activate` — само `fleet_admin`.
- `GET /cars/telemetry/config` и `PUT /cars/telemetry/config` — само `fleet_admin`; записва/сменя NetFleet ключ без да връща текущата стойност.
- `GET /cars/telemetry/latest` — само `fleet_admin`; връща последните NetFleet GPS събития, ако ключът е конфигуриран.
- `GET /cars/{id}/telemetry/latest` — `fleet_admin`, `fleet_reception` за approved/active handoff коли или employee със собствена одобрена/активна резервация за тази кола.
- `GET /users`, `POST /users`, `POST /users/{id}/activate`, `POST /users/{id}/deactivate` — само `fleet_admin`.
- `POST /users` приема optional `email` и `gsm_number`; GSM номерът е contact поле, не auth фактор.
- `POST /users/{id}/handoff-admin` — guarded admin handoff към друг активен user.
- `POST /users/me/password` — логнат потребител, със задължителна текуща парола.
- `POST /cars/{id}/blackouts`, `GET /cars/{id}/blackouts`, `POST /cars/blackouts/{id}/deactivate` — blackout management за service/maintenance.
- `POST /reservations` — всеки логнат потребител. Резервацията се записва на името на логнатия (не може да се прави „от името на колега").
- `GET /reservations` — защитен списък; връща `requester_gsm_number` за видимите за текущия token резервации, за да може approver/reception/служител да се свържат със заявителя. `/public/*` endpoints не връщат GSM.
- `GET /reservations/suggest` и `POST /reservations/quick-book` — employee quick-booking за най-подходящата свободна активна кола през същите conflict/blackout guardrails и Fleet Intelligence scoring.
- `GET /reservations/suggest-best-car?start=&end=` — explainable best-car suggestion за конкретен слот.
- `GET /admin/intelligence/pulse` — само `fleet_admin`; compact derived metrics + insight-и за Fleet Pulse.
- `GET /reservations/preferences` — employee smart prefill от последните 10 собствени резервации.
- `POST /reservations/{id}/approve`/`reject` и bulk approve/reject — `fleet_approver` или `fleet_admin`.
- `POST /reservations/{id}/start` и `POST /reservations/{id}/return` — `fleet_reception` или `fleet_admin`.
- `POST /reservations/{id}/cancel` — admin за всички, employee само за собствените си.
- `GET /reservations` — изисква auth. Employee вижда само собствените си; `fleet_approver`, `fleet_reception` и `fleet_admin` виждат operational queue според филтрите. Поддържа `car_id`, `status_filter`, `mine`, `limit`, `offset`.
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
14. **Role-separated dashboard** — employee, approver, reception и admin имат различни работни повърхности и primary actions.
15. **Dual backend strategy** — SQLite за лек dev старт, PostgreSQL чрез `DATABASE_URL` за production.
16. **Alembic baseline** — production schema changes вече имат versioned migration path.
17. **Dev-only seed** — deterministic тестови акаунти само в `APP_ENV=dev` + `DEV_SEED_DEMO_DATA=true`.
18. **Auth rate limiting** — in-memory brute-force guard за login и bootstrap endpoints.
19. **Refresh-token rotation** — short-lived access tokens + HttpOnly refresh cookie, replay protection и explicit logout invalidation.
20. **UI error prevention** — destructive reject/cancel flows пазят задължителна причина, показват inline грешка и маркират конкретното поле с `aria-invalid`.
21. **Separated pool lifecycle** — служителите заявяват и отменят свои заявки; `fleet_approver` решава заявки; `fleet_reception` отбелязва реално предаване/връщане на ключове и документи; `fleet_admin` има пълен контрол.
22. **Production cutover check** — `make prod-check` валидира `.env` за real origin, generated secrets, matching `DATABASE_URL`, pinned PostgreSQL image, disabled demo seed и production mode.
23. **Secret-safe readiness UI** — admin вижда blockers/warnings за live без да получава сурови secret-и, пароли или connection string.
24. **Backup before migration** — production backup и restore drill са Make targets, backup файловете са извън git, а успешният restore drill записва ignored evidence marker за `make go-live-check`.
25. **User contact data** — email и GSM номер се пазят в user профила за operational coordination, без да участват в login/auth.
26. **Structured production logs** — access logs са JSON в production и съдържат request id, route, status и latency без secret values.
27. **Explainable fleet intelligence first** — quick-book uses a thin rules/metrics layer and records `car_assignments`; snapshot tables/jobs stay future work until production usage proves the need.
28. **Public orientation, private operations** — pre-login UI may show fleet counts and calendar occupancy with plate/model for frictionless orientation; users, trip purpose, GPS, reservation ids and lifecycle actions stay behind auth.
29. **Production gates** — GitHub Actions пази `master` с Python 3.12/3.14 tests, JS syntax check, full production dependency audit and Docker build; `make release-check` дава стабилен локален guardrail без browser smoke.
30. **Route/schema guardrails** — тестовете вече пазят FastAPI route registry от duplicate `(method, path)`, проверяват SQLite bootstrap schema, сравняват SQLite/PostgreSQL table-column contracts и assert-ват single Alembic head.
31. **Premium QA gate** — `make qa-premium` комбинира dependency audit, Python compile, full pytest, JS syntax и browser role smoke; `make smoke-live APP_URL=...` проверява вече вдигнат stack.
32. **Final go-live gate** — `make go-live-check` валидира production `.env`, свеж restore-drill evidence marker, локалните release gates и live health/readiness/active-admin/public overview smoke срещу `APP_URL`.

## Тестове

```bash
pip install -r requirements-dev.txt
make test
make audit-prod
make audit-prod-full
make release-check
make qa-premium
make go-live-check APP_URL=http://127.0.0.1:8001
make smoke-live APP_URL=http://127.0.0.1:8001
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

`make test-e2e` стартира fresh FastAPI server с временна SQLite база за всеки
role flow, за да няма скрита зависимост между сценариите. Покрива public
pre-login orientation, browser-computed light/dark contrast guard, employee
quick-booking, employee admin-deny redirect, approver Decision Rail, admin
control surface, employee mobile calendar и reception handoff/calendar.
При `E2E_ARTIFACT_DIR` записва:
`public-mobile.png`, `employee-desktop.png`, `approver-desktop.png`,
`admin-desktop.png`, `employee-mobile.png` и `reception-desktop.png`.
`test-results/` е игнориран от git.

Последна локална проверка за route/schema guardrails пакета:
`pytest tests/test_schema_contracts.py -q` -> 5 passed,
`pytest -q` -> 140 passed. Следващата browser-evidence вълна раздели
Playwright smoke-а по роли:
`E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
-> 6 passed, `node --check static/app.js`, `node --check static/i18n.js`,
и `PYTHONPYCACHEPREFIX=/tmp/fleetflow-pycache .venv/bin/python -m py_compile e2e/test_browser_smoke.py tests/test_schema_contracts.py`
минаха чисто.

Последна локална проверка за pickup GPS след approval:
`pytest tests/test_ui_compliance.py -q` -> 31 passed,
`pytest -q` -> 140 passed,
`E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
-> 6 passed, `node --check static/app.js`, `node --check static/i18n.js`.
Employee notification polling вече презарежда резервации и pickup telemetry
при ново approval/start/return/cancel известие, така че "Къде да вземеш
колата" се появява без ръчно refresh-ване на страницата. Ако NetFleet не е
конфигуриран или временно не отговори, Current Trip Hero показва ясен fallback,
не празно място.

Последна локална проверка за формат на дата/час:
`pytest tests/test_ui_compliance.py -q` -> 32 passed,
`pytest -q` -> 141 passed,
`E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
-> 6 passed, `node --check static/app.js`, `node --check static/i18n.js`.
UI helper-ът вече форматира дата/час като `dd.mm.yyyy, HH:MM`, без AM/PM и
без locale-dependent `dateStyle/timeStyle`.

Последна локална проверка за requester GSM + employee admin guard:
targeted `tests/test_ui_compliance.py` -> 2 passed,
targeted Playwright employee-admin-deny flow -> 1 passed,
full `.venv/bin/python -m pytest -q` -> 143 passed,
full `E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
-> 7 passed, `node --check static/app.js`, `node --check static/i18n.js`.

Последна premium QA проверка:
`make qa-premium` -> passed (dependency audit, Python compile, 147 pytest
cases, JS syntax, 8 Playwright browser checks). `make smoke-live
APP_URL=http://127.0.0.1:8001` -> `/health`, `/health/ready` и
`/public/overview` passed. Новият go-live evidence guard е покрит от
`pytest tests/test_prod_readiness.py -q` -> 7 passed, включително fresh,
missing и stale restore-drill marker сценарии. Активният Docker stack
`fleetflow_prod_smoke` е healthy на `8001`.

Последна локална проверка за NetFleet pickup clarity:
`pytest tests/test_ui_compliance.py -q` -> 34 passed, `make qa-premium` ->
passed. GPS блоковете вече показват `Последно видяна` + freshness label, а
Fleet Pulse брои само свежи координати за активните коли от последните 60 мин.

Последна локална проверка за reception GPS + employee admin guard:
targeted API/UI tests -> 5 passed; targeted Playwright
employee-admin/reception flow -> 2 passed. Reception Rail вече показва GPS
context за approved/active handoff коли, а employee винаги се връща към
служителския изглед при опит да отвори `/admin`.

Последна локална проверка за browser-computed contrast:
`E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e/test_browser_smoke.py::test_browser_computed_contrast_guard -q`
-> 1 passed. Guard-ът изчислява реалните CSS token стойности в Chromium,
композира translucent surfaces върху фона и пази light/dark primary text,
muted text, primary button, focus ring и status chips от WCAG regressions.

Предишна локална проверка за request-first/role-separated-lifecycle/reception-calendar пакета:
`make audit-prod` -> no known vulnerabilities for pinned runtime dependencies,
direct `pip-audit -r requirements.txt` -> no known vulnerabilities when the resolver completes,
`docker scout cves fleetflow_prod_smoke-car-pool:latest` -> 0 vulnerable packages,
`make release-check` -> passed,
`pytest -q` -> 135 passed, `pytest tests/test_ui_compliance.py -q` -> 31 passed,
`node --check static/app.js`, `node --check static/i18n.js`,
`PYTHONPYCACHEPREFIX=/tmp/fleetflow-pycache .venv/bin/python -m py_compile e2e/test_browser_smoke.py tests/test_ui_compliance.py`,
и `E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
-> 1 passed. `make prod-check` fail-fast-ва без `.env`, както трябва за clean
repo. Старият `fleetflow_test` stack беше премахнат, Docker image-ът беше
rebuild-нат, PostgreSQL compose мина с pin-нат `postgres:16`, `/health` върна
`{"status":"ok"}`, `/health/ready` върна `{"status":"ready","database":"postgres"}`
и актуалният `fleetflow_prod_smoke-car-pool-1` е healthy на `8001`. Backup
drill доказателството мина: backup към `/tmp/fleetflow-backups/...dump` и
restore в изолиран `fleetflow_restore_drill` project с проверен
`alembic_version`. PostgreSQL smoke stack-ът е мигриран до
`alembic_version=20260420_0009`.

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
- Fleet Intelligence Seed: best-car scoring, admin intelligence pulse и `car_assignments` traceability
- timeline-first reservation cards before the secondary table, including lifecycle actions and admin pending selection
- route/schema contracts: duplicate route registry guard, SQLite bootstrap execution, SQLite/PostgreSQL schema parity and single Alembic head
- role-specific Playwright browser evidence: public, browser-computed contrast, employee, approver, admin, mobile employee и reception flows с отделни failure points и screenshots
- pickup GPS refresh after approval: reservation lifecycle notifications trigger reservation + pickup telemetry reload, with visible fallback copy when NetFleet is missing/unavailable
- NetFleet pickup clarity: employee/admin GPS blocks now show `Последно видяна`, freshness state and "потвърди с рецепция" copy for stale/unknown signals; Fleet Pulse counts only active cars with fresh coordinates from the last 60 minutes
- Reception GPS handoff: `fleet_reception` can see scoped location for approved/checked-out cars in Reception Rail; employees cannot remain on `/admin` with either fresh login or restored session

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
- Следващата production/UI стъпка е външно closure доказателство и визуална проверимост: потвърди GitHub Actions Production Gates + Dependabot alert, разшири destructive-action browser evidence и продължи с модулното разделяне на `static/app.js`.

## План за развитие

Виж `ROADMAP.md`.
