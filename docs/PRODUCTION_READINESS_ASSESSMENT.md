# FleetFlow Production Readiness Assessment

Дата: 2026-04-21

## Short verdict

FleetFlow е готов за **контролиран вътрешен production pilot**, след като
операторските cutover условия бъдат изпълнени върху реалния deployment.

Оценка: **91/100 за контролиран pilot**.

Текущ security override: **STOP за live**, ако има отворен critical
infrastructure-secret alert. Оценката 91/100 остава техническата pilot оценка
на продукта, но go-live не продължава, докато alert metadata не бъде проверена,
засегнатите ключове не бъдат ротирани и `make secrets-scan` /
`make secrets-scan-history` не са зелени.

Оценка за unattended/full rollout: **не още**. Преди това трябва да има реален
production URL rehearsal, преглед на GitHub Dependabot alert-а и поне няколко
дни наблюдение на служебния процес.

Launch signal today:

- **PILOT GO** за контролиран вътрешен rollout, ако final deployment env мине
  `make go-live-check APP_URL=<production-url>` и няма отворен real secret /
  Dependabot blocker.
- **STOP** за broad unattended production rollout, докато не се затворят
  външните security сигнали, не се докаже restore drill на final env и не мине
  поне една наблюдавана седмица без high-severity role-flow дефекти.

Това не е "няма какво да се счупи" оценка. Това е: core процесите, ролите,
UI guardrails, backup/restore discipline и browser evidence са достатъчно
зрели за първа реална употреба с внимателен операторски cutover.

## 99/100 Premium Robust Production Gate

99/100 не трябва да се отбелязва само от локални тестове. Това е праг за
реално, спокойно и устойчиво production ползване. За да се вдигне оценката от
pilot-ready към 99/100, трябва всички точки по-долу да са доказани:

1. **Production environment**
   - real `.env` е генериран с `make setup` и няма dev/default secret-и;
   - `APP_ENV=production`;
   - `CORS_ALLOW_ORIGINS` съдържа реалния домейн, без wildcard/example;
   - `DATABASE_URL` сочи към PostgreSQL с реалната генерирана парола;
   - `DEMO_SEED` е изключен.

2. **Final cutover gate**
   - `make prod-check` е зелен;
   - има свеж `make prod-backup`;
   - `make prod-restore-drill BACKUP=<backup-file>` е минал успешно;
   - `make go-live-check APP_URL=<production-url>` е зелен срещу реалния URL;
   - Docker stack-ът е rebuild-нат и няма стари FleetFlow контейнери/volumes,
     които обслужват стар код.

3. **People and roles**
   - има минимум двама active `fleet_admin`;
   - има отделен `fleet_approver`, ако процесът иска отделно одобрение;
   - има отделен `fleet_reception`, ако ключове/документи се предават на
     рецепция;
   - employee потребител не може да остане на `/admin`;
   - requester GSM се вижда само в authenticated operational surfaces.

4. **End-to-end role rehearsal**
   - employee подава заявка;
   - approver/admin получава новата pending заявка като in-app/SMTP сигнал;
   - approver одобрява/отказва с reason recovery;
   - reception/admin получава **Курс чака ключове** след approval;
   - reception стартира курс след ключове/документи;
   - reception връща автомобил;
   - admin вижда audit/notifications/readiness без secret leakage;
   - календарите показват active/pending/approved occupancy правилно преди и
     след login.

5. **NetFleet and pickup clarity**
   - NetFleet ключът е добавен през Admin UI или runtime env;
   - Fleet Pulse показва fresh/stale/unavailable state коректно;
   - employee вижда pickup location само за своя одобрена/активна заявка;
   - reception вижда scoped location за approved/active handoff коли;
   - ако доставчикът не отговаря, UI показва **Няма връзка**, не "липсва ключ".

6. **Notification and recovery discipline**
   - in-app notifications не се трупат като шум след прочитане;
   - SMTP е конфигуриран с `SMTP_HOST`, `SMTP_FROM_EMAIL` и user email-и или
     `SMTP_TO_EMAIL` fallback;
   - Teams webhook е проверен, ако част от екипа работи през Teams;
   - admin test notification доказва `in_app`, `email` и `teams` статуса преди
     live, без да показва secret стойности;
   - returned/rejected/cancelled записи не доминират текущия employee flow;
   - destructive actions имат keyboard/Escape recovery evidence;
   - invalid forms фокусират точния проблем и пазят въведения текст.

7. **Security and dependency closure**
   - GitHub Dependabot alert-ът е отворен, записан и resolved или explicitly
     accepted;
   - всеки secret-leak alert е проверен през official provider/GitHub surface,
     засегнатите ключове са ротирани и metadata-та е записана без secret value;
   - `make secrets-scan` и incident-only `make secrets-scan-history` са зелени;
     current checkout scan-ът е част от `make release-check`/CI;
   - `make audit-prod`/production dependency audit е зелен или има документирано
     решение;
   - browser-facing assets не съдържат NetFleet API key, database URL или secret.

8. **Accessibility and responsive evidence**
   - `make qa-premium` е зелен;
   - desktop/tablet/mobile screenshots са прегледани за overlap, density и
     календарни записи;
   - manual screen-reader smoke е направен за login, booking, approve/reject,
     start/return и NetFleet unavailable copy;
   - contrast evidence остава зелен в light/dark mode.

9. **First monitored production week**
   - има човек, който следи първите реални заявки;
   - всички high-severity UX дефекти се фиксират преди broad rollout;
   - няма lost reservation, wrong-role action, missing pickup location или
     misleading readiness/NetFleet status;
   - след първата седмица се актуализират README, ROADMAP, ROADMAP_IMPROVEMENTS
     и този документ с реалните наблюдения.

10. **No silent / no noisy regressions**
   - automated gates пазят duplicate routes, schema parity, missing i18n,
     readiness score drift, stale static assets и browser-facing secret leaks;
   - browser evidence пази overlap, density, destructive recovery, role
     visibility и calendar/reception next signals;
   - всяка UI/role/lifecycle/production промяна има targeted test, обновени
     `.md` handoff документи и зелен `make qa-premium`.

## Green areas

- Auth, refresh-token rotation, logout и live role rebinding са production
  ориентирани.
- Служебният pool процес е разделен по роли:
  `employee`, `fleet_approver`, `fleet_reception`, `fleet_admin`.
- Employee не може да остане на `/admin`.
- Approver одобрява/отказва, reception стартира/връща, admin управлява
  настройки и override-и.
- Admin може да коригира email/GSM на конкретен потребител с audit следа,
  без да повтаря bulk import или да сменя пароли/роли.
- Pre-login surface показва полезна заетост без requester, GSM, GPS или
  lifecycle действия.
- NetFleet ключът е server-side/admin-managed и не стига до browser assets.
- Fleet Pulse различава неконфигуриран NetFleet от конфигуриран ключ с
  временно недостъпен live GPS доставчик.
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
- Липсващи literal UI преводи вече се хващат от тестовете, а runtime fallback
  показва неутрален български текст вместо raw key.
- Reception и admin получават top next signal за просрочено връщане преди
  pending approvals, защото това е по-спешен operational риск.
- Premium visual calm guard е добавен: decorative radial orb backgrounds са
  премахнати, mobile KPI остава компактен 3-column status strip, а тест пази
  `radial-gradient` да не се върне тихо.
- Role-first login routing е добавен: operational роли (`fleet_admin`,
  `fleet_approver`, `fleet_reception`) започват в `/admin`, а служителят не може
  да остане на `/admin`.
- Production GitHub Actions са изравнени към `actions/checkout@v6` и
  `actions/setup-python@v6`; production checkout използва
  `persist-credentials: false`.
- Repository secret hygiene guard is added: `.env.*` and `.claude/` are ignored,
  while `.env.example` stays tracked; `make secrets-scan` fails on real-looking
  tracked `SECRET_KEY`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `NETFLEET_API_KEY`,
  webhook/token/password assignments and private key blocks; `make
  secrets-scan-history` scans all local reachable git refs/blobs during
  incident response.
- Dependabot dev dependency pins са обновени: `pytest==9.0.3`,
  `filelock==3.20.3`, `requests==2.33.0`. Тези dev pins изискват Python 3.10+
  and match the CI floor of Python 3.12/3.14; стар локален Python 3.9 venv не е
  валиден go-live evidence за dev dependency audit.

## Remaining go-live blockers

1. **Real `.env` for the deployment.**
   Current source checkout няма `.env`; `make prod-check` правилно отказва с
   `Run 'make setup' first to create .env`. Преди live трябва реален `.env`
   с generated secrets, PostgreSQL URL, real CORS origin и disabled demo seed.

2. **GitHub external signal closure.**
   Последният push още показа 1 moderate Dependabot alert. Локалният
   `pip-audit --no-deps` минава, но GitHub Security/Dependabot alert трябва
   да се отвори директно и да се запише exact finding/решение.

3. **Critical secret-leak alert closure.**
   Ако alert-ът "Environment secrets are public" е от GitHub/GitGuardian или
   реален доставчик, rotate/revoke първо, после запиши provider, secret type,
   file path и commit SHA. Локалната проверка до момента не намира реална
   NetFleet/API/DB стойност в tracked current files; това не отменя ротацията
   на ключ, който е бил публично споделен извън repo-то.

4. **Real production URL rehearsal.**
   Локалният smoke на `http://127.0.0.1:8001` е зелен, но final cutover трябва
   да пусне:

   ```bash
   make prod-check
   make prod-backup
   make prod-restore-drill BACKUP=<backup-file>
   make go-live-check APP_URL=<production-url>
   ```

   За самия execution/evidence използвай
   [`PRODUCTION_CUTOVER_CHECKLIST.md`](PRODUCTION_CUTOVER_CHECKLIST.md), вместо
   да държиш cutover notes разпилени.

5. **At least two active admins.**
   За реално ползване препоръката е минимум двама active `fleet_admin`, плюс
   отделни `fleet_approver` и `fleet_reception`, ако процесът е разделен.
   `/ops/readiness` вече показва `admin_redundancy` warning при само един active
   admin и pass при двама или повече.

## External cutover pack

Използвай
[`PRODUCTION_CUTOVER_CHECKLIST.md`](PRODUCTION_CUTOVER_CHECKLIST.md) като
операторски пакет за:

- реалния production URL rehearsal;
- GitHub Security / Dependabot manual review;
- secret rotation metadata;
- final GO / STOP signoff.

## Latest local evidence

- `node --check static/app.js` -> passed.
- `node --check static/i18n.js` -> passed.
- `pytest tests/test_documentation_contracts.py -q` -> 5 passed.
- `pytest tests/test_ui_compliance.py -q` -> 38 passed.
- Targeted Playwright admin destructive recovery -> 1 passed.
- Targeted Playwright reception calendar + overdue return signal -> 2 passed.
- Full Playwright smoke -> 16 passed.
- `make qa-premium` -> dependency audit, secret scan, Python compile,
  181 pytest cases, JS syntax and 16 Playwright browser checks passed.
- PostgreSQL smoke stack was rebuilt on `APP_PORT=8001`; app and database
  containers are healthy.
- `make smoke-live APP_URL=http://127.0.0.1:8001` after rebuild -> `/health`,
  `/health/ready`, `/auth/setup-status` and `/public/overview` passed.
- `make prod-check` -> passed with warning only for optional `NETFLEET_API_KEY`
  env value because Admin UI can configure live GPS later.
- `make prod-backup` -> created `backups/fleetflow-20260422T205423Z.dump`.
- `make prod-restore-drill BACKUP=backups/fleetflow-20260422T205423Z.dump` ->
  passed and wrote `.fleetflow/restore-drill-ok.json`.
- `make go-live-check APP_URL=http://127.0.0.1:8001` -> passed against the
  local production-like stack after the restore drill.
- `/ops/readiness` now reads the same restore-drill marker and exposes a
  dedicated `restore_drill` item in the Admin readiness panel, so runtime UI
  and shell cutover evidence share one source of truth.
- Docker Scout on the rebuilt image -> 0 critical, 0 high, 0 medium, 0 low
  vulnerabilities across 80 packages.
- Python 3.14 container dev audit -> `pip-audit -r requirements-dev.txt` found
  no known vulnerabilities after the Dependabot dev pin updates.
- Docker release artifact pushed: `dmedarov/fleetflow:latest`, digest
  `sha256:96ef7229f656b5993653aab20ad7db4ebc78d6cc6215e8d07c2cb060070a2853`.
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
- approver bulk selection is keyboard-safe: timeline checkbox, table checkbox,
  selected state and bulk action bar stay synchronized;
- calendar range records stay visible on every covered day without overflowing
  neighboring date cells;
- calendar month grid switches to a full-width layout by container width before
  cells become cramped;
- empty selected calendar days point to the next busy date instead of ending
  the flow;
- HTML/CSS/JS cache headers and versioned asset URLs prevent stale i18n bundles
  from leaking raw translation keys after deployment;
- literal `t("...")` calls are checked against `static/i18n.js`, and runtime
  missing translations do not expose raw implementation keys.
- public login surface is intentionally simplified to login/setup, KPI strip,
  calendar and fleet orientation; inbox and reservations ledger stay hidden
  until authentication.
- manual role keyboard pass is documented in
  `docs/ROLE_KEYBOARD_ACCESSIBILITY.md` and should be run on the final URL
  before broad rollout.

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
 - public pre-login screen shows separate `Чака вземане` and does not count
   approved-but-not-started cars as free;

99/100 е честна цел едва след реален production URL rehearsal, свеж
backup/restore drill evidence, проверен GitHub Dependabot alert, минимум двама
active admins, реален CORS домейн, потвърден NetFleet сигнал в работната мрежа
и първа седмица наблюдение без high-severity flow дефекти.
- reception has rehearsed start/return with one real approved reservation.

No-go if:

- CORS is wildcard/example;
- database password or `DATABASE_URL` is dev/default;
- restore drill is missing/stale;
- no active admin exists;
- employee can access `/admin` in the deployed build;
- requester GSM/GPS appears on public/pre-login surfaces.
