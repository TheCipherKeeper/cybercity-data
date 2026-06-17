# ADR-0007: Базовые артефакты сборки

## Status

Accepted

## Context

Нужен фиксированный набор артефактов сборки для потребителей: `cybercity-engine`
(runtime), `cybercity-ui` (граф) и человекочитаемый вид.

## Decision

Базовый набор артефактов `cybercity-data build`: `network.json`, `network.md`,
`schema.json`, `topology.json`, `network.html`, `engine.zip`.

## Consequences

- Фиксированный контракт data → engine/ui для v0.3.0.
- Расширен новыми артефактами в ADR-0014; `engine.zip` всегда генерируется
  (ADR-0013).

## Related

- [ADR-0013](0013-engine-zip-always-produced.md) — `engine.zip` всегда.
- [ADR-0014](0014-new-artifacts.md) — дополнительные артефакты.