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

## 1. Repository map (as of 2026-04-18)

```text
app.py                       FastAPI factory, router mounting, /, /admin, /health
config.py                    12-factor settings (APP_ENV, SECRET_KEY, DATABASE_URL, ...)
db.py                        SQLite + PostgreSQL adapters, schema bootstrap
security.py                  HMAC token sign/verify, PBKDF2 hash, auth deps
schemas.py                   Pydantic request/response models
notifications_service.py     In-app + SMTP/Slack/Teams dispatch
routers/
  auth.py                    setup-status, bootstrap-admin, login, /auth/me
  cars.py                    fleet CRUD + blackout windows
  reservations.py            full lifecycle state machine
  users.py                   user CRUD + password change + admin handoff
  notifications.py           user inbox
templates/
  index.html                 employee surface
  admin.html                 admin surface
static/
  app.js                     ~1400-line SPA logic
  styles.css                 ~900-line stylesheet
alembic/                     migration scripts
tests/test_app.py            ~50 cases, FastAPI TestClient
```

> ⚠️ The prior UI audit referenced `static/index.html`. The correct path is
> `templates/index.html` (FastAPI serves via Jinja). Similarly `static/admin.html`
> -> `templates/admin.html`. When this doc cites line numbers from the audit,
> re-open the file and grep for the referenced selector/string rather than
> trusting the line number.

---

## Phase 1 - Quick wins (<= 1 week total)

Low-risk, small-surface improvements that noticeably raise the baseline.

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

## Phase 2 - UX high-impact (1-2 weeks)

Deeper UX work; pays off every day the product is used.

### 2.1 Mobile calendar - collapse to list/day view below 768 px

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

### 2.2 Loading skeletons + submit-button states

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

### 2.4 Bulk approve/reject in the admin pending queue

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

---

## Phase 3 - Security & hardening (1 week)

Must land before any external-facing deployment.

### 3.1 Refresh token flow

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
  - No file > 300 lines.
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

- **Files:** new `e2e/` directory, CI workflow
- **Approach:**
  1. `playwright` with the Python API (matches the stack).
  2. Three scenarios to start:
     - Employee: bootstrap -> login -> request car -> wait for approval.
     - Admin: login -> approve pending -> verify in employee inbox.
     - Admin: create blackout -> verify overlapping reservation rejected.
  3. Runs in CI against a real server + SQLite DB fresh per test.
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

## Phase 6 - Serious admin module

This phase turns the current admin surface into a proper operational control
center. Some baseline pieces already exist (`/admin`, user CRUD, admin handoff,
blackout windows), but the next wave should make user administration explicit,
auditable and safe enough for real company operations.

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

## Cross-cutting concerns (apply to every item)

- **No new dependencies** without listing them in the PR description with
  size + license + alternatives considered.
- **Bulgarian is the default locale.** If you add any copy, add it to
  `static/i18n.js` (item 1.2) - don't inline English.
- **Every user-visible change needs a screenshot** in the PR (mobile + desktop
  for UI work).
- **Every DB change needs an Alembic revision.** Never hand-edit the schema
  in `db.py` without a matching `alembic revision --autogenerate` +
  human review of the generated script.
- **Every new endpoint needs** `pytest` coverage that includes an
  authorization negative test (unauth + wrong-role).
- **Respect the existing dual-DB abstraction.** If you write SQL, it must
  work on both SQLite and PostgreSQL. Check `db.py` for the placeholder
  style and parameter adaptation helpers.

---

## Suggested sequencing (TL;DR)

1. **Phase 1** (quick wins) - land in a single week.
2. **Phase 3.1 + 3.2 + 3.3** (refresh tokens, async notifications, bootstrap
   hardening) in parallel with **Phase 2.1 + 2.2** (mobile calendar, loading
   states). These are independent and unblock everything else.
3. **Phase 2.3 + 2.4 + 2.5 + 2.6** (conflict preview, bulk approve, default
   filter, auto-refresh) - the daily-productivity wave.
4. **Phase 6.1 + 6.2 + 6.3 + 6.4** (serious admin module) once the daily
   booking flow is stable.
5. **Phase 3.4 + 3.5** (admin invariant, token audit) before any
   external-customer rollout.
6. **Phase 4** - paying down debt once user-facing wins ship.
7. **Phase 5** - opportunistic, user-demand-driven.

---

## Done

### 2026-04-18 - Security review fixes

- **Shipped:** Signed-token verification now rebinds to current DB user state,
  so deactivated or demoted users do not keep stale privileges until token
  expiry.
- **Shipped:** Reservation creation rejects past `start_time`, not only past
  `end_time`.
- **Verification:** Covered by `pytest`.

### 2026-04-18 - Initial product hardening and production path

- **Shipped:** Dockerized FastAPI app, PostgreSQL-ready configuration,
  Alembic baseline, real auth/user management, lifecycle start/return,
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

_Last updated: 2026-04-19. When you ship an item, move it to this `## Done`
section with the commit or PR link._
