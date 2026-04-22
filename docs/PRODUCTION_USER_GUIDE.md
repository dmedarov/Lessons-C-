# FleetFlow Production User Guide

Тази инструкция е за първо реално използване на FleetFlow. Целта е production
setup да остане прост: един `.env`, един контейнерен stack и ясен служебен pool
процес.

## 1. Първо пускане

```bash
git clone <repo>
cd <repo>
make setup
```

`make setup` създава `.env` и автоматично генерира:

- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `DATABASE_URL` със същата PostgreSQL парола

Production compose използва pin-нат PostgreSQL major image. Не сменяй
`POSTGRES_IMAGE` към `latest` върху работещ volume; major upgrade се прави само
с отделен backup/restore план.

Преди live промени:

```env
CORS_ALLOW_ORIGINS=https://your-real-domain.example
```

След това провери готовността:

```bash
make prod-check
```

Преди реална употреба направи backup и restore drill, за да има доказателство,
че базата може да се възстанови:

```bash
make prod-backup
make prod-restore-drill BACKUP=backups/fleetflow-YYYYmmddTHHMMSSZ.dump
```

Ако проверките са зелени:

```bash
make prod
```

След това създай първия admin по следващата секция и чак тогава пусни:

```bash
make go-live-check APP_URL=http://127.0.0.1:8000
```

`make go-live-check` е финалният gate: проверява `.env`, свежото restore-drill
доказателство, локалните release тестове и live health/readiness/active-admin/
public overview smoke срещу подадения `APP_URL`.

Текущата readiness оценка е **91/100 за контролиран production pilot**.
Go/no-go правилата са в
[`docs/PRODUCTION_READINESS_ASSESSMENT.md`](PRODUCTION_READINESS_ASSESSMENT.md).
Не третирай това като full rollout без наблюдение: първо направи реален
production URL rehearsal, провери GitHub Dependabot alert-а и наблюдавай първите
дни работа.

## 2. Bootstrap token и първи admin

При първо production стартиране, ако още няма admin, приложението генерира
еднократен bootstrap token в логовете.

```bash
make logs
```

Отвори `/admin`, попълни:

- потребителско име
- име
- силна парола
- bootstrap token от логовете

След успешно създаване token-ът вече не може да се използва повторно.

## 3. Production readiness в Admin UI

След вход като admin отвори панела **Готовност за live**. Той проверява без да
показва тайни:

- production режим
- генерирани секрети
- PostgreSQL връзка
- pin-нат PostgreSQL image, не `latest`
- реален CORS origin
- изключен demo seed
- активен admin
- NetFleet GPS статус
- outbound notification канал

Блокерите трябва да са 0 преди реална употреба. Бележките може да останат само
ако са съзнателно решение, например NetFleet ще се добави по-късно.

Практическа go-live оценка:

- **Go за pilot:** `make go-live-check APP_URL=<production-url>` е зелен,
  има поне двама active admins, има отделни approver/reception потребители или
  съзнателно решение admin да поема тези роли.
- **No-go:** wildcard/example CORS, dev/default database password, липсващ
  restore drill, липсващ active admin, или employee достъп до `/admin`.

## 3.1 No-regression правило преди live

Преди реална употреба не приемай промяна само защото "работи на екрана".
Приеми я само ако не създава:

- **тиха регресия:** role leakage, грешен readiness verdict, schema drift,
  липсващ превод, стар cached JS/CSS, липсващ audit trail или подвеждащ
  NetFleet статус;
- **шумна регресия:** overlap, втори primary action, натрупани read
  notifications, върнати/отказани курсове в основния поток, неясен next move
  или статус само с икона/цвят.

Операторският минимум преди cutover остава `make go-live-check`; инженерният
минимум за UI/role/security промяна е targeted тест плюс `make qa-premium`.

## 3.2 Secret leak stop signal

Ако получиш предупреждение, че infrastructure secret е public, production
cutover спира, докато alert-ът не бъде потвърден или затворен.

Направи това, без да копираш стойността на ключа:

1. Ротирай засегнатия ключ при доставчика. За FleetFlow това най-често е
   NetFleet API key, Docker Hub token, OpenShift token, SMTP password,
   Slack/Teams webhook, `SECRET_KEY`, `POSTGRES_PASSWORD` или production DB
   парола в `DATABASE_URL`.
2. Провери official source-а: GitHub Security tab, GitGuardian dashboard или
   реалната provider конзола. Не плащай и не отваряй payment/resolution links
   от непоискани имейли.
3. Запиши само metadata: тип на secret-а, файл, commit SHA и remediation дата.
4. Пусни:

   ```bash
   make secrets-scan
   make secrets-scan-history
   make release-check
   ```

5. Ако реална стойност е била committed в public history, историята може да се
   чисти само след ротация и след отделно одобрение, защото public forks/cache
   вече може да са я видели.

`make secrets-scan` е guardrail за текущите tracked файлове.
`make secrets-scan-history` сканира всички локални reachable git refs/blob-ове
и е по-подходящ за incident response. Нито един от двата не отменя нуждата от
ротация, ако ключът е бил публично видим.

### Как да разчетеш най-честите блокери

| Блокер | Какво означава | Как се оправя |
| --- | --- | --- |
| `Database password` | `POSTGRES_PASSWORD` още е dev/default стойност. | Пусни `make setup` за нов `.env` или задай силна парола ръчно. |
| `Database URL` | `DATABASE_URL` не е PostgreSQL production URL или не съдържа същата парола. | Увери се, че паролата в `DATABASE_URL` съвпада с `POSTGRES_PASSWORD`. |
| `CORS origin` | Домейнът липсва, е wildcard или е example. | Задай реалния адрес, например `CORS_ALLOW_ORIGINS=https://fleetflow.company.bg`. |
| `PostgreSQL image` | Използван е `latest`, което може да счупи стар volume при major upgrade. | Остави `POSTGRES_IMAGE=postgres:16` или друг умишлено избран major pin. |

`NetFleet GPS` и `Outbound notifications` са warning-и, не блокери. Може да
стартираш без тях, ако решението е съзнателно: GPS ключът се добавя от Admin UI,
а in-app нотификациите работят и без SMTP/Slack/Teams.

### SMTP и Teams известия

SMTP е полезен за персонални служебни сигнали:

- нова заявка -> admin/approver;
- одобрение/отказ -> requester;
- одобрена заявка -> reception/admin като **Курс чака ключове**;
- старт/връщане -> requester и reception operators.

Минимална production конфигурация:

```env
SMTP_HOST=smtp.company.bg
SMTP_PORT=587
SMTP_FROM_EMAIL=fleetflow@company.bg
SMTP_USERNAME=fleetflow@company.bg
SMTP_PASSWORD=
SMTP_USE_TLS=true
SMTP_TO_EMAIL=pool-operators@company.bg
TEAMS_WEBHOOK_URL=
```

Ако потребителят има попълнен `email`, FleetFlow изпраща към него. Ако няма,
използва `SMTP_TO_EMAIL` като operator fallback, за да не се губи важен
служебен сигнал. Teams webhook-ът е shared operational channel за колеги, които
следят процеса от Teams; не го използвай за чувствителни secret стойности.
Попълни `SMTP_PASSWORD` и `TEAMS_WEBHOOK_URL` само в реалния `.env` или в
deployment secret manager, не в документация, screenshot или git commit.
Преди live admin натиска **Тест** в Notifications секцията и проверява
резултатите за `in_app`, `email`, `teams`.

## 4. NetFleet ключ

NetFleet ключът се добавя еднократно от admin:

1. Влез в `/admin`.
2. Намери **NetFleet ключ**.
3. Постави ключа.
4. Запази.

Ключът не се показва обратно в браузъра след запис. След успешна настройка
служителят вижда секция **Къде да вземеш колата** при одобрен курс, ако има
последна GPS позиция.

Ако ключът е записан, но NetFleet временно не отговаря, Fleet Pulse показва
**Няма връзка**, а не съобщение, че ключът липсва. Това означава provider/network
проблем, не липсваща настройка. Операторският ход е да се провери връзката или
по-късно да се презареди, без да се сменя ключът прибързано.

## 5. Служебен pool процес

FleetFlow е role-separated служебен pool процес:

- employee surface: **Моят курс / Нова заявка**;
- approver surface: **Decision Desk**;
- reception surface: **Handoff Desk**;
- admin surface: **Control Tower**;
- служителят подава заявка и вижда следващия си ход;
- `fleet_approver` одобрява или отказва;
- `fleet_reception` отбелязва началото на активен курс след реално предадени
  документи и ключове;
- `fleet_reception` отбелязва връщането след реално върнат автомобил и ключове;
- `fleet_admin` пази настройките, потребителите, флот конфигурацията и full
  override;
- служителят не управлява lifecycle бутоните за start/return.

Практически препоръчан production setup:

- поне двама active `fleet_admin` за continuity;
- поне един `fleet_approver`, ако решенията няма да се правят само от admin;
- поне един `fleet_reception`, ако ключове/документи се държат на рецепция;
- не давай `fleet_admin` на човек, който само одобрява или само предава ключове.

Default изгледите са спокойни:

- служителят вижда текущи заявки, не стар архив;
- прочетените нотификации се прибират;
- върнатите/отказаните/отменените курсове са достъпни през филтрите, но не
  стоят постоянно на екрана.
- одобряващият започва от Decision Desk cards с GSM, причина, автомобил,
  период и urgency преди таблица/филтри; bulk бутонът само избира, а не
  одобрява автоматично.
- рецепция започва от Handoff Desk: първо просрочени връщания, после текущи
  предавания, после календарът; таблицата остава след тях.
- календарът за рецепция показва одобрените предавания и активните връщания
  като operational контекст, дори таблицата да е филтрирана.

## 6. Ежедневна работа

Admin започва от:

1. **Одобрения** - чакащи заявки и batch действия.
2. **Пулс на флота** - активни курсове, чакащи решения, GPS покритие.
3. **Флот** - коли, бележки, blackout прозорци.
4. **Потребители** - активиране, деактивиране, role handoff и контактни
   корекции.

Когато създаваш потребител, попълни email и GSM номер, ако ги имаш. GSM номерът
е оперативна контактна информация за координация около служебния pool процес;
той не е login credential и не замества парола.

Ако след импорт или първоначално създаване GSM/имейл е грешен, използвай
бутона **Контакт** в user картата. Това коригира само контактните данни и
записва `contact_updated` в audit историята, без да сменя роля, активност или
парола.

За много служители използвай **Импорт на служители** в Admin UI. Постави
таблицата с колони `Име / Презиме / Фамилия / Телефон`; FleetFlow използва
само `Име + Фамилия + GSM`, създава липсващите `employee` акаунти и обновява
съществуващите. Чип и тахограф карта не се записват в приложението.

Служителят започва от:

1. текущ курс, ако има такъв;
2. одобрена предстояща заявка, ако има такава;
3. бърза заявка, ако няма активен ангажимент.

## 7. Спокойни и надеждни flows

Production UX правилото е: всеки човек вижда следващия си ход, не всички
възможни административни действия. Подробната инструкция по роли е в
[`docs/ROLE_USER_FLOWS.md`](ROLE_USER_FLOWS.md).

Кратко:

- `employee` не вижда `/admin`, чужди заявки, чужд GSM/GPS или start/return;
- `fleet_approver` вижда Decision Desk cards и решава заявки, но не управлява
  ключове или настройки;
- `fleet_reception` вижда Reception Rail и управлява start/return, но не
  approve/reject;
- `fleet_admin` има full control, но daily queue, readiness и настройки са
  подредени с ясна йерархия.

Надеждните destructive flows са ритуали:

- отказът изисква причина и връща фокуса в полето, ако е празно;
- връщането на автомобил има confirmation dialog и Escape cancel;
- dialog формите използват нашия български recovery copy, `aria-invalid` и
  точен focus target, не browser-native validation bubble;
- след действие потребителят получава кратко потвърждение и списъците се
  обновяват.

Преди go-live пази тези flows с `make qa-premium`. Browser smoke-ът генерира
responsive density screenshots и destructive recovery screenshots в
`test-results/e2e/`.

След deploy HTML/CSS/JS се сервират с `no-cache` guard и versioned static URLs.
Ако потребител види raw UI ключ като `calendar.*`, това вече е blocker за
cache или превод и трябва да се провери с `make qa-premium` преди реална работа.

## 8. Минимална live проверка

Преди да кажеш “ползваме го реално”, провери:

- `make prod-check` минава без `ERROR`;
- `make prod-backup` е създал актуален dump;
- `make prod-restore-drill BACKUP=<backup-file>` е минал успешно;
- `make go-live-check APP_URL=<production-url>` минава успешно;
- `make audit-prod` минава без известни pinned production dependency vulnerabilities;
- GitHub Actions Production Gates минава с full resolver dependency audit;
- `make release-check` минава локално преди cutover;
- `/health/ready` връща `{"status":"ready"}`;
- `/admin` има 0 production blockers;
- има поне един резервен active `fleet_admin`;
- има ясно определен approver/reception процес или съзнателно решение admin да
  поеме тези роли временно;
- NetFleet е конфигуриран или съзнателно отложен;
- поне един реален служител може да влезе;
- тестова заявка минава през pending -> approved -> checked out -> returned.

## 9. Backup и restore drill

Преди първа реална употреба направи поне един backup и dry-run restore.

Създай backup:

```bash
make prod-backup
```

Файлът се записва в `backups/` като PostgreSQL custom dump и директорията е
изключена от git. Пази backup файловете извън repo-то в защитено място.

Провери, че backup-ът реално може да се възстанови:

```bash
make prod-restore-drill BACKUP=backups/fleetflow-YYYYmmddTHHMMSSZ.dump
```

Restore drill-ът стартира отделен Docker project
`fleetflow_restore_drill`, възстановява dump-а в отделна база и проверява
`alembic_version`. След успех записва локален evidence marker в
`.fleetflow/restore-drill-ok.json`, който е игнориран от git и се използва от
`make go-live-check`. По подразбиране временният restore project се изтрива
след успех. Ако искаш да го инспектираш:

```bash
KEEP_RESTORE_DRILL=1 make prod-restore-drill BACKUP=backups/fleetflow-YYYYmmddTHHMMSSZ.dump
```

Преди всяка production миграция:

1. `make prod-backup`
2. `make prod-restore-drill BACKUP=<новия backup>`
3. `make prod`
4. `make go-live-check APP_URL=<production-url>`
5. провери `/health/ready`

По подразбиране restore-drill доказателството е валидно 168 часа. Ако
организацията изисква по-кратък прозорец, задай
`RESTORE_DRILL_MAX_AGE_HOURS=24` в `.env`.

`make smoke-live APP_URL=...`, който се изпълнява вътре в `make go-live-check`,
проверява `/health`, `/health/ready`, `/auth/setup-status` с `has_admin=true` и
`/public/overview`. Така финалният smoke не може да мине на празна production
инсталация без active admin.

## 10. Логове и проследимост

В production `LOG_FORMAT=auto` логва HTTP заявките като единичен JSON ред към
stdout. Всеки access log
съдържа:

- `request_id`
- `method`
- `path`
- `route`
- `status_code`
- `latency_ms`

Когато потребител докладва проблем, вземи `X-Request-ID` от отговора или от
browser/network tooling и търси същия `request_id` в логовете. Логовете не
трябва да съдържат `SECRET_KEY`, `POSTGRES_PASSWORD`, NetFleet ключ или други
секрети.

## 11. Fleet Intelligence

Fleet Intelligence Seed е включен без отделен background worker. Бързата
резервация и `GET /reservations/suggest-best-car` използват explainable scoring
върху текущите operational данни: наличност, blackout/conflict guardrails,
скорошно натоварване и обичайна кола на потребителя.

Изборът се записва в `car_assignments` със score и reason, за да може
admin/support да разбере защо FleetFlow е предложил конкретна кола. Admin Fleet
Pulse чете `/admin/intelligence/pulse` и показва compact insight-и без тежък BI
dashboard. Snapshot таблици и scheduled recompute jobs са планирани след реална
production употреба, ако inline метриките станат бавни или трябва исторически
trend review.

## 12. Първи екран преди login

Преди вход FleetFlow зарежда `GET /public/overview`, за да покаже реални
агрегирани стойности за чакащи одобрение, активни курсове и свободни коли.
Календарът зарежда и `GET /public/calendar?start=&end=`, за да покаже реална
заетост по дни със статус, регистрационен номер и модел.

Това е умишлено public orientation слой. Не се показват заявител, цел на
пътуването, GPS, reservation id или lifecycle действия. За действия и лични
детайли потребителят влиза в системата.
