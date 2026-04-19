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
| Login/setup | `templates/index.html`, `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Apple buttons, WCAG labels/errors, bootstrap token copy, keyboard submit | Verify labels, focus order, error recovery and 390 px layout. |
| Employee booking form | `templates/index.html`, `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | Apple layout, NN/g error prevention, WCAG form semantics, conflict preview status | Test invalid date range, conflict warning, preserved input after failure. |
| Calendar studio | `templates/index.html`, `static/app.js`, `static/styles.css` | needs evidence | Responsive 390/768/1440, keyboard reachability, color+text statuses, no overlap | Capture mobile day mode and desktop month screenshots; verify day controls. |
| Reservation list/cards | `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | Status text, lifecycle clarity, cards at mobile, table/card labels | Verify no color-only state and all actions have accessible names. |
| Notifications | `static/app.js`, `static/i18n.js`, `static/styles.css` | needs evidence | `aria-live`, unread badge clarity, concise copy, no noisy motion | Verify polling update announcement and mark-read keyboard path. |
| Admin pending queue | `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Bulk selection semantics, action bar visibility, partial-failure feedback | Test keyboard checkbox selection and bulk approve/reject result copy. |
| Admin users | `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Destructive confirmations, role-change clarity, audit timeline readability | Verify reset/deactivate/role dialog focus return and success/error copy. |
| Admin fleet/cars | `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Notes textarea labels, active/inactive text state, 44 px controls | Verify notes save path, employee visibility and mobile card spacing. |
| Blackout management | `templates/admin.html`, `static/app.js`, `static/styles.css` | needs evidence | Dialog APG behavior, date validation, conflict errors, no overlap | Test create/edit/deactivate via keyboard and invalid dates. |
| Dialog system | `static/app.js`, `static/styles.css` | needs fix | APG modal focus trap/return, ESC cancel, destructive role clarity | Audit every dialog helper; add tests or Playwright assertions. |
| Toast/message system | `static/app.js`, `static/styles.css` | needs evidence | Polite live region, non-color-only severity, visible long enough | Verify screen-reader announcement and reduced-motion behavior. |
| Mobile bottom nav | `templates/index.html`, `templates/admin.html`, `static/styles.css` | needs evidence | 44 px targets, safe-area padding, no content occlusion | Screenshot 390 px bottom area and keyboard focus order. |
| Theme/dark mode | `static/theme.js`, `static/styles.css` | needs fix | NASA/WCAG contrast matrix, focus ring visibility, reduced motion | Implement automated token contrast test in Phase 8.2. |

## Contrast Matrix To Automate

Fill this table during Phase 8.2 after extracting real CSS variable values.

| Pair | Light Status | Dark Status | Required Ratio | Notes |
| --- | --- | --- | --- | --- |
| page background / primary text | needs evidence | needs evidence | 4.5:1 | Core readability. |
| surface / primary text | needs evidence | needs evidence | 4.5:1 | Cards, dialogs, panels. |
| muted text / surface | needs evidence | needs evidence | 4.5:1 preferred | Avoid low-value gray-on-gray. |
| primary button / button text | needs evidence | needs evidence | 4.5:1 | Apple button clarity. |
| danger status / status text | needs evidence | needs evidence | 4.5:1 | Must include label/shape too. |
| warning status / status text | needs evidence | needs evidence | 4.5:1 | Gold often fails; test carefully. |
| success status / status text | needs evidence | needs evidence | 4.5:1 | Must work for color-blind users. |
| focus ring / adjacent background | needs evidence | needs evidence | 3:1 | Keyboard discoverability. |

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
