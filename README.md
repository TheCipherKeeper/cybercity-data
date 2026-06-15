# CyberCity — City Data

[![Part of CyberCity](https://img.shields.io/badge/CyberCity-composition-blueviolet)](#)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)](docs/LICENSE-DOCS)

Canonical declarative data layer for the CyberCity digital twin:
organizations, networks, services, links.

This repository models the IT/OT infrastructure of an abstract city as a
directed graph: services are nodes, links are edges. Other tools consume this
graph to simulate traffic, run security scenarios, and visualize the city.

In v3.0 the declarative layer only describes topology — organizations,
network roles, service placement, and links. Concrete IP addressing is generated
automatically by the allocator, keeping the model focused on structure rather
than address bookkeeping.

Links are always directed; if a relationship is bidirectional, declare two
explicit links.

- **Architecture & model:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Per-org layout conventions:** [`docs/ORGANIZATIONS.md`](docs/ORGANIZATIONS.md)
- **Generated view:** [`build/network.md`](build/network.md)

## Quick start

```bash
uv sync
uv run cybercity-data check .
uv run cybercity-data build .
uv run pytest -q
uv run ruff check
uv run mypy --strict src/cybercity_data
```

## CLI

```
cybercity-data check [PATH] [--json] [--strict] [--seed SEED]   # validate only
cybercity-data build [PATH] [--out DIR] [--json] [--strict] [--clean] [--seed SEED]
cybercity-data init ID --kind KIND [--path PATH] [--empty]
```

- `--strict` treats warnings as errors.
- `--clean` removes the output directory before rendering.
- `--seed` makes IP allocation reproducible; without it each build uses a random allocation.
- `init` scaffolds a new organization under `organizations/<ID>/`. By default it includes an example network and service; use `--empty` for a minimal template.

## Artifacts

`cybercity-data build` produces:

- `build/network.json` — canonical machine-readable dump
- `build/network.md` — human-readable projection
- `build/schema.json` — JSON Schema for downstream validation
- `build/topology.json` — graph of services and links for UI/simulation
- `build/network.html` — self-contained interactive graph viewer (opens in a browser)
- `build/attack-surface.json` — publicly exposed services and CVE metadata
- `build/inventory.md` — discovered service asset directories
- `build/changes.json` — git-based diff against the previous build
- `build/engine.zip` — bundled runtime package for `cybercity-engine`

## License

- Code / YAML: [MIT](LICENSE)
- Documentation: [CC BY 4.0](docs/LICENSE-DOCS)
