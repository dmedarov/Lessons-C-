# Lessons-C- / Car Pool Reservation API

Това е **прост, работещ пример** за резервация на пул от служебни автомобили, контейнеризиран с Docker.

## Какво прави

- Добавя автомобили.
- Прави резервации по автомобил и време.
- Предпазва от застъпващи се резервации за една и съща кола.
- Дава списък с автомобили и резервации.
- Има `health` endpoint за Docker healthcheck.

## Бърз старт

```bash
docker compose up --build
```

API ще е достъпно на:
- `http://localhost:8000/` (Simple Web UI)
- `http://localhost:8000/docs` (Swagger UI)
- `http://localhost:8000/health`


## Уеб интерфейс

Има минимален HTML/Bootstrap интерфейс на `/`, от който можеш:
- да добавяш автомобили,
- да създаваш резервации,
- да виждаш текущите автомобили и резервации в таблици.

## Примерни заявки

### 1) Добавяне на автомобил

```bash
curl -X POST http://localhost:8000/cars \
  -H "Content-Type: application/json" \
  -d '{
    "plate_number": "CA1234AB",
    "model": "Skoda Octavia"
  }'
```

### 2) Създаване на резервация

```bash
curl -X POST http://localhost:8000/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "car_id": 1,
    "employee_name": "Ivan Petrov",
    "start_time": "2026-04-18T09:00:00",
    "end_time": "2026-04-18T11:00:00",
    "purpose": "Client meeting"
  }'
```

### 3) Списък на резервациите

```bash
curl http://localhost:8000/reservations
```

## Архитектурни решения (best practices, practical)

1. **Транзакция при създаване на резервация (`BEGIN IMMEDIATE`)**
   - Намалява риска от race condition при едновременни заявки за една и съща кола.

2. **Проверка за застъпване по време**
   - Условие: `start_time < existing_end` и `end_time > existing_start`.

3. **Индекс за заявки по кола и период**
   - `idx_reservations_car_time` ускорява проверките за конфликт.

4. **Docker security basics**
   - Контейнерът върви с non-root user (`appuser`).
   - Добавен е `HEALTHCHECK`.
   - Използва се slim базов image.

5. **Персистентни данни**
   - Базата е в Docker volume (`/data/fleet.db`), така че данните остават при рестарт.

## Проучени източници

- Dockerfile best practices (официална документация):
  https://docs.docker.com/engine/userguide/eng-image/dockerfile_best-practices/
- FastAPI в Docker (официална документация):
  https://fastapi.tiangolo.com/deployment/docker/
- SQLite isolation & concurrency (официална документация):
  https://www.sqlite.org/isolation.html

## Ограничения на този прост пример

- SQLite е добра за малък/среден товар, но за по-голям е добре да се мигрира към PostgreSQL.
- Няма authentication/authorization.
- Няма audit лог/история на промени.

## Следващи стъпки (ако искаш)

- JWT login + роли (служител / администратор).
- Одобрение на резервации (workflow).
- Автоматични тестове + CI pipeline.
- PostgreSQL + migration tool (Alembic).
