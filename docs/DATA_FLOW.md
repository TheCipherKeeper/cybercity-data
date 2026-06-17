# CyberCity Data — Поток данных

> Системный поток данных и контракты между репозиториями — в
> [`cybercity/COMPOSITION.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/COMPOSITION.md)
> (раздел «Поток данных и контракты»). Ниже — только внутренний поток
> `cybercity-data` от YAML-декларации до артефакта `engine.zip`.

## Общий поток

```text
organizations/<id>/config.yml   ┐
  + organizations/<id>/services/ ┘
        │
        ▼
   loader              per-org → in-memory CityNetwork (org_id инъецируется)
        │
        ▼
   allocator           сети → CIDR, сервисы → bind_ip
                       воспроизводимо через --seed (иначе случайная аллокация)
        │
        ▼
   checker             13 cross-field правил (ids/refs/ip-in-network/…)
                       ошибки → build пропускается
        │
        ▼
   renderer            генерация строк артефактов
        │
        ▼
   filesystem          запись в build/  (с --clean — поверх чистого каталога)
        │
        ▼
   zip                 сборка engine.zip (внутри runtime/…)
        │
        ▼
   build/              9 артефактов + engine.zip
```

Pipeline реализован как именованные шаги (`_load`, `_allocate`, `_validate`,
`_render`, `_write`) — см. [ADR-0018](adr/0018-pipeline-steps-testable.md);
каждый шаг тестируется изолированно. Слоистая архитектура CLI
(Controller → Service → UseCase → Data/IO) — см.
[ADR-0017](adr/0017-layered-cli-architecture.md).

## Источник: organizations/

Декларативная модель — `organizations/<id>/config.yml` (один файл на
организацию; имя папки совпадает с `id`). Опциональные ассеты сервисов — в
`organizations/<id>/services/<svc-id>/` (см.
[ORGANIZATIONS.md](ORGANIZATIONS.md)). `services[].org_id` не пишется — loader
подставляет его из имени папки (см.
[ADR-0005](adr/0005-org-id-injected-by-loader.md)).

## loader → CityNetwork

`loader` (`src/cybercity_data/data/loader.py`) обходит `organizations/`,
читает каждый `config.yml`, инъецирует `org_id` и собирает in-memory
`CityNetwork` (`organizations[]`, `services[]`, `links[]`, `version`).
Underscore-папки (`_archive/`, `_draft/`, `_wip/`) игнорируются. См.
[ADR-0001](adr/0001-per-org-layout.md).

## allocator

`allocator` (`src/cybercity_data/domain/allocator.py`) генерирует адресацию:

- `org_index` — второй октет городского пространства `10.0.0.0/8`.
- `net_cidr` — CIDR на сеть по её `kind` (`dmz`/`lan`/`ot`/`mgmt`/`internet`).
- `svc_ip` — `bind_ip` сервиса внутри его сети, начиная с `.10`.

Одинаковый `--seed` → одинаковая адресация (воспроизводимость для replay и
тестов). Без `--seed` — свежая случайная аллокация на каждой сборке. См.
[ADR-0016](adr/0016-generated-networks-allocator.md).

## checker

`checker` (`src/cybercity_data/domain/checker.py`) применяет 13 cross-field
правил к собранной `CityNetwork` + сгенерированной `Allocation`. Правила не
short-circuit'ят — собирают все находки. При ошибках `build` пропускает
рендеринг. Полная таблица правил — в [ARCHITECTURE.md](ARCHITECTURE.md).

## renderer → build/

`renderer` (`src/cybercity_data/data/renderer.py`) порождает артефакты;
`filesystem` пишет их в `build/`; `zip` собирает `engine.zip`. С `--clean`
выходной каталог пересоздаётся с нуля. `engine.zip` генерируется всегда, даже
без ассетов (см. [ADR-0013](adr/0013-engine-zip-always-produced.md)).

9 артефактов:

- `network.json` — канонический дамп `CityNetwork` (без сгенерированных IP).
- `topology.json` — граф для UI/симулятора (с `bind_ip` / `network_index`).
- `schema.json` — JSON Schema (Pydantic).
- `attack-surface.json` — публично открытые сервисы + CVE/criticality.
- `inventory.md` — каталоги ассетов сервисов.
- `changes.json` — git-дифф с предыдущей сборкой.
- `network.html` — интерактивный просмотрщик графа.
- `network.md` — человекочитаемая проекция.
- `engine.zip` — пакет runtime (внутри `runtime/engine.json`, `topology.json`,
  `attack-surface.json`, `schema.json`).

## Контракт data → engine/ui

`engine.zip` — контракт между `cybercity-data` и `cybercity-engine` /
`cybercity-ui`. `engine` грузит `engine.zip`, ведёт world-state и причинный
граф; `ui` читает `topology.json` + поток событий `engine`. Авторинг сценариев
(отдельный артефакт — цели, injects, флаги, scoring-rubric, timebox) — контракт
**data → engine**: `data` порождает декларацию, `engine` исполняет.

`build/` лежит в `.gitignore`; CI генерирует артефакты заново на каждом запуске
(см. [PIPELINES.md](PIPELINES.md)).

## Связанные документы

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — внутренняя архитектура, модель данных,
  cross-field правила, артефакты.
- [`ORGANIZATIONS.md`](ORGANIZATIONS.md) — per-org layout conventions.
- [`DEVELOPMENT.md`](DEVELOPMENT.md) — рецепты и тестирование.
- [`cybercity/COMPOSITION.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/COMPOSITION.md)
  — системный поток данных и контракты.