# CyberCity — City Data

[![CyberCity-composition](https://img.shields.io/badge/CyberCity-composition-blueviolet)](https://github.com/TheCipherKeeper/cybercity)
[![code-MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![docs-CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)](LICENSE-DOCS)

`cybercity-data` — Python-сервис cybercity: декларативная модель города
(source of truth) + авторинг сценариев/уязвимостей + сборка артефактов. CLI
`cybercity-data` валидирует YAML-декларацию (`organizations/<org>/config.yml`),
генерирует IP/CIDR аллокатором и собирает `engine.zip`/`topology.json`/`overlays`
(контракт **data → engine/ui/manage**, out-of-band файлы). После завершения
Phase 2 также публикует `city.build.completed` в брокер Redpanda
([ADR-0010](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/0010-data-broker-producer.md)).

> Состав из репозиториев, контракты и доверительная граница — в
> [`cybercity/COMPOSITION.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/COMPOSITION.md)
> (канон). Версия методологии закреплена в `.methodology.yml`.

В v3.0 декларативный слой описывает только топологию (организации, роли сетей,
размещение сервисов, направленные связи); IP-адресация генерируется аллокатором.

- [Архитектура](docs/ARCHITECTURE.md)
- [Спеки модулей](docs/specs/)
- [Хаб и бэклог программы](https://github.com/TheCipherKeeper/cybercity)
- [Правила для AI-агентов](AGENTS.md)
- [Руководство разработчика](docs/DEVELOPMENT.md)
- [Conventions per-org layout](docs/ORGANIZATIONS.md) · [CI/CD-пайплайны](docs/PIPELINES.md)

## Quick start

```bash
uv sync
uv run cybercity-data check .
uv run cybercity-data build .
uv run pytest -q
uv run ruff check
uv run mypy --strict src/cybercity_data
```

Локальная разработка с брокером (для Phase 2 — публикации `city.build.completed`):

```bash
cp .env.example .env
docker compose up --build   # broker (Redpanda) + data
```

## CLI

```
cybercity-data check [PATH] [--json] [--strict] [--seed SEED]   # только валидация
cybercity-data build [PATH] [--out DIR] [--json] [--strict] [--clean] [--seed SEED]
cybercity-data init ID --kind KIND [--path PATH] [--empty]
```

- `check` — только валидация.
- `build` — валидация + запись артефактов; пропускается при ошибках.
- `init` — скаффолд новой организации; `--empty` — минимальный шаблон.
- `--strict` — предупреждения считаются ошибками.
- `--clean` — удалить выходной каталог перед рендерингом.
- `--seed` — воспроизводимая аллокация IP; без флага — свежая случайная.

## Импорты Python

Корневой пакет `cybercity_data` больше не переэкспортирует внутренние типы и
функции. Репозиторные потребители используют явные канонические пути модуля:

```python
from cybercity_data.city_model.adapters.inbound.domain.checker import check
from cybercity_data.city_model.adapters.inbound.domain.models import CityNetwork
```

Прежние импорты вида `from cybercity_data import CityNetwork, check` намеренно
несовместимы с канонической модульной границей. Команды CLI и файловые контракты
при этом не изменились.

## Артефакты

`cybercity-data build` создаёт в `build/`: `network.json`, `network.md`,
`schema.json`, `topology.json`, `network.html`, `attack-surface.json`,
`inventory.md`, `changes.json`, каталог `runtime/` и `engine.zip` — контракт
**data → engine/ui**. Полный список и назначение — в
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Лицензии

- Код / YAML: [MIT](LICENSE)
- Документация: [CC BY 4.0](LICENSE-DOCS)
