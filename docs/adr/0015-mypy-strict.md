# ADR-0015: `mypy --strict` для статической проверки типов

## Status

Accepted

## Context

Репозиторий зрелый; помимо тестов и валидатора нужна статическая гарантия типов
на уровне кода.

## Decision

`mypy --strict` запускается в CI и pre-commit (`mypy --strict
src/cybercity_data`). Никакие `Any`-эскейпы без явного `# type: ignore` не
допускаются.

## Consequences

- Дополнительный слой строгости поверх тестов.
- Появляется job typecheck в CI (GitHub Actions и GitLab CI).
- Добавлено в Unreleased (CHANGELOG: «Статическая проверка типов `mypy --strict`
  в CI и pre-commit хуках»).

## Related

- [ADR-0002](0002-pydantic-v2-extra-forbid.md) — Pydantic v2.
- [ADR-0006](0006-cli-commands-exit-codes.md) — CLI.
- [`docs/DEVELOPMENT.md`](../DEVELOPMENT.md) — linting и typecheck.