# FleetFlow Role User Flows

Този документ е кратката production инструкция за това какво вижда и прави
всяка роля. Целта е FleetFlow да остане **спокоен, надежден и ролево ясен**:
един основен ход, без UI шум и без скрити permissions.

## Общ модел

| Роля | Основна задача | Основен екран | Не трябва да вижда |
| --- | --- | --- | --- |
| `employee` | заявява автомобил и следи своя курс | `/` | `/admin`, чужди заявки, чужд GPS, start/return |
| `fleet_approver` | одобрява или отказва заявки | `/admin` Decision Rail | потребители, NetFleet ключ, production readiness, start/return |
| `fleet_reception` | предава/приема ключове и документи | `/admin` Reception Rail | approve/reject, настройки, fleet-wide GPS |
| `fleet_admin` | конфигурира и наблюдава целия процес | `/admin` full cockpit | няма, но daily queue не трябва да се губи сред настройки |

UI naming за production handoff:

- `fleet_admin`: **Control Tower**
- `fleet_approver`: **Decision Desk**
- `fleet_reception`: **Handoff Desk**
- `employee`: **Моят курс / Нова заявка**

Следващият accepted UI план не променя permissions; променя само first
viewport hierarchy:

- employee: Current Trip Hero или Suggested Booking Hero преди manual form;
- approver: Decision cards преди таблица;
- reception: overdue returns, после handoffs, после календар;
- admin: Fleet Pulse + next focus + readiness преди settings.

Employee Suggested Booking Hero вече е shipped: показва се само когато
служителят няма pending/approved/active работа, използва `/reservations/suggest`
и не заменя manual form-а; само го премества в fallback/change режим.

Никоя роля не вижда реални infrastructure secrets: NetFleet key, DB password,
`SECRET_KEY`, webhook-и и tokens никога не се echo-ват в UI.

## Notification routing

- Employee подава заявка -> `fleet_admin` и `fleet_approver` получават
  `reservation_requested`.
- Approver/admin одобрява -> requester получава `reservation_decision`, а
  `fleet_reception` и `fleet_admin` получават `reception_handoff` / **Курс чака
  ключове**.
- Reception стартира курс -> requester и другите reception operators получават
  `trip_started`.
- Reception връща автомобил -> requester и reception operators получават
  `trip_returned`.
- SMTP delivery следва същите in-app recipients: ако user има `email`, мейлът
  отива към него; ако няма, fallback е `SMTP_TO_EMAIL`. Teams webhook-ът е
  shared operational channel, не лична поща.

## Login routing

- `employee` влиза в служителския desk и няма persistent достъп до `/admin`.
- `fleet_approver`, `fleet_reception` и `fleet_admin` винаги започват в
  `/admin` след login или cookie restore, защото това са operational роли с
  решение, ключове или пълен контрол като първа задача.
- Ако служител отвори `/admin`, приложението го връща към `/` и скрива Admin
  shortcut-а; ако operational роля отвори `/`, приложението я връща към
  `/admin`.

## Employee flow

**Цел:** служителят да не мисли къде да започне.

1. Отваря `/`.
2. Ако има активен или одобрен курс, вижда Current Trip Hero.
3. Ако няма курс, вижда бърза заявка и smart prefill.
4. След approval вижда `Къде да вземеш колата`, когато има разрешен GPS сигнал.
5. Вижда само собствените си резервации и нотификации.

**Надеждност:**

- служител не може да остане на `/admin`;
- start/return не са employee действия;
- публичният календар и pre-login surface не показват GSM/GPS/заявител.
- GSM може да се вижда в authenticated operational context, но никога публично
  преди login.

## Approver flow

**Цел:** одобряващият решава заявки, без да администрира системата.

1. Отваря `/admin`.
2. Вижда Decision Desk cards като първи работен блок, преди таблицата.
3. Вижда GSM номера на заявителя, когато е въведен.
4. Вижда причина/цел, автомобил, период и urgency marker без да сканира редове.
5. Одобрява директно или отказва с причина.
6. Bulk flow-ът първо избира заявките и показва action bar; няма директен
   approve-all от hero бутона.
7. При празна причина dialog-ът показва български error, маркира полето с
   `aria-invalid` и връща фокуса в textarea.
8. След действие получава кратък success/error feedback.
9. При нова заявка получава in-app/SMTP сигнал, ако каналът е конфигуриран.

**Надеждност:**

- няма достъп до user management, NetFleet ключ и readiness;
- няма start/return бутони;
- таблицата не е първият cognitive load за `fleet_approver`;
- reject recovery е покрит с Playwright screenshot
  `destructive-reject-recovery.png`.

## Reception flow

**Цел:** рецепция управлява реалното предаване и връщане на ключове/документи.

1. Отваря `/admin`.
2. Вижда Handoff Desk като first viewport: първо секция **Чака връщане**, после
   **Чака предаване**, после календара.
3. Вижда GSM номера на заявителя, когато е въведен.
4. Ако active курс е след крайния час, **Следващ сигнал** показва
   `чака връщане` преди нормалните handoff задачи.
5. При approved курс използва `Започни курс`.
6. При active курс използва `Върни автомобил`.
7. Одобрен, но още непредаден курс стои като **Чака вземане**, не като
   **Активен курс**.
8. Вижда локация само за approved/checked-out handoff коли, не fleet-wide GPS.
9. След approval получава handoff сигнал **Курс чака ключове** още преди
   старта на курса.

**Надеждност:**

- няма approve/reject бутони;
- return има confirmation dialog;
- Escape cancel затваря dialog-а и връща фокуса към бутона;
- return confirmation е покрит с Playwright screenshot
  `destructive-return-confirmation.png`.

## Admin flow

**Цел:** admin има full control, но интерфейсът остава подреден.

1. Започва от Control Tower next-focus hero, Fleet Pulse и production
   readiness.
2. Вижда overdue returns като първи next signal, после Decision Rail и
   Reception Rail, когато има operational работа.
3. Hero картата показва един primary ход и кратък insight list, преди admin да
   отвори settings/forms.
4. Управлява потребители, роли, автомобили, blackout-и, NetFleet ключ и
   production settings.
5. Коригира email/GSM от бутона **Контакт** в user картата; всяка промяна
   остава в audit историята.
6. Импортира служители от таблица с `Име / Фамилия / GSM`, без да записва
   чип/тахограф данни в FleetFlow.
7. За role change и admin handoff добавя причина, за да има audit trail.
8. Използва `make go-live-check` и Admin readiness panel преди live.
9. Тества SMTP/Teams от Notifications секцията и следи delivery резултата без
   да вижда secret стойности.

**Надеждност:**

- поне двама active `fleet_admin` са препоръчителни преди production;
- admin handoff е guarded flow;
- destructive/configuration действия трябва да имат причина, confirmation или
  точен recovery path;
- bulk employee import е admin-only и трябва да поддържа съществуващи служители
  без ръчна работа в контейнера;
- production readiness verdict-ът се поддържа в
  `docs/PRODUCTION_READINESS_ASSESSMENT.md`.

## Responsive density evidence

Playwright density guard-ът проверява ключови роли и viewport-и за:

- horizontal overflow;
- clipped controls;
- module overlap;
- стабилен calendar toolbar на tablet/desktop.

Screenshot evidence се пише в `test-results/e2e/` при:

```bash
E2E_ARTIFACT_DIR=test-results/e2e make test-e2e
```

Ключови файлове:

- `density-public-390.png`
- `density-public-768.png`
- `density-employee-390.png`
- `density-approver-768.png`
- `density-reception-768.png`
- `density-admin-1024.png`
- `density-admin-1440.png`
- `destructive-reject-recovery.png`
- `destructive-return-confirmation.png`
- `destructive-user-deactivate-confirmation.png`
- `destructive-role-change-recovery.png`
- `destructive-handoff-recovery.png`
- `destructive-handoff-confirmation.png`
- `destructive-blackout-deactivate-confirmation.png`
- `admin-overdue-return-signal.png`
- `reception-overdue-return-signal.png`

Latest verification:

- `make qa-premium` -> passed: dependency audit, secret scan, Python compile,
  174 pytest cases, JS syntax and 16 Playwright browser checks.
- `make smoke-live APP_URL=http://127.0.0.1:8001` -> passed:
  `/health`, `/health/ready`, `/auth/setup-status` and `/public/overview`.

## Do Not Regress

Преди go-live пазим едновременно от **тихи регресии** (грешни permissions,
липсващ GPS/GSM контекст, schema/i18n drift) и **шумни регресии** (overlap,
твърде много действия, стари записи в текущия поток).

- Не добавяй повече от един primary action на surface.
- Не показвай таблица като първи избор, ако rail/card/timeline върши работата.
- При approver bulk decisions timeline card selection трябва да показва един
  bulk action bar. Таблицата е скрита за чистия `fleet_approver` first viewport,
  така че не трябва да се разчита на table checkbox като primary control.
- Не показвай role controls на роля, която няма право да ги използва.
- Не връщай read notifications, returned, rejected или cancelled записи в
  основния оперативен поток.
- Не скривай requester GSM/GPS/public privacy правила зад икона, hover или
  implicit permission.
- Не допускай NetFleet UI да бърка "липсва ключ" с "има ключ, но live
  доставчикът не отговаря".
- Не ship-вай role или lifecycle промяна без targeted test и без да обновиш
  README, ROADMAP, ROADMAP_IMPROVEMENTS и засегнатия user/production документ.
- Не ship-вай при отворен secret-leak alert без rotation/closure evidence и
  зелен `make secrets-scan`.
- Не разчитай на native browser validation за destructive dialogs; custom
  recovery copy + `aria-invalid` + focus target са product standard.
- Не допускай хоризонтален overflow на 390, 768, 1024 или 1440 px.
