# Roadmap: FleetFlow

## Product North Star
Вътрешно приложение за pool car управление, позиционирано като **calm
operations assistant for internal mobility**, което е:

- спокойно и ясно като executive tool, не като ERP
- intent-driven: surface-ът сам показва следващия най-важен ход
- сигурно и предвидимо при role промени, деактивации и operational edge cases
- устойчиво за production промени чрез миграции, audit trail и контролируем lifecycle

## Design Principles

- Една основна задача на екран: employee вижда бърз booking и собствените курсове; admin вижда флот, чакащи решения и operational visibility.
- Един primary action на surface: всичко останало е secondary или contextual.
- Ясен status model: заявка, одобрение, активен курс, връщане и уведомяване без скрити състояния.
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
- admin вижда global queue и lifecycle transitions
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
  - admin получава start/return/cancel при employee actions
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
- Apple/NASA/USWDS compliance roadmap за следващите UI подобрения
- UI error prevention: reject dialogs now require a human reason and expose
  exact-field `aria-invalid` recovery instead of silent generic fallback reasons
- Cancel dialogs now require a human reason and send it to the reservation
  audit trail while keeping backward-compatible no-body API calls.
- Intent-driven summary layer: employee/admin surfaces now expose contextual
  next-action buttons for free mode, active/approved trips, pending admin work,
  active trips and calm fleet state.
- Current Trip Hero: employee active or next approved trip is promoted above
  the calendar/table with one primary action (`Старт` or `Върни`).
- Admin Decision Rail: `/admin` now promotes the top 3 pending decisions above
  the bulk bar/table, with direct approve/reject actions and a bulk approve
  path for the full pending queue.
- Fleet Pulse strip: `/admin` now shows a calm executive strip for active
  trips, cars releasing within 1 hour, pending decisions, busiest car and GPS
  telemetry availability.
- NetFleet telemetry: server-side proxy reads latest GPS events by plate number
  from `NETFLEET_API_KEY`; the key never reaches browser code. Admins see
  fleet-wide telemetry, while employees see pickup location only for their own
  approved/active trip.
- Status bar now reports free cars as active cars minus active trips, matching
  the cockpit wireframe's "available now" mental model.
- Latest local verification for this slice: `pytest -q` -> 94 passed, JS
  syntax checks, Python compile check, `git diff --check`, Docker rebuild and
  `/health` on `8001`; `fleetflow_test-car-pool-1` is healthy.

## Next Recommended Slices

1. One-tap booking: "резервирай най-подходящата свободна кола" върху вече наличните conflict/slot правила.
2. Smart prefill: последна кола, често време и типична продължителност.
3. Timeline-first reservation view; таблицата остава вторичен режим.
4. Browser-level Playwright screenshots/e2e за employee booking, admin approve/reject, bulk reject reason validation, intent actions, current trip hero, admin decision rail, fleet pulse, NetFleet telemetry empty/configured states, refresh/logout и mobile calendar.
5. Browser-computed contrast checks for translucent surfaces, focus rings and theme-aware message alerts.
6. Complete the Phase 8.5 error-prevention sweep for return, deactivate, role change, handoff and blackout deactivate.
7. PostgreSQL migration smoke + backup/restore playbook за production оператори.
8. Split на `static/app.js` в малки vanilla JS модули преди следващия голям UI пакет.

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
