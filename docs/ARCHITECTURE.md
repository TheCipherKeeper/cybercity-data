# CyberCity — Data Architecture

> **TL;DR.** `cybercity-data` — canonical declarative data layer for the CyberCity cyber-range:
> organizations, networks, services, links. `check` validates; `build` writes artifacts.

- [README](../README.md)
- [Per-org layout conventions](ORGANIZATIONS.md)
- [CI/CD pipelines](PIPELINES.md)

## Composition

| Слой | Репозиторий | Роль |
|---|---|---|
| Данные (этот репо) | `cybercity-data` | YAML-модель + loader + checker + builder |
| Сценарии | `cybercity-scenarios` | playbooks атак, ссылаются на `attack_chain` в Link |
| UI | `cybercity-ui` | рисует граф из `build/topology.json` |
| Агенты | `cybercity-agents` | LLM-генератор недостающих org'ов |
| Blueprints | `cybercity-blueprints` | шаблоны организаций |

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
│   ├── city.yml                 # version + meta.city + meta.allocation
│   └── <org>/config.yml         # per-organization data
├── src/cybercity_data/
│   ├── models.py                # Pydantic v2 schema
│   ├── loader.py                # per-org → CityNetwork
│   ├── check.py                 # cross-field rules
│   ├── build.py                 # artifact generation
│   └── cli.py                   # check, build, init
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_loader.py
│   ├── test_check.py
│   ├── test_build.py
│   └── test_cli.py
└── build/                       ← generated artifacts (gitignored)
    ├── network.json             # canonical full dump
    ├── network.md               # human-readable projection
    ├── schema.json              # JSON Schema
    ├── topology.json            # graph for UI
    └── attack-surface.json      # public weak services
```

## Data model (v1.0)

### `Meta`

```
city: str
allocation:
  corp: CIDR
  ot: CIDR
  mgmt: CIDR
  internet: CIDR
```

`allocation` provides base ranges for auto-allocated per-org networks.

### `Organization`

```
id, name, kind, segment
description, third_party[], notes, tags[], regulated[]
headcount_estimate
networks[]                       # auto-allocated if empty
```

Default networks by segment:
- `corp` → `dmz`, `lan`, `mgmt`
- `ot` → `ot`, `mgmt`
- `mgmt` → `mgmt`
- `public` → `internet`

### `Network`

```
id, org_id, name, kind, cidr
description
```

`kind ∈ {dmz, lan, ot, mgmt, internet}`.

### `Service`

```
id, org_id, name, kind, exposure, host
network_id, bind_ip            # concrete placement; auto-allocated if omitted
software {vendor, product, version?, cve_id?}
auth, data_classification
ports, owner_team, known_weakness
decoy {kind, fingerprint, os_hint, note}   # optional honeypot
```

### `Link`

```
from_service, to_service, kind, protocol?
encryption, bidirectional, label, attack_chain[]
```

### `CityNetwork`

```
version, meta
organizations[], services[], links[]
```

## CLI

```bash
cybercity-data check [PATH] [--json] [--strict]
cybercity-data build [PATH] [--out DIR] [--json] [--strict]
cybercity-data init ID --kind KIND --segment SEGMENT [--path PATH]
```

- `check` — validate only.
- `build` — validate + write artifacts; skips on errors.
- `init` — scaffold a new org directory.
- `--strict` — treat warnings as errors.

## Cross-field rules

| Код | Уровень | Что проверяет |
|---|---|---|
| `ids` | error | unique id for org/network/service; unique `(from,to,kind)` link |
| `refs` | error | service.org_id and link endpoints exist |
| `network-belongs` | error | service.network_id exists and belongs to the same org |
| `ip-in-network` | error | bind_ip lies inside service network CIDR |
| `network-overlap` | error | networks do not overlap |
| `exposure-network` | error | exposure allowed on network kind |
| `self-loop` | error | link does not point to itself |
| `software` | error | cve_id matches `CVE-YYYY-NNNNN` |
| `link-encryption` | warning | public service reached over unencrypted link |
| `posture` | warning | public service with weak auth or known weakness |
| `quota` | warning | v1.0 targets: 30 orgs, 95 services |

## ADR

| ADR | Решение |
|---|---|
| ADR-0001 | Per-org layout; loader builds in-memory `CityNetwork` |
| ADR-0002 | Pydantic v2, `extra="forbid"` |
| ADR-0003 | `Network` first-class; auto-allocation from `meta.allocation` |
| ADR-0004 | `Service.decoy` replaces standalone `Decoy` entity |
| ADR-0005 | `org_id` injected by loader, not repeated in YAML |
| ADR-0006 | CLI: `check`, `build`, `init`; exit codes 0/1 |
| ADR-0007 | Build artifacts: `network.json`, `network.md`, `schema.json`, `topology.json`, `attack-surface.json` |
| ADR-0008 | `--strict` makes warnings fail CI near v1.0 |

## License

- Code / YAML: [MIT](../LICENSE)
- Documentation: [CC BY 4.0](LICENSE-DOCS)
