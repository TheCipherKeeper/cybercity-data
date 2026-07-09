# Backlog

Строгая последовательная очередь задач (сверху вниз). Агент берёт первый
невыполненный `[ ]`; после реализации `[x]` + перенос пункта из «Что TODO» в
«Что есть» в спеке (`docs/specs/<module>.md`). Человек меняет порядок. Формат
задачи: `### N. [<модуль>] Краткое название` / `Зависит от:` / `Спек:` /
что сделать / `Тесты:`.

> Статус реализации по репозиториям — в
> [`cybercity/COMPOSITION.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/COMPOSITION.md)
> → *Статус реализации*. Здесь — задачи этого репо, упорядоченные.

---

### 1. [scenario] Завершить авторинг сценариев

- **Зависит от:** —
- **Спек:** `docs/specs/scenario.md`
- **Что сделать:** формализовать модуль `scenario` (манифест сценария: цели,
  injects, флаги, scoring-rubric, timebox); завести пакет
  `src/cybercity_data/scenario/` по швам MODULE.md (usecases/ports/domain/adapters);
  интегрировать в `build` (артефакт сценария — контракт data → engine,
  out-of-band). Авторинг — декларативный (YAML), как и модель города.
- **Тесты:** `tests/scenario/` — парсинг, валидация, рендер артефакта сценария;
  property-based на инварианты манифеста.

### 2. [vuln] Авторинг уязвимостей (манифест + overlay-исходники)

- **Зависит от:** —
- **Спек:** `docs/specs/vuln.md` (завести как placeholder с заполненным «Что TODO»)
- **Что сделать:** уязвимость как first-class сущность: манифест + overlay-исходники
  рядом (один PR = одна vuln), `realism ∈ {real, narrative}`; `cve_id` в
  vuln-сущности, не в дескрипторе сервиса
  ([ADR-0006](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/0006-vulnerability-declarative-overlay-realism.md)).
  Завести пакет `src/cybercity_data/vuln/` по швам MODULE.md. Сборка
  `overlays`-артефакта (контракт data → manage out-of-band).
- **Тесты:** `tests/vuln/` — парсинг манифеста, валидация `requires`-предусловий,
  сборка overlay-тарболла; одна vuln на фикс-ветке как пример.

### 3. [build] Broker-producer wiring: EventPublisher port + Redpanda adapter

- **Зависит от:** `docker-compose.yml` (брокер `broker`), `.env.example`
  (`BROKER_ADDR`)
- **Спек:** `docs/specs/build.md` → «Что TODO» (публикация `city.build.completed`)
- **Что сделать:** завести output port `EventPublisher` в `ports/` (Python
  `Protocol`), реализовать Redpanda adapter в `adapters/`
  (`<methodology-repo>`/docs/refs/MODULE.md). `BuildUseCase` после успешной
  сборки публикует `city.build.completed` (payload: путь/версия артефактов;
  envelope `CONVENTIONS@v1` —
  [`cybercity/CONVENTIONS.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/CONVENTIONS.md)).
  Решение —
  [ADR-0010](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/0010-data-broker-producer.md).
- **Тесты:** `tests/build/test_event_publisher.py` — fake adapter, проверка
  envelope и payload; интеграционный тест на `broker` из `docker-compose.yml`.

### 4. [model] Швы модулей: ports/ + adapters/ по MODULE.md

- **Зависит от:** 3 (для build/scenario/vuln)
- **Спек:** `docs/specs/<module>.md` (обновить «Ограничения»/«Зависимости»)
- **Что сделать:** привести существующие модули (`build`, `check`, `init`) к
  каноническим швам MODULE.md: выделить `ports/` (output ports: файловые
  репозитории, публикатор), `adapters/` (реализации IO из текущего `data/`),
  `domain/`, `usecases/`. Инвариант: usecases зависят только от ports+domain,
  не от adapters; adapters реализуют ports. Без ADR-отступлений.
- **Тесты:** структурный линт/импорт-граф (`tests` не нужны; проверяется
  verification gate #13/#14).

### 5. [ci] Синхронизация CI с compose/verify

- **Зависит от:** 3 (broker в локальном compose)
- **Спек:** —
- **Что сделать:** сверить `.github/workflows/ci.yml`, `.gitlab-ci.yml` с
  verification gate
  ([`<methodology-repo>`/docs/guide/40-verify.md](https://github.com/TheCipherKeeper/ai-project-template/blob/main/docs/guide/40-verify.md)):
  lint/test/build + (опционально) сборка артефактов через `cybercity-data build`.
  Убедиться, что `docker-compose.yml` (брокер+сервис) проходит healthcheck в CI.
- **Тесты:** CI зелёный на feat-ветке.

---

## Готово

(пусто — задачи выше не реализованы; `model`/`allocator`/`build`/`check` уже
существуют как зрелый код, но формализация швов и broker-producer — TODO)