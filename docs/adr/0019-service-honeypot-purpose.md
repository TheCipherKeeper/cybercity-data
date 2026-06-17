# ADR-0019: `Service.honeypot` — флаг назначения-наживки (переименование из `decoy`)

## Status

Accepted

## Context

Ранее (ADR-0004) поле `Service.decoy` помечало simulation-only mock-сервисы. Термин
«decoy» оказался перегружен: одновременно runtime-режим (`{real, simulated, decoy}`) и
блок-наживка в data-модели, и «simulation-only mock». Сквозное решение (umbrella
ADR-0004) упраздняет «decoy» как runtime-режим: остаются `runtime_kind ∈ {vm, container,
lite}` (deployment-time, в `cybercity-manage`) + ортогональный флаг назначения-наживки.

Сам блок-наживка остаётся свойством сервиса в `cybercity-data` (это топологическое
свойство, не deployment-concern), но переименовывается из `decoy` в `honeypot`, чтобы
развести понятия и убрать слово «decoy» из проекта.

## Decision

Поле `Service.honeypot {kind, fingerprint, os_hint, note}` помечает сервис как
honeypot / bait-purpose (наживку). Это свойство сервиса в декларативной модели,
ортогональное `runtime_kind`: honeypot-сервис исполняется как `vm`/`container`/`lite`
на усмотрение manage, но обычно `lite`.

Cross-field правила переименованы и сохраняют семантику:
- `honeypot-criticality` — honeypot-сервис не может быть `critical`.
- `honeypot-write-real` — honeypot-сервис не может `db-write`/`backup-of` реальный сервис.

Контрактные артефакт-ключи (data→engine→ui) переименованы: `is_mock`→`is_honeypot`,
`mock_services`→`honeypot_services`, `decoy_profile`→`honeypot_profile`; id
`decoy-printer-01`→`honeypot-printer-01`.

## Consequences

- Слово «decoy» уходит из модели данных; единственный назначение-флаг — `honeypot`.
- `runtime_kind` в `cybercity-data` НЕ добавляется (deployment-time, живёт в manage).
- Honeypot-сервис наблюдается коллектором как любая другая runtime-цель (класса
  «engine-synthesized service events» нет — движок регистратор, не симулятор).
- Checker по-прежнему защищает реальные сервисы от honeypot-ов (правила сохранились).

## Alternatives considered

- **Оставить `decoy`.** Перегрузка термина сохраняется; противоречит umbrella ADR-0004.
- **Вынести honeypot в manage (как runtime_kind).** Нет: назначение-наживка —
  топологическое свойство (отражается в артефакте, нужно UI/checker), а не deployment.
- **Убрать блок целиком, оставить bool-флаг.** Потеря `kind`/`fingerprint` (нужны для
  отрисовки и для manage-провижнинга lite-стаба).

## Related

- [ADR-0004](0004-service-decoy-mock.md) — предшественник (Superseded).
- [ADR-0011](0011-links-directed.md) — направленные связи.
- [`cybercity/adr/0004-runtime-kind-vm-container-lite.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/0004-runtime-kind-vm-container-lite.md) — umbrella: `runtime_kind {vm, container, lite}` + `honeypot` purpose; движок = регистратор.
- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — cross-field правила `honeypot-criticality`, `honeypot-write-real`.