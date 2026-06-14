# CyberCity — City Data

[![Part of CyberCity](https://img.shields.io/badge/CyberCity-composition-blueviolet)](#)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)](docs/LICENSE-DOCS)

Canonical declarative data layer for the CyberCity digital twin:
organizations, networks, services, links.

This repository models the IT/OT infrastructure of an abstract city.
Security scenarios, vulnerabilities, pentesting playbooks and honeypots live in
separate repositories; here we keep the neutral city model that other tools
consume.

In v2.0 everything is explicit: each organization declares its own networks,
IP addresses, and service placement. The validator catches missing or
inconsistent declarations.

- **Architecture & model:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Per-org layout conventions:** [`docs/ORGANIZATIONS.md`](docs/ORGANIZATIONS.md)
- **Generated view:** [`build/network.md`](build/network.md)

## Quick start

```bash
uv sync
uv run cybercity-data check .
uv run cybercity-data build .
uv run pytest
uv run ruff check
```

## CLI

```
cybercity-data check [PATH] [--json] [--strict]   # validate only
cybercity-data build [PATH] [--out DIR] [--json] [--strict]
cybercity-data init ID --kind KIND --network-index INDEX [--path PATH]
```

- `--strict` treats warnings as errors.
- `init` scaffolds a new organization under `organizations/<ID>/`.

## Artifacts

`cybercity-data build` produces:

- `build/network.json` — canonical machine-readable dump
- `build/network.md` — human-readable projection
- `build/schema.json` — JSON Schema for downstream validation
- `build/topology.json` — graph of services and links for UI/simulation

## License

- Code / YAML: [MIT](LICENSE)
- Documentation: [CC BY 4.0](docs/LICENSE-DOCS)
