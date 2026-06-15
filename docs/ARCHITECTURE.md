# CyberCity — Data Architecture

> **TL;DR.** `cybercity-data` — canonical declarative data layer for the CyberCity digital twin:
> organizations, networks, services, links. `check` validates; `build` writes artifacts.
> Concrete IP addressing is generated, not declared.

- [README](../README.md)
- [Per-org layout conventions](ORGANIZATIONS.md)
- [CI/CD pipelines](PIPELINES.md)

## Composition

| Слой | Репозиторий | Роль |
|---|---|---|
| Данные (этот репо) | `cybercity-data` | YAML-модель + loader + checker + builder + allocator |
| Симуляция | `cybercity-simulator` | запускает модель, эмулирует трафик и события |
| UI | `cybercity-ui` | рисует граф из `build/topology.json` |
| Агенты | `cybercity-agents` | LLM-генератор недостающих org'ов |
| Blueprints | `cybercity-blueprints` | шаблоны организаций |
| Сценарии / безопасность | `cybercity-scenarios` | внешний слой, потребляет эту модель |

## Repository layout

```
cybercity-data/
├── README.md                    ← quickstart
├── LICENSE                      ← code / YAML license
├── pyproject.toml               ← package + CLI `cybercity-data`
├── .gitlab-ci.yml               ← lint / test / check / build
├── docs/
│   ├── ARCHITECTURE.md          ← вы здесь
│   ├── ORGANIZATIONS.md         ← per-org layout conventions
│   └── LICENSE-DOCS             ← docs license
├── organizations/
│   └── <org>/
│       ├── config.yml           # per-organization data (v3.0 logical only)
│       └── services/            # optional per-service asset directories
├── src/cybercity_data/
│   ├── domain/                  # pure business logic
│   │   ├── models.py            # Pydantic v2 schema (declarative layer)
│   │   ├── allocator.py         # automatic network / IP allocation
│   │   └── checker.py           # cross-field rules
│   ├── data/                    # IO adapters
│   │   ├── loader.py            # per-org → CityNetwork
│   │   ├── renderer.py          # artifact string generation
│   │   ├── filesystem.py        # disk writer / cleaner
│   │   ├── git.py               # previous-build diff reader
│   │   └── zip.py               # engine.zip bundler
│   ├── use_cases/               # orchestration
│   │   ├── check.py             # CheckUseCase
│   │   ├── build.py             # BuildUseCase
│   │   ├── init.py              # InitUseCase
│   │   └── validate_step.py     # shared load/allocate/check pipeline
│   ├── dto/                     # use-case result DTOs
│   │   ├── build_result.py
│   │   ├── check_result.py
│   │   ├── counts.py
│   │   └── init_result.py
│   ├── services/                # application services (CLI facade)
│   │   ├── build.py
│   │   ├── check.py
│   │   ├── init.py
│   │   └── exceptions.py
│   ├── controllers/             # CLI + presenters
│   │   ├── app.py               # Typer application
│   │   ├── commands.py          # command registration
│   │   ├── dependencies.py      # CLI dependency injection
│   │   ├── responses.py         # human / JSON output formatting
│   │   └── handlers/            # command handlers
│   │       ├── build.py
│   │       ├── check.py
│   │       └── init.py
│   └── __init__.py              # public API re-exports
├── tests/
│   ├── conftest.py
│   ├── test_property.py
│   ├── data/
│   │   ├── test_filesystem.py
│   │   ├── test_git.py
│   │   ├── test_loader.py
│   │   ├── test_renderer.py
│   │   └── test_zip.py
│   ├── domain/
│   │   ├── test_allocator.py
│   │   ├── test_checker.py
│   │   └── test_models.py
│   ├── use_cases/
│   │   ├── test_build.py
│   │   ├── test_check.py
│   │   └── test_init.py
│   └── controllers/
│       └── test_cli.py
└── build/                       ← generated artifacts (gitignored)
    ├── network.json             # canonical source dump (no generated IPs)
    ├── network.md               # human-readable projection
    ├── schema.json              # JSON Schema
    ├── topology.json            # graph for UI / simulator
    ├── network.html             # self-contained interactive viewer
    └── engine.zip               # bundled runtime package for cybercity-engine
```

## Data model (v3.0)

### `Organization`

```
id, name, kind
description
networks[]                       # REQUIRED in v3.0
```

### `Network`

```
id, org_id, name, kind           # kind drives generated CIDR
description
```

`kind ∈ {dmz, lan, ot, mgmt, internet}`.

### `Link` kinds

`kind ∈ {api-call, auth, db-read, db-write, log-sink, backup-of, trusts, vendor-vpn, dns-query, ntp-query}`.

Links are always directed. If a relationship is bidirectional, declare two explicit links.

### `Service`

```
id, org_id, name, description?, kind, exposure, host
network_id                       # logical placement; REQUIRED in v3.0
software {vendor, product, version?, cve_id?}
auth, data_classification, criticality
ports, os_hint
decoy {kind, fingerprint, os_hint, note}   # optional mock service
```

### `Link`

```
from_service, to_service, kind, protocol?
encryption, label
```

### `CityNetwork`

```
version                            # schema version, code constant
organizations[], services[], links[]
```

### `Allocation` (generated)

```
org_index: dict[str, int]          # network_index per org
net_cidr: dict[str, str]           # CIDR per network
svc_ip: dict[str, str]             # bind_ip per service
```

## CLI

```bash
cybercity-data check [PATH] [--json] [--strict] [--seed SEED]   # validate only
cybercity-data build [PATH] [--out DIR] [--json] [--strict] [--clean] [--seed SEED]
cybercity-data init ID --kind KIND [--path PATH] [--empty]
```

- `check` — validate only.
- `build` — validate + write artifacts; skips on errors.
- `init` — scaffold a new org directory. By default includes an example network and service; `--empty` keeps lists blank.
- `--strict` — treat warnings as errors.
- `--clean` — remove the output directory before rendering.
- `--seed` — reproducible allocation; without it each build uses a fresh random allocation.

## Cross-field rules

| Код | Уровень | Что проверяет |
|---|---|---|
| `ids` | error | unique id for org/network/service; unique `(from,to,kind)` link |
| `refs` | error | service.org_id and link endpoints exist |
| `network-belongs` | error | service.network_id exists and belongs to the same org |
| `ip-in-network` | error | generated bind_ip lies inside generated network CIDR |
| `ip-unique` | error | generated bind_ip is unique within the same network |
| `network-overlap` | error | generated CIDRs do not overlap |
| `ip-scheme` | error | generated CIDRs live under `10.<org_index>.x.x` |
| `exposure-network` | error | exposure allowed on network kind |
| `self-loop` | error | link does not point to itself |
| `software` | error | cve_id matches `CVE-YYYY-NNNNN` (format only) |
| `assets` | warning | service asset directory matches a declared service |
| `decoy-criticality` | error | decoy services are not marked `critical` |
| `decoy-write-real` | error | decoy services do not write/backup real services |

## ADR

| ADR | Решение |
|---|---|
| ADR-0001 | Per-org layout; loader builds in-memory `CityNetwork` |
| ADR-0002 | Pydantic v2, `extra="forbid"` |
| ADR-0003 | Explicit networks and IP addresses in v2.0 |
| ADR-0004 | `Service.decoy` marks simulation-only mock services |
| ADR-0005 | `org_id` injected by loader, not repeated in YAML |
| ADR-0006 | CLI: `check`, `build`, `init`; exit codes 0/1 |
| ADR-0007 | Build artifacts: `network.json`, `network.md`, `schema.json`, `topology.json`, `network.html`, `engine.zip` |
| ADR-0008 | `--strict` makes warnings fail CI |
| ADR-0009 | `CityNetwork` version is a code constant (`SCHEMA_VERSION`); no city-wide allocation file |
| ADR-0010 | `Organization` keeps only structural fields; narrative metadata lives in `description` or is removed |
| ADR-0011 | Links are directed; no `bidirectional` flag |
| ADR-0012 | Optional `services/<svc-id>/` directories hold runtime assets; canonical service description stays in `config.yml` |
| ADR-0013 | `engine.zip` is always produced, even without assets |
| ADR-0014 | New artifacts: `attack-surface.json`, `inventory.md`, `changes.json` |
| ADR-0015 | `mypy --strict` for static type checking |
| **ADR-0016** | **Networks and IP addresses are generated by `allocator.py`; declarative model only describes topology** |
| **ADR-0017** | **Controller → Service → UseCase → Data/IO layered architecture for CLI: Service is a thin facade that wires adapters and translates errors into `ApplicationError`** |
| **ADR-0018** | **Service methods are decomposed into named pipeline steps (`_load`, `_allocate`, `_validate`, `_render`, `_write`) so each step is testable in isolation** |

## Artifacts

`build/` contains:

- `network.json` — canonical `CityNetwork` dump (declarative fields only, no generated IPs).
- `network.md` — human-readable projection.
- `schema.json` — JSON Schema emitted by Pydantic.
- `topology.json` — graph for UI/simulator consumption (includes generated `bind_ip` / `network_index`).
- `network.html` — self-contained interactive graph viewer.
- `attack-surface.json` — publicly exposed services and metadata.
- `inventory.md` — discovered service asset directories.
- `changes.json` — git-based diff against the previous build.
- `engine.zip` — bundled runtime package for `cybercity-engine`.

## License

- Code / YAML: [MIT](../LICENSE)
- Documentation: [CC BY 4.0](LICENSE-DOCS)
