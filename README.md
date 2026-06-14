# CyberCity — City Data

[![Part of CyberCity](https://img.shields.io/badge/CyberCity-composition-blueviolet)](#)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)](docs/LICENSE-DOCS)

Canonical declarative data layer for the CyberCity cyber-range:
organizations, networks, services, links.

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
cybercity-data check [PATH] [--json]   # validate only
cybercity-data build [PATH] [--out DIR] [--json]
```

## License

- Code / YAML: [MIT](LICENSE)
- Documentation: [CC BY 4.0](docs/LICENSE-DOCS)
