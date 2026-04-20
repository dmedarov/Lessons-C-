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
2. Вижда Decision Rail с най-важните pending заявки.
3. Вижда GSM номера на заявителя, когато е въведен.
4. Одобрява директно или отказва с причина.
5. При празна причина dialog-ът показва български error, маркира полето с
   `aria-invalid` и връща фокуса в textarea.
6. След действие получава кратък success/error feedback.

**Надеждност:**

- няма достъп до user management, NetFleet ключ и readiness;
- няма start/return бутони;
- reject recovery е покрит с Playwright screenshot
  `destructive-reject-recovery.png`.

## Reception flow

**Цел:** рецепция управлява реалното предаване и връщане на ключове/документи.

1. Отваря `/admin`.
2. Вижда Reception Rail с approved handoffs и active returns пред таблицата.
3. Вижда GSM номера на заявителя, когато е въведен.
4. Ако active курс е след крайния час, **Следващ сигнал** показва
   `чака връщане` преди нормалните handoff задачи.
5. При approved курс използва `Започни курс`.
6. При active курс използва `Върни автомобил`.
7. Вижда локация само за approved/checked-out handoff коли, не fleet-wide GPS.

**Надеждност:**

- няма approve/reject бутони;
- return има confirmation dialog;
- Escape cancel затваря dialog-а и връща фокуса към бутона;
- return confirmation е покрит с Playwright screenshot
  `destructive-return-confirmation.png`.

## Admin flow

**Цел:** admin има full control, но интерфейсът остава подреден.

1. Започва от Fleet Pulse и production readiness.
2. Вижда overdue returns като първи next signal, после Decision Rail и
   Reception Rail, когато има operational работа.
3. Управлява потребители, роли, автомобили, blackout-и, NetFleet ключ и
   production settings.
4. За role change и admin handoff добавя причина, за да има audit trail.
5. Използва `make go-live-check` и Admin readiness panel преди live.

**Надеждност:**

- поне двама active `fleet_admin` са препоръчителни преди production;
- admin handoff е guarded flow;
- destructive/configuration действия трябва да имат причина, confirmation или
  точен recovery path;
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

- `make qa-premium` -> passed: dependency audit, Python compile, 149 pytest
  cases, JS syntax and 12 Playwright browser checks.
- `make smoke-live APP_URL=http://127.0.0.1:8001` -> passed:
  `/health`, `/health/ready`, `/auth/setup-status` and `/public/overview`.

## Do Not Regress

- Не добавяй повече от един primary action на surface.
- Не показвай таблица като първи избор, ако rail/card/timeline върши работата.
- Не показвай role controls на роля, която няма право да ги използва.
- Не разчитай на native browser validation за destructive dialogs; custom
  recovery copy + `aria-invalid` + focus target са product standard.
- Не допускай хоризонтален overflow на 390, 768, 1024 или 1440 px.
