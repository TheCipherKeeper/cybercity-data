# CyberCity Data — Архитектура

> **TL;DR.** `cybercity-data` — канонический декларативный слой данных
> цифрового двойника CyberCity: организации, сети, сервисы, связи. `check`
> валидирует; `build` пишет артефакты. Конкретная IP-адресация генерируется, а
> не декларируется.

> Системная архитектура (контекст, доверительная граница, слои развёртывания) —
> в [`cybercity/ARCHITECTURE.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/ARCHITECTURE.md).
> Состав проекта и контракты — в
> [`cybercity/COMPOSITION.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/COMPOSITION.md).
> Ниже — только внутреннее устройство репозитория данных.

- [README](../README.md)
- [Conventions per-org layout](ORGANIZATIONS.md)
- [CI/CD-пайплайны](PIPELINES.md)
- [Поток данных](DATA_FLOW.md)
- [Руководство разработчика](DEVELOPMENT.md)
- [Индекс ADR](adr/README.md)

## Структура репозитория

```
cybercity-data/
├── README.md                    ← quick start + сводка
├── AGENTS.md                    ← правила для AI-агентов
├── CONTRIBUTING.md              ← указатель → docs/DEVELOPMENT.md
├── CHANGELOG.md
├── LICENSE                      ← лицензия на код / YAML (MIT)
├── LICENSE-DOCS                 ← лицензия на документацию (CC BY 4.0)
├── pyproject.toml               ← пакет + CLI `cybercity-data`
├── .gitlab-ci.yml               ← lint / test / check / build
├── docs/
│   ├── ARCHITECTURE.md          ← вы здесь
│   ├── DEVELOPMENT.md           ← руководство разработчика
│   ├── DATA_FLOW.md             ← поток данных
│   ├── ORGANIZATIONS.md         ← per-org layout conventions
│   ├── PIPELINES.md             ← CI/CD-пайплайны
│   └── adr/                     ← архитектурные решения (NNNN-*.md + индекс)
├── organizations/
│   └── <org>/
│       ├── config.yml           # данные организации (v3.0 — только логика)
│       └── services/            # опциональные ассеты сервисов
├── src/cybercity_data/
│   ├── domain/                  # чистая бизнес-логика
│   │   ├── models.py            # Pydantic v2 схема (декларативный слой)
│   │   ├── allocator.py         # автоматическая аллокация сетей / IP
│   │   └── checker.py           # cross-field правила
│   ├── data/                    # IO-адаптеры
│   │   ├── loader.py            # per-org → CityNetwork
│   │   ├── renderer.py          # генерация артефактов
│   │   ├── filesystem.py        # запись на диск / очистка
│   │   ├── git.py               # чтение диффа с предыдущей сборкой
│   │   └── zip.py               # сборщик engine.zip
│   ├── use_cases/               # оркестрация
│   │   ├── check.py             # CheckUseCase
│   │   ├── build.py             # BuildUseCase
│   │   ├── init.py              # InitUseCase
│   │   └── validate_step.py     # общий pipeline load/allocate/check
│   ├── dto/                     # result DTO use-case'ов
│   │   ├── build_result.py
│   │   ├── check_result.py
│   │   ├── counts.py
│   │   └── init_result.py
│   ├── services/                # application services (CLI facade)
│   │   ├── build.py
│   │   ├── check.py
│   │   ├── init.py
│   │   └── exceptions.py
│   ├── controllers/             # CLI + presenters
│   │   ├── app.py               # Typer-приложение
│   │   ├── commands.py          # регистрация команд
│   │   ├── dependencies.py      # DI для CLI
│   │   ├── responses.py         # вывод human / JSON
│   │   └── handlers/            # обработчики команд
│   │       ├── build.py
│   │       ├── check.py
│   │       └── init.py
│   └── __init__.py              # public API re-exports
├── tests/
│   ├── conftest.py
│   ├── test_property.py
│   ├── data/
│   │   ├── test_filesystem.py
│   │   ├── test_git.py
│   │   ├── test_loader.py
│   │   ├── test_renderer.py
│   │   └── test_zip.py
│   ├── domain/
│   │   ├── test_allocator.py
│   │   ├── test_checker.py
│   │   └── test_models.py
│   ├── use_cases/
│   │   ├── test_build.py
│   │   ├── test_check.py
│   │   └── test_init.py
│   └── controllers/
│       └── test_cli.py
└── build/                       ← сгенерированные артефакты (gitignored)
    ├── network.json             # канонический дамп (без сгенерированных IP)
    ├── network.md               # человекочитаемая проекция
    ├── schema.json              # JSON Schema
    ├── topology.json            # граф для UI / симулятора
    ├── network.html             # самодостаточный интерактивный просмотрщик
    └── engine.zip               # пакет runtime для cybercity-engine
```

## Модель данных (v3.0)

### `Organization`

```
id, name, kind
description
networks[]                       # ОБЯЗАТЕЛЬНО в v3.0
```

### `Network`

```
id, org_id, name, kind           # kind задаёт генерируемый CIDR
description
```

`kind ∈ {dmz, lan, ot, mgmt, internet}`.

### Типы `Link`

`kind ∈ {api-call, auth, db-read, db-write, log-sink, backup-of, trusts, vendor-vpn, dns-query, ntp-query}`.

Связи всегда направленные. Если отношение двунаправленное — декларируются две
явные связи.

### `Service`

```
id, org_id, name, description?, kind, exposure, host
network_id                       # логическое размещение; ОБЯЗАТЕЛЬНО в v3.0
software {vendor, product, version?, cve_id?}
auth, data_classification, criticality
ports, os_hint
decoy {kind, fingerprint, os_hint, note}   # опциональный mock-сервис
```

### `Link`

```
from_service, to_service, kind, protocol?
encryption, label
```

### `CityNetwork`

```
version                            # версия схемы, константа в коде
organizations[], services[], links[]
```

### `Allocation` (генерируется)

```
org_index: dict[str, int]          # network_index на org
net_cidr: dict[str, str]           # CIDR на сеть
svc_ip: dict[str, str]             # bind_ip на сервис
```

## CLI

```bash
cybercity-data check [PATH] [--json] [--strict] [--seed SEED]   # validate only
cybercity-data build [PATH] [--out DIR] [--json] [--strict] [--clean] [--seed SEED]
cybercity-data init ID --kind KIND [--path PATH] [--empty]
```

- `check` — только валидация.
- `build` — валидация + запись артефактов; пропускается при ошибках.
- `init` — скаффолд новой организации. По умолчанию включает пример сети и
  сервиса; `--empty` оставляет списки пустыми.
- `--strict` — предупреждения считаются ошибками.
- `--clean` — удалить выходной каталог перед рендерингом.
- `--seed` — воспроизводимая аллокация; без флага каждая сборка использует
  свежую случайную.

## Cross-field правила

| Код | Уровень | Что проверяет |
|---|---|---|
| `ids` | error | уникальный id для org/network/service; уникальная связь `(from,to,kind)` |
| `refs` | error | `service.org_id` и endpoints связи существуют |
| `network-belongs` | error | `service.network_id` существует и принадлежит той же org |
| `ip-in-network` | error | сгенерированный `bind_ip` лежит внутри сгенерированного CIDR сети |
| `ip-unique` | error | сгенерированный `bind_ip` уникален внутри одной сети |
| `network-overlap` | error | сгенерированные CIDR не пересекаются |
| `ip-scheme` | error | сгенерированные CIDR лежат под `10.<org_index>.x.x` |
| `exposure-network` | error | `exposure` разрешён для `kind` сети |
| `self-loop` | error | связь не указывает на саму себя |
| `software` | error | `cve_id` соответствует `CVE-YYYY-NNNNN` (только формат) |
| `assets` | warning | каталог ассетов сервиса соответствует объявленному сервису |
| `decoy-criticality` | error | decoy-сервисы не помечены `critical` |
| `decoy-write-real` | error | decoy-сервисы не пишут/бэкапят реальные сервисы |

## ADR

Архитектурные решения вынесены в отдельные файлы — см.
[индекс ADR](adr/README.md) (`ADR-0001`..`ADR-0018`). Сквозные решения,
затрагивающие несколько репозиториев, — в
[`cybercity/adr/`](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/).

## Артефакты

`build/` содержит:

- `network.json` — канонический дамп `CityNetwork` (только декларативные поля,
  без сгенерированных IP).
- `network.md` — человекочитаемая проекция.
- `schema.json` — JSON Schema, эмитируемая Pydantic.
- `topology.json` — граф для UI/симулятора (включает сгенерированные
  `bind_ip` / `network_index`).
- `network.html` — самодостаточный интерактивный просмотрщик графа.
- `attack-surface.json` — публично открытые сервисы и их метаданные.
- `inventory.md` — обнаруженные каталоги ассетов сервисов.
- `changes.json` — git-дифф относительно предыдущей сборки.
- `engine.zip` — пакет runtime для `cybercity-engine` (внутри
  `runtime/engine.json`, `topology.json`, `attack-surface.json`, `schema.json`).

## Лицензии

- Код / YAML: [MIT](../LICENSE)
- Документация: [CC BY 4.0](../LICENSE-DOCS)