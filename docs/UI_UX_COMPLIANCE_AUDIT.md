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
| Current trip hero | `templates/index.html`, `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | One primary action, status text, keyboard focus, mobile fit | Active/next approved employee trip is promoted above calendar/table with `Старт` or `Върни`. Capture desktop/mobile screenshots and verify focus after action. |
| Status bar / fleet KPIs | `templates/index.html`, `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Live system status, text labels, no color-only meaning, 390 px fit | KPI strip now reports pending, active trips and free cars. Verify mobile wrapping and screen-reader order. |
| Fleet Pulse / NetFleet telemetry | `templates/admin.html`, `templates/index.html`, `static/app.js`, `static/i18n.js`, `static/styles.css`, `routers/cars.py`, `netfleet_service.py` | needs evidence | No exposed API key, employee pickup authorization, text-backed GPS status, responsive strip, coordinates do not overwhelm decisions | Fleet Pulse now uses a global reservation snapshot and optional NetFleet GPS events by plate number. Employee pickup location is limited to the user's own approved/active trip. Capture configured/unconfigured screenshots and verify no key appears in browser payloads. |
| Employee booking form | `templates/index.html`, `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | Apple layout, NN/g error prevention, WCAG form semantics, conflict preview status | Test invalid date range, conflict warning, preserved input after failure. `conflictPreview` already has `role=status` + `aria-live=polite`. |
| Calendar studio | `templates/index.html`, `static/app.js`, `static/styles.css` | needs evidence | Responsive 390/768/1440, keyboard reachability, color+text statuses, no overlap | Capture mobile day mode and desktop month screenshots; verify day controls. Month prev/next controls now have accessible labels on both surfaces. |
| Reservation list/cards | `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | Status text, lifecycle clarity, cards at mobile, table/card labels, cancel recovery | Verify no color-only state and all actions have accessible names. Lifecycle meter has text labels; table body is `aria-live=polite`; cancel now requires a reason. |
| Notifications | `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | `aria-live`, unread badge clarity, concise copy, no noisy motion | Notification lists are now polite live regions. Verify polling update announcement with a screen reader. |
| Admin pending queue / decision rail | `templates/admin.html`, `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | Top pending decisions first, bulk selection semantics, action bar visibility, partial-failure feedback, required reject reason | Decision rail now appears before the table with top 3 pending cards, direct row actions and bulk approve. Capture desktop/mobile screenshots and test keyboard checkbox selection plus empty reject reason recovery. |
| Admin users | `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Destructive confirmations, role-change clarity, audit timeline readability | Verify reset/deactivate/role dialog focus return and success/error copy. |
| Admin fleet/cars | `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Notes textarea labels, active/inactive text state, 44 px controls | Verify notes save path, employee visibility and mobile card spacing. |
| Blackout management | `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Dialog APG behavior, date validation, conflict errors, no overlap | Test create/edit/deactivate via keyboard and invalid dates. |
| Dialog system | `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | APG modal focus trap/return, ESC cancel, destructive role clarity, exact invalid-field recovery | Native `<dialog>` is used, ESC cancel exists, helper-level focus return is covered, dialogs expose modal name/description/error semantics, and validation can focus/mark the exact invalid field for reject/cancel/password/blackout flows. Manual screen-reader pass still needed. |
| Toast/message system | `static/app.js`, `static/styles.css` | needs evidence | Polite live region, non-color-only severity, visible long enough | `#message` uses `role=alert`, receives focus and now uses theme-aware alert classes instead of inline light-theme colors. Verify with screen reader and dark-mode screenshots. |
| Mobile bottom nav | `templates/index.html`, `templates/admin.html`, `static/styles.css` | needs evidence | 44 px targets, safe-area padding, no content occlusion | CSS sets `min-height: 44px` and accounts for `safe-area-inset-bottom`; screenshot 390 px bottom area and keyboard focus order still required. |
| Theme/dark mode | `static/theme.js`, `static/styles.css` | needs evidence | NASA/WCAG contrast matrix, focus ring visibility, reduced motion | Solid text/status token pairs now covered by `tests/test_design_tokens.py`; translucent surfaces still need browser-computed contrast evidence. |

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
- `pass`: solid light/dark foreground tokens in `tests/test_design_tokens.py`
  meet WCAG AA after the warning token adjustment.
- `evidence`: latest local handoff check ran `pytest -q` -> 94 passed,
  `node --check static/app.js`, `node --check static/i18n.js` and
  Python compile check for `config.py`, `netfleet_service.py` and
  `routers/cars.py`, plus `git diff --check`, Docker rebuild and `/health` on
  `8001`; `fleetflow_test-car-pool-1` is healthy.

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
