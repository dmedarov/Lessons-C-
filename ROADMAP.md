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
- Ролевите surfaces имат кратки, стабилни имена: **Моят курс / Нова заявка**,
  **Decision Desk**, **Handoff Desk**, **Control Tower**.
- Кратки и стойностни нотификации: без шум, без дублиране, без чувствителни данни.
- Migration-first backend: schema промени минават през Alembic, не през ad-hoc ръчни SQL промени.
- Security by default: пароли с slow hash, short-lived access token-и, refresh-token rotation, rebinding към текущ user state, least-privilege UI.
- Secret hygiene by default: реални ключове стоят само в runtime `.env`,
  provider consoles или admin-managed DB setting; source, tests, docs, frontend
  assets и screenshots не трябва да съдържат NetFleet/API/DB/token стойности.

## What Best Practice Research Suggests

### Authentication and user management
- OWASP Authentication Cheat Sheet препоръчва активна сесия + reauthentication за чувствителни действия, неясни auth грешки и силно логване на auth събития.
- За нашия продукт това означава: bootstrap на първи admin, без demo users в production, моментно отнемане на достъп при deactivation, refresh-token rotation с logout invalidation, и password change с текуща парола.

### Notifications
- Apple HIG насърчава concise, glanceable notifications и избягване на noise/duplicates.
- За FleetFlow това означава: in-app inbox с кратки operational съобщения само
  при request, approval/rejection, reception handoff, start, return, cancel;
  SMTP следва личния recipient, Teams е shared operational channel.

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
  - admin/approver получава нова заявка
  - requester получава approve/reject
  - reception/admin получава handoff сигнал след approval
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

### Accepted Product Leap

Следващата UI/UX вълна е **surface hierarchy**, не нова функционална маса.
Приемаме blueprint-а в тази форма:

- **Employee:** suggestion-first hero. Current Trip Hero остава първи, когато
  има approved/active курс; ако няма курс, Suggested Booking Hero става първи,
  а manual form/table/calendar слизат надолу като fallback/context.
- **Approver:** **Decision Desk** е board-first. Първият viewport показва
  pending decision cards с GSM, причина, автомобил, urgency и approve/reject;
  bulk flow-ът първо избира, после потвърждава approve/reject. Таблицата е
  secondary context, не landing surface.
- **Reception:** **Handoff Desk** е overdue-first. Просрочено връщане е първи
  сигнал, после approved handoffs с pickup/GPS context, после календар.
- **Admin:** **Control Tower** е pulse-first. Fleet Pulse, next operational
  focus и readiness warnings са над users/fleet/settings и преди всички
  конфигурационни панели.
- **Components:** приемаме HeroActionCard, DecisionCard, HandoffCard,
  PulseStrip, InsightList и NextBusyDayCard като product contracts, но без
  frontend framework и без build step.

Отлагаме големия frontend module split до след стабилен production pilot или
до първата UI промяна, която реално стане рискована в `static/app.js`. Той
остава vanilla JS modules, без React rewrite.

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
- surface names and layout hierarchy: **Моят курс / Нова заявка**,
  **Decision Desk**, **Handoff Desk**, **Control Tower**

### Success metric
- employee може да направи заявка без обучение
- admin може да одобрява и управлява флота без да “лови” действия из интерфейса
- UI change не влиза без screenshots, keyboard pass и contrast evidence
- first viewport не е table-first за нито една роля
- всяка роля има един доминиращ next move, без competing primary actions

### Current Progress

- Shipped: Employee Suggested Booking Hero за free mode без pending/approved/
  active работа. Hero-то използва `/reservations/suggest`, показва car/time/
  reason, дава един primary **Резервирай сега** и secondary **Промени**.
- Shipped: Approver Decision Desk board-first pass. Decision Rail вече е пред
  reservations модула, показва GSM/причина/urgency и прави bulk select без
  директно bulk approve.
- Shipped: Reception Handoff Desk / Admin Control Tower hierarchy pass.
  Reception Rail вече е отделен first-viewport блок с две ясни секции:
  просрочени връщания и текущи handoff-и; календарът идва след него, а
  reservations ledger е tertiary context. Production readiness панелът вече е
  в main admin rail след Fleet Pulse и next focus, преди decision/settings
  потока.
- Next: Admin Control Tower next-focus strip refinement, then vanilla JS module
  split.

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
- Browser-level evidence started: optional Playwright smoke now runs
  role-specific public, employee, employee-admin-deny, approver, admin, mobile
  and reception flows, plus responsive density, approver keyboard bulk-selection
  and destructive recovery checks
  with separate screenshots under `test-results/e2e`.
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
  factor. Full admins can now correct email/GSM from the user card and the
  change is recorded as `contact_updated` in user audit, avoiding a fresh bulk
  import for one bad phone number.
- Repeatable employee import: full admins can paste the source employee table
  into Admin UI; FleetFlow uses `Име + Фамилия + GSM`, updates existing
  `employee` accounts, creates missing ones and ignores chip/tachograph data.
- Authenticated requester contact: reservation lists/cards now surface the
  requester's GSM number after login for records the current role can already
  see, including an explicit `GSM: не е въведен` fallback for older users
  without a saved phone number. Public overview/calendar stay anonymous and
  never expose GSM.
- Employee admin guard: employee users are redirected away from `/admin`, and
  the employee top navigation exposes the Admin shortcut only to operational
  roles.
- Role-first login routing: `fleet_admin`, `fleet_approver` and
  `fleet_reception` redirect to `/admin` even when login starts from `/`, so
  the first authenticated screen matches the user's pool-process job.
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
- Approver Decision Desk: `/admin` now promotes pending decision cards above
  the reservation module, with GSM, reason, urgency, direct approve/reject and
  a safer bulk-select -> action-bar approve/reject path.
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
  trips, cars releasing within 1 hour, pending decisions, busiest car and
  fresh GPS telemetry availability for the active FleetFlow cars only (`X/Y`
  from the last 60 minutes), not raw NetFleet device event counts.
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
  purpose, GSM, GPS, reservation ids and lifecycle actions remain authenticated.
- NetFleet telemetry: server-side proxy reads latest GPS events by plate number
  from the admin-managed DB setting or `NETFLEET_API_KEY`; the key never
  reaches browser code and the UI never echoes the current secret. Admins see
  fleet-wide telemetry, reception sees scoped location for approved/checked-out
  handoff cars, and employees see pickup location only for their own
  approved/active trip. Employee notification polling now refreshes
  reservations and pickup GPS after approval/start/return/cancel lifecycle
  signals, with visible fallback copy when NetFleet is missing or unavailable.
  GPS UI now uses human pickup wording: `Последно видяна`, freshness labels and
  a reception confirmation prompt for stale/unknown signals.
- Production readiness: `/health/ready` checks database reachability for
  orchestration, while admin-only `/ops/readiness` and the `/admin` panel show
  live blockers/warnings without exposing secret values. Operator instructions
  now live in `docs/PRODUCTION_USER_GUIDE.md`. Runtime readiness now warns when
  there is only one active `fleet_admin`, keeping the two-admin continuity rule
  visible before full go-live.
- PostgreSQL image is pinned to major version 16 by default; do not use
  `latest` against a persistent production volume without a planned dump/restore
  major upgrade.
- Backup/restore posture: `make prod-backup` creates a custom-format PostgreSQL
  dump under ignored `backups/`, and `make prod-restore-drill BACKUP=...`
  restores it into an isolated Docker project before migrations. Successful
  restore drills now write ignored evidence to `.fleetflow/restore-drill-ok.json`.
- Final go-live gate: `make go-live-check APP_URL=...` requires production env
  readiness, fresh restore-drill evidence, local release gates and live
  health/readiness/active-admin/public overview smoke before real use.
- Structured production logs: access logs now switch to JSON in production and
  include request id, route, status and latency without secret values. The
  dedicated `fleetflow.access` logger writes one clean stdout JSON line per
  request in production.
- Status bar now reports free cars as active cars minus active trips, matching
  the cockpit wireframe's "available now" mental model.
- Latest local verification for this slice: `pytest -q` -> 147 passed,
  `pytest tests/test_ui_compliance.py -q` -> 32 passed, Playwright browser
  smoke -> 8 passed with public/browser-computed-contrast/employee/
  employee-admin-deny/approver/admin/mobile/reception coverage, JS syntax
  checks and Python compile check. UI date/time now
  renders as `dd.mm.yyyy, HH:MM` with 24-hour time. `make prod-check` fails fast when `.env` is missing in
  a clean checkout. Old `fleetflow_test` containers were removed, Docker stack
  was rebuilt with pinned `postgres:16`, `/health` and `/health/ready` on
  `8001` returned ok/ready and the app container is healthy. A real
  backup/restore drill succeeded from `/tmp/fleetflow-backups/...dump` into
  isolated project `fleetflow_restore_drill`; PostgreSQL smoke is migrated to
  Alembic revision `20260420_0009`.
- Latest go-live gate verification: `pytest tests/test_prod_readiness.py -q`
  -> 7 passed, `make qa-premium` -> 164 pytest cases + 14 browser checks,
  and `make smoke-live APP_URL=http://127.0.0.1:8001` returned
  health/ready/active-admin/public overview from the running PostgreSQL stack.
  The latest rebuilt Docker artifact was pushed to `dmedarov/fleetflow:latest`
  as digest `sha256:96ef7229f656b5993653aab20ad7db4ebc78d6cc6215e8d07c2cb060070a2853`.
- Latest calm-flow verification: Playwright captures responsive density
  evidence for public/employee/approver/reception/admin viewports and
  destructive-action recovery screenshots for reject required-reason, return
  confirmation, user deactivate, role change, admin handoff and blackout
  deactivate. Approver keyboard bulk-selection now has browser evidence:
  Space on a timeline checkbox selects the decision and reveals the bulk action
  bar; pure approver first viewport no longer depends on a table checkbox.
  The dialog system uses custom
  validation (`novalidate`) so errors are Bulgarian, focused and
  `aria-invalid` instead of browser-native validation bubbles. Role-by-role
  user flows are documented in `docs/ROLE_USER_FLOWS.md`; production readiness
  is summarized in `docs/PRODUCTION_READINESS_ASSESSMENT.md`.
- Calendar and reception/admin signal update: multi-day records now appear on
  every covered calendar date as start/continue/end, range records are sorted
  at the top of each day, and overdue returns are the first next signal for
  both reception and admin before lower-risk approval work. The calendar also
  uses container-width layout, so the day panel drops below the month grid when
  the calendar card itself is narrow even on a wider browser window, and empty
  selected days point to the next day with work instead of becoming a dead end.
- Static asset cache guard: templates now use versioned `/static/*.css/js`
  URLs and the app sends `Cache-Control: no-cache, must-revalidate` for HTML,
  CSS and JS, preventing stale `i18n.js` from showing raw translation keys
  after deploy. Literal `t("...")` keys are now checked against
  `static/i18n.js`, and runtime missing-translation fallback avoids exposing
  implementation keys to users.
- NetFleet production UX guard: Fleet Pulse now distinguishes missing API key
  from configured-but-unavailable live GPS, and shows text-backed
  `Няма връзка` instead of a symbol-only warning.
- Current tracked size: 14,513 production app/script/template/style lines,
  20,256 code lines including automated tests/e2e, and 26,389 tracked project
  lines including docs/config/workflows.

## Go-Live Plan

1. Freeze feature work; only production blockers, UX flow defects and security
   fixes land until first real use.
2. Set real domain/CORS, create at least two active `fleet_admin` users, one
   `fleet_approver` and one `fleet_reception` where the business process uses
   separated duties.
3. Run `make prod-check`, `make prod-backup`,
   `make prod-restore-drill BACKUP=<backup-file>`, `make prod` and
   `make go-live-check APP_URL=<production-url>`.
4. Execute one real rehearsal: employee request -> approver decision ->
   reception start -> reception return -> employee notification review.
5. Treat 99/100 production readiness as external-evidence gated: production URL
   rehearsal, fresh restore-drill marker, checked Dependabot alert, real CORS
   domain, at least two active admins and observed NetFleet connectivity.
6. After go-live, collect operator friction for one week before adding heavier
   Fleet Intelligence snapshots or new modules.

## No-Regression Doctrine

The next wave is not feature accumulation. It is keeping the existing pool
process precise under real use. Future agents should block both classes of
regression:

- **Silent regression:** schema drift, duplicate routes, stale docs, missing
  i18n, security header loss, role leakage, secret exposure, wrong readiness
  score, or NetFleet state that says "not configured" when the provider is down.
- **Noisy regression:** overlapping modules, too many visible actions, tables
  before decision rails, stale notifications dominating the screen, returned
  trips in current work, or status conveyed only by icon/color.

Preferred implementation order: add/adjust the narrow guardrail test first,
then change the code/UI, then update every affected `.md`, then run the
targeted test plus `make qa-premium` for UI/role/production changes.

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

- **Frontend size:** `static/app.js` is 4814 lines and `static/styles.css` is
  3485 lines. New UX work should stop growing the monolith and start extracting
  stable vanilla modules.
- **Reservation router size:** `routers/reservations.py` is 1004 lines and owns
  creation, conflict checks, suggestions, lifecycle, bulk decisions, listing
  and export. Split service logic after the next small hardening pass.
- **Schema duality:** `db.py` still supports runtime `CREATE TABLE IF NOT
  EXISTS` bootstrap and `_apply_runtime_upgrades()` while production also uses
  Alembic. The first automated guardrail now checks SQLite bootstrap execution,
  SQLite/PostgreSQL schema contracts, route uniqueness and the single Alembic
  head. Keep extending this when schema complexity grows.
- **Browser evidence:** Playwright coverage is now split into role-specific
  tests for public overview/calendar, employee booking/current trip, approver
  decisions, reception handoff/return, admin settings, browser-computed
  light/dark contrast, responsive density and destructive recovery, including
  deeper keyboard coverage for approver bulk selection, user deactivate, role
  change, admin handoff, blackout deactivate, reception calendar and
  admin/reception overdue return signal. Remaining evidence gap is manual
  screen-reader confirmation and
  configured/unconfigured NetFleet screenshots.
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
2. Run the real production rehearsal with final `.env`, backup/restore drill
   and `make go-live-check APP_URL=<production-url>`.
3. Keep the responsive density pass green and inspect the current screenshots
   for weak hierarchy before each production handoff.
4. Split `static/app.js` into small vanilla JS modules before the next large UI
   package. Suggested boundaries: API/session, shell/overview, reservations
   lifecycle, calendar, admin users/fleet/settings, notifications/dialogs.
5. Split reservation domain logic out of `routers/reservations.py` into service
   modules without changing endpoint contracts.
6. Add session-management UI and refresh-token cleanup job after the role flows
   are stable.
7. After real production usage, add materialized intelligence snapshots
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
