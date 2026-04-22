# FleetFlow Production Cutover Checklist

Дата: __________

Този документ е за реалния production cutover, не за локалния smoke stack.
Целта е да съберем на едно място автоматичната проверка, външните security
сигнали и човешкия go/no-go signoff.

Използвай го заедно с:

- [PRODUCTION_USER_GUIDE.md](/Users/dmedarov/Documents/Codex/2026-04-18-https-github-com-dmedarov-lessons-c/docs/PRODUCTION_USER_GUIDE.md)
- [PRODUCTION_READINESS_ASSESSMENT.md](/Users/dmedarov/Documents/Codex/2026-04-18-https-github-com-dmedarov-lessons-c/docs/PRODUCTION_READINESS_ASSESSMENT.md)

## 1. Cutover context

- Production URL: `____________________________`
- Release SHA: `____________________________`
- Docker image digest/tag: `____________________________`
- Operator 1: `____________________________`
- Operator 2 / witness: `____________________________`
- Planned cutover window: `____________________________`

## 2. Preflight inputs

- [ ] Реалният `.env` е генериран с `make setup`.
- [ ] `APP_ENV=prod`.
- [ ] `CORS_ALLOW_ORIGINS` е реалният production домейн.
- [ ] `DEV_SEED_DEMO_DATA=false`.
- [ ] Има поне двама active `fleet_admin`.
- [ ] Има отделни `fleet_approver` / `fleet_reception`, ако процесът го изисква.

## 3. Automated gates

Изпълни в този ред и запиши резултата:

```bash
make prod-check
make prod-backup
make prod-restore-drill BACKUP=backups/fleetflow-YYYYmmddTHHMMSSZ.dump
make prod
make go-live-check APP_URL=https://your-production-url.example
```

### Evidence

- `make prod-check`: `PASS / FAIL`
- Backup file: `____________________________`
- Restore drill marker timestamp: `____________________________`
- `make go-live-check`: `PASS / FAIL`
- Live smoke URL: `____________________________`

Notes:

`______________________________________________________________`

`______________________________________________________________`

## 4. Runtime UI verification

След deploy отвори `/admin` и провери:

- [ ] `Control Tower` е достъпен.
- [ ] `Готовност за live` няма blockers.
- [ ] `restore_drill` е `OK`.
- [ ] `admin_redundancy` е `OK`.
- [ ] `NetFleet GPS` показва вярно `OK / Внимание`, без secret leak.
- [ ] `Outbound notifications` статусът е очакваният.

Снимки / evidence paths:

- Admin readiness screenshot: `____________________________`
- Public overview screenshot: `____________________________`

## 5. GitHub Security / Dependabot closure

Тази част е manual-only. В текущата локална среда:

- GitHub repo metadata е видим (`dmedarov/Lessons-C-`, public, default branch
  `master`);
- но няма директен tool за GitHub Security alerts;
- `gh` CLI не е наличен.

Затова отвори **GitHub web UI -> Security tab** и запиши:

### Dependabot

- Alert count at cutover: `____________________________`
- Resolved / accepted finding ids: `____________________________`
- Remaining accepted risk, if any: `____________________________`

### Secret scanning / external alert

- Provider / source: `GitHub / GitGuardian / other`
- Alert title: `____________________________`
- Secret type: `____________________________`
- Affected path or commit SHA: `____________________________`
- Rotated / revoked at provider: `YES / NO`
- Rotation timestamp: `____________________________`
- Metadata recorded without secret value: `YES / NO`

No-go if:

- има отворен unresolved secret-leak alert;
- има unresolved critical/high dependency finding без изрично risk решение;
- някой екип още разчита на не-ротирана публично изложена стойност.

## 6. Live role rehearsal

Изпълни поне един реален служебен сценарий:

- [ ] Employee request
- [ ] Approver approve/reject with reason
- [ ] Reception sees `Курс чака ключове`
- [ ] Reception starts trip
- [ ] Reception returns trip
- [ ] Employee sees correct status / pickup context

Evidence:

- Role rehearsal notes: `____________________________________________`
- Screenshots/video path: `___________________________________________`

## 7. Final decision

### Go for controlled pilot

Всичко по-долу трябва да е вярно:

- [ ] `make go-live-check APP_URL=<production-url>` е зелен.
- [ ] GitHub Security / Dependabot е прегледан.
- [ ] Няма unresolved secret-leak blocker.
- [ ] Има двама active admins.
- [ ] Live role rehearsal е минал.

### Stop signal

Спри cutover-а, ако някое от тези е вярно:

- [ ] readiness blocker остава отворен;
- [ ] GitHub security status е неясен;
- [ ] restore drill е stale/missing;
- [ ] employee still reaches wrong surface or role flow breaks on the live URL;
- [ ] production URL rehearsal е непълен или нестабилен.

## 8. Signoff

- Operator signoff: `____________________________`
- Witness signoff: `____________________________`
- Final verdict: `GO / STOP`
- Follow-up items after pilot: `________________________________________`
