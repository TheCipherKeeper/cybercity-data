# ADR-0017: Слоистая архитектура CLI: Controller → Service → UseCase → Data/IO

## Status

Accepted

## Context

CLI должен быть тонким; бизнес-логика — тестируемой и изолированной от IO;
ошибки разных адаптеров нужно нормализовать в единый тип.

## Decision

Слоистая архитектура CLI:

- **Controllers** (`controllers/`) — CLI (Typer) + presenters (human/JSON).
- **Services** (`services/`) — тонкий facade: собирает адаптеры, транслирует
  ошибки адаптеров в `ApplicationError`.
- **UseCases** (`use_cases/`) — оркестрация (check/build/init).
- **Data/IO** (`data/`) — loader / renderer / filesystem / git / zip.
- **Domain** (`domain/`) — чистая логика (models / allocator / checker), без
  зависимостей от IO.

## Consequences

- Чёткие слои; зависимости направлены внутрь (domain не импортирует adapters).
- Ошибки нормализованы в `ApplicationError`.
- Высокая тестируемость каждого слоя.

## Related

- [ADR-0018](0018-pipeline-steps-testable.md) — pipeline-шаги внутри Service/UseCase.
- [ADR-0006](0006-cli-commands-exit-codes.md) — команды CLI.
- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — структура репозитория.