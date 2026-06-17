# ADR-0002: Pydantic v2, `extra="forbid"`

## Status

Accepted

## Context

Нужна строгая схема декларативной модели с явной валидацией полей: опечатки и
лишние поля в YAML должны падать, а не молча игнорироваться. Схема должна
самодокументироваться и быть доступной downstream-потребителям.

## Decision

Модель реализована на Pydantic v2 с `extra="forbid"` (`domain/models.py`).
JSON Schema эмитируется Pydantic и пишется в `schema.json`.

## Consequences

- Любые неизвестные/лишние поля в YAML → ошибка валидации.
- Схема самодокументируется и переиспользуется downstream.
- Дополняется статической проверкой типов (ADR-0015).

## Related

- [ADR-0009](0009-schema-version-code-constant.md) — `SCHEMA_VERSION`.
- [ADR-0015](0015-mypy-strict.md) — `mypy --strict`.
- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — модель данных (v3.0).