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

Ако проверката е зелена:

```bash
make prod
```

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

## 4. NetFleet ключ

NetFleet ключът се добавя еднократно от admin:

1. Влез в `/admin`.
2. Намери **NetFleet ключ**.
3. Постави ключа.
4. Запази.

Ключът не се показва обратно в браузъра след запис. След успешна настройка
служителят вижда секция **Къде да вземеш колата** при одобрен курс, ако има
последна GPS позиция.

## 5. Служебен pool процес

FleetFlow е admin-owned служебен pool процес:

- служителят подава заявка и вижда следващия си ход;
- admin одобрява или отказва;
- admin отбелязва началото на активен курс;
- admin отбелязва връщането след приключване;
- служителят не управлява lifecycle бутоните за start/return.

Default изгледите са спокойни:

- служителят вижда текущи заявки, не стар архив;
- прочетените нотификации се прибират;
- върнатите/отказаните/отменените курсове са достъпни през филтрите, но не
  стоят постоянно на екрана.

## 6. Ежедневна работа

Admin започва от:

1. **Одобрения** - чакащи заявки и batch действия.
2. **Пулс на флота** - активни курсове, чакащи решения, GPS покритие.
3. **Флот** - коли, бележки, blackout прозорци.
4. **Потребители** - активиране, деактивиране, role handoff.

Служителят започва от:

1. текущ курс, ако има такъв;
2. одобрена предстояща заявка, ако има такава;
3. бърза заявка, ако няма активен ангажимент.

## 7. Минимална live проверка

Преди да кажеш “ползваме го реално”, провери:

- `make prod-check` минава без `ERROR`;
- `/health/ready` връща `{"status":"ready"}`;
- `/admin` има 0 production blockers;
- има поне един резервен active `fleet_admin`;
- NetFleet е конфигуриран или съзнателно отложен;
- поне един реален служител може да влезе;
- тестова заявка минава през pending -> approved -> checked out -> returned.

## 8. Backup и restore drill

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
`alembic_version`. По подразбиране временният restore project се изтрива след
успех. Ако искаш да го инспектираш:

```bash
KEEP_RESTORE_DRILL=1 make prod-restore-drill BACKUP=backups/fleetflow-YYYYmmddTHHMMSSZ.dump
```

Преди всяка production миграция:

1. `make prod-backup`
2. `make prod-restore-drill BACKUP=<новия backup>`
3. `make prod`
4. провери `/health/ready`
