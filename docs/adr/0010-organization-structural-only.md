# ADR-0010: `Organization` хранит только структурные поля

## Status

Accepted

## Context

У организации были свободные narrative-поля, размывающие декларативную модель и
затрудняющие валидацию.

## Decision

`Organization` хранит только структурные поля (`id`, `name`, `kind`,
`description`, `networks[]`). Narrative-метаданные живут в `description` или
удаляются; заметки — через YAML-комментарии (`#`).

## Consequences

- Модель сфокусирована на структуре; меньше дрейфа.
- Закреплено в v0.4.0 (CHANGELOG: «Схема организации упрощена»).

## Related

- [ADR-0002](0002-pydantic-v2-extra-forbid.md) — `extra="forbid"`.
- [`docs/ORGANIZATIONS.md`](../ORGANIZATIONS.md) — соглашения.