# FleetFlow Production Readiness Assessment

Дата: 2026-04-21

## Short verdict

FleetFlow е готов за **контролиран вътрешен production pilot**, след като
операторските cutover условия бъдат изпълнени върху реалния deployment.

Оценка: **90/100 за контролиран pilot**.

Оценка за unattended/full rollout: **не още**. Преди това трябва да има реален
production URL rehearsal, преглед на GitHub Dependabot alert-а и поне няколко
дни наблюдение на служебния процес.

Това не е "няма какво да се счупи" оценка. Това е: core процесите, ролите,
UI guardrails, backup/restore discipline и browser evidence са достатъчно
зрели за първа реална употреба с внимателен операторски cutover.

## Green areas

- Auth, refresh-token rotation, logout и live role rebinding са production
  ориентирани.
- Служебният pool процес е разделен по роли:
  `employee`, `fleet_approver`, `fleet_reception`, `fleet_admin`.
- Employee не може да остане на `/admin`.
- Approver одобрява/отказва, reception стартира/връща, admin управлява
  настройки и override-и.
- Pre-login surface показва полезна заетост без requester, GSM, GPS или
  lifecycle действия.
- NetFleet ключът е server-side/admin-managed и не стига до browser assets.
- Reception и employee виждат GPS само в scoped pickup/handoff контекст.
- Production setup е опростен: `make setup`, `make prod`, `make go-live-check`.
- Backup/restore drill е част от финалния gate.
- UI/UX evidence вече включва responsive density, contrast и destructive
  keyboard recovery screenshots.
- Всички календарни изгледи показват multi-day записи на всяка засегната дата
  като начало/продължава/край, със записи от диапазони най-горе в деня.
- Month calendar layout-ът вече реагира на ширината на самия календарен card:
  при тесен card day panel-ът пада отдолу и записите остават четими вместо
  да се свиват между датите.
- Празен избран ден в календара вече предлага следващия ден със запис, вместо
  да оставя статично empty state съобщение.
- Static assets имат versioned URLs и `no-cache` headers, така че production
  deploy не оставя стар `i18n.js` в браузъра с raw translation keys.
- Reception и admin получават top next signal за просрочено връщане преди
  pending approvals, защото това е по-спешен operational риск.

## Remaining go-live blockers

1. **Real `.env` for the deployment.**
   Current source checkout няма `.env`; `make prod-check` правилно отказва с
   `Run 'make setup' first to create .env`. Преди live трябва реален `.env`
   с generated secrets, PostgreSQL URL, real CORS origin и disabled demo seed.

2. **GitHub external signal closure.**
   Последният push още показа 1 moderate Dependabot alert. Локалният
   `pip-audit --no-deps` минава, но GitHub Security/Dependabot alert трябва
   да се отвори директно и да се запише exact finding/решение.

3. **Real production URL rehearsal.**
   Локалният smoke на `http://127.0.0.1:8001` е зелен, но final cutover трябва
   да пусне:

   ```bash
   make prod-check
   make prod-backup
   make prod-restore-drill BACKUP=<backup-file>
   make go-live-check APP_URL=<production-url>
   ```

4. **At least two active admins.**
   За реално ползване препоръката е минимум двама active `fleet_admin`, плюс
   отделни `fleet_approver` и `fleet_reception`, ако процесът е разделен.

## Latest local evidence

- `node --check static/app.js` -> passed.
- `node --check static/i18n.js` -> passed.
- `pytest tests/test_ui_compliance.py -q` -> 36 passed.
- Targeted Playwright admin destructive recovery -> 1 passed.
- Targeted Playwright reception calendar + overdue return signal -> 2 passed.
- Full Playwright smoke -> 12 passed.
- `make qa-premium` -> dependency audit, Python compile, 150 pytest cases,
  JS syntax and 12 Playwright browser checks passed.
- `make smoke-live APP_URL=http://127.0.0.1:8001` -> `/health`,
  `/health/ready`, `/auth/setup-status` and `/public/overview` passed.
- `make prod-check` in the source checkout -> blocked as expected because
  `.env` is missing.

## UX readiness judgement

The app is no longer just feature-complete. It now has evidence for calm,
reliable flows:

- reject requires reason and focuses the invalid textarea;
- return confirmation supports keyboard activation and Escape recovery;
- user deactivate confirmation returns focus after cancel;
- role change requires a reason and focuses the invalid textarea;
- admin handoff requires a reason and field-level recovery;
- blackout deactivate confirmation supports keyboard activation and Escape
  recovery.
- admin/reception overdue return next signal is visible before less urgent
  work;
- calendar range records stay visible on every covered day without overflowing
  neighboring date cells;
- calendar month grid switches to a full-width layout by container width before
  cells become cramped;
- empty selected calendar days point to the next busy date instead of ending
  the flow;
- HTML/CSS/JS cache headers and versioned asset URLs prevent stale i18n bundles
  from leaking raw translation keys after deployment.

The remaining UX risk before broad rollout is not a missing module; it is
operational observation. Use the first week to collect where employees,
approvers and reception hesitate, then tune wording and ordering before adding
larger Fleet Intelligence modules.

## Go / no-go

Go for controlled pilot when:

- `make go-live-check APP_URL=<production-url>` is green;
- the GitHub Dependabot alert is inspected and resolved/accepted explicitly;
- there are at least two active admins;
- NetFleet key is configured or consciously postponed;
- reception has rehearsed start/return with one real approved reservation.

No-go if:

- CORS is wildcard/example;
- database password or `DATABASE_URL` is dev/default;
- restore drill is missing/stale;
- no active admin exists;
- employee can access `/admin` in the deployed build;
- requester GSM/GPS appears on public/pre-login surfaces.
