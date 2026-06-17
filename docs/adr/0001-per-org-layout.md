# ADR-0001: Per-org layout; loader собирает in-memory `CityNetwork`

## Status

Accepted

## Context

Модель города состоит из многих организаций. Правка одной организации не
должна затрагивать остальные; люди ревьюят изменения по организации; LLM-агент
читает один файл за раз (см. `docs/ORGANIZATIONS.md`, раздел «Зачем отдельные
файлы»).

## Decision

Каждая организация — отдельная папка `organizations/<id>/` с одним файлом
`config.yml` (имя папки совпадает с `id`). Loader обходит папки, читает каждый
`config.yml` и собирает in-memory `CityNetwork` (`organizations[]`,
`services[]`, `links[]`). Underscore-папки (`_archive/`, `_draft/`, `_wip/`)
игнорируются.

## Consequences

- Diff правки одной организации — в одном `config.yml`.
- Добавление/удаление организации — созданием/удалением папки.
- Loader — единая точка сборки модели в память.

## Related

- [ADR-0005](0005-org-id-injected-by-loader.md) — инъекция `org_id` из папки.
- [ADR-0012](0012-service-asset-directories.md) — ассеты сервисов внутри папки org.
- [`docs/ORGANIZATIONS.md`](../ORGANIZATIONS.md) — per-org layout conventions.