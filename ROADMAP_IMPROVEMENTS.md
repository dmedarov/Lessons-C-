# FleetFlow Improvements Roadmap (AI Handoff)

> **Companion to `ROADMAP.md`.** That document describes the product north star
> and the phases already shipped. This document is a **tactical** plan for the
> next wave of improvements - written so another AI (or engineer) can pick up
> any single item and execute it cold, without access to the conversation that
> produced it.

---

## 0. How to use this document

Each work item follows the same template:

- **Goal** - the outcome, one sentence
- **Files** - exact paths to touch
- **Approach** - step-by-step implementation notes
- **Acceptance criteria** - the checklist that proves it's done
- **Verification** - how to test / what to run
- **Depends on** - other items that must land first
- **Effort** - S (< 1 day), M (1-3 days), L (> 3 days)

Work items are grouped into **phases**. Phases are sequenced by risk and
dependency, not by value alone - Phase 1 unblocks Phase 2, etc. Inside a phase,
items are mostly independent and can be parallelised.

**Before starting any item:**

1. Re-verify file paths and line numbers - the code evolves, the doc may not.
2. Run the existing test suite (`pytest`) to establish a green baseline.
3. Stick to the existing stack: FastAPI + raw SQL adapters, vanilla JS + HTML
   templates, no build step, no frontend framework. If an item seems to require
   new tooling, confirm first.

**Definition of done for every item:**

- Tests pass (`pytest` green).
- Manual smoke test of the affected flow on both SQLite (dev) and - where
  schema/data changes are involved - PostgreSQL via `docker-compose.postgres.yml`.
- If the item touches user-visible copy, strings are in Bulgarian and go
  through the i18n layer (see item 1.2).
- No new dependencies added without justification in the PR description.

---

## 1. Repository map (as of 2026-04-20)

```text
app.py                       FastAPI factory, router mounting, /, /admin, /health, /health/ready
config.py                    12-factor settings (APP_ENV, SECRET_KEY, DATABASE_URL, ...)
db.py                        SQLite + PostgreSQL adapters, schema bootstrap
app_settings.py              DB-backed runtime settings such as NetFleet API key
production_readiness.py      Shared prod checks for make prod-check and /ops/readiness
logging_config.py            Text/dev and JSON/prod access log formatter
security.py                  HMAC token sign/verify, PBKDF2 hash, auth deps
schemas.py                   Pydantic request/response models
notifications_service.py     In-app + SMTP/Slack/Teams dispatch
routers/
  auth.py                    setup-status, bootstrap-admin, login, refresh, logout, /auth/me
  cars.py                    fleet CRUD + telemetry proxy/config + blackout windows
  notifications.py           user inbox
  ops.py                     admin-only production readiness preflight
  reservations.py            960-line full lifecycle state machine and reservation query surface
  users.py                   user CRUD + password change + admin handoff
templates/
  index.html                 employee surface
  admin.html                 admin surface
static/
  app.js                     4048-line SPA logic; split before next large UI package
  i18n.js                    Bulgarian UI copy dictionary + interpolation
  styles.css                 3140-line design system stylesheet with responsive cockpit UI
alembic/                     migration scripts
tests/test_app.py            Core FastAPI TestClient regression cases
e2e/test_browser_smoke.py    Optional Playwright browser smoke + screenshots
scripts/prod_check.py        Live cutover .env readiness guard
scripts/backup_postgres.sh   PostgreSQL custom-format backup helper
scripts/restore_postgres_drill.sh Isolated restore drill helper
docs/PRODUCTION_USER_GUIDE.md Production user/operator guide
```

> ⚠️ The prior UI audit referenced `static/index.html`. The correct path is
> `templates/index.html` (FastAPI serves via Jinja). Similarly `static/admin.html`
> -> `templates/admin.html`. When this doc cites line numbers from the audit,
> re-open the file and grep for the referenced selector/string rather than
> trusting the line number.

---

## Current status snapshot (2026-04-20)

This document is now the tactical source of truth. Completed work stays in
`## Done` with commit references; active work remains in the phase sections.
If a phase below says **Status: shipped**, do not re-implement it unless the
task is explicitly a refactor or a bug fix against the shipped behavior.

### Shipped capabilities

- Dockerized FastAPI app with SQLite dev path and PostgreSQL-ready production
  path.
- Real auth/user management with DB re-binding for token roles and active
  status.
- Employee desk and dedicated `/admin` surface separated by role and UI intent.
- Reservation lifecycle: employee request/cancel, admin approve/reject, admin
  start active trip and admin return car.
- Service/maintenance blackout windows and conflict-aware reservation creation.
- Live booking conflict preview in the UI.
- In-app notifications, unread badge and polling refresh.
- Outbound notification hooks for email, Slack and Teams.
- Admin password reset, role change and per-user audit history.
- Dev-only deterministic seed accounts/cars and auth rate limiting.
- CI quality gates for Python compile, `pytest`, JS syntax, `pip-audit` and
  production Docker image build across Python 3.12/3.14.
- Request ID propagation and baseline browser security headers.
- Refresh-token rotation with HttpOnly cookie storage, replay-chain
  invalidation and explicit logout revocation.
- Admin reservation productivity: status/scope filters, search by plate/model/
  requester/purpose, date-window filtering and CSV export that follows the
  current filtered view.
- Calendar density affordance: visible `+N more` indicator when a day has more
  than three events.
- Admin bulk approve/reject UX: pending rows have checkbox selection, a
  selection action bar, one-request batch decisions and partial-failure
  summaries.
- Loading skeletons and submit-button busy states for the main data sections
  and forms.
- Mobile calendar day mode below 768 px with previous/next day controls and a
  "book this day" affordance.
- Intent-driven summary, one-tap booking, smart prefill, Current Trip Hero,
  Admin Decision Rail, timeline-first reservations and Fleet Pulse started as
  the premium "calm operations assistant" layer.
- UX hierarchy review started: employee requests/lifecycle now sit before the
  calendar, the new-request panel sits before inbox, and after login guidance
  cards are hidden to reduce first-viewport noise.
- Calm defaults started: employee reservations default to open/current work
  and hide returned/rejected/cancelled from the main flow; read notifications
  are removed from the visible inbox instead of accumulating.
- Role-specific pool process is now the target model: `fleet_approver` owns
  approve/reject only, `fleet_reception` owns start/return only, `fleet_admin`
  owns configuration and override, and employee stays request/cancel only.
- Reception Rail is shipped as the reception counterpart to Decision Rail:
  approved key handoffs and active-trip returns are promoted above the table
  for `fleet_reception`/`fleet_admin`, using the global operational snapshot
  rather than the currently filtered table rows.
- Reception calendar is now role-aware: `fleet_reception` sees approved
  handoffs plus checked-out returns from the operational snapshot, not only the
  table's current status filter.
- Fleet Intelligence Seed is shipped: quick-book and explicit best-car
  suggestions use explainable scoring, admin Fleet Pulse shows compact derived
  insights, and `car_assignments` records why a car was chosen.
- Pre-login status is now real: `/public/overview` exposes only aggregate
  counts so the first screen shows actual free cars, active trips and pending
  approvals without leaking detailed records.
- Pre-login calendar is now real: `/public/calendar` exposes calendar
  occupancy with status, registration number and model, while requester,
  purpose, GSM, GPS, reservation ids and actions remain authenticated.
- NetFleet latest GPS events are wired through an admin-only server-side proxy;
  employees can read pickup location only for their own approved/active trip.
  The key can be supplied by `.env` or saved once/changed from Admin UI as a
  DB-backed setting; it must never be committed or echoed back to the browser.
- Requester GSM is now visible in authenticated reservation surfaces for the
  records the current token may already see: Decision Rail, Reception Rail,
  lifecycle cards, table rows and authenticated calendar day timeline. Public
  overview/calendar stay anonymous and do not return requester GSM.
- Current automated coverage: growing `pytest` suite plus optional Playwright
  browser smoke (`e2e/`) that captures desktop/mobile screenshots, JS syntax
  checks, Python compile checks and Docker smoke used in shipped verification.

### Active product gaps

- Apple / NASA / USWDS UI compliance is defined below, but the codebase still
  needs a formal audit report, automated contrast checks and browser-level
  accessibility regression tests before claiming "compliant" in release notes.
- Browser-level end-to-end coverage is now role-specific for public, employee,
  approver, admin, mobile employee and reception flows. It still needs
  browser-computed contrast checks and more destructive-action recovery
  screenshots.
- Production observability now has structured request logs; next hardening is
  external alert delivery and an operator-facing log retention/export decision.
- Intelligence snapshots/materialized insights remain intentionally deferred
  until production usage shows inline metrics are too slow or operators need
  historical trend review.
- PostgreSQL migration smoke, backup and restore posture still need a clear
  operator workflow.
- The monolithic `static/app.js` should be split before the frontend grows much
  further; it is now 4048 lines and `static/styles.css` is 3140 lines.
- `routers/reservations.py` is now 960 lines and carries too many concerns:
  creation, conflict checks, lifecycle transitions, suggestions, bulk decisions,
  listing and export. Keep endpoints stable, but extract service modules before
  adding more reservation behavior.
- `db.py` intentionally still supports runtime bootstrap for SQLite/dev and
  PostgreSQL smoke, while production also uses Alembic. Add schema parity tests
  before the next database-heavy slice so bootstrap SQL, runtime upgrades and
  Alembic head cannot drift silently.
- The last visible GitHub security banner pointed at the Docker base image;
  FleetFlow now builds on a Chainguard Python runtime with local Docker Scout
  `0C/0H/0M/0L`, but GitHub Security must be rechecked after push to confirm
  the alert is closed.

## Codebase analysis handoff (2026-04-20)

This is the latest high-level audit of code shape, risk and future direction.
Use it before choosing the next implementation task.

| Area | Strength | Risk | Next AI-agent action |
| --- | --- | --- | --- |
| Product model | Role-separated pool process is clear: employee, approver, reception, admin. | Extra roles/features can make the app feel like ERP. | Preserve the four-role model; add permissions only when a real pool workflow requires them. |
| Backend API | FastAPI routers, auth rebinding, refresh rotation, readiness and audit trail are strong. | `routers/reservations.py` has too many responsibilities. | Extract reservation services in small slices without changing routes or schemas. |
| Frontend | Intent-driven cockpit, rails, timeline and NetFleet context are already premium. | `static/app.js` is too large for safe autonomous edits. | Create module boundaries before the next large UI addition. |
| CSS/design system | Responsive cockpit styling and compliance principles exist. | 3140-line stylesheet makes overlap/contrast regressions easy. | Add browser-computed contrast checks, then split component CSS if churn continues. |
| Database | Alembic production path and PostgreSQL smoke exist. | Runtime bootstrap/upgrades in `db.py` can drift from migrations. | Add schema parity tests for SQLite bootstrap, PostgreSQL bootstrap and Alembic head. |
| E2E evidence | Playwright smoke now runs separate public, employee, approver, admin, mobile and reception flows. | More contrast and destructive-action evidence is still needed. | Add browser-computed contrast checks and targeted recovery screenshots. |
| NetFleet | Server-side key handling and scoped employee pickup context are correct. | Raw GPS can confuse users if freshness/location text is unclear. | Add freshness labels and human pickup wording before adding maps/complex telemetry. |
| Production | Makefile, prod checks, Docker health, backups and restore drill are in place. | GitHub alert state still needs direct external confirmation. | Inspect GitHub Security/Dependabot after push and record exact closure evidence. |
| Intelligence | Best-car scoring and compact Fleet Pulse are explainable and light. | Premature analytics tables would add complexity before real usage data. | Defer snapshots until production data volume or operator needs prove the need. |
| Documentation | README, ROADMAP and this handoff are active. | Chat-only decisions disappear between agents. | Update `.md` files after tests and before every commit/push. |

### Code analysis conclusions

- Do **not** start with another feature module. Start with guardrails: route
  registry uniqueness, schema parity and role-specific e2e tests.
- Do **not** add generic AI chat, heavy BI dashboards, GPS tracking workflows,
  extra role sprawl or a settings labyrinth before live usage demands it.
- Continue optimizing for the product target: **calm operations assistant for
  internal mobility**. Every screen should answer: "What is my next move?"
- Verified during this audit: the current `POST /reservations/{reservation_id}/cancel`
  route is registered once in `routers/reservations.py`. Add a route-registry
  test anyway so future decorator collisions are caught automatically.

### Quality bar

FleetFlow should be treated like a premium operations cockpit: calm UI, strong
defaults, explicit confirmations, auditable admin actions and no hidden
authorization assumptions. Every new endpoint needs a happy-path test, an
authorization-negative test and a stale-role/inactive-user test where relevant.

### UI/UX compliance operating notes for future AI agents

Compliance here means **internal conformance target**, not a legal
certification. Every UI PR should cite which guardrails it improves and include
desktop + mobile screenshots. Use these official references as design
guardrails for future UI work:

- Apple HIG Layout (`https://developer.apple.com/design/human-interface-guidelines/layout`):
  group related items, align components for scanning, keep essential
  information near the top/leading area, respect safe areas and avoid layout
  overlap when viewport or text size changes.
- Apple HIG Buttons: every custom button needs an obvious press state, clear
  role/content, and at least a 44 x 44 pt hit region. Keep prominent actions
  rare and non-destructive.
- Apple HIG Accessibility + Typography: support keyboard-only operation,
  larger text, clear hierarchy, minimum AA contrast, non-thin type weights and
  layouts that avoid truncation/overlap when text grows.
- USWDS Accessibility: design for keyboard-only and touch-only operation, do
  not rely on hover or color alone, keep layouts readable/linear under zoom,
  and announce state changes where practical.
- NASA WDS Colors / Section 508 contrast: favor a calm blue/neutral
  operational palette, strong text contrast, and explicit labels/shapes
  alongside status color.
- W3C WCAG 2.2 + WAI-ARIA APG: use semantic landmarks and native controls
  first; custom dialogs, tabs, tables, toolbars and alerts must follow APG
  keyboard/focus patterns.
- NN/g heuristics: every screen must communicate system status, prevent costly
  mistakes, preserve user control/freedom, use domain language and keep visual
  design focused on the primary task.

For FleetFlow specifically: status must always have text, tables must collapse
into labeled cards on phones, chips/toggles must expose `aria-pressed`, dynamic
regions should use polite live updates, and every workflow should have a visible
next action.

### UI/UX evidence required in future PRs

- **Screenshots:** desktop 1440 px, tablet 768 px and phone 390 px for every
  visible change.
- **Keyboard proof:** tab-order pass through login, booking, admin queue,
  dialogs, calendar and mobile bottom navigation.
- **Contrast proof:** all design-token foreground/background pairs meet WCAG
  AA (4.5:1 for normal text, 3:1 for large text/icons); failures documented
  with remediation before merge.
- **Zoom/text proof:** 200% browser zoom and enlarged text do not create
  overlap, clipped labels or unreachable controls.
- **Screen reader semantics:** landmarks, headings, dialog names, table/card
  labels, `aria-live` regions and status text are verified manually or via
  Playwright accessibility snapshots.
- **Motion proof:** no essential information depends on animation; reduced
  motion remains respected.

---

## Phase 1 - Quick wins (shipped baseline)

Low-risk, small-surface improvements that noticeably raise the baseline.

**Status:** Shipped across `8f8648a`, `8834312`, `b9dd216`, `a91ab3e` and
related follow-up commits. Items remain here as historical handoff detail.

### 1.1 Visible focus indicators + keyboard navigation

- **Goal:** Every interactive element has a clear `:focus-visible` outline, and
  Tab order flows logically through the page.
- **Files:** `static/styles.css`
- **Approach:**
  1. Add a global rule: `*:focus-visible { outline: 2px solid var(--accent);
     outline-offset: 2px; border-radius: inherit; }`. Adjust `--accent` to an
     existing design token (search `styles.css` for primary brand color).
  2. Audit the three interactive surfaces - calendar day cells, status-filter
     chips, pagination (`‹` / `›`) - each must be a `<button>` not a `<div>`,
     and must receive focus. Fix any that aren't.
  3. Verify Tab order in `templates/index.html` and `templates/admin.html` by
     tabbing from the top: topbar -> filters -> form fields -> table actions.
     Add `tabindex="0"` only where semantic HTML can't carry focus; never use
     positive `tabindex`.
- **Acceptance criteria:**
  - Every button, link, input, and select shows a visible focus ring.
  - Calendar days are tabbable and focus-visible.
  - No regression in mouse-click styling.
- **Verification:** Manual keyboard-only navigation through a full booking
  flow on both surfaces. Run Lighthouse accessibility audit - score >= 95.
- **Depends on:** -
- **Effort:** S

### 1.2 Extract all UI strings into an i18n module

- **Goal:** A single source of truth for all user-visible strings, so future
  locale additions are mechanical and mixed-language bugs are impossible.
- **Files:** `static/app.js`, `templates/index.html`, `templates/admin.html`,
  new `static/i18n.js`
- **Approach:**
  1. Create `static/i18n.js` exporting an object `const bg = { ... }` keyed by
     stable IDs: `status.pending`, `status.approved`, `status.active`,
     `status.returned`, `action.approve`, `action.reject`, `action.cancel`,
     `calendar.legend.pending`, `calendar.records.singular`,
     `calendar.records.plural`, `form.submit.loading`, etc.
  2. Add a tiny helper: `function t(key, vars) { ... }` with `{count}` style
     interpolation and a pluralization helper that respects Bulgarian rules
     (singular for 1, plural otherwise - adequate until a second locale
     arrives, then revisit).
  3. Find every English string currently in `static/app.js` and both templates.
     Known offenders from the audit:
     - `"Pending"`, `"Approved"`, `"Active trip"`, `"Returned"` in status pills
     - `<option value="employee">employee</option>` and `fleet_admin` in role selects
     - `${items.length} record${items.length > 1 ? "s" : ""}` pluralization
     - Button labels `"Bootstrap admin"`, `"Admin handoff"`
     - "operational" sprinkled across `templates/index.html`
  4. Replace each with `t("...")`. In templates, inject the i18n object into the
     Jinja render context or expose via a `<script>window.__i18n = {...}</script>`
     block and read from JS.
- **Acceptance criteria:**
  - `grep -niE 'pending|approved|returned|record[s]?|bootstrap' templates/ static/app.js`
    returns zero user-visible English strings (technical identifiers like
    `status === "pending"` in code stay).
  - Changing a value in `static/i18n.js` and reloading updates the UI.
- **Verification:** Visual inspection of both surfaces + `pytest`.
- **Depends on:** -
- **Effort:** M

### 1.3 Confirm dialogs for destructive actions

- **Goal:** No one-click irreversible actions.
- **Files:** `static/app.js`, `static/styles.css`
- **Approach:**
  1. Add a small `confirmAction(message, confirmLabel)` helper returning a
     Promise. Implement as a modal `<dialog>` element (native, with
     `dialog::backdrop` styling) - fall back to `window.confirm` only if
     `<dialog>` support is missing (all current targets support it).
  2. Wrap these actions in `static/app.js`:
     - Return trip (`POST /reservations/{id}/return`)
     - Cancel reservation (`POST /reservations/{id}/cancel`)
     - Reject reservation (`POST /reservations/{id}/reject`)
     - Deactivate user, deactivate car
     - Admin handoff submit
  3. All dialog strings flow through `t()`.
- **Acceptance criteria:**
  - Each listed action opens a confirmation before firing the API call.
  - ESC cancels; Enter confirms when the confirm button is focused.
  - Screen readers announce the dialog (use `<dialog>` + `aria-labelledby`).
- **Verification:** Manual keyboard test for each action.
- **Depends on:** 1.2 (for strings)
- **Effort:** S

### 1.4 Rate limit `/auth/login` and `/auth/bootstrap-admin`

- **Goal:** Brute-force protection on credential endpoints.
- **Files:** `requirements.txt`, `app.py`, `routers/auth.py`, `config.py`
- **Approach:**
  1. Add `slowapi` to `requirements.txt`.
  2. In `app.py`, instantiate a `Limiter(key_func=get_remote_address)` and
     register the exception handler. Store on `app.state.limiter`.
  3. Decorate `POST /auth/login` with `@limiter.limit("5/minute; 20/hour")`
     and `POST /auth/bootstrap-admin` with `@limiter.limit("3/hour")`.
  4. Surface limits via `config.py` env vars (`LOGIN_RATE_LIMIT`,
     `BOOTSTRAP_RATE_LIMIT`) so ops can tune per environment.
  5. On 429, response body should carry a Bulgarian error via the existing
     error-envelope shape so the UI can render it cleanly.
- **Acceptance criteria:**
  - 6th login attempt within a minute returns HTTP 429.
  - Rate limit counters reset correctly.
  - Tests cover the 429 path.
- **Verification:** Add `tests/test_rate_limit.py` with `TestClient` spamming
  login attempts. Ensure the test uses a fresh `Limiter` per test to avoid
  cross-test contamination.
- **Depends on:** -
- **Effort:** S

### 1.5 CORS configuration

- **Goal:** Explicit, correct CORS so embedding the API in future clients
  (e.g. a mobile app) doesn't silently fail.
- **Files:** `app.py`, `config.py`, `.env.example`
- **Approach:**
  1. Read `CORS_ALLOW_ORIGINS` from env as a comma-separated list, default
     `""` (no origins allowed) in production, `"*"` in `APP_ENV=dev`.
  2. Add `CORSMiddleware` with `allow_credentials=True`, appropriate methods
     and headers. Never pair `allow_origins=["*"]` with `allow_credentials=True`.
  3. Document the variable in `.env.example`.
- **Acceptance criteria:**
  - Preflight `OPTIONS` requests from an allowed origin return correct headers.
  - Disallowed origins receive no `Access-Control-Allow-Origin` header.
- **Verification:** `curl -i -H 'Origin: http://localhost:3000' -X OPTIONS ...`
- **Depends on:** -
- **Effort:** S

---

## Phase 2 - UX high-impact (partially shipped)

Deeper UX work; pays off every day the product is used.

**Status:** Items 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9 and
2.10-2.12 are shipped. Future Phase 2 work should be bug fixes or UX
extensions on top of the shipped baseline, not reimplementation.

### 2.1 Mobile calendar - collapse to list/day view below 768 px ✅ shipped 2026-04-19

- **Goal:** Make the calendar usable on phones (currently the 7-col grid with
  118 px min-height per day breaks below 768 px).
- **Files:** `templates/index.html`, `static/app.js`, `static/styles.css`
- **Approach:**
  1. Add a `@media (max-width: 767px)` block in `styles.css` that switches
     `.calendar-grid` to `display: block`. Hide the month grid; show a
     single-day card with `‹ ›` controls to step through days.
  2. In `app.js` `renderCalendar()`, branch on
     `window.matchMedia("(max-width: 767px)")`. Emit a list layout for mobile
     instead of the 42-cell grid.
  3. Listen on the `matchMedia` `change` event to re-render on orientation flip.
  4. Preserve the "click day -> prefill form" affordance via a sticky
     `Book this day` button in the mobile day card.
- **Acceptance criteria:**
  - At 375 x 667 (iPhone SE) the calendar fits without horizontal scroll.
  - Navigation between days preserves the current month state in `state`.
  - Desktop experience is unchanged.
- **Verification:** Chrome DevTools device emulation on 3 screen sizes
  (375, 768, 1280). Test actual iOS Safari if accessible.
- **Depends on:** -
- **Effort:** M

### 2.2 Loading skeletons + submit-button states ✅ shipped 2026-04-19

- **Goal:** Replace silent fetches with obvious loading states; never leave a
  submit button "stuck".
- **Files:** `static/app.js`, `static/styles.css`
- **Approach:**
  1. In `styles.css` add a `.skeleton` class with a subtle shimmer animation
     (`background: linear-gradient(...); animation: shimmer 1.5s infinite;`).
  2. In `app.js`, every `load*()` function should set a loading flag in
     `state.loading[section] = true`, trigger re-render, fire the fetch,
     then clear on completion. `render*()` functions branch on the flag to
     emit skeleton placeholders (3-5 rows).
  3. Wrap every form's submit handler: disable the button + swap its label to
     `t("form.submit.loading")` on dispatch; re-enable on `finally` (not just
     success - current code leaves the button disabled on error in some paths).
- **Acceptance criteria:**
  - A throttled-to-Slow-3G reload shows skeletons, not empty sections.
  - A failed submit re-enables the button and restores the original label.
- **Verification:** Throttle Chrome to Slow 3G; reload both surfaces; submit
  a form while the API is paused (e.g. breakpoint in the handler).
- **Depends on:** 1.2
- **Effort:** M

### 2.3 Live conflict preview in the booking form

- **Goal:** User sees overlapping reservations and blackout windows as they
  pick start/end times, before they submit.
- **Files:** `templates/index.html`, `static/app.js`, `routers/reservations.py`
- **Approach:**
  1. Backend: add `GET /reservations/conflicts?car_id=...&start=...&end=...` that
     returns existing reservations + blackouts that overlap the supplied
     window. Reuse the overlap logic currently inlined in
     `routers/reservations.py`. Require the same auth as listing.
  2. Frontend: debounce (250 ms) on change of `car_id`, `start`, `end` and
     call the endpoint. Render matches beneath the form with
     `t("conflict.reservation", {start, end, plate})` etc.
  3. Also highlight the conflicting days in the calendar with a distinct
     border color (not a fill, to keep the existing pills readable).
- **Acceptance criteria:**
  - Picking a known-booked window shows an inline warning within 400 ms.
  - Submitting anyway still surfaces the server-side rejection - defence in depth.
- **Verification:** Test with two overlapping reservations and one blackout.
- **Depends on:** 1.2
- **Effort:** M

### 2.4 Bulk approve/reject in the admin pending queue ✅ shipped 2026-04-19

- **Goal:** Admins can clear a pending queue in one click per batch, not one
  per reservation.
- **Files:** `templates/admin.html`, `static/app.js`, `routers/reservations.py`,
  `schemas.py`
- **Approach:**
  1. Backend: add `POST /reservations/bulk-approve` and
     `POST /reservations/bulk-reject` accepting `{ ids: [int], reason?: str }`.
     Wrap in a single transaction; return per-id success/failure so partial
     failures are visible (e.g. one conflict among many). Admin-only.
  2. Frontend: checkbox column in the pending table; a floating action bar
     appears when >=1 row selected, with `Approve selected (n)` and
     `Reject selected (n)` buttons. Confirm via the 1.3 dialog. Show a
     toast summarising successes and failures.
  3. Add tests covering: all-succeed, some-fail-due-to-conflict, all-fail.
- **Acceptance criteria:**
  - Selecting 5 pending and clicking Approve issues one request, not 5.
  - A partial failure reports the offending IDs.
- **Verification:** `pytest tests/test_reservations_bulk.py` + manual smoke.
- **Depends on:** 1.3
- **Effort:** M

### 2.5 Default filter + notification badge

- **Goal:** Admins land on `Pending`, not `All`; employees see an unread
  notification count in the topbar.
- **Files:** `static/app.js`, `templates/index.html`, `templates/admin.html`,
  `static/styles.css`
- **Approach:**
  1. Change admin initial `state.statusFilter` to `"pending"`.
  2. Add a badge element next to the notification icon in the topbar; update
     it from `loadNotifications()` output (already returns unread count).
  3. Animate the badge on increment (subtle, not attention-seeking).
- **Acceptance criteria:**
  - Fresh admin login opens Pending tab.
  - Badge reflects real count; decrements on mark-read.
- **Depends on:** -
- **Effort:** S

### 2.6 Auto-refresh notifications (SSE or polling)

- **Goal:** Users see approvals/rejections without manually refreshing.
- **Files:** `app.py`, `routers/notifications.py`, `static/app.js`
- **Approach:** Start with **polling** (simpler): in `app.js`, after
  successful login kick off `setInterval(() => loadNotifications(), 30000)`.
  Store the interval ID on `state` so logout can clear it. If polling load
  proves too high in production, migrate to SSE via a dedicated
  `GET /notifications/stream` endpoint (keep-alive, `text/event-stream`,
  per-user channel). Do not jump to SSE first.
- **Acceptance criteria:**
  - Approved request appears in requester's inbox within ~30 s without refresh.
  - Interval is cleared on logout (no zombie fetches).
- **Verification:** Two browsers (admin + employee); approve in one, watch
  the other.
- **Depends on:** 2.5
- **Effort:** S (polling) / M (SSE)

### 2.7 Missing affordances

**Status:** Shipped in `9d61cdd` for date-range filters, search, CSV export
following current filters, `+N more` calendar overflow and preserving booking
start/end after submit.

Bundle these small items into a single PR to share review overhead:

- **Date-range filter** on reservations table (two `<input type="date">` with
  clear-all).
- **"+N more" indicator** on calendar days with more than 3 pills (currently
  `.slice(0, 3)` silently drops them).
- **Don't reset the form after successful booking** - keep start/end so
  the user can change only the purpose and rebook a repeat trip.
- **Search box** over `plate` / `purpose` / `employee name`.

- **Files:** `static/app.js`, `static/styles.css`, templates as needed
- **Effort:** M

### 2.8 Global accessibility and lifecycle polish

**Status:** Shipped on 2026-04-19 in the global UI/UX polish iteration.

- **Goal:** Make core controls and lifecycle state readable without relying on
  color alone, while keeping premium cockpit density.
- **Files:** `templates/index.html`, `templates/admin.html`, `static/app.js`,
  `static/styles.css`, `tests/test_app.py`
- **Approach:**
  1. Add `aria-label` to top-level navigation and `role="group"` to filter
     toolbars.
  2. Keep `aria-pressed` synchronized for chip-style filters in `wireToolbar`.
  3. Add a text-labeled lifecycle meter for reservation rows and day timeline
     cards: pending -> approved -> checked_out -> returned, with explicit
     terminal states for rejected/cancelled.
  4. Ensure custom buttons/chips/segmented controls meet the Apple 44 px hit
     target guidance and expose press/active states.
  5. Keep reservations table updates polite (`aria-live="polite"`) so assistive
     tech users understand filtered state changes.
- **Acceptance criteria:**
  - Filter chips expose correct `aria-pressed` on initial render and after
    interaction.
  - Lifecycle state includes text labels, not only colored pills.
  - All custom clickable controls used in the global shell are at least 44 px
    tall.
- **Verification:** `pytest`, `node --check static/app.js`, template smoke for
  `/` and `/admin`, manual keyboard Tab pass.
- **Depends on:** 1.1, 1.2
- **Effort:** S

### 2.10 Blackout прозорец — редактиране ✅ shipped `16443ad`

- **Goal:** Fleet admin може да смени датите или вида на blackout прозорец, без да
  го изтрива и пресъздава.
- **Files:** `routers/cars.py`, `schemas.py`, `templates/admin.html`, `static/app.js`,
  `static/i18n.js`, `tests/test_app.py`
- **Approach:**
  1. Add `BlackoutUpdatePayload(BaseModel)` в `schemas.py`:
     `start_time: str`, `end_time: str`, `kind: str`, `reason: Optional[str]`.
  2. Add `PUT /admin/cars/{car_id}/blackouts/{blackout_id}` (admin-only); validates
     that `start_time < end_time`; reuses the same overlap check as create.
  3. In `admin.html` blackout accordion: add an edit button per row that pre-fills a
     dialog with current values (reuse the existing `userDialog` pattern).
  4. New `handleBlackoutEdit(id, carId)` в `app.js` opens the dialog; on confirm
     calls `PUT` and refreshes the blackout list.
  5. New i18n keys: `action.editBlackout`, `admin.editBlackoutTitle`.
  6. Tests: happy path, overlap rejection, employee forbidden, invalid window.
- **Acceptance criteria:**
  - Admin can change both dates and kind without deleting the record.
  - If the new window overlaps an approved reservation, the edit is rejected (409).
  - Change is visible immediately after save without a page reload.
- **Verification:** `pytest` new cases + manual admin blackout smoke.
- **Depends on:** —
- **Effort:** S

### 2.11 Бележки за автомобил (car notes) ✅ shipped `16443ad`

- **Goal:** Fleet admin може да записва оперативни бележки на автомобил ("смяна
  на гума", "предстои технически преглед") — бележката е видима за служителите при
  избор на кола.
- **Files:** `alembic/versions/` (new), `db.py`, `schemas.py`, `routers/cars.py`,
  `templates/admin.html`, `templates/index.html`, `static/app.js`, `static/i18n.js`
- **Approach:**
  1. Alembic migration: `ALTER TABLE cars ADD COLUMN notes TEXT`.
  2. `_ensure_column(conn, "cars", "notes", "TEXT")` в `db.py`.
  3. `CarResponse.notes: Optional[str]` в `schemas.py`.
  4. Extend `PUT /admin/cars/{id}` to accept `notes` in the payload.
  5. In admin car accordion: add a textarea for notes; save on blur or explicit Save.
  6. In employee car picker (booking form): show a muted italic note below the plate
     if `car.notes` is non-empty. Use `entity.carNote` i18n key.
- **Acceptance criteria:**
  - Admin saves a note; employee sees it when selecting that car.
  - Empty note renders nothing in the employee view (no blank space).
- **Verification:** Manual admin→employee smoke + `pytest` schema test.
- **Depends on:** —
- **Effort:** S

### 2.12 Бутон „Тест известие" ✅ shipped `16443ad`

- **Goal:** Admin може да провери дали каналите за известия (in-app / SMTP / Slack)
  работят, без да прави реална резервация.
- **Files:** `routers/notifications.py`, `notifications_service.py`,
  `templates/admin.html`, `static/app.js`, `static/i18n.js`
- **Approach:**
  1. Add `POST /admin/notifications/test` (admin-only); dispatches a test
     notification to the calling user via all configured channels.
  2. Returns `{ channels: [{ name, status, error? }] }` so the UI can show
     per-channel results.
  3. In admin Notifications section: "Изпрати тест" button; on response renders a
     small result list — green tick for success, red X + error text for failure.
  4. New i18n keys: `action.testNotification`, `notification.testTitle`,
     `notification.testSuccess`, `notification.testFail`.
- **Acceptance criteria:**
  - With valid SMTP config, admin receives a test email within 30 s.
  - With invalid config, the UI shows the error without crashing.
- **Verification:** Manual with live SMTP + intentionally wrong host.
- **Depends on:** Phase 3.2 async dispatch (already shipped).
- **Effort:** S

### 2.9 Mobile quick navigation

**Status:** Shipped on 2026-04-19 after 2.8.

- **Goal:** Restore fast navigation on phones after `.topbar__nav` collapses,
  without crowding the header.
- **Files:** `templates/index.html`, `templates/admin.html`, `static/styles.css`
- **Approach:** Add a mobile-only bottom navigation/command rail with 3-4
  high-frequency destinations per surface. Keep links text-labeled, 44 px
  minimum, and visible only below the tablet breakpoint.
- **Acceptance criteria:** At 375 px width, users can jump to calendar,
  reservations, fleet and inbox/admin sections without scrolling from the top.
- **Verification:** Browser mobile viewport smoke at 375, 430 and 768 px.
- **Depends on:** 2.8
- **Effort:** S

---

## Phase 3 - Security & hardening (1 week)

Must land before any external-facing deployment.

### 3.1 Refresh token flow

**Status:** Shipped on 2026-04-19. Keep this section as implementation
history and a regression checklist for future auth changes.

- **Goal:** Users aren't forcibly logged out every hour.
- **Files:** `security.py`, `routers/auth.py`, `db.py`, `schemas.py`,
  `static/app.js`, new Alembic migration
- **Approach:**
  1. Add a `refresh_tokens` table: `id`, `user_id`, `token_hash`, `issued_at`,
     `expires_at`, `revoked_at`, `user_agent`, `ip`. Hash the token with the
     same PBKDF2 helper or a simple `sha256` (refresh tokens are long random
     strings, slow hashing is overkill; `sha256` is fine here).
  2. On login: issue both access (1 h) and refresh (14 d, configurable) tokens.
     Return refresh in an `HttpOnly; Secure; SameSite=Strict` cookie, not in
     the body.
  3. Add `POST /auth/refresh`: validates the cookie, rotates the refresh
     token (old one revoked, new one issued - rotation prevents replay),
     returns a new access token.
  4. Add `POST /auth/logout` that revokes the current refresh token and
     clears the cookie.
  5. Frontend: on 401 from any call, try `/auth/refresh` once; if that also
     fails, redirect to login.
  6. Emit the Alembic revision.
- **Acceptance criteria:**
  - Access token expires in 1 h; UI silently recovers via refresh.
  - Refresh rotation works: using an old refresh fails and revokes the chain
    (standard refresh-rotation replay protection).
  - Logout invalidates both tokens.
- **Verification:** `tests/test_auth_refresh.py` covering happy path + replay
  + logout.
- **Depends on:** -
- **Effort:** M

### 3.2 Async notification dispatch

- **Goal:** SMTP / Slack / Teams timeouts don't block API responses.
- **Files:** `notifications_service.py`, `routers/reservations.py`,
  `routers/users.py`, `app.py`
- **Approach:**
  1. Short-term: switch outbound dispatch to FastAPI `BackgroundTasks`. The
     in-app notification write stays in the request transaction (keeps the
     inbox consistent); only the external fan-out moves to background.
  2. Wrap each outbound channel in a timeout (5 s) and a try/except that
     records failure to the existing `notification_deliveries` table.
  3. Long-term (optional, document as a follow-up): extract to a proper queue
     (RQ / Celery / arq). Don't do this until load justifies it.
- **Acceptance criteria:**
  - With SMTP intentionally pointed at a sinkhole, a successful approval
    still returns in < 500 ms.
  - Failure is visible in `notification_deliveries`.
- **Verification:** Manual with a blackhole SMTP host + existing pytest suite.
- **Depends on:** -
- **Effort:** S

### 3.3 Harden admin bootstrap

- **Goal:** Close the window where anyone can create the first admin if the
  API is exposed before the real admin signs up.
- **Files:** `config.py`, `routers/auth.py`, `app.py`
- **Approach:**
  1. At startup, if no admin exists **and** `APP_ENV != "dev"`, generate a
     one-shot `BOOTSTRAP_TOKEN` (32-byte URL-safe random) and log it to stdout
     exactly once. Store its hash in memory (or a small `bootstrap_token`
     table) with a 30-minute TTL.
  2. `POST /auth/bootstrap-admin` now requires the header
     `X-Bootstrap-Token: ...`. Invalid / expired token -> 403.
  3. Successfully creating the first admin immediately voids the token.
  4. In dev, keep the current behaviour (no token required) for ergonomics -
     but log a warning.
- **Acceptance criteria:**
  - Without the token, bootstrap fails in production.
  - Token can be used once and once only.
  - Ops runbook (README addendum) documents where to find the token.
- **Depends on:** -
- **Effort:** S

### 3.4 At-least-one-active-admin invariant

- **Goal:** System can never end up with zero active admins.
- **Files:** `db.py`, `routers/users.py`, new Alembic migration
- **Approach:**
  1. DB-level check: a partial unique index or a trigger. On SQLite use a
     trigger; on PostgreSQL prefer a deferrable constraint via a `CHECK` on a
     materialised count column, or a trigger. Start with application-level
     validation if DB-level is too invasive.
  2. Application-level: in `users.py`, any `deactivate`, `delete`, or
     role-change action on an admin must first count `SELECT COUNT(*) FROM
     users WHERE role='fleet_admin' AND is_active=1` and refuse if the result
     would drop to 0.
  3. Also enforce in `routers/users.py` handoff: can't demote yourself if
     you're the last admin (existing handoff flow may already cover this -
     re-check).
  4. Add a CLI recovery path (`python -m app recover-admin --email ...`) as
     a break-glass.
- **Acceptance criteria:**
  - Attempting to deactivate the last admin returns a 400 with a clear
    Bulgarian message.
  - CLI path works end-to-end.
- **Verification:** New `tests/test_admin_invariant.py`.
- **Depends on:** -
- **Effort:** M

### 3.5 Audit the signed-token format

- **Goal:** Confirm the custom HMAC token in `security.py` is resistant to
  length-extension, timing attacks, and replay.
- **Files:** `security.py`, `tests/test_security.py` (new)
- **Approach:**
  1. Review: the payload is `base64(json).hmac`. Confirm `hmac.compare_digest`
     is used for comparison (timing-safe).
  2. Ensure the signing key is at least 32 bytes; reject shorter keys at
     startup in production.
  3. Add `iat` / `exp` / `jti` claims if absent; persist a small
     `revoked_tokens` set for forced logout.
  4. Write targeted tests: tampered payload rejected, expired token rejected,
     timing-safe comparison.
- **Acceptance criteria:** All four new tests pass.
- **Depends on:** 3.1 (revoke list plays with refresh flow)
- **Effort:** S

### 3.6 Session-management UI

- **Goal:** Admins and users can inspect and revoke active refresh sessions
  without database access.
- **Files:** `routers/auth.py`, `routers/users.py`, `schemas.py`,
  `static/app.js`, `static/i18n.js`, `static/styles.css`,
  `templates/admin.html`, `tests/test_auth_refresh.py`
- **Approach:**
  1. Add a read endpoint for the current user's active refresh sessions:
     session id, issued_at, expires_at, user_agent, ip and current-session
     marker. Never return token hashes.
  2. Add `POST /auth/sessions/{id}/revoke` for the current user and an
     admin-only `POST /users/{id}/sessions/revoke-all` for support incidents.
  3. Add a compact "Активни сесии" panel in account/admin surfaces with
     revoke-current/revoke-all controls and confirmation dialogs.
  4. Record revocations in `user_audit_log` or a dedicated auth audit table
     if the event needs stronger traceability.
- **Acceptance criteria:**
  - User can revoke another browser/device session without logging out of the
    current browser.
  - Admin can revoke all sessions for a deactivated/compromised user.
  - No API response exposes raw refresh tokens or token hashes.
- **Verification:** Tests for self list, self revoke, admin revoke-all,
  employee forbidden on other user and stale cookie rejection after revoke.
- **Depends on:** 3.1
- **Effort:** M

---

## Phase 4 - Frontend code quality (1-2 weeks)

Paying down debt to keep Phase 5+ velocity high. No user-visible change.

### 4.1 Split `static/app.js` into ES modules

- **Goal:** Break the 1,400-line monolith into focused modules.
- **Files:** `static/app.js` -> `static/js/{api,state,i18n,calendar,forms,render,main}.js`
- **Approach:**
  1. Templates load `<script type="module" src="/static/js/main.js">`.
  2. Target modules:
     - `api.js`: `apiFetch`, endpoint wrappers.
     - `state.js`: the global `state` object + setters/subscribers.
     - `i18n.js`: from item 1.2.
     - `calendar.js`: `startOfMonth`, `addMonths`, `dateKey`, `renderCalendar`.
     - `forms.js`: submit handlers, validation.
     - `render.js`: `renderShell`, `renderCars`, `renderReservations`,
       `renderNotifications`, `renderBlackouts`.
     - `main.js`: wires everything together on `DOMContentLoaded`.
  3. No bundler - native ES modules. Works on all current evergreen targets.
- **Acceptance criteria:**
  - No new module > 300 lines; the temporary shell can remain larger during
    migration only if every extraction commit shrinks it.
  - All existing user flows work.
  - Lighthouse performance score doesn't regress.
- **Verification:** Full manual smoke + pytest (API unaffected).
- **Depends on:** 1.2 (clean extraction of strings first)
- **Effort:** M

### 4.2 Centralise fetch error handling

- **Goal:** One place decides how to handle 401 / 422 / 5xx.
- **Files:** `static/js/api.js` (from 4.1)
- **Approach:**
  1. `apiFetch` already exists - extend it:
     - 401 -> clear session state and redirect to login (unless the call was
       `/auth/refresh` itself; then bubble up).
     - 422 -> parse the FastAPI validation envelope and return a structured
       `FieldErrors` object callers can map onto form fields.
     - 5xx -> toast with a generic message; log to console.
     - Network error -> toast + offer retry.
  2. All call sites stop doing their own try/catch for these cases.
- **Acceptance criteria:** Forms correctly highlight field errors from 422;
  a server 500 doesn't leave a submit button disabled forever.
- **Depends on:** 4.1
- **Effort:** S

### 4.3 Deduplicate form validation

- **Files:** `static/js/forms.js`
- **Approach:** Extract the common pattern from `validateLoginForm`,
  `validateBootstrapForm`, `validateReservationForm` into a single
  `validate(form, rules)` helper taking a rules object keyed by field name
  (`required`, `email`, `minLength`, custom `fn`).
- **Effort:** S

### 4.4 Unified date utilities

- **Files:** `static/js/date.js` (new)
- **Approach:** Collect `startOfMonth`, `addMonths`, `dateKey`,
  `localDateFromKey`, `localInputValue`, `nextLocalSlot` into one module.
  Document the timezone assumption (treat all times as local user TZ; server
  receives ISO strings). Add unit tests via a tiny QUnit / plain `assert`
  harness or - pragmatic - a handful of pytest-driven tests that load the
  module in a JS runtime. Start with manual verification and defer testing
  to item 5.5 (Playwright).
- **Depends on:** 4.1
- **Effort:** S

### 4.5 Cache frequently-accessed DOM nodes

- **Files:** `static/js/render.js`
- **Approach:** On `DOMContentLoaded`, populate a `const els = { ... }` map
  with the 20-30 most-queried nodes. Replace repeated `getElementById` calls
  (~92 instances) with `els.thing`.
- **Effort:** S

---

## Phase 5 - Nice-to-haves (open-ended)

Order is by estimated value; pick based on user demand.

### 5.0 Fleet Gantt изглед

- **Goal:** Admin вижда наситеността на флота за седмица: един ред = една кола,
  X-ос = дни, цветови блокове = резервации/blackout-и.
- **Files:** `templates/admin.html`, `static/app.js`, `static/styles.css`,
  `static/i18n.js`
- **Approach:**
  1. New tab „Gantt" в admin dashboard (button in `.topbar__nav` beside
     „Резервации"). Tab shows/hides via `data-view` pattern already used.
  2. Reuse the existing `GET /admin/reservations?from=&to=` endpoint (no new API
     needed). Also fetch blackouts for the same window.
  3. JS `renderGantt(reservations, blackouts, cars)`:
     - Header row: 7 day columns, label with weekday + date.
     - One row per car; cells are a `position: relative` container.
     - Each reservation/blackout is an absolutely-positioned bar spanning the
       correct columns. Width = (overlap days / 7) × 100 %. Bars at the same car
       row stack vertically if they overlap.
     - Color coding: pending=amber (--warning), checked_out=blue (--brand),
       returned=green (--success), blackout=gray (--surface-sunken).
     - Tooltip on hover: employee, purpose, interval — built as a `<title>` on the
       bar SVG or a CSS `::after` pseudo with `data-tooltip`.
  4. Navigation: `‹ Предишна седмица` / `Следваща →` buttons update `state.ganttWeek`.
  5. No new dependencies — pure CSS + vanilla JS. No SVG library needed; use
     `position: absolute` grid bars inside a CSS grid column layout.
  6. New i18n keys: `ui.gantt`, `gantt.noData`, `gantt.week`.
- **Acceptance criteria:**
  - Current week renders on first open; nav buttons shift the window.
  - Each car row shows correct bars that align with the day columns.
  - Blackout bars are visually distinct from reservation bars.
  - Desktop and ≥768 px tablet views are usable; mobile falls back to a
    "too small for Gantt" message suggesting the list view.
- **Verification:** Manual smoke with at least 3 cars and overlapping reservations.
  `node --check` on updated `app.js`.
- **Depends on:** —
- **Effort:** M

### 5.0b Месечен обобщаващ widget

- **Goal:** Admin вижда бързо „колко резервации / коли / служители тази месец"
  без да отваря таблицата.
- **Files:** `routers/reservations.py`, `schemas.py`, `templates/admin.html`,
  `static/app.js`, `static/i18n.js`
- **Approach:**
  1. New `GET /admin/stats/monthly?year=&month=` (admin-only):
     ```json
     {
       "period": "2026-04",
       "total_requests": 42,
       "approved": 38,
       "rejected": 4,
       "cancelled": 2,
       "active_cars": 5,
       "busiest_car_id": 3,
       "busiest_car_plate": "CB 1234 AB",
       "unique_employees": 11
     }
     ```
     Single SQL query with `COUNT + GROUP BY` filtered by `start_time` year/month.
  2. In admin dashboard, above KPI cards: a slim `.monthly-summary` bar showing
     the five key numbers as inline `<dl>` pairs. Defaults to current month; a
     `‹ ›` chevron pair lets admin browse past months.
  3. Auto-loads on dashboard init alongside `updateOverview()`.
  4. New i18n keys: `stats.monthly`, `stats.totalRequests`, `stats.approved`,
     `stats.rejected`, `stats.activeCars`, `stats.uniqueEmployees`.
- **Acceptance criteria:**
  - Widget shows correct numbers for current month.
  - Previous months navigate correctly; empty months show zeros.
  - Employee surface does NOT show this widget.
- **Verification:** `pytest` new endpoint test (auth + content) + manual smoke.
- **Depends on:** —
- **Effort:** S

### 5.1 Dark mode

- **Files:** `static/styles.css`, `templates/*.html`
- **Approach:**
  1. Lift every hex color into CSS custom properties on `:root`.
  2. Add a `@media (prefers-color-scheme: dark)` block overriding the tokens.
  3. Add an explicit override (`data-theme="dark"` attribute on `<html>`)
     toggled by a topbar button; persist choice in `localStorage`.
- **Effort:** M

### 5.2 CSV export

- **Goal:** Admins can export trip history + fleet utilization.
- **Files:** `routers/reservations.py`, `routers/cars.py`
- **Approach:**
  1. Add `GET /reservations.csv` and `GET /cars/utilization.csv` endpoints,
     admin-only, streaming with `StreamingResponse`. Use the stdlib `csv`
     module; UTF-8 with BOM for Excel compatibility (Bulgarian diacritics).
  2. Accept the same filters as the HTML views (date range, status, car).
  3. Add a "Export CSV" button on each admin table.
- **Effort:** S

### 5.3 Audit-log UI

- **Goal:** Surface the existing `reservation_audit` table as a per-reservation
  timeline.
- **Files:** `routers/reservations.py`, `templates/admin.html`, `static/*`
- **Approach:**
  1. Add `GET /reservations/{id}/audit` returning chronological events.
  2. Render a vertical timeline in the admin detail view with actor, action,
     timestamp (relative + absolute on hover), and optional reason.
- **Effort:** M

### 5.4 Observability

- **Files:** `app.py`, `config.py`, `requirements.txt`
- **Approach:**
  1. `structlog` - JSON logs in production, pretty logs in dev.
  2. Request ID middleware (`X-Request-ID`, generate if absent) bound to all
     log lines via structlog contextvars.
  3. `prometheus-fastapi-instrumentator` exposing `/metrics`. Scrape from
     Prometheus; dashboards are out of scope.
  4. Error reporting hook - leave a `report_error()` stub that ops can wire
     to Sentry / Rollbar later without touching every caller.
- **Effort:** M

### 5.5 Playwright end-to-end tests

- **Status:** Started on 2026-04-20 and expanded in Phase 10.2.
  `e2e/test_browser_smoke.py` now runs a fresh FastAPI server with temporary
  SQLite data per role flow and covers public orientation, employee
  quick-booking, approver decisions, admin control, employee mobile calendar
  and reception handoff/calendar. It writes screenshots when `E2E_ARTIFACT_DIR`
  is set.
- **Files:** `e2e/`, `requirements-dev.txt`, `Makefile`, CI workflow later
- **Approach:**
  1. Keep `pytest` fast by default through `pyproject.toml` `testpaths = ["tests"]`.
  2. Run browser checks explicitly with `make test-e2e`.
  3. Next scenarios to add:
     - Admin approve/reject -> employee inbox and timeline update.
     - Bulk reject empty-reason recovery.
     - Admin NetFleet key configured/unconfigured states with mocked payloads.
     - Admin start/return and logout/refresh recovery.
  4. Add CI only after timing and artifact behavior stay stable.
- **Effort:** M

### 5.6 Pre-commit hooks

- **Files:** `.pre-commit-config.yaml` (new), `requirements-dev.txt`,
  `README.md`
- **Approach:** `ruff`, `ruff-format`, `mypy` (start with `--ignore-missing-imports`
  and incrementally strengthen), `prettier` for `static/*.{js,css,html}`.
- **Effort:** S

### 5.7 Scheduled reminders

- **Goal:** Users get reminded 30 min before reservation start + on overdue
  return.
- **Files:** `notifications_service.py`, a scheduler (APScheduler) or cron
  inside Docker
- **Approach:** APScheduler with a persistent job store in the same database;
  on reservation state change, schedule/cancel the reminder job. Don't over-
  engineer - a 1-minute tick that scans for due reminders is adequate.
- **Effort:** M

### 5.8 Calendar week/day views + drag to reschedule

- **Goal:** Richer planning UX for heavy users.
- **Files:** `static/js/calendar.js`, templates, `static/styles.css`
- **Approach:** Consider an established, small library (`fullcalendar` weighs
  too much; evaluate `event-calendar` or a custom implementation). Drag to
  reschedule must open a confirm dialog (item 1.3) before firing an update.
- **Effort:** L

### 5.9 Write comprehensive tests

- **Goal:** Build enough automated confidence that FleetFlow can evolve without
  accidental lifecycle, auth, UI or deployment regressions.
- **Files:** `tests/`, new `e2e/`, `.github/workflows/tests.yml`,
  `requirements-dev.txt`, `README.md`
- **Approach:**
  1. Expand backend tests by domain: `test_auth.py`, `test_users.py`,
     `test_cars.py`, `test_reservations.py`, `test_notifications.py`,
     `test_blackouts.py`, `test_security.py`.
  2. Add negative authorization coverage for every admin endpoint: unauth,
     employee, inactive user and stale token where relevant.
  3. Add lifecycle matrix tests: request, approve, reject, start, return,
     cancel, overlap rejection, blackout rejection and second-user visibility.
  4. Add PostgreSQL smoke tests for Alembic migrations and core lifecycle
     flows via `docker-compose.postgres.yml`.
  5. Add Playwright end-to-end tests for the three core journeys: employee
     booking, admin approval, maintenance blackout blocking.
  6. Add CI gates for `pytest`, `pip-audit`, migration smoke and frontend
     smoke checks.
- **Acceptance criteria:**
  - Every endpoint has happy-path and authorization-negative tests.
  - Every lifecycle transition has at least one regression test.
  - CI fails on vulnerable Python dependencies, broken migrations or failing
    smoke journeys.
  - New bugs should first get a failing test, then a fix.
- **Verification:** `pytest`, Playwright e2e run, PostgreSQL compose smoke,
  `pip-audit -r requirements.txt`.
- **Depends on:** 5.5 for browser-level e2e, but backend expansion can start now.
- **Effort:** L

---

## Phase 6 - Serious admin module (shipped baseline)

This phase turns the current admin surface into a proper operational control
center. Some baseline pieces already exist (`/admin`, user CRUD, admin handoff,
blackout windows), but the next wave should make user administration explicit,
auditable and safe enough for real company operations.

**Status:** Items 6.1-6.4 shipped as baseline in `82ff34e` and `0a5a57f`.
Future admin work should extend this baseline rather than duplicating controls
back into the employee dashboard.

### 6.1 Admin password reset for users

- **Goal:** Fleet admins can reset another user's password without knowing the
  old password, while the action is audited.
- **Files:** `routers/users.py`, `schemas.py`, `db.py`, `templates/admin.html`,
  `static/app.js`, `static/i18n.js`, `static/styles.css`,
  new Alembic migration, `tests/test_app.py` or `tests/test_users.py`
- **Approach:**
  1. Add `AdminPasswordResetPayload` with `new_password` and optional
     `force_change_on_next_login` (default `true` once forced-change support
     exists; start with a documented no-op if needed).
  2. Add `POST /users/{user_id}/reset-password`, admin-only, rejecting inactive
     target users unless an explicit `allow_inactive` flag is added later.
  3. Hash the new password with `hash_password`; never return it in responses.
  4. Write a `user_audit_log` event with actor, target, action
     `password_reset`, reason and timestamp.
  5. Add an admin UI action on user cards/table with a confirmation dialog and
     password validation.
- **Acceptance criteria:**
  - Admin can reset an employee password; employee can log in with the new
    password and not with the old one.
  - Employees cannot reset anyone else's password.
  - Resetting the last active admin's password remains allowed, but is audited.
  - User-visible strings are Bulgarian and flow through `static/i18n.js`.
- **Verification:** `pytest` coverage for success, unauth, employee forbidden,
  inactive target behavior and audit event creation; manual admin UI smoke.
- **Depends on:** Existing `user_audit_log` table.
- **Effort:** M

### 6.2 Admin role change flow

- **Goal:** Admins can promote/demote users between `employee` and
  `fleet_admin` safely, without accidentally leaving the system with no admin.
- **Files:** `routers/users.py`, `schemas.py`, `templates/admin.html`,
  `static/app.js`, `static/i18n.js`, `tests/test_app.py` or
  `tests/test_users.py`
- **Approach:**
  1. Add `UserRoleChangePayload` with `role` and optional `reason`.
  2. Add `POST /users/{user_id}/role`, admin-only.
  3. Reuse the at-least-one-active-admin invariant from item 3.4 before any
     demotion takes effect.
  4. Invalidate stale privilege assumptions by relying on `verify_token()`
     re-binding to current DB user state (already required by review finding).
  5. Record `role_changed` in `user_audit_log` with old role, new role and
     reason.
  6. In the UI, show role controls only on the dedicated admin page and require
     confirmation for demotions.
- **Acceptance criteria:**
  - Admin can promote an employee to `fleet_admin`.
  - Admin cannot demote/deactivate the last active admin.
  - A user with an old token sees updated permissions after role change.
  - Role changes appear in audit history.
- **Verification:** Tests for promote, demote, last-admin refusal, stale-token
  behavior and employee forbidden; manual two-browser smoke.
- **Depends on:** 3.4 for invariant completeness.
- **Effort:** M

### 6.3 User action audit history UI

- **Goal:** Admins can inspect a chronological history of user/admin actions,
  including password resets, role changes, activation changes and handoffs.
- **Files:** `routers/users.py`, `schemas.py`, `templates/admin.html`,
  `static/app.js`, `static/i18n.js`, `static/styles.css`,
  `tests/test_app.py` or `tests/test_users.py`
- **Approach:**
  1. Add `GET /users/{user_id}/audit`, admin-only, returning chronological
     `user_audit_log` entries with actor display name, action, reason and time.
  2. Add optional query filters: `limit`, `offset`, `action`.
  3. Render an admin-side timeline or drawer from each user card/table row.
  4. Ensure sensitive values are never stored in audit logs (no raw passwords,
     no token values).
  5. Add Bulgarian labels for audit actions in `static/i18n.js`.
- **Acceptance criteria:**
  - Admin can open audit history for a user.
  - Employee cannot access audit endpoints.
  - Password reset and role change events appear immediately after action.
  - Audit UI is readable on mobile and desktop.
- **Verification:** Tests for list, auth negative, pagination and event order;
  manual UI smoke with at least two users and one admin.
- **Depends on:** 6.1 and 6.2 for richer event sources.
- **Effort:** M

### 6.4 Dedicated admin module, not mixed dashboard controls

- **Goal:** Administrative workflows live on a dedicated `/admin` module with
  clean navigation, while the employee dashboard stays focused on personal
  bookings and lifecycle actions.
- **Files:** `app.py`, `templates/index.html`, `templates/admin.html`,
  `static/app.js`, `static/styles.css`, `static/i18n.js`, `tests/test_app.py`
- **Approach:**
  1. Keep `/admin` as the canonical admin surface; remove or hide remaining
     duplicated admin-only creation/management panels from `templates/index.html`.
  2. Add admin module navigation sections: `Заявки`, `Потребители`, `Флот`,
     `Blackout-и`, `Audit`, `Настройки`.
  3. Make `/admin` visibly distinct but consistent with the FleetFlow design
     system: compact headers, responsive cards/tables and no horizontal overflow.
  4. If an employee opens `/admin`, show a polite forbidden/redirect state
     instead of leaking admin controls.
  5. Preserve quick links from employee desk to admin for users with
     `fleet_admin` role.
- **Acceptance criteria:**
  - Employee dashboard has no user/fleet admin forms.
  - `/admin` contains all admin controls and is usable at 375 px width.
  - Admin role users can still create cars/users, manage blackouts and handle
    approvals from `/admin`.
  - Employees cannot see or operate admin controls.
- **Verification:** `pytest` UI route smoke, manual admin/employee smoke in two
  browsers, responsive check at 375, 768 and 1280 px.
- **Depends on:** Current `/admin` baseline already shipped; 6.1-6.3 enrich it.
- **Effort:** M

---

## Phase 7 - Mars-grade production readiness

This phase is the difference between a good internal app and a robust operations
system that can survive real deployment, audits and incident recovery. Prioritize
these before exposing FleetFlow beyond a trusted internal network.

### 7.1 Resolve the GitHub Dependabot alert to zero

- **Goal:** The default branch has no open GitHub security alerts.
- **Files:** `requirements.txt`, lock/constraints file if introduced,
  `Dockerfile`, `README.md`
- **Status:** Local dependency audit, zero-CVE app Dockerfile remediation and
  zero-CVE PostgreSQL service image remediation shipped across `0503e95`,
  `ab1a0f2`, `0076814` and `a71121d`; GitHub alert closure still needs
  confirmation after push. On 2026-04-20, `make audit-prod`, direct
  `pip-audit -r requirements.txt` and `docker scout cves
  fleetflow_prod_smoke-car-pool:latest` were clean, but the GitHub push banner
  still reported one moderate Dependabot alert, so the next step is to inspect
  the Security tab item directly.
- **Approach:**
  1. Open the GitHub alert referenced on push:
     `https://github.com/dmedarov/Lessons-C-/security/dependabot/1`.
  2. Identify the package, vulnerable range and patched version.
  3. Upgrade the smallest safe dependency set; avoid broad unpinned upgrades.
  4. Rebuild Docker and run the full verification suite.
  5. Document the fix in the commit body if the vulnerable package is
     transitive or not obvious from `requirements.txt`.
- **Acceptance criteria:**
  - GitHub no longer reports the moderate alert on default branch.
  - `pip-audit -r requirements.txt` is clean locally.
  - Docker image rebuilds without dependency conflicts.
- **Verification:** GitHub Security page, `pip-audit`, `pytest`, Docker smoke.
- **Depends on:** GitHub security alert visibility.
- **Effort:** S

### 7.2 CI quality gates

- **Goal:** Every push/PR runs the checks currently performed manually.
- **Files:** `.github/workflows/production-gates.yml`, `Makefile`,
  `requirements-dev.txt`, `Dockerfile`, `README.md`
- **Status:** Shipped on 2026-04-20 as `Production Gates`; monitor the first
  GitHub Actions run after push.
- **Approach:**
  1. Add a GitHub Actions workflow for Python 3.12 and 3.14.
  2. Install runtime and dev dependencies.
  3. Run `python -m py_compile` on app/router modules.
  4. Run `pytest -q`.
  5. Run `node --check static/app.js static/i18n.js`.
  6. Run `pip-audit -r requirements.txt`.
  7. Build the production Docker image on the Python 3.14 lane.
  8. Keep the stable local equivalent in `make release-check`; `make audit-prod`
     uses no-resolver pinned runtime audit for local reliability, while CI runs
     the full resolver audit.
- **Acceptance criteria:**
  - A broken backend test blocks merge.
  - A JS syntax error blocks merge.
  - A vulnerable dependency blocks merge.
  - A broken production Docker build blocks merge.
- **Verification:** `make audit-prod` is clean locally for pinned
  `requirements.txt`; direct `pip-audit -r requirements.txt` is clean when the
  local resolver completes; open GitHub after push and confirm the workflow
  passes/fails as expected.
- **Depends on:** —
- **Effort:** S

### 7.3 PostgreSQL migration smoke and backup posture

- **Goal:** Production database changes are repeatable and recoverable.
- **Files:** `docker-compose.postgres.yml`, `alembic/`, `README.md`,
  optional `scripts/backup_postgres.sh`, optional `scripts/restore_postgres.sh`
- **Approach:**
  1. Add a documented smoke command that starts PostgreSQL, applies Alembic
     migrations and runs the core lifecycle tests against `DATABASE_URL`.
  2. Add a minimal backup command using `pg_dump` and a restore command using
     `pg_restore` or `psql`, documented but not over-automated.
  3. Add a release checklist step: backup before migrations, migrate, smoke,
     rollback plan.
  4. Keep SQLite dev flow unchanged.
- **Acceptance criteria:**
  - A fresh PostgreSQL container can run migrations and core tests.
  - Backup and restore commands are documented and tested once manually.
  - No schema change lands without an Alembic revision.
- **Verification:** PostgreSQL compose smoke + documented backup/restore dry run.
- **Depends on:** Existing Alembic baseline.
- **Effort:** M

### 7.4 Security headers, request IDs and structured logs

- **Goal:** Production traffic is traceable and receives safe default browser
  headers.
- **Files:** `app.py`, `config.py`, `README.md`, optional `logging_config.py`
- **Status:** Request ID propagation and baseline security headers shipped in
  `2a3c30f`; structured JSON logging remains open.
- **Approach:**
  1. Add request ID middleware: accept `X-Request-ID` or generate one.
  2. Return `X-Request-ID` on every response.
  3. Add security headers: `X-Content-Type-Options`, `Referrer-Policy`,
     `X-Frame-Options` or CSP-compatible equivalent.
  4. Switch production logs to JSON with request ID, route, status and latency.
  5. Keep dev logs readable.
- **Acceptance criteria:**
  - Every response has a request ID.
  - Errors can be traced across app logs.
  - Browser responses include baseline security headers.
- **Verification:** `pytest` middleware/header test + `curl -i /health`.
- **Depends on:** -
- **Effort:** M

### 7.5 Vehicle handover and return checklist

- **Goal:** Start/return lifecycle captures operational condition, not only a
  timestamp.
- **Files:** `schemas.py`, `routers/reservations.py`, `db.py`, Alembic
  migration, `templates/index.html`, `templates/admin.html`, `static/app.js`,
  `static/i18n.js`, `tests/test_app.py`
- **Approach:**
  1. Add optional fields for checkout/return: odometer, fuel/charge level,
     parking location, condition note and damage flag.
  2. Store these as structured columns or a JSON text payload depending on DB
     portability tradeoffs; prefer explicit columns for core reporting fields.
  3. Render compact admin-only forms in the start/return confirmation dialogs.
  4. Surface condition info in admin lifecycle view and audit trail.
  5. Add validation that return odometer cannot be lower than checkout odometer
     when both exist.
- **Acceptance criteria:**
  - Admin can start and return with condition metadata.
  - Employee can see condition details for their own approved/active/returned
    trips without receiving transition buttons.
  - Invalid odometer sequence is rejected.
- **Verification:** Tests for lifecycle metadata, invalid odometer and admin
  visibility; manual employee/admin smoke.
- **Depends on:** Existing lifecycle endpoints.
- **Effort:** M

### 7.6 Data retention and audit export

- **Goal:** Admins can satisfy internal audit/compliance requests without DB
  access.
- **Files:** `routers/users.py`, `routers/reservations.py`, `static/app.js`,
  `templates/admin.html`, `README.md`
- **Approach:**
  1. Add CSV export endpoints for user audit and reservation lifecycle audit.
  2. Support date range filters.
  3. Document retention expectations: audit logs are append-only and not
     deleted by normal UI actions.
  4. Keep exports admin-only and covered by authorization-negative tests.
- **Acceptance criteria:**
  - Admin can export audit history for a date range.
  - Employee cannot access exports.
  - CSV opens correctly with Bulgarian text in Excel/Numbers.
- **Verification:** `pytest` for auth and content type; manual CSV open.
- **Depends on:** Existing user audit + reservation audit tables.
- **Effort:** M

---

## Phase 8 - Apple/NASA UI & UX compliance

This phase turns the current premium visual direction into a repeatable
compliance program. Do **not** claim external certification; claim only that
FleetFlow has passed the internal checks below against Apple HIG, NASA WDS,
USWDS, WCAG 2.2, WAI-ARIA APG and NN/g heuristics.

### Research baseline for AI agents

- **Apple HIG Layout:** adaptive layout should preserve familiar relationships
  between controls and content, respect safe areas and standard margins, and
  support orientation/viewport changes without explaining the layout to users.
- **Apple HIG Buttons:** buttons need clear content, visual style and semantic
  role; custom buttons need visible press state and at least a 44 x 44 pt hit
  region.
- **Apple HIG Accessibility / Typography:** support larger text, keyboard-only
  operation, sufficient control spacing, non-thin type weights, color contrast
  and layouts that avoid truncation when text grows.
- **NASA WDS Colors / 508:** use a calm blue/neutral foundation, spare accent
  colors and verified 508/WCAG contrast combinations; never use color alone to
  communicate state.
- **USWDS Accessibility:** design around POUR (perceivable, operable,
  understandable, robust), semantic regions, clear labels, keyboard focus and
  state-change announcements.
- **W3C WCAG 2.2 + WAI-ARIA APG:** prefer native HTML; when custom widgets are
  unavoidable, follow APG keyboard/focus expectations for dialogs, tabs,
  toolbars, alerts, tables/grids, switches and tooltips.
- **NN/g heuristics:** prioritize system status visibility, real-world
  language, user control, consistency, error prevention, recognition over
  recall, efficient expert workflows, minimal visual noise and helpful errors.

Reference URLs:

- Apple Layout: `https://developer.apple.com/design/human-interface-guidelines/layout`
- Apple Buttons: `https://developer.apple.com/design/human-interface-guidelines/buttons`
- Apple Accessibility: `https://developer.apple.com/design/human-interface-guidelines/accessibility`
- Apple Typography: `https://developer.apple.com/design/human-interface-guidelines/typography`
- NASA WDS Colors: `https://nasa.github.io/nasawds-site/components/colors/`
- USWDS Accessibility: `https://designsystem.digital.gov/documentation/accessibility/`
- W3C WCAG overview: `https://www.w3.org/WAI/standards-guidelines/wcag/`
- WAI-ARIA APG patterns: `https://www.w3.org/WAI/ARIA/apg/patterns/`
- NN/g 10 usability heuristics: `https://www.nngroup.com/articles/ten-usability-heuristics/`

### 8.1 Compliance audit inventory

**Status:** Started on 2026-04-20. `docs/UI_UX_COMPLIANCE_AUDIT.md`
exists with surface inventory, current findings, contrast matrix scaffold and
PR/handoff checklist. Continue by adding screenshot evidence.

- **Goal:** Produce a living inventory of every UI surface and the guidelines
  it must satisfy.
- **Files:** new `docs/UI_UX_COMPLIANCE_AUDIT.md`, `ROADMAP_IMPROVEMENTS.md`
- **Approach:**
  1. Inventory screens: `/`, `/admin`, login/setup, booking form, calendar,
     reservation cards/table, notifications, users, cars, blackouts, dialogs,
     toasts and mobile bottom nav.
  2. For each surface, map required checks: Apple layout/buttons, NASA color,
     USWDS/WCAG accessibility, APG widget pattern, NN/g heuristic.
  3. Record current status as `pass`, `needs evidence`, `needs fix`, or
     `not applicable`. Link each `needs fix` row to a roadmap item.
  4. Add a short "How to update this audit" section for future AI agents.
- **Acceptance criteria:**
  - Every visible workflow has an owner row and at least one verification
    method.
  - The audit distinguishes shipped behavior from unverified claims.
  - New AI agents can pick a single row and know exactly where to inspect.
- **Verification:** Markdown review + grep that all major template IDs
  (`calendarStudio`, `reservationsDeck`, `usersDeck`, `fleetDeck`,
  `notificationsDeck`) appear in the audit.
- **Depends on:** -
- **Effort:** S

### 8.2 Design-token compliance matrix

**Status:** Started on 2026-04-20. `tests/test_design_tokens.py` covers the
first solid light/dark text and status token pairs. Continue with
browser-computed checks for translucent surfaces and message styles.

- **Goal:** Make NASA/508/WCAG contrast compliance measurable from
  `static/styles.css`.
- **Files:** `static/styles.css`, new `tests/test_design_tokens.py` or
  `scripts/check_contrast.py`, `docs/UI_UX_COMPLIANCE_AUDIT.md`
- **Approach:**
  1. Extract semantic token pairs: page/background, surface/text, muted/text,
     brand/button text, danger/warning/success/info statuses, focus rings,
     dark-mode equivalents.
  2. Add a small contrast checker using WCAG relative luminance; no runtime
     dependency. Fail if normal text pairs are below 4.5:1 or icon/focus pairs
     below 3:1.
  3. Keep NASA-inspired palette constraints: blues/neutrals as foundation,
     red/gold/green only for status, no one-note purple/blue gradients.
  4. Document allowed token pairs in the audit so new CSS does not invent
     unverified color combinations.
- **Acceptance criteria:**
  - Automated test fails for a deliberately low-contrast token pair.
  - Every status color has text and shape support, not color alone.
  - Light and dark themes both pass.
- **Verification:** `pytest tests/test_design_tokens.py`, manual browser check
  in light/dark mode and 200% zoom.
- **Depends on:** 8.1
- **Effort:** M

### 8.3 Apple layout and responsive density pass

- **Goal:** Remove overlap/crowding risk and make the cockpit feel native,
  calm and adaptive on phone, tablet and desktop.
- **Files:** `templates/index.html`, `templates/admin.html`,
  `static/styles.css`, `static/app.js`, `docs/UI_UX_COMPLIANCE_AUDIT.md`
- **Approach:**
  1. Define page-level layout rules: max readable line length, consistent
     section rhythm, safe spacing around fixed/sticky controls and no cards
     nested inside cards.
  2. Audit all controls for Apple hit target: interactive controls >=44 px
     high on touch viewports; icon-only controls need accessible names and
     visible hover/focus/press states.
  3. At 390, 768, 1024 and 1440 px, verify no text overlaps, table/card labels
     fit, mobile nav does not hide primary actions and calendar controls stay
     reachable.
  4. Add CSS utility constraints only where needed: `minmax(0, 1fr)`,
     `overflow-wrap`, stable aspect/height for calendar/day cells and resilient
     toolbar wrapping.
- **Acceptance criteria:**
  - No horizontal page scroll at 390 px except intentional data tables if any
    remain; preferred outcome is no horizontal scroll anywhere.
  - Topbar, mobile nav, calendar and admin modules never overlap at tested
    breakpoints.
  - All custom buttons/chips have press/focus states and 44 px touch target.
- **Verification:** Playwright screenshots for `/` and `/admin` at 390, 768,
  1024, 1440; visual diff review; manual keyboard pass.
- **Depends on:** 8.1
- **Effort:** M

### 8.4 WCAG/USWDS semantic accessibility pass

**Status:** Started on 2026-04-20 for small high-confidence fixes:
notification list live regions, dialog focus return, admin calendar accessible
names, field-error `aria-describedby` wiring, dialog modal
name/description/error semantics, mobile safe-area handling and theme-aware
message alert classes. Continue with keyboard and screen-reader evidence.

- **Goal:** Make FleetFlow operable and understandable without a mouse or
  visual styling.
- **Files:** `templates/index.html`, `templates/admin.html`,
  `static/app.js`, `static/styles.css`, `static/i18n.js`
- **Approach:**
  1. Add/verify landmarks: header/nav/main/section names and one logical H1 per
     surface.
  2. Ensure form labels, helper text and errors are programmatically connected
     (`for`, `aria-describedby`, `aria-invalid`) and visible in Bulgarian.
  3. Verify dialogs follow APG: focus moves into dialog, ESC/cancel exits,
     focus returns to trigger, destructive action buttons are clearly labeled.
  4. Convert any custom toggle/chip/tab UI to native buttons with
     `aria-pressed`/`aria-selected` as appropriate; avoid `div` click targets.
  5. Add polite live regions for filtered result counts, bulk-action outcome,
     refresh/logout state and notification updates.
- **Acceptance criteria:**
  - Core flows work with keyboard only: login, make booking, cancel booking,
    admin approve/reject, bulk decision, edit blackout, save car notes.
  - Screen reader labels communicate status, owner, car, date and next action.
  - No state is conveyed by color or icon alone.
- **Verification:** Playwright accessibility snapshots where practical,
  manual VoiceOver/NVDA pass, `pytest` template assertions for key ARIA
  attributes.
- **Depends on:** 8.1, 8.3
- **Effort:** M

### 8.5 Error prevention and recovery rewrite

**Status:** Started on 2026-04-20. Single-reservation reject, bulk reject and
cancel dialogs now require a human reason, mark the empty textarea with
`aria-invalid`, keep focus on the field and use Bulgarian inline recovery copy.
Cancel also sends the reason to the API so `audit_log.reason` records why the
reservation was cancelled. The shared dialog helper can now target the exact
invalid field for password reset and blackout edit validation too. Continue
with return/deactivate/role/handoff/blackout recovery checks.

- **Goal:** Align destructive/complex workflows with NN/g error prevention and
  Apple clarity.
- **Files:** `static/app.js`, `static/i18n.js`, `static/styles.css`,
  routers only if API error shapes need tightening
- **Approach:**
  1. Audit every destructive or expensive action: reject, cancel, return,
     deactivate, role change, password reset, handoff, blackout deactivate,
     bulk decisions.
  2. Replace generic errors with actionable Bulgarian messages: what happened,
     why it matters and what the user can do next.
  3. Add pre-submit checks where the UI can prevent mistakes: missing reason on
     reject, impossible date ranges, no selected rows, inactive car/user.
  4. Preserve user input after failed submits; never make people retype long
     notes/reasons.
- **Acceptance criteria:**
  - Every destructive action has confirmation, cancel path and clear success/
    failure feedback.
  - 422/409/500 surfaces never show raw technical jargon to end users.
  - Failed forms keep values and focus the first invalid field.
- **Verification:** API error tests where applicable, browser smoke for every
  action, Bulgarian copy review, `pytest tests/test_ui_compliance.py`.
- **Depends on:** 8.4
- **Effort:** M

### 8.6 Operational command model

- **Goal:** Give novice users obvious paths and expert users efficient paths
  without adding visual noise.
- **Files:** `templates/index.html`, `templates/admin.html`,
  `static/app.js`, `static/i18n.js`, `static/styles.css`
- **Approach:**
  1. Define the primary command per surface: employee booking; admin pending
     queue. All secondary commands must be visually quieter.
  2. Add optional keyboard accelerators for high-frequency admin actions only
     after visible controls exist. Never hide essential actions behind
     shortcuts.
  3. Add a command/help affordance only if it is contextual and short; avoid
     in-app explanatory walls.
  4. Keep shortcut docs in `docs/UI_UX_COMPLIANCE_AUDIT.md`, not scattered in
     templates.
- **Acceptance criteria:**
  - Users can complete core flows without reading instructions.
  - Admin can clear a pending queue with minimal pointer travel.
  - Keyboard shortcuts do not conflict with browser/system shortcuts.
- **Verification:** Manual timed smoke for employee booking and admin approval;
  keyboard-only pass.
- **Depends on:** 8.3, 8.4
- **Effort:** S

### 8.7 Automated UI regression harness

- **Status:** Started on 2026-04-20. Optional Playwright smoke exists in
  `e2e/test_browser_smoke.py`, `make test-e2e` is documented, and screenshot
  artifacts are ignored under `test-results/`.
- **Goal:** Turn "Apple/NASA quality" into repeatable checks, not taste-based
  review.
- **Files:** `requirements-dev.txt`, `Makefile`, `pyproject.toml`, `e2e/`,
  CI workflow later, `docs/UI_UX_COMPLIANCE_AUDIT.md`
- **Approach:**
  1. Add Playwright e2e tests for login, booking, admin approve/reject, bulk
     actions, mobile calendar and logout/refresh recovery.
  2. Capture screenshots at 390, 768 and 1440 px for `/` and `/admin`.
  3. Add accessibility assertions: no missing accessible names for buttons,
     no duplicate IDs, visible focus after tab, live region exists.
  4. Run these checks locally first; add CI only after stable timing and test
     data setup are reliable.
- **Acceptance criteria:**
  - E2E suite can run against a fresh local container without manual setup.
  - Screenshots are deterministic enough for review artifacts.
  - CI failure tells agents which surface and viewport regressed.
- **Verification:** `pytest` + Playwright command documented in README and
  audit doc; latest local browser run -> 6 passed with `public-mobile.png`,
  `employee-desktop.png`, `approver-desktop.png`, `admin-desktop.png`,
  `employee-mobile.png`, `reception-desktop.png`.
- **Depends on:** 8.2, 8.3, 8.4
- **Effort:** L

### 8.8 Human handoff checklist

- **Goal:** Make every UI PR reviewable by another AI agent or engineer in
  under five minutes.
- **Files:** `docs/UI_UX_COMPLIANCE_AUDIT.md`,
  `ROADMAP_IMPROVEMENTS.md`, PR template if added later
- **Approach:**
  1. Add a checklist with: changed surfaces, screenshots, keyboard path,
     contrast pairs, ARIA/live-region changes, copy changes, tests and known
     residual risk.
  2. Require "guideline mapping": each UI change names the relevant Apple,
     NASA, USWDS/WCAG/APG or NN/g principle.
  3. Include a "do not merge if" list: overlap, unreadable contrast,
     inaccessible custom control, unlabeled icon button, missing error state,
     broken mobile nav.
- **Acceptance criteria:**
  - A future AI agent can continue from the checklist without reading the
    prior chat.
  - The checklist is short enough to paste into a PR description.
- **Verification:** Dry-run the checklist against the current admin page and
  record at least three follow-up findings in the audit doc.
- **Depends on:** 8.1
- **Effort:** S

---

## Phase 9: Obsessively Good Product Experience

**Product target:** FleetFlow is not a "car booking app"; it is a **calm
operations assistant for internal mobility**. Future agents should optimize for
one primary action, less thinking, fewer visible controls and stronger
confidence after every click.

### Production UX readiness pass

Before live use, every shipped change must preserve these flow-level checks:

1. **Pre-login:** hero status bar shows real aggregate counts for pending
   approvals, active trips and free cars without exposing detailed records.
2. **Login/setup:** setup/login panels remain the only primary action before
   authentication; no operational form is actionable before auth.
3. **Employee free mode:** quick-book is visible before manual form scanning,
   the button cannot overflow on mobile, and manual booking stays available.
4. **Employee active/next trip:** Current Trip Hero answers "what is my next
   move" before calendar/table browsing; pickup telemetry is scoped to the
   user's own approved/active trip.
5. **Employee history/noise:** returned/rejected/cancelled rows stay out of
   the default operational flow; read notifications do not accumulate in the
   visible inbox.
6. **Decision/reception modes:** pending requests and Decision Rail appear
   before tables for approvers; approved key handoffs and active returns appear
   in Reception Rail before lifecycle cards/tables for reception. Approve/reject
   and start/return are separated by role and by screen priority.
7. **Admin operations:** Fleet Pulse shows compact insight cards, not a BI
   dashboard; production readiness and NetFleet setup never reveal secrets.
8. **Calendar/fleet:** timeline/card views come before tables; calendar is for
   planning context, not the only way to find the next action. Operational roles
   must not lose calendar visibility just because a table filter is active.
9. **Errors/loading:** every destructive action has a reason ritual, every
   slow surface has a skeleton/busy state, and every failed action keeps user
   input intact.
10. **Evidence:** run unit/static tests, targeted UI/API pack, Playwright
    desktop/mobile screenshots and Docker smoke before production handoff.

### 9.1 Intent-driven home / next-action layer ✅ started 2026-04-20

**Status:** Started. The summary deck now exposes contextual next-action
buttons for employee free mode, approved trip, active trip, admin pending
queue, admin active trips and calm fleet state. The top status bar now reports
free cars as active cars minus active trips, so the KPI matches the cockpit
wireframe's "available now" meaning.

- **Files:** `templates/index.html`, `templates/admin.html`, `static/app.js`,
  `static/i18n.js`, `static/styles.css`, `tests/test_ui_compliance.py`
- **Acceptance criteria:**
  - No authenticated surface should leave the user without a next step.
  - Each surface gets at most one primary intent action; secondary actions
    remain visually quieter.
  - Intent actions must call existing workflows, not create duplicate business
    logic.
- **Verification:** `pytest tests/test_ui_compliance.py`, full `pytest -q`,
  manual browser check at desktop and 390 px.
- **Next agent action:** Capture screenshots and continue with current trip
  hero so active/approved reservations stop feeling like table rows.

### 9.2 Current trip hero

**Status:** Started on 2026-04-20. Employee desk now renders
`#currentTripHero` above the calendar when there is an active trip or next
approved reservation, with one primary action to view the trip. Start/return
belong to `fleet_reception` or `fleet_admin`, not employee.

- **Goal:** Make an active or next approved trip the hero object for employee
  mode.
- **Files:** `templates/index.html`, `static/app.js`, `static/styles.css`,
  `static/i18n.js`
- **Acceptance criteria:** active trip shows car, time window, status, pickup
  context when available and one primary "view trip" action without requiring
  table scanning; no employee start/return buttons.
- **Verification:** `pytest tests/test_ui_compliance.py`, full `pytest -q`,
  manual browser check at desktop and 390 px.

### 9.3 Admin decision rail

**Status:** Started on 2026-04-20. Admin surface now renders
`#decisionRail` before the bulk action bar/table, promotes the top 3 pending
reservations by start time, exposes direct approve/reject actions per card and
provides an "Одобри всички" action that selects the full pending queue before
using the existing bulk approval flow.

- **Goal:** Admin starts with the top 3 pending decisions and batch action,
  while the full table becomes secondary.
- **Files:** `templates/admin.html`, `static/app.js`, `static/styles.css`,
  `static/i18n.js`
- **Acceptance criteria:** pending queue is visible before filters/tables;
  urgency is text-backed, not color-only; every card keeps 44 px action
  targets and uses existing lifecycle handlers.
- **Verification:** `pytest tests/test_ui_compliance.py`, full `pytest -q`,
  `node --check static/app.js`, `node --check static/i18n.js`; still needs
  browser screenshot evidence at desktop and 390 px.

### 9.4 Quiet intelligence

**Status:** Started on 2026-04-20. Admin surface now renders `#fleetPulse`
before approvals with a global reservation snapshot independent of table
filters. It summarizes active trips, cars releasing within 1 hour, pending
decisions, busiest car and NetFleet GPS signal availability as `X/Y` active
FleetFlow cars with a last position, not raw NetFleet device counts. Admin
fleet cards show last GPS coordinates/speed/time when NetFleet is configured
by Admin UI or runtime env.
Employee Current Trip Hero shows "Къде да вземеш колата" only for the user's
own approved/active reservation, so location helps pickup without exposing the
whole fleet. Employee free-mode booking now uses `/reservations/suggest` and
`/reservations/quick-book` so the primary "Резервирай сега" action creates a
pending request for the nearest available active car without scanning the form.
Smart prefill now reads `/reservations/preferences` and offers the user's most
common car, hour and duration from recent reservations as a reviewed one-click
form fill, not an invisible auto-submit.
Admins can now open `/admin`, use the GPS signals panel to add/change the
NetFleet key, and see only status/last-change metadata; the secret is stored
server-side and never echoed back.
Reservation lists now render a timeline-first lifecycle flow before the table,
with direct actions and admin pending selection; the table remains a secondary
detail view.
Fleet Intelligence Seed now scores available cars by conflict/blackout-safe
availability, recent utilization and the user's recent car preference. Quick
booking records the chosen mode, score and reason in `car_assignments`, while
`/admin/intelligence/pulse` adds compact admin insights under Fleet Pulse.
The quick-book button is now full-width and wrapping, so the Bulgarian label
cannot overflow its container on narrow screens.
The hero status bar now loads aggregate counts before login through
`/public/overview`, keeping the first screen informative without exposing
reservation rows or user names. The calendar now loads anonymized operational
slots through `/public/calendar`; registration number and model are visible for
orientation, but requester, purpose, GPS, reservation ids and actions are not.

- **Goal:** Predict useful defaults without "AI assistant" complexity.
- **Initial rules:** conflict/blackout-safe quick booking, best-car scoring
  across recent utilization and user preference, last used car/common time
  prefill, next free slot action, pending-first admin dashboard.
- **Files:** `templates/admin.html`, `static/app.js`, `static/i18n.js`,
  `static/styles.css`, `fleet_intelligence/`, `routers/intelligence.py`,
  `app_settings.py`, `config.py`, `netfleet_service.py`, `routers/cars.py`,
  `routers/reservations.py`, `db.py`,
  `alembic/versions/20260420_0008_car_assignments.py`,
  `alembic/versions/20260420_0009_split_operational_roles.py`, `.env.example`,
  `docker-compose.yml`, `docker-compose.postgres.yml`
- **Verification:** `pytest -q` -> 140 passed,
  `pytest tests/test_ui_compliance.py -q` -> 31 passed,
  `node --check static/app.js`, `node --check static/i18n.js`, Python compile
  check and Playwright browser smoke pass with public/employee/approver/admin/
  reception desktop plus employee mobile screenshots.

### 9.5 Applicability notes from premium wireframe

- **Already present / strengthened:** live KPI strip, contextual lifecycle
  actions, timeline-first reservation flow, timeline meter, next free slot
  action, smart prefill, intent-driven next step, Admin Decision Rail,
  Reception Rail, plus Admin UI NetFleet key setup/change.
- **UX review decision:** employee surface is now request-first, not
  calendar-first. The order is current trip/context, reservations lifecycle,
  calendar planning, fleet availability; the new-request control sits before
  inbox in the side rail. Admin remains decision-first.
- **Lifecycle ownership:** because this is a служебен pool процес, only admin
  can approve, mark active trip and mark returned. Employee UI must never show
  start/return transition buttons.
- **Now evidenced:** initial Playwright smoke verifies employee one-tap booking,
  timeline-first cards, Admin Decision Rail, Fleet Pulse copy and mobile
  calendar, with screenshots for employee desktop, admin desktop and employee
  mobile.
- **Apply next:** browser-computed contrast and broader Playwright evidence for
  admin approve/reject, bulk reject reason recovery, NetFleet configured/
  unconfigured states, refresh/logout and admin start/return.
- **Defer:** heavy BI dashboards, extra roles, settings labyrinth and generic
  chat assistant. GPS stays limited to read-only coordinates/availability
  context unless a specific operational flow needs more.

---

## Phase 10: Production Hardening and Codebase Shape

**Goal:** Make the current premium product safer to operate and easier for
future agents to change. This phase is intentionally less glamorous than new
features, but it is the difference between "works today" and "survives live
usage".

### 10.1 Route and schema guardrails

**Status:** Shipped on 2026-04-20. `tests/test_schema_contracts.py` now covers
route registry uniqueness, SQLite bootstrap execution, SQLite/PostgreSQL
bootstrap schema contract parity, runtime-upgrade bootstrap columns and the
single Alembic head revision. `alembic.ini` also declares `path_separator = os`
to keep Alembic config parsing warning-free.

- **Goal:** Catch duplicate routes and schema drift automatically.
- **Files:** `app.py`, `db.py`, `tests/test_app.py` or new
  `tests/test_schema_contracts.py`
- **Approach:**
  1. Add a test that builds the FastAPI app and asserts no duplicate
     `(method, path)` route pairs exist, excluding automatically generated
     `HEAD` if present.
  2. Add tests that execute/parse the SQLite bootstrap schema against an empty
     in-memory DB.
  3. Add a PostgreSQL bootstrap smoke or SQL parse check when a live Postgres
     URL is available; otherwise keep it as a documented optional smoke.
  4. Add an Alembic head check so production migrations are not silently behind.
- **Acceptance criteria:** route registry is unique, bootstrap schema test is
  green, and the test failure points to the exact duplicate or broken statement.
- **Verification:** `pytest tests/test_schema_contracts.py -q`, full
  `pytest -q`, `make release-check` before push.
- **Depends on:** current test suite.
- **Effort:** S

### 10.2 Role-specific Playwright production flows

**Status:** Shipped on 2026-04-20. `e2e/test_browser_smoke.py` now starts a
fresh SQLite-backed app server per test and splits browser evidence into
public orientation, employee quick-booking, approver decision, admin control,
employee mobile calendar and reception handoff/calendar flows.

- **Goal:** Keep smaller browser tests that map to real pool-process roles.
- **Files:** `e2e/test_browser_smoke.py`, optional new `e2e/test_public.py`,
  `e2e/test_employee.py`, `e2e/test_approver.py`, `e2e/test_reception.py`,
  `e2e/test_admin.py`, `README.md`, `docs/UI_UX_COMPLIANCE_AUDIT.md`
- **Approach:**
  1. Keep each role flow isolated with a fresh temporary SQLite database.
  2. Add public flow: pre-login overview shows real aggregate counts; public
     calendar shows active/approved occupancy with plate/model but no requester
     or actions.
  3. Add employee flow: quick-book, smart prefill, Current Trip Hero and hidden
     start/return buttons.
  4. Add approver flow: Decision Rail, direct approve/reject, bulk reject
     reason validation.
  5. Add reception flow: Reception Rail, approved handoff, checked-out return
     and role-aware calendar.
  6. Add admin flow: NetFleet key setup/change, production readiness panel,
     user GSM field and fleet settings.
- **Acceptance criteria:** each role test can fail independently with its own
  screenshot artifacts and no manual setup.
- **Verification:** `make test-e2e` or documented Playwright command,
  screenshots at 390 and 1440 px for changed surfaces.
- **Depends on:** Phase 8.7 baseline.
- **Effort:** M

### 10.3 Frontend module split

- **Goal:** Reduce risk in `static/app.js` before further premium UI work.
- **Files:** `static/app.js`, new `static/modules/*.js` or equivalent
  no-build vanilla modules, `templates/index.html`, `templates/admin.html`,
  `README.md`
- **Approach:**
  1. Start with pure extraction, no behavior change.
  2. Suggested boundaries: `api/session`, `shell/overview`, `reservations`,
     `calendar`, `admin-users`, `admin-fleet`, `settings/netfleet`,
     `notifications`, `dialogs`.
  3. Keep global state shape stable for the first extraction.
  4. Move one slice at a time and run JS syntax + browser smoke after each
     meaningful split.
- **Acceptance criteria:** no endpoint or UI behavior changes; source files are
  smaller and named by responsibility; no new build step.
- **Verification:** `node --check` on every JS file, `pytest -q`,
  Playwright role smoke.
- **Depends on:** 10.2 recommended first, but can start with API/dialog helpers.
- **Effort:** L

### 10.4 Reservation service extraction

- **Goal:** Make reservation behavior testable without one giant router file.
- **Files:** `routers/reservations.py`, new `reservation_services/` or
  `services/reservations/`, `tests/test_app.py`, targeted reservation tests.
- **Approach:**
  1. Move pure helpers first: conflict/overlap, serialization, recipient
     selection and scoring wrappers.
  2. Then extract command services: create, cancel, approve/reject, start,
     return, bulk decisions.
  3. Keep FastAPI route function signatures and response contracts unchanged.
  4. Add focused unit tests around extracted service functions where practical.
- **Acceptance criteria:** `routers/reservations.py` becomes mostly route
  wiring; existing API tests pass without fixture rewrites.
- **Verification:** full `pytest -q`, route registry test from 10.1, manual
  employee/approver/reception smoke.
- **Depends on:** 10.1.
- **Effort:** L

### 10.5 Session management UI and cleanup job

- **Goal:** Give operators and users visibility into refresh sessions without
  weakening the current rotation model.
- **Files:** `routers/auth.py`, `routers/users.py`, `security.py`, `db.py`,
  `static/app.js`, `static/i18n.js`, `templates/admin.html`, Alembic revision.
- **Approach:**
  1. Add current-user endpoint for active sessions: issued time, expiry,
     browser/user-agent summary and current session marker.
  2. Add revoke current/all-other sessions actions.
  3. Add admin-only session visibility for a user if operationally needed.
  4. Add cleanup job/command for expired refresh tokens.
- **Acceptance criteria:** user can see and revoke sessions; expired tokens do
  not grow forever; no raw token values are ever exposed.
- **Verification:** auth tests for list/revoke/cleanup, UI smoke, logout/
  refresh regression.
- **Depends on:** stable auth baseline and current refresh-token table.
- **Effort:** M

### 10.6 NetFleet pickup clarity

- **Goal:** Make live vehicle location useful without turning FleetFlow into a
  noisy tracking system.
- **Files:** `netfleet_service.py`, `routers/cars.py`, `static/app.js`,
  `static/i18n.js`, `static/styles.css`, tests around telemetry serialization.
- **Approach:**
  1. Add freshness labels: "обновено преди X мин", "стар GPS сигнал" and
     "няма сигнал" with thresholds documented in config.
  2. Replace coordinate-first employee copy with pickup wording:
     "Последна позиция за ориентация" and clear last-seen time.
  3. Keep full fleet GPS visible only to `fleet_admin`; employee remains scoped
     to own approved/active trip.
  4. Defer map rendering until operators prove it helps pickup more than simple
     address/coordinates.
- **Acceptance criteria:** users understand whether a location is fresh; no
  raw event counts appear in product copy; scoped privacy remains intact.
- **Verification:** NetFleet configured/unconfigured Playwright states, API
  tests with stale/current telemetry fixtures.
- **Depends on:** current NetFleet proxy.
- **Effort:** M

### 10.7 Materialized intelligence snapshots (deferred)

- **Goal:** Add historical intelligence only after live usage proves inline
  metrics are insufficient.
- **Files:** future Alembic revisions, `fleet_intelligence/`, `routers/intelligence.py`,
  `README.md`, `ROADMAP_IMPROVEMENTS.md`
- **Approach:**
  1. First collect production pain: slow pulse, repeated operator questions or
     need for trend review.
  2. If justified, add `car_status_snapshots`, `fleet_insights` and
     `fleet_demand_snapshots`.
  3. Add a scheduled recompute command before any always-on background worker.
  4. Keep Fleet Pulse compact; do not build a heavy BI dashboard.
- **Acceptance criteria:** snapshots have a clear operator question they answer;
  UI shows concise insights, not analytics sprawl.
- **Verification:** migration tests, recompute command test, admin pulse smoke.
- **Depends on:** real production usage data.
- **Effort:** L

### 10.8 Production release evidence pack

- **Goal:** Make go-live evidence repeatable and inspectable.
- **Files:** `README.md`, `docs/PRODUCTION_USER_GUIDE.md`,
  `docs/UI_UX_COMPLIANCE_AUDIT.md`, `ROADMAP.md`, `ROADMAP_IMPROVEMENTS.md`
- **Approach:**
  1. Record the exact commands and latest passing results for `pytest -q`,
     `pytest tests/test_ui_compliance.py -q`, JS syntax, Playwright,
     `make release-check`, `make prod-check`, backup and restore drill.
  2. Record GitHub Actions and GitHub Security status after push.
  3. Keep production secrets out of docs and screenshots.
  4. Add a first-live checklist: domain/CORS, admin bootstrap, NetFleet key,
     backup path, operator contacts and rollback step.
- **Acceptance criteria:** a human can decide "ready/not ready" from docs and
  evidence without reading chat history.
- **Verification:** dry-run the checklist on a clean checkout.
- **Depends on:** 7.1/7.2 confirmation and current production setup.
- **Effort:** S

---

## Cross-cutting concerns (apply to every item)

- **No new dependencies** without listing them in the PR description with
  size + license + alternatives considered.
- **Bulgarian is the default locale.** If you add any copy, add it to
  `static/i18n.js` (item 1.2) - don't inline English.
- **Every user-visible change needs a screenshot** in the PR (mobile + desktop
  for UI work).
- **Every UI change must map to a guideline** from Phase 8 when applicable:
  Apple HIG, NASA WDS/508, USWDS/WCAG/APG or NN/g. If no guideline applies,
  say why in the PR notes.
- **Do not merge UI work with known overlap, clipped text, unlabeled icon
  buttons, low contrast, hover-only actions or color-only status.**
- **Every DB change needs an Alembic revision.** Never hand-edit the schema
  in `db.py` without a matching `alembic revision --autogenerate` +
  human review of the generated script.
- **Every new endpoint needs** `pytest` coverage that includes an
  authorization negative test (unauth + wrong-role).
- **Respect the existing dual-DB abstraction.** If you write SQL, it must
  work on both SQLite and PostgreSQL. Check `db.py` for the placeholder
  style and parameter adaptation helpers.

---

## Suggested sequencing (from current state)

1. **7.1/7.2 external production signal closure** - confirm GitHub Actions
   Production Gates and inspect the GitHub Dependabot alert directly.
   Note: local `gh` is not installed and unauthenticated `curl` to the private
   Dependabot API returns 401, so use GitHub web UI or an authenticated API
   token to inspect the exact alert.
2. **8.2 browser-computed contrast** - close translucent surfaces, focus rings
   and alert/status pair evidence.
3. **8.3 responsive density pass** - use the new screenshots to hunt overlap,
   clipped text and weak hierarchy at 390/768/1024/1440.
4. **8.5 destructive-action recovery sweep** - return, deactivate, role change,
   handoff and blackout deactivate.
5. **5.4/5.9 production proof** - PostgreSQL migration smoke, backup/restore
   playbook and structured logs.
6. **7.3 PostgreSQL migration smoke + backups** - required before serious
   production rollout.
7. **10.3 Split `static/app.js` into modules** - do this before large frontend
   additions; the file is already 4048 lines.
8. **10.4 reservation service extraction** - keep endpoints stable while
    moving lifecycle/domain logic out of the router.
9. **5.5 Playwright e2e + 5.9 comprehensive tests** - browser-level confidence
    after the core flows stabilize.
10. **5.0 Fleet Gantt + 5.0b monthly summary** - high-value admin planning once
   the frontend is modular enough.
11. **10.5 Session-management UI** - list active refresh sessions per user,
   revoke current/all sessions and expose security audit history.
12. **10.6 NetFleet pickup clarity** - freshness labels and human pickup
    wording before maps or telemetry-heavy features.
13. **7.5 Vehicle handover checklist + 7.6 audit export** - operational polish
    for real fleet accountability.
14. **10.7 materialized intelligence snapshots** - only after live usage proves
    inline metrics are too slow or historical trend review is needed.

If time is limited, execute items 1-4 before any new feature work.

---

## Done

### 2026-04-20 - Authenticated requester GSM in reservation surfaces

- **UX rule:** requester GSM is contact metadata for operational coordination,
  not public data and not an auth factor.
- **API:** `GET /reservations` now joins the requester user and returns
  `requester_gsm_number` for reservations visible to the authenticated token.
  Public `/public/overview` and `/public/calendar` remain anonymous.
- **UI:** Decision Rail, Reception Rail, lifecycle cards, table requester cells
  and authenticated calendar day timeline show `GSM: ...` when the reservation
  payload has a requester GSM number.
- **Verification:** targeted `tests/test_app.py` confirms approver, reception
  and employee-visible reservation payloads include requester GSM, while public
  calendar does not. `tests/test_ui_compliance.py` guards the UI/i18n/public
  no-leak rule. Full local gate:
  - `.venv/bin/python -m pytest -q` -> 142 passed
  - `E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
    -> 6 passed
  - `node --check static/app.js`
  - `node --check static/i18n.js`

### 2026-04-20 - Deterministic Bulgarian date/time format

- **UX rule:** UI date/time now renders as `dd.mm.yyyy, HH:MM` everywhere that
  uses `formatDateTime()`. Hours are zero-padded 24-hour values, with no AM/PM
  and no browser-dependent locale suffix such as `г.`.
- **Mobile calendar:** `formatDayLabel()` now shows weekday plus `dd.mm.yyyy`
  instead of a long locale date.
- **Guardrail:** `tests/test_ui_compliance.py` now rejects `dateStyle`,
  `timeStyle` and `hour12` in `static/app.js` and asserts the deterministic
  formatting template.
- **Verification:** `pytest tests/test_ui_compliance.py -q` -> 32 passed;
  `pytest -q` -> 141 passed;
  `E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
  -> 6 passed; `node --check static/app.js`; `node --check static/i18n.js`.

### 2026-04-20 - Pickup GPS refresh after approval

- **Root cause:** employee notification polling refreshed the inbox and KPI
  overview, but did not reload reservations or pickup telemetry when an
  approver/admin approved a reservation in another session. The location block
  could therefore remain missing until a manual refresh/full data reload.
- **Fix:** new reservation lifecycle notifications (`reservation_decision`,
  `reservation_cancelled`, `trip_started`, `trip_returned`) now trigger
  `loadReservations()` and `loadPickupTelemetry()` during polling.
- **UX fallback:** Current Trip Hero now shows explicit Bulgarian fallback
  copy when NetFleet is not configured or pickup telemetry is temporarily
  unavailable, instead of silently hiding the location block.
- **Verification:** `pytest tests/test_ui_compliance.py -q` -> 31 passed;
  `pytest -q` -> 140 passed;
  `E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
  -> 6 passed; `node --check static/app.js`; `node --check static/i18n.js`.

### 2026-04-20 - Phase 10.2 role-specific Playwright browser evidence

- **E2E split:** `e2e/test_browser_smoke.py` no longer has one broad smoke.
  It now has separate tests for public pre-login orientation, employee
  quick-booking, approver decision surface, admin control surface, employee
  mobile calendar and reception handoff/calendar.
- **Fresh DB per flow:** the server fixture now uses a fresh temporary SQLite
  database per test, so one role flow cannot accidentally depend on another.
- **New evidence artifacts:** `E2E_ARTIFACT_DIR=test-results/e2e` now writes
  `public-mobile.png`, `employee-desktop.png`, `approver-desktop.png`,
  `admin-desktop.png`, `employee-mobile.png` and `reception-desktop.png`.
- **Dependabot inspection note:** GitHub connector can read repo metadata, but
  this environment has no `gh` binary and unauthenticated GitHub API calls to
  private Dependabot alerts return 401. Inspect the alert in GitHub web UI or
  with an authenticated token before changing dependencies.
- **Verification:** `E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
  -> 6 passed; `pytest -q` -> 140 passed; `node --check static/app.js`;
  `node --check static/i18n.js`; `PYTHONPYCACHEPREFIX=/tmp/fleetflow-pycache
  .venv/bin/python -m py_compile e2e/test_browser_smoke.py tests/test_schema_contracts.py`.

### 2026-04-20 - Phase 10.1 route/schema guardrails

- **Route registry guard:** new `tests/test_schema_contracts.py` asserts every
  FastAPI `(method, path)` pair is unique, so accidental duplicate decorators
  fail fast.
- **Bootstrap schema guard:** SQLite bootstrap SQL executes cleanly against an
  empty in-memory DB and required operational tables are present.
- **Schema parity guard:** SQLite and PostgreSQL bootstrap table/column
  contracts are compared so dual-DB drift is caught before production.
- **Migration guard:** Alembic is asserted to have the single expected head
  revision `20260420_0009`.
- **Alembic hygiene:** `alembic.ini` now sets `path_separator = os`, removing
  the config deprecation warning from the new guard test.
- **Verification:** `pytest tests/test_schema_contracts.py -q` -> 5 passed;
  `pytest -q` -> 140 passed.

### 2026-04-20 - Codebase analysis and future-development handoff

- **Full roadmap audit:** `ROADMAP.md` now has a 2026-04-20 codebase analysis
  section with architecture strengths, current production risks and updated
  next recommended slices.
- **Tactical handoff expanded:** this document now records actual code sizes,
  module risks, schema parity risk, GitHub alert follow-up, role-specific e2e
  gaps and a new Phase 10 for production hardening/codebase shape.
- **Important correction:** the current `POST /reservations/{reservation_id}/cancel`
  route was rechecked and is registered once. Future protection should be an
  automated route-registry uniqueness test, not an assumed bug fix.
- **Next implementation priority:** Phase 10.1 route/schema guardrails, then
  GitHub Actions/Dependabot confirmation, then role-specific Playwright flows.
- **Verification:** documentation-only change; run `git diff --check` before
  commit/push.

### 2026-04-20 - UI/UX compliance audit and first accessibility guardrails

- **Phase 8.1 started:** `docs/UI_UX_COMPLIANCE_AUDIT.md` is now a real
  handoff artifact with surface inventory, status legend, contrast matrix,
  current findings, PR checklist and "do not merge if" rules.
- **Phase 8.2 started:** `tests/test_design_tokens.py` checks solid light/dark
  foreground token pairs against WCAG AA. The light warning token was darkened
  to `#8a5200` so warning text passes 4.5:1 on the light page background.
- **Phase 8.4 first fixes:** Notification lists are polite live regions,
  dialog helpers restore focus to the triggering element, admin calendar
  previous/next glyph buttons have accessible names and field validation errors
  now set `aria-describedby`. Follow-up commit extended dialogs with modal
  name/description/error semantics and made the mobile bottom rail safe-area
  aware for iOS-style home indicator layouts. Message alerts now use
  theme-aware classes instead of inline light-theme colors.
- **Phase 8.5 started:** Single and bulk reject dialogs require a concrete
  reason, focus the textarea on empty submit, expose `aria-invalid` and use
  Bulgarian inline copy instead of a silent generic fallback. Cancel dialogs
  now require a reason and persist it to reservation audit history. The shared
  dialog validation path targets the exact invalid field rather than always
  marking the first control.
- **Phase 9.1 started:** Summary deck now acts as an intent-driven next-action
  layer with one primary action per mode: book now, view current trip, review
  pending admin work, view active trips or inspect fleet state. Status bar now
  reports free cars instead of merely active cars.
- **Phase 9.2 started:** Employee desk now promotes the active or next
  approved reservation into a Current Trip Hero with one primary view action,
  moving the most important trip out of the table without giving employee
  start/return transition control.
- **Phase 9.3 started:** Admin surface now promotes the top 3 pending
  decisions into a Decision Rail before the table, with direct approve/reject
  actions and a bulk approve path for the whole pending queue.
- **Phase 9.4 started:** Admin surface now includes Fleet Pulse and optional
  NetFleet live GPS coordinates via Admin UI DB setting or runtime env.
  Employee free-mode booking now has one-tap quick-booking through the same
  conflict and blackout guardrails as manual reservations, plus smart prefill
  for the user's usual car/hour/duration.
- **Phase 9.5 started:** Reservation surfaces now render timeline-first
  lifecycle cards before the table. Fleet Pulse GPS copy now reports `X/Y`
  active FleetFlow cars with a NetFleet position, so admins do not see raw
  NetFleet event counts such as `63`.
- **Phase 8.7 started:** Optional Playwright browser smoke now lives in
  `e2e/test_browser_smoke.py`. It starts a fresh app server, verifies employee
  one-tap booking, timeline-first cards, Admin Decision Rail, Fleet Pulse copy
  and mobile calendar, and writes `employee-desktop.png`, `admin-desktop.png`
  and `employee-mobile.png` under `test-results/e2e`.
- **UX hierarchy / production prep started:** Employee requests now render
  before calendar, new request before inbox, guidance cards hide after login,
  start/return are admin-only in API and UI, and `make prod-check` validates
  live `.env` readiness without starting containers.
- **Production readiness expanded:** `production_readiness.py` now shares the
  same blocker logic between `make prod-check` and admin-only `/ops/readiness`.
  `/health/ready` provides a DB-backed probe for deployment checks, the Admin
  UI shows a secret-safe "Готовност за live" panel, and
  `docs/PRODUCTION_USER_GUIDE.md` gives operators the first-use checklist.
  PostgreSQL is now major-pinned in compose so `latest` cannot silently advance
  a persistent volume from v16 to an incompatible major version.
- **Backup posture started:** `make prod-backup` creates an ignored
  custom-format PostgreSQL dump, and `make prod-restore-drill BACKUP=...`
  validates that dump in isolated Docker project `fleetflow_restore_drill`
  without touching the production volume. First real drill passed against the
  active smoke stack using `/tmp/fleetflow-backups/fleetflow-20260420T075807Z.dump`.
- **User contact field:** Admin-created users now support optional
  `gsm_number` across SQLite/PostgreSQL schema, Alembic revision
  `20260420_0007`, API responses and the admin user card.
- **Phase 7.4 completed:** Production access logs are structured JSON by
  default (`LOG_FORMAT=auto`) with request id, method, path, route, status,
  latency and app env; dev keeps text logs. `fleetflow.access` writes a single
  stdout JSON line per request in production without propagating duplicate
  logger output.
- **Calm default started:** Read notifications are hidden from the visible
  inbox and employee reservations default to `Текущи`, hiding returned,
  rejected and cancelled records until the user explicitly chooses a history
  filter.
- **Fleet Intelligence Seed shipped:** `fleet_intelligence/` provides inline
  metrics/rules/service scoring; `/reservations/suggest-best-car` exposes
  explainable best-car suggestions; quick-book records `car_assignments`;
  `/admin/intelligence/pulse` feeds compact admin insights; the quick-book
  button now wraps inside its card instead of overflowing on narrow layouts.
- **Pre-login overview shipped:** `/public/overview` returns only aggregate
  counts for active cars, pending approvals, active trips and free cars; the
  hero status bar uses those values before login.
- **Verification:** `pytest -q` passes with 135 tests,
  `pytest tests/test_ui_compliance.py -q` passes with 31 tests, Playwright
  browser smoke passes with 1 test and screenshots, `make audit-prod` reports
  no known vulnerabilities for pinned runtime dependencies, direct
  `pip-audit -r requirements.txt` reports no known vulnerabilities when the
  resolver completes, `docker scout cves fleetflow_prod_smoke-car-pool:latest`
  reports 0 vulnerable packages, `make release-check` passes, JS syntax checks
  and Python compile check pass.
  `make prod-check` fails fast when `.env` is missing in a clean
  checkout. Old `fleetflow_test` containers were removed, Docker stack was
  rebuilt with pinned `postgres:16`, `/health` and `/health/ready` on `8001`
  return ok/ready and the app container is healthy. Backup creation and
  isolated restore drill were executed successfully. PostgreSQL smoke is on
  Alembic revision `20260420_0009`.

### 2026-04-19 - Phase 3.1 refresh-token rotation + logout invalidation

- **Refresh-token schema:** `refresh_tokens` now exists in both SQLite and
  PostgreSQL runtime schema plus Alembic revision `20260419_0005`. Stored
  values are SHA-256 hashes only, with issued/expires/revoked timestamps,
  user-agent and IP metadata.
- **Auth endpoints:** `POST /auth/login` still returns the short-lived bearer
  access token, and now also sets `fleetflow_refresh` as an HttpOnly,
  SameSite=Strict cookie. `POST /auth/refresh` rotates the refresh token and
  returns a fresh access token. `POST /auth/logout` revokes the current refresh
  hash and clears the cookie.
- **Replay protection:** Reusing an already rotated/expired refresh token
  returns 401 and revokes remaining active refresh tokens for that user, so a
  stolen old cookie cannot keep a session chain alive.
- **Frontend session recovery:** `apiFetch()` retries one time after a 401 by
  calling `/auth/refresh`; failed refresh clears local auth state and returns
  the user to login. Logout now also calls `/auth/logout` before local cleanup.
- **Docs:** `README.md`, `ROADMAP.md` and this tactical handoff now describe
  the production setup, refresh-token lifecycle and next recommended slices.
- **Verification:** `tests/test_auth_refresh.py` covers login cookie issuance,
  refresh rotation, replay invalidation and logout invalidation. `pytest -q`
  passes with 72 tests, plus JS syntax, dependency audit, Docker rebuild and
  PostgreSQL migration smoke on the live test stack.

### 2026-04-19 - Phase 2 UI completion + production docs refresh

- **2.4 Bulk approve/reject UI:** `/admin` reservation table now exposes a
  pending-only checkbox column, "select all pending" control and a live
  bulk-action bar. Approve/reject uses the existing batch endpoints, sends one
  request per batch and surfaces partial failures by reservation id.
- **2.2 Loading skeletons + submit states:** Main data sections render shimmer
  skeletons while loading; form submit buttons disable and switch to a busy
  label until the request completes or fails.
- **2.1 Mobile calendar:** Below 768 px the calendar switches from a dense
  month grid to a single-day card with previous/next controls and a "book this
  day" action that preserves the date prefill behavior.
- **Production setup docs:** `README.md` now documents the simplified
  `make setup && make prod` flow, generated `SECRET_KEY` /
  `POSTGRES_PASSWORD`, consistent `DATABASE_URL`, the only required live edit
  (`CORS_ALLOW_ORIGINS`) and one-shot bootstrap token handling.
- **Container hygiene:** Old compose projects were stopped and removed; the
  active test stack is `fleetflow_test` on `APP_PORT=8001`.
- **Verification:** `pytest` (`69 passed`), JS syntax checks, `pip-audit`,
  `git diff --check`, Docker compose rebuild and `/health` smoke.

### 2026-04-18 - Security review fixes

- **Shipped:** Signed-token verification now rebinds to current DB user state,
  so deactivated or demoted users do not keep stale privileges until token
  expiry.
- **Shipped:** Reservation creation rejects past `start_time`, not only past
  `end_time`.
- **Verification:** Covered by `pytest`.

### 2026-04-18 - Initial product hardening and production path

- **Shipped:** Dockerized FastAPI app, PostgreSQL-ready configuration,
  Alembic baseline, real auth/user management, role-aware lifecycle start/return,
  notifications, outbound SMTP/Slack/Teams hooks, service/maintenance blackout
  windows and separate `/admin` surface.
- **Verification:** Manual Docker smoke and growing FastAPI TestClient suite.

### 2026-04-18 - Phase 1 UI quick wins (`8f8648a`)

- **Shipped:** Bulgarian i18n helper, visible focus styling and confirmation
  dialogs for destructive actions.
- **Verification:** `pytest` and manual UI smoke.

### 2026-04-18 - Notifications and admin defaults (`8834312`)

- **Shipped:** Admin defaults to pending queue, unread notification badge and
  notification polling with logout cleanup.
- **Verification:** `pytest` and manual two-session smoke.

### 2026-04-18 - CORS configuration (`b9dd216`)

- **Shipped:** Explicit environment-driven CORS handling with safe dev/prod
  defaults and preflight coverage.
- **Verification:** `pytest` CORS preflight test.

### 2026-04-18 - Dev seed accounts and auth rate limiting (`a91ab3e`)

- **Shipped:** Dev-only deterministic seed accounts/cars, Docker runtime module
  fix and in-memory rate limiting for login/bootstrap endpoints.
- **Verification:** `pytest` (`19 passed` at shipment), Docker healthcheck and
  login smoke for `admin`, `ivan`, `maria`.

### 2026-04-19 - Live reservation conflict preview (`dd78b3a`)

- **Shipped:** `GET /reservations/conflicts`, frontend debounced booking
  preview, calendar conflict outline and regression tests for reservation and
  blackout conflicts.
- **Verification:** `pytest` (`21 passed` at shipment), `node --check`,
  `git diff --check`, Docker healthcheck and endpoint smoke.

### 2026-04-19 - Admin user controls and audit history (`82ff34e`)

- **Shipped:** Admin password reset, admin role change, user action audit API
  and admin UI actions/timeline for user cards.
- **Shipped:** Stale tokens re-read current role state, so promotions/demotions
  apply immediately to existing sessions.
- **Verification:** `pytest` (`24 passed` at shipment), Python/JS syntax checks,
  `git diff --check`, Docker healthcheck and admin reset/audit endpoint smoke.

### 2026-04-19 - Dedicated employee/admin surfaces (`0a5a57f`)

- **Shipped:** Removed duplicated admin creation/user-management controls from
  the employee desk and made admin-only panels in `/admin` hidden by default
  until auth/role gating runs.
- **Verification:** `pytest` (`24 passed` at shipment), `node --check`,
  `git diff --check`, Docker healthcheck and HTML smoke for `/` + `/admin`.

### 2026-04-19 - CI quality gates and initial Docker base remediation (`0503e95`)

- **Shipped:** Replaced the placeholder GitHub Actions workflow with
  production quality gates for Python compile, `pytest`, JS syntax,
  `pip-audit` and Docker image build on the Python 3.14 lane.
- **Shipped:** Corrected the unavailable `uvicorn[standard]==0.44.0` pin to
  `0.39.0` and made the first Docker base-image remediation pass. The Alpine
  runtime from this commit was later superseded by the zero-CVE Chainguard
  runtime in `ab1a0f2`.
- **Verification:** `pip-audit -r requirements.txt` clean, `pytest`
  (`24 passed`), `node --check`, `git diff --check`, Docker no-cache build and
  container `/health` smoke with healthy status.

### 2026-04-19 - Zero-CVE Chainguard runtime and PostgreSQL smoke (`ab1a0f2`, `0076814`, `a71121d`)

- **Shipped:** Moved both Dockerfile stages to Chainguard Python images:
  `latest-dev` for dependency installation and `latest` for the final runtime.
  The runtime has no shell/pip and keeps the app on stable non-root UID
  `10001`.
- **Shipped:** Added a Python container entrypoint for optional Alembic
  migrations, normalized Alembic PostgreSQL URLs to the `psycopg` v3 SQLAlchemy
  dialect and removed fixed compose container names for isolated smoke stacks.
- **Shipped:** Moved PostgreSQL compose to `cgr.dev/chainguard/postgres:latest`
  after verifying the image reports `0C/0H/0M/0L`. This is a fresh-deploy
  production default; existing PostgreSQL 16 volumes need a deliberate major
  version migration plan before reuse.
- **Verification:** Docker Scout on the builder image and built app image
  reports `0C/0H/0M/0L`; Docker Scout on the PostgreSQL service image reports
  `0C/0H/0M/0L`; `pip-audit -r requirements.txt` clean, `pytest` (`24
  passed`), Python/JS syntax checks, Docker dev `/health`, PostgreSQL compose
  `/health` and `alembic_version=20260418_0002` in a clean temporary stack.

### 2026-04-19 - Request IDs and browser security headers (`2a3c30f`)

- **Shipped:** Added HTTP middleware that accepts or generates `X-Request-ID`,
  stores it on `request.state` and returns it on responses.
- **Shipped:** Added baseline security headers:
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and
  `Permissions-Policy`.
- **Verification:** `pytest` (`25 passed`), Python syntax checks, JS syntax
  checks, `git diff --check` and Docker `/health` smoke confirming the request
  ID and `nosniff` header.

### 2026-04-19 - Async notification dispatch + pre-commit hooks + rate-limit tests

- **Phase 3.2 — async notification dispatch:** Every call to
  `dispatch_outbound_notifications` in `routers/reservations.py` and
  `routers/users.py` moved off the request thread via FastAPI
  `BackgroundTasks`. The in-app notification write stays inside the
  transaction (inbox consistency); only the SMTP / Slack / Teams fan-out
  runs after the response is sent. Handlers now declare
  `background_tasks: BackgroundTasks` as a non-defaulted parameter. SMTP
  timeouts no longer block API latency.
- **Phase 5.6 — pre-commit hooks:** `.pre-commit-config.yaml` (new),
  `pyproject.toml` (new), `requirements-dev.txt`. Hooks: `ruff --fix`,
  `ruff-format`, `prettier` (JS/CSS/HTML/MD/YAML), trailing whitespace,
  end-of-file fixer, 500 KB large-file guard, merge-conflict check, LF
  line endings. `pyproject.toml` pins the ruff config (line length 110,
  standard rule set, `B008` ignore for `Depends(...)`). Developer install:
  `pip install -r requirements-dev.txt && pre-commit install`.
- **Rate-limit test coverage:** New `tests/test_rate_limit.py` with three
  cases (login 429, bootstrap 429, `limiter.reset()` recovery) using the
  existing `InMemoryRateLimiter` + `RateLimitRule` API with tightened
  env-var windows per test.
- **Verification:** `pytest -q` → 27 passed (24 from origin/master + 3
  new rate-limit cases). No new runtime dependencies; new dev-only
  deps: `pre-commit`, `ruff`.

### 2026-04-19 - Token hardening + admin invariant coverage + CSV export

- **Phase 3.5 — harden signed-token format:** `security.py` gains a minimum
  32-byte `SECRET_KEY` guard that fires at import time in non-dev
  environments, so a misconfigured prod deploy fails fast instead of silently
  signing weak tokens. Every issued token now carries `iat` (issued-at) and a
  random 12-byte `jti` reserved for a future revocation list once Phase 3.1
  (refresh tokens) lands. `verify_token` rejects tokens whose `iat` is more
  than 60 s in the future (small clock-skew tolerance) as defence against
  backdated forgeries. Signature comparison continues to use
  `hmac.compare_digest` — covered explicitly by a regression test.
- **Phase 3.4 — at-least-one-active-admin invariant:** The guard is already
  in place in `routers/users.py` (both `deactivate_user` and
  `change_user_role` call `_active_admin_count`), but lacked dedicated tests.
  Added `tests/test_admin_invariant.py` with five cases pinning the
  behaviour — last admin can't be deactivated, can't be demoted, demotion
  succeeds when a second admin exists, a second admin can deactivate the
  first, and an *inactive* admin doesn't count toward the invariant.
- **Phase 5.2 — CSV export of reservations:** New admin-only endpoint
  `GET /reservations/export.csv` in `routers/reservations.py`. Streams via
  `fastapi.responses.StreamingResponse` with a UTF-8 BOM prefix so Excel
  opens Cyrillic correctly, supports `car_id` / `status_filter` / `start` /
  `end` query filters, joins car plates into the output. Tests cover the
  auth boundary (401 unauth, 403 employee), BOM + header shape + Bulgarian
  round-trip, and both filters.
- **Verification:** `pytest -q` → 44 passed (27 prior + 7 token + 5 admin
  invariant + 5 CSV export). No new runtime dependencies.

### 2026-04-19 - UI/UX overhaul — design system, dark mode, a11y, motion

- **Design tokens refresh:** `static/styles.css` rewritten around a single
  source of truth: 4px spacing scale (`--sp-1`..`--sp-9`), a 50→900 brand ramp,
  semantic colour roles with soft/border variants for every status, five
  elevation levels (`--shadow-xs`..`--shadow-xl`), and motion tokens
  (`--ease-out`, `--ease-spring`, duration-fast/base/slow) so every transition
  feels consistent. All component CSS consumes tokens, not hard-coded hex.
- **Dark mode done right:** Full token redefinition under both
  `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` (honours
  OS preference) and `:root[data-theme="dark"]` (manual override). No-FOUC
  bootstrap inline `<script>` in `<head>` reads `localStorage` before the
  stylesheet is parsed, so the correct theme paints on first frame.
  `static/theme.js` (new, self-contained IIFE) handles the toggle button,
  a `⌘/Ctrl+Shift+L` keyboard shortcut, cross-tab `storage` event sync, and
  updates `aria-pressed` on state change. `<meta name="theme-color">` pairs
  per colour-scheme repaint the browser chrome.
- **Accessibility:** Added a "skip to content" link on both surfaces
  (`index.html` → `#calendarStudio`, `admin.html` → `#reservationsDeck`),
  positioned -48px off-screen and snapping in on focus. Every interactive
  element routes through a unified `:focus-visible` ring (4px brand-soft halo)
  so keyboard users always see where they are. `prefers-reduced-motion` zeroes
  out the animation layer entirely.
- **Mobile responsive:** At ≤760px, reservation/user tables collapse into
  stacked cards via `data-label` pseudo-elements on each `<td>`, so the same
  markup works in both layouts without JS branching. Stat grids, hero, and
  calendar re-flow with CSS grid `auto-fit`.
- **Micro-interactions:** Stat cards lift on hover with a gradient top-border
  reveal; nav links get an underline-reveal; form fields shake on validation
  error; newly inserted list items slide in; loading states use a shimmer
  animation; dialogs scale-and-fade. The theme toggle button rotates -12° and
  swaps sun/moon SVGs on press.
- **Templates:** `templates/index.html` and `templates/admin.html` gained the
  theme-color metas, description meta, no-FOUC bootstrap, deferred
  `theme.js`, skip link, and theme-toggle button in `.topbar__actions`. All
  existing IDs that `app.js` queries (`notificationBadge`, `calendarStudio`,
  `reservationsDeck`, `userCreatePanel`, `usersDeck`, etc.) are preserved —
  the rewrite is additive at the template layer.
- **Print:** New print stylesheet hides chrome (topbar, buttons, dialogs) and
  keeps data-dense cards readable on paper.
- **Verification:** `pytest -q` → 44 passed (HTML-string assertions in
  `test_health_and_ui` still match; no route or template-ID regressions).
  Smoke-tested by diff review; no `app.js` class selector was dropped.

### 2026-04-19 - Production bootstrap-admin gate + bulk approve/reject

- **Phase 3.3 — harden admin bootstrap:** New `bootstrap_tokens.py` module
  generates a random, URL-safe, 32-byte one-shot token at service startup
  **only when** `APP_ENV != "dev"` and no admin yet exists. The plaintext is
  logged to stdout exactly once (warning level, bannered) so ops can grab it
  from the deploy logs; only the sha256 digest lives in process memory with
  a 30-minute TTL. `POST /auth/bootstrap-admin` now requires an
  `X-Bootstrap-Token` header in non-dev environments — invalid, expired, or
  already-used tokens get a 403 with a Bulgarian-friendly detail. Dev stays
  permissive so the local smoke flow (`pytest`, Docker compose) is unchanged.
  After a successful bootstrap the token record is explicitly cleared, so a
  race between two in-flight requests can't both win.
  - New tests (`tests/test_bootstrap_token.py`, 5 cases): prod-no-header → 403,
    prod-wrong-token → 403, prod-correct-token → 201 + second call fails,
    expired token → 403, dev stays permissive without the header.
- **Phase 2.4 — bulk approve/reject pending reservations:** New admin-only
  endpoints `POST /reservations/bulk-approve` and `POST /reservations/bulk-reject`
  accept `{ ids: [int], reason?: str }` and process every id inside a single
  transaction. Partial failures (not-found, already-decided) don't abort the
  batch — each result surfaces as `{ id, status: "approved"|"rejected"|"skipped", error? }`
  so the admin UI can show "3 approved, 2 skipped" without an extra round-trip.
  Outbound notification fan-out runs once after the response is sent, via
  BackgroundTasks, regardless of batch size. Duplicate ids in the request are
  collapsed; empty `ids` is a 422.
  - New schemas (`schemas.py`): `BulkDecisionPayload`, `BulkDecisionItem`,
    `BulkDecisionResponse`.
  - New tests (`tests/test_bulk_decisions.py`, 6 cases): 403 for non-admin,
    all-succeed, mixed with already-decided (skipped + error code), missing
    ids (not_found), dedup, empty-ids validator.
- **Verification:** `pytest -q` → 55 passed (44 prior + 5 bootstrap-token +
  6 bulk-decide). No new runtime dependencies. Routes verified via live
  inspection (`/reservations/bulk-approve` registered, no collision with the
  single-id `/{id}/approve` route).

### 2026-04-19 — Phase 1 UX & feature improvements (commit `302484a`)

Five independent improvements shipped as one coherent commit:

- **Цветни KPI карти:** `stats-grid--3` grid with `.stat-card--urgent` (amber),
  `.stat-card--active-trips` (blue) and `.stat-card--available` (green) semantic
  colour classes. KPI cards `kpiPending`, `kpiActive`, `kpiAvailable` appear on
  both `index.html` and `admin.html`. `updateOverview()` in `app.js` toggles the
  correct modifier class on each card.
- **Следващ свободен слот:** When `renderConflictPreview()` detects at least one
  conflict it computes a next-available window starting from `end_time` and renders
  a `.conflict-suggestion` strip with an "Използвай" button wired via
  `[data-apply-slot]` event delegation. One-click populates `#startTime` /
  `#endTime` in the booking form.
- **Одобрено/Отказано от:** `list_reservations` in `routers/reservations.py` now
  LEFT-JOINs `users AS decider` and returns `decided_by_name`. `reservationContext()`
  in `app.js` surfaces it with `t("reservation.decidedBy")` /
  `t("reservation.rejectedBy")` labels. New i18n keys added to `static/i18n.js`.
- **Причина за отказ:** The reject lifecycle action in `reservationAction()` now
  opens the existing `userDialog` with a `<textarea>` for the rejection reason
  instead of a bare `window.confirm`. The reason is forwarded in the request body
  to `POST /reservations/{id}/reject`.
- **Имейл на потребител:** Full-stack: Alembic migration
  `alembic/versions/20260419_0003_user_email.py`, `_ensure_column` in `db.py`,
  `UserCreatePayload.email` and `UserResponse.email` in `schemas.py`, all SELECT /
  INSERT queries updated in `routers/users.py`, `#newEmail` input in the admin
  create-user form, displayed in user cards.

**Files changed (10):** `alembic/versions/20260419_0003_user_email.py` (new),
`db.py`, `routers/reservations.py`, `routers/users.py`, `schemas.py`,
`static/app.js`, `static/i18n.js`, `static/styles.css`, `templates/admin.html`,
`templates/index.html`.

**Verification:** `pytest -q` → 58 passed (no regressions). `node --check` clean.

### 2026-04-19 — Items 2.10–2.12: blackout edit, car notes, test notification (commit `16443ad`)

- **2.10 Blackout edit:** `PUT /cars/{car_id}/blackouts/{blackout_id}` (admin-only).
  Validates `end > start`, excludes self from overlap check (returns 409 on conflict,
  404 if inactive/missing). `BlackoutUpdatePayload` schema mirrors `CarBlackoutCreate`.
  Admin UI: each blackout card gains an „Редактирай" button that opens
  `editBlackoutDialog()` — a `userDialog` variant pre-filled with current values
  (kind select, start/end datetime-local, reason textarea). On confirm issues a `PUT`
  and refreshes. 4 tests: happy path, overlap 409, employee 403, invalid window 400.

- **2.11 Car notes:** Alembic migration `20260419_0004_car_notes` adds `notes TEXT`
  to `cars`. `_ensure_column` in `db.py` for runtime upgrade on existing DBs.
  `CarNotesPayload` schema + `PUT /cars/{car_id}/notes` endpoint (admin-only).
  Admin car card: inline `<textarea class="notes-textarea">` + „Запази бележки"
  button — `saveCarNotes()` issues the PUT and updates `state.cars` in place without
  a full reload. Employee car card: renders `.car-note-hint` (amber italic) when
  `car.notes` is non-empty; renders nothing when null. CSS: `.car-card__notes`,
  `.notes-textarea`, `.action-btn--notes`, `.car-note-hint`.
  3 tests: save+retrieve (verified via list_cars), clear to null, employee 403.

- **2.12 Test notification:** `notifications_service.test_dispatch(notification_id)`
  runs per-channel dispatch synchronously and returns
  `[{name, status, error?}]` — `"sent"`, `"failed"`, or `"not_configured"`.
  Failures are logged to `notification_deliveries`. `POST /notifications/test`
  (admin-only) creates an in-app notification then calls `test_dispatch`; returns
  `{notification_id, channels}`. Admin Notifications header: „Тест" chip button
  → `sendTestNotification()` shows a toast with per-channel status lines.
  3 tests: in-app created + visible in inbox, employee 403, unauthenticated 401.

**Files changed (11):** `alembic/versions/20260419_0004_car_notes.py` (new),
`db.py`, `notifications_service.py`, `routers/cars.py`, `routers/notifications.py`,
`schemas.py`, `static/app.js`, `static/i18n.js`, `static/styles.css`,
`templates/admin.html`, `tests/test_app.py`.

**Verification:** `pytest -q` → 68 passed (58 prior + 10 new). Python syntax clean.

---

_Last updated: 2026-04-20. When you ship an item, move it to this `## Done`
section with the commit or PR link._
