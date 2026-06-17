# ADR — cybercity-data

Локальные архитектурные решения репозитория данных. Сквозные решения
(затрагивающие несколько репозиториев) — в
[`cybercity/adr/`](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/).

| № | Решение | Статус |
|---|---------|--------|
| [0001](0001-per-org-layout.md) | Per-org layout; loader собирает in-memory `CityNetwork` | Accepted |
| [0002](0002-pydantic-v2-extra-forbid.md) | Pydantic v2, `extra="forbid"` | Accepted |
| [0003](0003-explicit-networks-ip-v2.md) | Явные сети и IP-адреса в v2.0 | Superseded (см. ADR-0016) |
| [0004](0004-service-decoy-mock.md) | `Service.decoy` помечает simulation-only mock-сервисы | Accepted |
| [0005](0005-org-id-injected-by-loader.md) | `org_id` инъецируется loader'ом, не повторяется в YAML | Accepted |
| [0006](0006-cli-commands-exit-codes.md) | CLI: `check`, `build`, `init`; exit codes 0/1 | Accepted |
| [0007](0007-build-artifacts.md) | Базовые артефакты сборки | Accepted |
| [0008](0008-strict-warnings-fail-ci.md) | `--strict` делает warnings ошибками в CI | Accepted |
| [0009](0009-schema-version-code-constant.md) | `CityNetwork.version` — константа в коде; нет city-wide файла аллокации | Accepted |
| [0010](0010-organization-structural-only.md) | `Organization` хранит только структурные поля | Accepted |
| [0011](0011-links-directed.md) | Связи направленные; нет флага `bidirectional` | Accepted |
| [0012](0012-service-asset-directories.md) | Опциональные `services/<svc-id>/` для runtime-ассетов; описание сервиса — в `config.yml` | Accepted |
| [0013](0013-engine-zip-always-produced.md) | `engine.zip` генерируется всегда, даже без ассетов | Accepted |
| [0014](0014-new-artifacts.md) | Новые артефакты: `attack-surface.json`, `inventory.md`, `changes.json` | Accepted |
| [0015](0015-mypy-strict.md) | `mypy --strict` для статической проверки типов | Accepted |
| [0016](0016-generated-networks-allocator.md) | Сети и IP генерируются `allocator.py`; декларативная модель описывает только топологию | Accepted |
| [0017](0017-layered-cli-architecture.md) | Слоистая архитектура CLI: Controller → Service → UseCase → Data/IO | Accepted |
| [0018](0018-pipeline-steps-testable.md) | Service-методы разложены в именованные pipeline-шаги | Accepted |

Формат ADR — в
[`cybercity/CONVENTIONS.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/CONVENTIONS.md).