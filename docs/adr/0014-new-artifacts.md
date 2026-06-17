# ADR-0014: Новые артефакты: `attack-surface.json`, `inventory.md`, `changes.json`

## Status

Accepted

## Context

Потребителям нужны дополнительно: публичная attack-surface, инвентарь
обнаруженных ассетов сервисов и дифф модели с предыдущей сборкой.

## Decision

Добавлены артефакты `attack-surface.json`, `inventory.md`, `changes.json`
(поверх базового набора ADR-0007).

## Consequences

- Расширенный контракт data → engine/ui.
- CI загружает новые артефакты.
- Добавлено в Unreleased (CHANGELOG: «Новые артефакты сборки»).

## Related

- [ADR-0007](0007-build-artifacts.md) — базовые артефакты.