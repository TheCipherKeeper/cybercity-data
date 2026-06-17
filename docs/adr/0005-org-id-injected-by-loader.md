# ADR-0005: `org_id` инъецируется loader'ом, не повторяется в YAML

## Status

Accepted

## Context

`org_id` выводится из имени папки организации (ADR-0001). Повторять его в каждом
сервисе в YAML — лишний шум и источник рассинхрона с папкой.

## Decision

`services[].org_id` не пишется в YAML; loader подставляет `org_id` из имени
папки организации.

## Consequences

- Меньше копипасты в `config.yml`.
- Невозможно рассинхронить `org_id` сервиса с папкой организации.

## Related

- [ADR-0001](0001-per-org-layout.md) — per-org layout.