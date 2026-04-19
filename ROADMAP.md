# Roadmap: FleetFlow

## Product North Star
Вътрешно приложение за pool car управление, което е:

- спокойно и ясно като executive tool, не като ERP
- сигурно и предвидимо при role промени, деактивации и operational edge cases
- устойчиво за production промени чрез миграции, audit trail и контролируем lifecycle

## Design Principles

- Една основна задача на екран: employee вижда бърз booking и собствените курсове; admin вижда флот, чакащи решения и operational visibility.
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
Да изглежда спокойно, точно и high-trust.

### Scope
- отделни admin и employee surfaces
- ясна visual hierarchy
- premium typography и по-малко, но по-силни action points
- timeline и calendar като primary planning tools
- notification banner за глобални operational messages
- празни състояния, които насочват към следващото действие

### Success metric
- employee може да направи заявка без обучение
- admin може да одобрява и управлява флота без да “лови” действия из интерфейса

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

## Next Recommended Slices

1. PostgreSQL migration smoke + backup/restore playbook за production оператори.
2. Structured JSON logs, request correlation и traceable incident debugging.
3. Browser-level Playwright e2e tests за employee booking, admin approve/reject, refresh/logout и mobile calendar.
4. Split на `static/app.js` в малки vanilla JS модули преди следващия голям UI пакет.
5. Fleet Gantt / week planning и utilization analytics.
6. Session-management UI: активни устройства, revoke current/all sessions и audit trail.
7. Scheduled reminder notifications преди start/end на резервация.
8. Maintenance workflows с attachment-и и service provider metadata.

## References

- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- Alembic Tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Apple Human Interface Guidelines: https://developer.apple.com/design/human-interface-guidelines/
- Apple Notifications HIG: https://developer.apple.com/design/human-interface-guidelines/notifications/
- GOV.UK Notification Banner: https://design-system.service.gov.uk/components/notification-banner/
- Material Design guidance: https://m3.material.io/
