# ADR-0004: `Service.decoy` помечает simulation-only mock-сервисы

## Status

Superseded — см.
[`ADR-0019`](0019-service-honeypot-purpose.md). Поле `Service.decoy` переименовано
в `Service.honeypot` (назначение-наживка); cross-field-правила `decoy-criticality`/
`decoy-write-real` → `honeypot-criticality`/`honeypot-write-real`. `runtime_kind`
(deployment-time) — в `cybercity-manage`, см. umbrella ADR-0004. Тело ADR сохранено
как история.

## Context

Для плотности симуляции нужны массовые mock-сервисы (decoys/honeypots), не
связанные с security-слоём. Они не должны считаться реальными ассетами и не
должны иметь критичность или писать в реальные сервисы.

## Decision

Поле `Service.decoy {kind, fingerprint, os_hint, note}` помечает
simulation-only mock-сервис. Cross-field правила `decoy-criticality` (decoy не
может быть `critical`) и `decoy-write-real` (decoy не может `db-write` /
`backup-of` реальный сервис) ограничивают деков.

## Consequences

- Декои дают плотность графа без влияния на реальную модель.
- Checker защищает реальные сервисы от деков.

## Related

- [ADR-0011](0011-links-directed.md) — направленные связи.
- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — cross-field правила `decoy-criticality`, `decoy-write-real`.