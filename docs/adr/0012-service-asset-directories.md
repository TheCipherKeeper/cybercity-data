# ADR-0012: Опциональные `services/<svc-id>/` для runtime-ассетов; описание сервиса — в `config.yml`

## Status

Accepted

## Context

Сервис может иметь runtime-ассеты (конфиги, сертификаты), но каноническое
описание сервиса должно быть единым источником правды.

## Decision

Опциональные ассеты живут в `organizations/<org>/services/<svc-id>/`.
Каноническое описание сервиса — в `config.yml`. Имя папки ассетов должно
совпадать с `id` сервиса; иначе checker выдаёт warning `assets`.

## Consequences

- Ассеты отделены от декларации.
- Правило `assets` проверяет соответствие папки ассетов объявленному сервису.

## Related

- [ADR-0001](0001-per-org-layout.md) — per-org layout.
- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — cross-field правило `assets`.