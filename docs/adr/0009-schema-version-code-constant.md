# ADR-0009: `CityNetwork.version` — константа в коде; нет city-wide файла аллокации

## Status

Accepted

## Context

Версия схемы и адресация — свойства кода/сборки, а не декларативного YAML.
Хранить city-wide файл аллокации в репозитории излишне (адресация генерируется).

## Decision

`CityNetwork.version` — константа в коде (`SCHEMA_VERSION`). Отдельного
city-wide файла аллокации нет; аллокация генерируется в памяти аллокатором
(ADR-0016).

## Consequences

- Версия схемы централизована в коде.
- Адресация не хранится в репозитории; воспроизводима через `--seed`.

## Related

- [ADR-0002](0002-pydantic-v2-extra-forbid.md) — Pydantic-схема.
- [ADR-0016](0016-generated-networks-allocator.md) — генерация аллокации.