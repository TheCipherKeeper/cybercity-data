# CyberCity — City Data

[![Part of CyberCity](https://img.shields.io/badge/CyberCity-composition-blueviolet)](https://github.com/TheCipherKeeper/cybercity)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)](LICENSE-DOCS)

Канонический декларативный слой данных цифрового двойника CyberCity:
организации, сети, сервисы, связи. Модель города — направленный граф
(сервисы — узлы, связи — рёбра); прочие инструменты потребляют этот граф для
симуляции трафика, проведения security-учений и визуализации. Тот же
репозиторий авторит сценарии учений и является **источником правды** о модели
города для остальных слоёв.

> Состав из 6 репозиториев, контракты и доверительная граница — в
> [`cybercity/COMPOSITION.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/COMPOSITION.md).

В v3.0 декларативный слой описывает только топологию — организации, роли сетей,
размещение сервисов и связи. Конкретная IP-адресация генерируется аллокатором,
так что модель сфокусирована на структуре, а не на адресной бухгалтерии. Связи
всегда направленные; двунаправленная связь — это две явные связи.

- [Архитектура и модель данных](docs/ARCHITECTURE.md)
- [Поток данных](docs/DATA_FLOW.md)
- [Conventions per-org layout](docs/ORGANIZATIONS.md)
- [Правила для AI-агентов и контрибьюторов](AGENTS.md)
- [Руководство разработчика](docs/DEVELOPMENT.md)
- Сгенерированный вид: `build/network.md` (после `cybercity-data build .`)

## Quick start

```bash
uv sync
uv run cybercity-data check .
uv run cybercity-data build .
uv run pytest -q
uv run ruff check
uv run mypy --strict src/cybercity_data
```

## CLI

```
cybercity-data check [PATH] [--json] [--strict] [--seed SEED]   # только валидация
cybercity-data build [PATH] [--out DIR] [--json] [--strict] [--clean] [--seed SEED]
cybercity-data init ID --kind KIND [--path PATH] [--empty]
```

- `check` — только валидация.
- `build` — валидация + запись артефактов; пропускается при ошибках.
- `init` — скаффолд новой организации в `organizations/<ID>/`; по умолчанию с
  примером сети и сервиса, `--empty` — минимальный шаблон.
- `--strict` — предупреждения считаются ошибками.
- `--clean` — удалить выходной каталог перед рендерингом.
- `--seed` — воспроизводимая аллокация IP; без флага каждая сборка использует
  свежую случайную.

## Артефакты

`cybercity-data build` создаёт в `build/`: `network.json`, `network.md`,
`schema.json`, `topology.json`, `network.html`, `attack-surface.json`,
`inventory.md`, `changes.json`, каталог `runtime/` и собирает `engine.zip` —
контракт **data → engine/ui**. Полный список артефактов и их назначение — в
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Лицензии

- Код / YAML: [MIT](LICENSE)
- Документация: [CC BY 4.0](LICENSE-DOCS)