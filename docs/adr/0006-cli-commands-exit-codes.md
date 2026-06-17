# ADR-0006: CLI: `check`, `build`, `init`; exit codes 0/1

## Status

Accepted

## Context

Нужен воспроизводимый CLI-интерфейс с тремя операциями; CI требует ясных exit
codes для решения «пропустить/провалить».

## Decision

CLI `cybercity-data` имеет три команды:

- `check` — только валидация;
- `build` — валидация + запись артефактов (пропускается при ошибках);
- `init` — скаффолд новой организации.

Exit codes: `0` — успех, `1` — ошибка данных/валидации.

## Consequences

- CI/пайплайн опирается на exit codes.
- `build` не пишет артефакты при ошибках `check`.

## Related

- [ADR-0008](0008-strict-warnings-fail-ci.md) — `--strict`.
- [ADR-0017](0017-layered-cli-architecture.md) — слоистая архитектура CLI.
- [ADR-0018](0018-pipeline-steps-testable.md) — pipeline-шаги.