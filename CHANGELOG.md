# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `engine.zip` is now generated on every build, even when no service assets are present.
- New build artifacts:
  - `attack-surface.json` — publicly exposed services and their CVE/criticality metadata.
  - `inventory.md` — discovered service asset directories.
  - `changes.json` — git-based diff of the current city model against the previous build.
- New cross-field validation rules:
  - `ip-unique` — prevents duplicate `bind_ip` values within the same network.
  - `decoy-criticality` — decoy services cannot be marked `critical`.
  - `decoy-write-real` — decoy services cannot perform `db-write` or `backup-of` against real services.
- CLI improvements:
  - `cybercity-data build --clean` removes the output directory before rendering.
  - `cybercity-data init` now scaffolds an example network and service by default; use `--empty` for the previous minimal template.
- Interactive HTML viewer improvements:
  - Filter by organization.
  - Criticality halo and legend.
  - Search highlight and reset filters button.
- Static type checking with `mypy --strict` in CI and pre-commit hooks.
- Property-based tests using `hypothesis`.
- GitHub Release workflow for tagged versions.

### Changed
- CLI loads the city model only once and passes discovered assets directly to the builder.
- GitHub Actions and GitLab CI now include a typecheck job and upload all new artifacts.

## [0.4.0] — 2026-06-14

### Changed
- Links are now always directed; bidirectional and many-to-many links have been removed.
- `Service` model restructured: `network_id` and `bind_ip` are required, `known_weakness` removed.
- Organization schema streamlined: narrative fields removed, only structural fields remain.
- City IP scheme changed: `network_index` replaces `segment`, all orgs renumbered under `10.<index>.x.x`.

## [0.3.0] — earlier

### Added
- Pydantic v2 models with `extra="forbid"`.
- Per-organization layout with loader injecting `org_id`.
- Explicit networks and IP addresses in v2.0.
- `Service.decoy` for simulation-only mock services.
- CLI commands: `check`, `build`, `init`.
- Build artifacts: `network.json`, `network.md`, `schema.json`, `topology.json`, `network.html`, `engine.zip`.
- `--strict` flag treating warnings as errors.
