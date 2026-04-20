# FleetFlow UI/UX Compliance Audit

Internal conformance target for Apple HIG, NASA WDS/508, USWDS, WCAG 2.2,
WAI-ARIA APG and NN/g heuristics. This is not a legal certification.

## How To Use

1. Pick one surface from the inventory.
2. Re-open the referenced files; line numbers may drift.
3. Verify desktop 1440 px, tablet 768 px and phone 390 px.
4. Record evidence: screenshots, keyboard path, contrast pairs, ARIA/focus
   notes and test command.
5. If a row is `needs fix`, link the fix to `ROADMAP_IMPROVEMENTS.md` Phase 8.
6. For browser evidence, run `E2E_ARTIFACT_DIR=test-results/e2e make test-e2e`
   after installing Playwright Chromium.

## Reference Baseline

- Apple Layout: https://developer.apple.com/design/human-interface-guidelines/layout
- Apple Buttons: https://developer.apple.com/design/human-interface-guidelines/buttons
- Apple Accessibility: https://developer.apple.com/design/human-interface-guidelines/accessibility
- Apple Typography: https://developer.apple.com/design/human-interface-guidelines/typography
- NASA WDS Colors: https://nasa.github.io/nasawds-site/components/colors/
- USWDS Accessibility: https://designsystem.digital.gov/documentation/accessibility/
- W3C WCAG: https://www.w3.org/WAI/standards-guidelines/wcag/
- WAI-ARIA APG: https://www.w3.org/WAI/ARIA/apg/patterns/
- NN/g Heuristics: https://www.nngroup.com/articles/ten-usability-heuristics/

## Status Legend

- `pass`: verified with evidence in this document.
- `needs evidence`: likely acceptable, but not proven with screenshots/tests.
- `needs fix`: known gap or high-risk area.
- `not applicable`: guideline does not apply to the surface.

## Surface Inventory

| Surface | Files | Status | Required Checks | Next Agent Action |
| --- | --- | --- | --- | --- |
| Login/setup | `templates/index.html`, `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Apple buttons, WCAG labels/errors, bootstrap token copy, keyboard submit | Verify labels, focus order, error recovery and 390 px layout. Field errors are now wired with `aria-invalid` + `aria-describedby`. |
| Intent summary / next action | `templates/index.html`, `templates/admin.html`, `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | One primary action, clear next step, keyboard focus, 44 px targets | Summary deck now renders contextual next-action buttons for employee/admin modes. Capture desktop/mobile screenshots and verify no surface exposes competing primary actions. |
| Current trip hero | `templates/index.html`, `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | One primary action, status text, keyboard focus, mobile fit | Active/next approved employee trip is promoted above calendar/table with one "view trip" action. Start/return are admin-only lifecycle transitions. Capture desktop/mobile screenshots and verify focus after action. |
| Status bar / fleet KPIs | `templates/index.html`, `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Live system status, text labels, no color-only meaning, 390 px fit | KPI strip now reports pending, active trips and free cars. Verify mobile wrapping and screen-reader order. |
| Fleet Pulse / NetFleet telemetry | `templates/admin.html`, `templates/index.html`, `static/app.js`, `static/i18n.js`, `static/styles.css`, `app_settings.py`, `routers/cars.py`, `netfleet_service.py` | needs evidence | No exposed API key, employee pickup authorization, text-backed GPS status, responsive strip, coordinates do not overwhelm decisions | Fleet Pulse now uses a global reservation snapshot and optional NetFleet GPS events by plate number. The pulse shows `X/Y` active FleetFlow cars with a last position instead of raw NetFleet event counts. Employee pickup location is limited to the user's own approved/active trip. Capture configured/unconfigured screenshots and verify no key appears in browser payloads. |
| Admin NetFleet key setup | `templates/admin.html`, `static/app.js`, `static/i18n.js`, `routers/cars.py`, `app_settings.py`, `schemas.py` | needs evidence | Password input, no current-secret echo, admin-only access, status text, explicit save feedback | Admin can add/change the key once from `/admin`; UI resets the input after save and only shows configured/source metadata. Capture keyboard path and configured/unconfigured screenshots. |
| One-tap booking | `templates/index.html`, `static/app.js`, `static/i18n.js`, `static/styles.css`, `routers/reservations.py`, `e2e/test_browser_smoke.py` | pass | One primary action, conflict/blackout-safe suggestion, no hidden destructive action, clear pending feedback | Browser smoke verifies employee quick booking and captures `employee-desktop.png`; add failure/conflict screenshots next. |
| Smart prefill | `templates/index.html`, `static/app.js`, `static/i18n.js`, `static/styles.css`, `routers/reservations.py`, `schemas.py` | needs evidence | User keeps review control, no invisible submit, useful defaults, manual form remains reachable | Preferences come from the user's last 10 reservations and fill car/start/end only after an explicit button press. Capture desktop/mobile screenshots and verify keyboard path. |
| Employee booking form | `templates/index.html`, `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | Apple layout, NN/g error prevention, WCAG form semantics, conflict preview status | New request is now before inbox in the side rail. Test invalid date range, conflict warning, preserved input after failure. `conflictPreview` already has `role=status` + `aria-live=polite`. |
| Calendar studio | `templates/index.html`, `static/app.js`, `static/styles.css`, `e2e/test_browser_smoke.py` | needs evidence | Responsive 390/768/1440, keyboard reachability, color+text statuses, role-aware operational visibility, no overlap | Mobile day mode is covered by `employee-mobile.png`; reception calendar now uses the global operational snapshot for approved/checked-out work instead of the current table filter. Still capture tablet/desktop month and keyboard day controls. |
| Reservation timeline/cards | `templates/index.html`, `templates/admin.html`, `static/app.js`, `static/i18n.js`, `static/styles.css`, `e2e/test_browser_smoke.py` | pass | Timeline before table, status text, lifecycle clarity, 44 px actions, table remains secondary, cancel recovery | Employee reservations now render before calendar; browser smoke asserts timeline cards appear before tables. Continue with admin lifecycle action screenshots. |
| Notifications | `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | `aria-live`, unread badge clarity, concise copy, no noisy motion | Notification lists are polite live regions and show only unread items by default; read items are hidden with a calm note. Verify polling update announcement with a screen reader. |
| Admin pending queue / decision rail | `templates/admin.html`, `static/app.js`, `static/i18n.js`, `static/styles.css`, `e2e/test_browser_smoke.py` | needs evidence | Top pending decisions first, bulk selection semantics, action bar visibility, partial-failure feedback, required reject reason | Desktop Decision Rail is covered by `admin-desktop.png`; still test keyboard checkbox selection, mobile and empty reject reason recovery. |
| Admin reception queue / reception rail | `templates/admin.html`, `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | Approved handoffs and active returns before table, role-separated start/return, direct 44 px actions, no dependency on current table filter | Reception Rail uses the global operational reservation snapshot and promotes approved/checked-out work above lifecycle cards/table. It stays as an empty state for `fleet_reception`, but hides for `fleet_admin` when there is no handoff work to avoid dashboard noise. Capture reception/admin screenshots and keyboard path next. |
| Admin users | `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Destructive confirmations, role-change clarity, audit timeline readability | Verify reset/deactivate/role dialog focus return and success/error copy. |
| Admin fleet/cars | `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Notes textarea labels, active/inactive text state, 44 px controls | Verify notes save path, employee visibility and mobile card spacing. |
| Blackout management | `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Dialog APG behavior, date validation, conflict errors, no overlap | Test create/edit/deactivate via keyboard and invalid dates. |
| Dialog system | `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | APG modal focus trap/return, ESC cancel, destructive role clarity, exact invalid-field recovery | Native `<dialog>` is used, ESC cancel exists, helper-level focus return is covered, dialogs expose modal name/description/error semantics, and validation can focus/mark the exact invalid field for reject/cancel/password/blackout flows. Manual screen-reader pass still needed. |
| Toast/message system | `static/app.js`, `static/styles.css` | needs evidence | Polite live region, non-color-only severity, visible long enough | `#message` uses `role=alert`, receives focus and now uses theme-aware alert classes instead of inline light-theme colors. Verify with screen reader and dark-mode screenshots. |
| Mobile bottom nav | `templates/index.html`, `templates/admin.html`, `static/styles.css` | needs evidence | 44 px targets, safe-area padding, no content occlusion | CSS sets `min-height: 44px` and accounts for `safe-area-inset-bottom`; screenshot 390 px bottom area and keyboard focus order still required. |
| Theme/dark mode | `static/theme.js`, `static/styles.css` | needs evidence | NASA/WCAG contrast matrix, focus ring visibility, reduced motion | Solid text/status token pairs now covered by `tests/test_design_tokens.py`; translucent surfaces still need browser-computed contrast evidence. |
| Production cutover | `Makefile`, `scripts/prod_check.py`, `production_readiness.py`, `routers/ops.py`, `docker-compose.postgres.yml`, `README.md`, `docs/PRODUCTION_USER_GUIDE.md` | pass | No demo seed, generated secrets, real CORS origin, matching DB URL, pinned PostgreSQL image, runtime env propagation, secret-safe admin readiness | `make prod-check` validates `.env` without starting containers; compose now pins PostgreSQL major version and passes CORS, refresh TTL, rate limits, DB password and notification settings to the app container. `/health/ready` checks DB reachability; `/ops/readiness` powers the Admin UI preflight panel without returning secret values. |
| Structured access logs | `app.py`, `config.py`, `logging_config.py`, `docker-compose.postgres.yml`, `README.md` | pass | Production JSON logs, request correlation, no secret values | Request middleware emits access logs with request id, method, path, route, status and latency. `LOG_FORMAT=auto` keeps dev text logs and production JSON logs; `fleetflow.access` writes one stdout JSON line per request. |
| Backup / restore drill | `Makefile`, `scripts/backup_postgres.sh`, `scripts/restore_postgres_drill.sh`, `docs/PRODUCTION_USER_GUIDE.md` | pass | Backup files outside git, custom PostgreSQL dump, restore test isolated from production volume | `make prod-backup` writes a `pg_dump --format=custom` file under ignored `backups/`; `make prod-restore-drill BACKUP=...` restores into project `fleetflow_restore_drill`, checks `alembic_version` and removes the temporary volume by default. |
| User contact fields | `templates/admin.html`, `static/app.js`, `static/i18n.js`, `schemas.py`, `routers/users.py`, `db.py`, `alembic/versions/20260420_0007_user_gsm_number.py` | pass | GSM is optional contact metadata, not auth; field has tel keyboard, max length guard and visible card text | Admin can enter optional GSM number when creating a user. API returns `gsm_number`, user cards show text-backed `GSM: ...`, and tests cover optional/too-long values. |
| Role-separated pool workflow | `security.py`, `routers/reservations.py`, `static/app.js`, `static/i18n.js`, `templates/admin.html`, `alembic/versions/20260420_0009_split_operational_roles.py` | pass | Least privilege, one primary task per role, no irrelevant control panels | `fleet_approver` can approve/reject but cannot start/return or manage users/settings. `fleet_reception` can start/return but cannot approve/reject or manage settings. `/admin` adapts copy, default filters and visible panels by role. |
| Fleet Intelligence Seed | `fleet_intelligence/`, `routers/reservations.py`, `routers/intelligence.py`, `static/app.js`, `static/styles.css`, `alembic/versions/20260420_0008_car_assignments.py` | pass | One primary booking action, explainable suggestions, no heavy BI surface | Quick-book uses best-car scoring and records assignment reason/score. Admin Fleet Pulse shows compact insights below the strip. Quick-book button is full-width/wrapping so text cannot overflow its card on narrow surfaces. |
| Pre-login operational overview | `app.py`, `static/app.js`, `templates/index.html`, `templates/admin.html` | pass | Informative first screen, public orientation without private operations | `/public/overview` powers pending/active/free counts before login. `/public/calendar` powers calendar occupancy with status, plate number and model. Requester, purpose, GPS, reservation ids and actions remain authenticated. |

## Contrast Matrix To Automate

First automated coverage exists in `tests/test_design_tokens.py`. It checks
solid light/dark text and status token pairs against WCAG AA. Browser-computed
checks are still needed for translucent surfaces, gradients and inline message
styles.

| Pair | Light Status | Dark Status | Required Ratio | Notes |
| --- | --- | --- | --- | --- |
| page background / primary text | pass | pass | 4.5:1 | Covered against `--bg-bottom`. |
| surface / primary text | needs evidence | needs evidence | 4.5:1 | Needs browser-computed check because surfaces are translucent. |
| muted text / page background | pass | pass | 4.5:1 preferred | Covered against `--bg-bottom`. |
| primary button / button text | pass | pass | 4.5:1 | White on `--brand` covered. |
| danger status / page background | pass | pass | 4.5:1 | Must include label/shape too. |
| warning status / page background | pass | pass | 4.5:1 | Light warning token darkened to `#8a5200`. |
| success status / page background | pass | pass | 4.5:1 | Must work for color-blind users. |
| focus ring / adjacent background | needs evidence | needs evidence | 3:1 | Needs screenshot/browser-computed check over translucent cards. |

## Current Findings

- `pass`: dialog helpers in `static/app.js` now capture the triggering element
  and restore focus after close; covered by `tests/test_ui_compliance.py`.
- `pass`: dialog helpers now expose `aria-modal`, `aria-labelledby`,
  `aria-describedby` and live validation error semantics; covered by
  `tests/test_ui_compliance.py`.
- `pass`: notification lists in both templates are polite live regions for
  non-blocking inbox changes; covered by `tests/test_ui_compliance.py`.
- `pass`: admin and employee calendar previous/next glyph controls have
  explicit accessible names; covered for admin by `tests/test_ui_compliance.py`.
- `pass`: field validation errors are programmatically associated with their
  inputs through `aria-invalid` and `aria-describedby`; covered by
  `tests/test_ui_compliance.py`.
- `pass`: custom button/chip/action controls have visible active/hover/focus
  states and the global focus ring is centralized in `static/styles.css`.
- `pass`: mobile bottom nav anchors are at least 44 px high in CSS.
- `pass`: mobile bottom nav and page bottom padding account for iOS safe-area
  insets; covered by `tests/test_ui_compliance.py`.
- `pass`: message alerts now use theme-aware CSS classes instead of inline
  light-theme colors; covered by `tests/test_ui_compliance.py`.
- `pass`: single and bulk reject dialogs require a concrete reason, focus the
  textarea on empty submit and mark it with `aria-invalid`; covered by
  `tests/test_ui_compliance.py`.
- `pass`: shared dialog validation can target a named invalid control for
  password, blackout and reject errors instead of always marking the first
  field; covered by `tests/test_ui_compliance.py`.
- `pass`: cancel dialogs require a concrete reason before the destructive
  action and the backend stores the reason in `audit_log`; covered by
  `tests/test_ui_compliance.py` and `tests/test_app.py`.
- `pass`: intent-driven summary actions expose one primary next step for
  employee/admin modes and keep 44 px button targets; covered by
  `tests/test_ui_compliance.py`.
- `pass`: status bar reports free cars as active cars minus active trips,
  aligning the KPI with the cockpit wireframe; covered by
  `tests/test_ui_compliance.py`.
- `pass`: current trip hero promotes an active or next approved employee trip
  above table scanning and exposes one primary lifecycle action; covered by
  `tests/test_ui_compliance.py`.
- `pass`: admin decision rail promotes the top 3 pending decisions before the
  table, keeps text-backed urgency and preserves 44 px direct approve/reject
  actions; covered by `tests/test_ui_compliance.py`.
- `pass`: fleet pulse promotes admin executive insights before approvals, and
  NetFleet GPS data stays behind server endpoints; employee pickup telemetry
  is authorized only for the user's own approved/active trip; covered by
  `tests/test_ui_compliance.py` and `tests/test_app.py`.
- `pass`: one-tap booking creates a pending reservation via conflict/blackout
  guarded backend suggestion instead of only focusing the manual form; covered
  by `tests/test_ui_compliance.py` and `tests/test_app.py`.
- `pass`: smart prefill predicts the user's usual car, hour and duration while
  preserving explicit review before submit; covered by
  `tests/test_ui_compliance.py` and `tests/test_app.py`.
- `pass`: NetFleet service tests cover unconfigured and normalized live payload
  paths without storing a real key in the repository.
- `pass`: Admin-managed NetFleet key flow is admin-only, stores/changes the key
  server-side, uses it for telemetry calls and never returns the current secret;
  covered by `tests/test_app.py` and `tests/test_ui_compliance.py`.
- `pass`: reservation timeline appears before the table on employee/admin
  surfaces, keeps lifecycle actions available and preserves admin pending
  selection; covered by `tests/test_ui_compliance.py`.
- `pass`: employee surface is request-first rather than calendar-first:
  skip link and nav target reservations first, reservations render before the
  calendar, new-request controls render before inbox, and guidance cards hide
  after login; covered by `tests/test_ui_compliance.py` and Playwright smoke.
- `pass`: calm default surfaces hide stale history: read notifications are
  removed from the visible inbox, and employee reservations default to current
  open work instead of showing returned/rejected/cancelled items; covered by
  `tests/test_ui_compliance.py`.
- `pass`: start active trip and return car are admin-only in API and UI;
  employee Current Trip Hero now links to the trip instead of exposing
  lifecycle transition buttons; covered by `tests/test_app.py` and
  `tests/test_ui_compliance.py`.
- `pass`: `make prod-check` validates live `.env` readiness and production
  compose forwards operational env vars to the app container; covered by
  `tests/test_prod_readiness.py`.
- `pass`: admin-only production readiness panel exposes live blockers/warnings
  without secret values, and `/health/ready` provides a DB-backed readiness
  probe for production operations; covered by `tests/test_app.py` and
  `tests/test_ui_compliance.py`.
- `pass`: backup/restore operator helpers are documented, syntax-checked and
  guarded so backup artifacts stay out of git and restore drills use an
  isolated Docker project; covered by `tests/test_prod_readiness.py`.
- `pass`: admin user creation supports optional GSM number with API/schema/UI
  coverage and text-backed display in user cards; covered by
  `tests/test_app.py` and `tests/test_ui_compliance.py`.
- `pass`: production access logs are structured JSON with request id, route,
  status and latency while dev logs stay text; covered by `tests/test_app.py`.
- `pass`: Fleet Pulse GPS count now uses matching active FleetFlow plates and
  reports `X/Y` instead of raw NetFleet event totals.
- `pass`: initial Playwright browser smoke verifies employee one-tap booking,
  employee/admin/reception timeline-first card order, Admin Decision Rail,
  Reception Rail, role-aware reception calendar, Fleet Pulse copy and employee
  mobile calendar against a fresh app server; screenshots are
  written to `test-results/e2e/employee-desktop.png`,
  `test-results/e2e/admin-desktop.png`,
  `test-results/e2e/employee-mobile.png` and
  `test-results/e2e/reception-desktop.png`.
- `pass`: solid light/dark foreground tokens in `tests/test_design_tokens.py`
  meet WCAG AA after the warning token adjustment.
- `evidence`: latest local handoff check ran `pytest -q` -> 135 passed,
  `pytest tests/test_ui_compliance.py -q` -> 31 passed,
  `E2E_ARTIFACT_DIR=test-results/e2e .venv/bin/python -m pytest e2e -q`
  -> 1 passed, `node --check static/app.js`,
  `node --check static/i18n.js` and Python compile check for
  `e2e/test_browser_smoke.py tests/test_ui_compliance.py`.
  `make prod-check` fails fast when `.env` is missing in a clean checkout. Old
  `fleetflow_test` containers were removed, Docker was rebuilt with pinned
  `postgres:16`, `/health` and `/health/ready` on `8001` returned ok/ready and
  the app container is healthy. Backup creation and isolated restore drill
  succeeded using the current smoke stack. PostgreSQL smoke is migrated to
  Alembic revision `20260420_0009`.

## PR/Handoff Checklist

- Changed surfaces:
- Guideline mapping:
- Desktop screenshot:
- Tablet screenshot:
- Phone screenshot:
- Keyboard path tested:
- Contrast pairs checked:
- ARIA/focus/live-region changes:
- Bulgarian copy changes in `static/i18n.js`:
- Tests run:
- Known residual risk:

## Do Not Merge If

- Any visible overlap or clipped essential text remains.
- A custom control lacks accessible name, focus state or press state.
- A status relies on color/icon alone.
- Normal text contrast is below WCAG AA.
- A dialog cannot be canceled with keyboard or does not return focus.
- Mobile navigation hides the primary action or creates unreachable content.
