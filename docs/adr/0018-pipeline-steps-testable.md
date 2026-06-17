# ADR-0018: Service-методы разложены в именованные pipeline-шаги

## Status

Accepted

## Context

Сборка/проверка — последовательность шагов (load → allocate → validate →
render → write). Монолитный метод плохо тестируется и не переиспользуется между
`check` и `build`.

## Decision

Методы Service/UseCase разложены в именованные pipeline-шаги: `_load`,
`_allocate`, `_validate`, `_render`, `_write`. Общий pipeline
load/allocate/check вынесен в `use_cases/validate_step.py`.

## Consequences

- Каждый шаг тестируется изолированно.
- Переиспользование между `check` и `build`.

## Related

- [ADR-0017](0017-layered-cli-architecture.md) — слоистая архитектура CLI.
- [ADR-0006](0006-cli-commands-exit-codes.md) — команды CLI.
- [`docs/DATA_FLOW.md`](../DATA_FLOW.md) — общий поток.