# FleetFlow Manual Keyboard / Accessibility Pass

Дата: 2026-04-22

Този документ е кратък handoff за manual pass преди go-live. Целта не е
формална сертификация, а спокойно доказателство, че основните роли могат да
работят keyboard-first без скрити dead ends, overlap или загуба на контекст.

## Как да се ползва

1. Пусни production-like stack на `http://127.0.0.1:8001`.
2. Потвърди, че `make qa-premium` и `make smoke-live APP_URL=http://127.0.0.1:8001`
   са зелени.
3. За всяка роля по-долу мини само с клавиатура:
   `Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`.
4. Ако нещо счупи focus order, скрие status, или остави диалог без recovery,
   това е go-live blocker.

## Public orientation

- Очакван first screen: login/setup, KPI strip, календар, флот.
- Не трябва да има видими inbox или reservations ledger панели.
- KPI strip трябва да различава `Чака вземане` от `Активен курс`.
- Calendar pills трябва да са текстови: `Вземане · ...`, `Активен · ...`.
- `Tab` отива логично към login полетата и после към календарните контроли.

## Employee

- Login -> employee остава на `/`, не влиза в `/admin`.
- При липса на текущ курс Suggested Booking Hero е първият primary action.
- `Tab` стига до `Резервирай сега`, после до `Промени`, после до form fallback.
- След quick-book резултатът показва ясно pending state и че няма нужда от
  повторно натискане.
- Employee не трябва да вижда start/return lifecycle бутони.

## Approver

- Login -> `/admin`, Decision Desk е преди таблицата.
- `Tab` първо стига decision cards, не филтри/таблица.
- `Space` върху checkbox в timeline card синхронизира bulk action bar-а.
- Reject без причина връща focus в textarea и показва inline error.
- `Escape`/Cancel от reject dialog връща focus към trigger бутона.

## Reception

- Login -> `/admin`, Handoff Desk е преди календара и таблицата.
- Просрочените връщания са над `Чака предаване`.
- `Tab` стига първо до overdue/return action, после до handoff start action.
- Approved, но непредаден курс е `Чака вземане`, не `Активен курс`.
- Pickup location/GPS се вижда само в scoped handoff context.
- Return confirmation поддържа `Escape` и връща focus към trigger бутона.

## Admin

- Login -> `/admin`, Control Tower hero и Fleet Pulse са над settings.
- `Tab` стига first към Next Focus primary action.
- Readiness blockers/warnings са текстови, не color-only.
- Destructive settings actions изискват причина/потвърждение и имат keyboard recovery.
- NetFleet конфигурацията не показва текущия secret обратно в UI.

## Final pilot gate

Този manual pass е достатъчен за **PILOT GO**, ако:

- role flows са keyboard-usable;
- public surface не лъже за `Чака вземане` / `Активен курс` / `Свободна`;
- няма диалог без `Escape` recovery;
- няма focus trap или hidden next move.

За `99/100` broad production rollout остава нуждата от screen-reader check на
final production URL и наблюдавана първа седмица без high-severity UX дефекти.
