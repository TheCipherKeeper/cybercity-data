# ADR-0008: `--strict` делает warnings ошибками в CI

## Status

Accepted

## Context

Некоторые cross-field правила — warnings (например, `assets`), а не errors. В
CI нужен режим, где warnings тоже проваливают сборку.

## Decision

Флаг `--strict` трактует warnings как ошибки (exit 1).

## Consequences

- CI может гонять `--strict` для строгого режима.
- По умолчанию warnings не проваливают `build`.

## Related

- [ADR-0006](0006-cli-commands-exit-codes.md) — exit codes 0/1.