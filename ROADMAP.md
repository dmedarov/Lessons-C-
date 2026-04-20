# Roadmap: FleetFlow

## Product North Star
Вътрешно приложение за pool car управление, позиционирано като **calm
operations assistant for internal mobility**, което е:

- спокойно и ясно като executive tool, не като ERP
- intent-driven: surface-ът сам показва следващия най-важен ход
- сигурно и предвидимо при role промени, деактивации и operational edge cases
- устойчиво за production промени чрез миграции, audit trail и контролируем lifecycle

## Design Principles

- Една основна задача на екран: employee вижда бърз booking и собствените курсове; approver вижда само решения; reception вижда ключове/документи/start-return; admin вижда флот, настройки и full operational visibility.
- Един primary action на surface: всичко останало е secondary или contextual.
- Ясен status model: заявка, одобрение, активен курс, връщане и уведомяване без скрити състояния.
- Служебен lifecycle ownership: employee заявява/отменя, approver
  одобрява/отказва, reception отбелязва реално предаване и връщане, admin
  остава full-control override.
- Кратки и стойностни нотификации: без шум, без дублиране, без чувствителни данни.
- Migration-first backend: schema промени минават през Alembic, не през ad-hoc ръчни SQL промени.
- Security by default: пароли с slow hash, short-lived access token-и, refresh-token rotation, rebinding към текущ user state, least-privilege UI.

## What Best Practice Research Suggests

### Authentication and user management
- OWASP Authentication Cheat Sheet препоръчва активна сесия + reauthentication за чувствителни действия, неясни auth грешки и силно логване на auth събития.
- За нашия продукт това означава: bootstrap на първи admin, без demo users в production, моментно отнемане на достъп при deactivation, refresh-token rotation с logout invalidation, и password change с текуща парола.

### Notifications
- Apple HIG насърчава concise, glanceable notifications и избягване на noise/duplicates.
- За FleetFlow това означава: in-app inbox с кратки operational съобщения само при request, approval/rejection, start, return, cancel.

### Admin and operational UX
- Apple HIG и Material guidance сочат към ясна визуална йерархия, спокойни повърхности, малко, но силни действия и status visibility.
- GOV.UK notification banner guidance подсказва, че важните състояния трябва да са в контекста на текущата задача, а не смесени с validation errors.
- За FleetFlow това означава: отделни admin/employee изгледи, status rail, notification center, и контекстни действия в самия ред/карта.

### Database evolution
- Alembic official docs препоръчват migration scripts като основен механизъм за change management, вместо приложението да “гадае” schema evolution в production.
- За нас това означава: `alembic upgrade head` в production compose flow и versioned schema история.

## Delivery Roadmap

## Phase 1: Trusted Core

### Goal
Да махнем demo поведението и да имаме реален access model.

### Scope
- bootstrap на първи `fleet_admin`
- admin-created users
- activate/deactivate users
- промяна на парола с current password
- role-aware auth context, rebinding на token към live DB state

### Success metric
- няма предварително seed-нати production акаунти
- deactivated user губи достъп веднага
- employee няма достъп до admin действия нито в API, нито в UI

## Phase 2: Operational Reservation Lifecycle

### Goal
Да превърнем “заявка” в пълен служебен процес.

### Scope
- request
- approve / reject
- trip started / checked out
- returned
- cancel
- audit log на всяка стъпка
- видимост за това какво вижда employee 1, employee 2 и admin

### Success metric
- втори служител не вижда чужди резервации
- admin вижда global queue и управлява lifecycle transitions
- върната резервация вече не блокира бъдещ слот при overlap проверка

## Phase 3: Calm Notification Layer

### Goal
Да има operational awareness без UI шум.

### Scope
- in-app notification center
- unread/read state
- event routing:
  - admin получава нова заявка
  - requester получава approve/reject
  - requester получава start/return updates, защото reception отбелязва активен курс и връщане
- outbound hooks към email/Teams/Slack

### Success metric
- user вижда само релевантните за него събития
- notification count не расте с дублиращи се съобщения за едно и също действие

## Phase 3A: Admin Continuity

### Goal
Да няма single-point-of-failure при admin ownership и поддръжка на автомобили.

### Scope
- guarded admin handoff flow
- user audit trail за административни действия
- blackout windows за service/maintenance
- reservation validation срещу активни blackout windows

### Success metric
- handoff не оставя системата без активен admin
- blackout window винаги блокира конфликтна резервация
- admin промени оставят trace за бъдещ audit surface

## Phase 4: Apple-grade Interface System

### Goal
Да изглежда спокойно, точно и high-trust, с проверими Apple/NASA/USWDS guardrails.

### Scope
- отделни admin и employee surfaces
- ясна visual hierarchy
- premium typography и по-малко, но по-силни action points
- timeline и calendar като primary planning tools
- notification banner за глобални operational messages
- празни състояния, които насочват към следващото действие
- Apple HIG layout/buttons/accessibility правила: 44 px touch targets,
  press/focus states, no overlap, readable hierarchy, resilient larger text
- NASA-inspired palette и 508/WCAG contrast matrix

### Success metric
- employee може да направи заявка без обучение
- admin може да одобрява и управлява флота без да “лови” действия из интерфейса
- UI change не влиза без screenshots, keyboard pass и contrast evidence

## Phase 5: Production Discipline

### Goal
Да можем да пускаме промени безопасно.

### Scope
- Alembic baseline и production upgrade flow
- PostgreSQL-first production path
- smoke tests след deploy
- backup/restore playbook
- structured logging и request correlation

### Success metric
- всяка schema промяна има revision
- production boot минава през `alembic upgrade head`

## Phase 6: Security & Session Hardening

### Goal
Да имаме production-ready session model без forced hourly logouts и без скрити stale privileges.

### Scope
- short-lived HMAC access token-и
- HttpOnly refresh cookie, 14 дни по подразбиране
- refresh-token rotation при всяко `/auth/refresh`
- replay protection: стар refresh token ревокира активната refresh верига за user-а
- explicit logout invalidation
- бъдещ session-management UI по устройство/browser

### Success metric
- UI-то се възстановява тихо след access-token expiry
- logout прекратява текущата refresh сесия
- deactivation/role промяна продължава да влиза в сила веднага през live auth rebinding

## Phase 7: UI/UX Compliance Program

### Goal
Да превърнем "Apple/NASA качество" от вкус в измерим процес за бъдещи AI агенти.

### Scope
- `docs/UI_UX_COMPLIANCE_AUDIT.md` с inventory на всички повърхности
- design-token contrast matrix за light/dark theme
- responsive layout pass на 390 / 768 / 1024 / 1440 px
- WCAG/USWDS semantic pass: landmarks, labels, keyboard, dialogs, live regions
- NN/g error-prevention pass for destructive flows: confirmations, required
  reasons, preserved input and focused invalid fields
- Playwright screenshot + e2e harness за визуални/flow regressions
- PR/handoff checklist, който мапва всяка UI промяна към Apple, NASA, USWDS/WCAG/APG или NN/g принцип

### Success metric
- няма overlap, clipped text, unlabeled icon buttons, hover-only actions или color-only statuses
- core flows са keyboard-operable и screen-reader understandable
- contrast checks са автоматизирани и минават за light/dark theme
- бъдещ AI агент може да продължи UI work от audit таблицата без контекст от чат

## Current Implementation Focus

- реален auth/user management
- refresh-token rotation + logout invalidation
- lifecycle: request, approve, start, return, cancel
- in-app notifications
- outbound notifications към email/Slack/Teams
- guarded admin handoff flow
- service and maintenance blackout windows
- admin vs employee views
- Alembic baseline и versioned migrations за всяка schema промяна
- Production setup: `make setup` генерира secrets, `make prod` вдига PostgreSQL + app
- Production cutover: `make prod-check` валидира `.env` за generated secrets,
  pinned PostgreSQL image, real CORS origin, matching DB password и disabled
  demo seed преди live.
- Apple/NASA/USWDS compliance roadmap за следващите UI подобрения
- UI error prevention: reject dialogs now require a human reason and expose
  exact-field `aria-invalid` recovery instead of silent generic fallback reasons
- Cancel dialogs now require a human reason and send it to the reservation
  audit trail while keeping backward-compatible no-body API calls.
- Browser-level evidence started: optional Playwright smoke logs into the
  employee/admin surfaces, verifies one-tap booking, timeline-first cards,
  Admin Decision Rail, Fleet Pulse copy and mobile calendar, and writes
  handoff screenshots under `test-results/e2e`.
- UX hierarchy review: employee requests/lifecycle now appear before the
  calendar, the new-request panel appears before inbox, and auth-only guidance
  cards are hidden after login to keep the cockpit calm.
- Calm operational defaults: employee reservations default to **open/current**
  items, so returned/rejected/cancelled records stay out of the main flow until
  explicitly filtered; read notifications are hidden from the inbox.
- Split operational lifecycle: approval endpoints accept `fleet_approver` or
  `fleet_admin`; start/return endpoints accept `fleet_reception` or
  `fleet_admin`. Employee current-trip surfaces show context and pickup
  location without exposing lifecycle transition buttons.
- User contact readiness: admin user creation now stores optional email and
  GSM number for operational coordination without turning GSM into an auth
  factor.
- Intent-driven summary layer: employee/admin surfaces now expose contextual
  next-action buttons for free mode, active/approved trips, pending admin work,
  active trips and calm fleet state.
- One-tap booking: employee free-mode primary action now creates a pending
  reservation for the nearest available active car, using the existing
  reservation/blackout conflict rules.
- Smart prefill: employee booking now predicts the usual car, start hour and
  typical duration from the user's last 10 reservations, then fills the manual
  form on request without hiding review.
- Current Trip Hero: employee active or next approved trip is promoted above
  the calendar/table with one primary action to view the trip; reception is
  responsible for start/return lifecycle transitions.
- Role-aware surfaces: `/admin` now becomes an approver decision desk,
  reception handoff desk, or full admin cockpit depending on role. Irrelevant
  panels such as user management, NetFleet key and readiness stay hidden unless
  the role is `fleet_admin`.
- Admin Decision Rail: `/admin` now promotes the top 3 pending decisions above
  the bulk bar/table, with direct approve/reject actions and a bulk approve
  path for roles with approval capability.
- Reception Rail: `/admin` now promotes approved handoffs and checked-out
  returns above the lifecycle cards/table for `fleet_reception` and
  `fleet_admin`, using the global operational snapshot so the next key/document
  action is visible even when the detailed table is filtered.
- Role-aware operational calendar: `fleet_reception` calendar/day timeline now
  reads approved handoffs and checked-out returns from the global operational
  snapshot instead of the current table filter, so active returns remain visible
  while the table is filtered to approved work.
- Timeline-first reservation view: employee/approver/reception/admin surfaces
  now render lifecycle cards before the table, with direct actions and
  role-scoped pending selection; the
  table remains a secondary detail view.
- Fleet Pulse strip: `/admin` now shows a calm executive strip for active
  trips, cars releasing within 1 hour, pending decisions, busiest car and GPS
  telemetry availability for the active FleetFlow cars only (`X/Y`), not raw
  NetFleet device event counts.
- Fleet Intelligence Seed: quick-book and `/reservations/suggest-best-car`
  now use explainable scoring across availability, recent utilization and user
  preference; `car_assignments` records the selected mode, score and reason.
- Admin Intelligence Pulse: `/admin/intelligence/pulse` powers compact derived
  insights under Fleet Pulse without adding background jobs or heavy BI.
- Pre-login public overview: `/public/overview` feeds the hero status bar with
  aggregate pending/active/available counts before login, while detailed
  operational records remain authenticated.
- Pre-login public calendar: `/public/calendar` feeds month/day calendar
  occupancy before login with status, plate number and model, while requester,
  purpose, GPS, reservation ids and lifecycle actions remain authenticated.
- NetFleet telemetry: server-side proxy reads latest GPS events by plate number
  from the admin-managed DB setting or `NETFLEET_API_KEY`; the key never
  reaches browser code and the UI never echoes the current secret. Admins see
  fleet-wide telemetry, while employees see pickup location only for their own
  approved/active trip.
- Production readiness: `/health/ready` checks database reachability for
  orchestration, while admin-only `/ops/readiness` and the `/admin` panel show
  live blockers/warnings without exposing secret values. Operator instructions
  now live in `docs/PRODUCTION_USER_GUIDE.md`.
- PostgreSQL image is pinned to major version 16 by default; do not use
  `latest` against a persistent production volume without a planned dump/restore
  major upgrade.
- Backup/restore posture: `make prod-backup` creates a custom-format PostgreSQL
  dump under ignored `backups/`, and `make prod-restore-drill BACKUP=...`
  restores it into an isolated Docker project before migrations.
- Structured production logs: access logs now switch to JSON in production and
  include request id, route, status and latency without secret values. The
  dedicated `fleetflow.access` logger writes one clean stdout JSON line per
  request in production.
- Status bar now reports free cars as active cars minus active trips, matching
  the cockpit wireframe's "available now" mental model.
- Latest local verification for this slice: `pytest -q` -> 135 passed,
  `pytest tests/test_ui_compliance.py -q` -> 31 passed, Playwright browser
  smoke -> 1 passed with employee/admin/reception desktop and employee mobile
  screenshots, JS syntax checks and Python compile check. `make prod-check` fails fast when `.env` is missing in
  a clean checkout. Old `fleetflow_test` containers were removed, Docker stack
  was rebuilt with pinned `postgres:16`, `/health` and `/health/ready` on
  `8001` returned ok/ready and the app container is healthy. A real
  backup/restore drill succeeded from `/tmp/fleetflow-backups/...dump` into
  isolated project `fleetflow_restore_drill`; PostgreSQL smoke is migrated to
  Alembic revision `20260420_0009`.

## Codebase Analysis: 2026-04-20

FleetFlow is now beyond "feature prototype" and should be handled as a
production-prep operations product. The codebase has strong product direction,
but the next improvements should reduce regression risk before adding more
visible modules.

### Architecture strengths

- **Clear role model:** employee requests/cancels, `fleet_approver` decides,
  `fleet_reception` starts/returns, `fleet_admin` configures and overrides.
- **Production-oriented backend:** FastAPI routers, HMAC auth, refresh-token
  rotation, live DB rebinding, Alembic migrations, readiness checks and Docker
  production flow are in place.
- **Premium UX foundation:** intent summary, Current Trip Hero, Admin Decision
  Rail, Reception Rail, role-aware calendar, timeline-first reservations,
  Fleet Pulse and scoped NetFleet pickup context are shipped.
- **Operational safety:** audit trail, blackout windows, guarded admin handoff,
  in-app/outbound notifications and production readiness panel already support
  accountable use.
- **Verification baseline:** `pytest`, UI compliance tests, JS syntax checks,
  Playwright smoke, `make release-check`, Docker smoke and backup/restore drill
  have all been used successfully in recent slices.

### Current risks to address before broad production use

- **Frontend size:** `static/app.js` is 4048 lines and `static/styles.css` is
  3140 lines. New UX work should stop growing the monolith and start extracting
  stable vanilla modules.
- **Reservation router size:** `routers/reservations.py` is 960 lines and owns
  creation, conflict checks, suggestions, lifecycle, bulk decisions, listing
  and export. Split service logic after the next small hardening pass.
- **Schema duality:** `db.py` still supports runtime `CREATE TABLE IF NOT
  EXISTS` bootstrap and `_apply_runtime_upgrades()` while production also uses
  Alembic. The first automated guardrail now checks SQLite bootstrap execution,
  SQLite/PostgreSQL schema contracts, route uniqueness and the single Alembic
  head. Keep extending this when schema complexity grows.
- **Browser evidence gap:** current Playwright coverage is a valuable broad
  smoke, but production readiness needs smaller role-specific tests that fail
  near the broken flow: public overview/calendar, employee booking/current
  trip, approver decisions, reception handoff/return and admin settings.
- **External signal closure:** local audits and Docker Scout were clean, but
  GitHub Security/Dependabot must still be inspected directly after push
  before claiming the banner is closed.
- **Operational docs cadence:** ROADMAP, ROADMAP_IMPROVEMENTS and README must
  be updated after every material change and before commit/push, so future AI
  agents inherit the true state instead of chat-only context.

## Next Recommended Slices

1. Confirm GitHub Actions **Production Gates** and inspect the open GitHub
   Dependabot alert directly; local `pip-audit` and Docker Scout evidence is
   clean, so do not chase phantom upgrades without the alert details.
2. Split Playwright smoke into role-specific production flows: pre-login public
   overview/calendar, employee quick-book/current-trip, approver decision rail,
   reception handoff/return calendar and admin NetFleet/readiness.
3. Browser-computed contrast checks for translucent surfaces, focus rings,
   theme-aware message alerts and Fleet Pulse/status chips.
4. Complete the Phase 8.5 error-prevention sweep for return, deactivate, role
   change, handoff and blackout deactivate.
5. Split `static/app.js` into small vanilla JS modules before the next large UI
   package. Suggested boundaries: API/session, shell/overview, reservations
   lifecycle, calendar, admin users/fleet/settings, notifications/dialogs.
6. Split reservation domain logic out of `routers/reservations.py` into service
   modules without changing endpoint contracts.
7. Add session-management UI and refresh-token cleanup job after the role flows
   are stable.
8. After real production usage, add materialized intelligence snapshots
   (`car_status_snapshots`, `fleet_insights`, `fleet_demand_snapshots`) only if
   inline metrics become too slow or operators need historical trend review.

## References

- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- Alembic Tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Apple Human Interface Guidelines: https://developer.apple.com/design/human-interface-guidelines/
- Apple HIG Layout: https://developer.apple.com/design/human-interface-guidelines/layout
- Apple HIG Buttons: https://developer.apple.com/design/human-interface-guidelines/buttons
- Apple HIG Accessibility: https://developer.apple.com/design/human-interface-guidelines/accessibility
- Apple HIG Typography: https://developer.apple.com/design/human-interface-guidelines/typography
- Apple Notifications HIG: https://developer.apple.com/design/human-interface-guidelines/notifications/
- NASA WDS Colors / 508 contrast: https://nasa.github.io/nasawds-site/components/colors/
- USWDS Accessibility: https://designsystem.digital.gov/documentation/accessibility/
- W3C WCAG: https://www.w3.org/WAI/standards-guidelines/wcag/
- WAI-ARIA APG patterns: https://www.w3.org/WAI/ARIA/apg/patterns/
- Nielsen Norman Group 10 usability heuristics: https://www.nngroup.com/articles/ten-usability-heuristics/
- GOV.UK Notification Banner: https://design-system.service.gov.uk/components/notification-banner/
- Material Design guidance: https://m3.material.io/
