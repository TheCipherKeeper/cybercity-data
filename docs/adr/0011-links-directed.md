# ADR-0011: Связи направленные; нет флага `bidirectional`

## Status

Accepted

## Context

Связи в модели — направленные. Флаг `bidirectional` и many-to-many связи
усложняли граф и валидацию уникальности.

## Decision

Связи всегда направленные; флага `bidirectional` нет. Двунаправленное отношение
— две явные связи. Уникальность обеспечивается по `(from, to, kind)`.

## Consequences

- Граф строго направленный; уникальность `(from, to, kind)`.
- Закреплено в v0.4.0 (CHANGELOG: «Связи теперь всегда направленные;
  двунаправленные и many-to-many удалены»).

## Related

- [ADR-0019](0019-service-honeypot-purpose.md) — honeypot-сервисы (бывший `decoy`, см. ADR-0004).
- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — cross-field правило `ids`.