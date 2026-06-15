# Contributing to cybercity-data

## Quick start

```bash
uv sync
uv run ruff check
uv run mypy --strict src/cybercity_data
uv run pytest -q
uv run cybercity-data check .
uv run cybercity-data build .
```

## Project structure

- `src/cybercity_data/domain/models.py` — Pydantic v2 schema.
- `src/cybercity_data/data/loader.py` — assembles `CityNetwork` from `organizations/<org>/config.yml`.
- `src/cybercity_data/domain/checker.py` — cross-field validation rules.
- `src/cybercity_data/data/renderer.py` — artifact generation; `src/cybercity_data/use_cases/build.py` — build orchestration.
- `src/cybercity_data/controllers/` — `check`, `build`, `init` CLI commands.
- `organizations/` — canonical city data.
- `tests/` — pytest suite, including property-based tests.

## Adding an organization

```bash
uv run cybercity-data init my-org --kind government --network-index 42
```

This creates `organizations/my-org/config.yml` with an example DMZ and web service.
Use `--empty` for a minimal template.

## Adding a validation rule

1. Add a method to `NetworkChecker` in `src/cybercity_data/domain/checker.py`.
2. Call it from `NetworkChecker.check()`.
3. Add a test to `tests/domain/test_checker.py`.
4. Update `docs/ARCHITECTURE.md` cross-field rules table.

Rules should:
- Return `list[Issue]`.
- Never short-circuit; collect all findings.
- Use semantic codes like `ids`, `ip-in-network`, `decoy-write-real`.

## Adding a build artifact

1. Add a `_build_*` method to `ArtifactRenderer` in `src/cybercity_data/data/renderer.py`.
2. Include it in `ArtifactRenderer.render()`.
3. Add it to `engine.zip` in `EngineZipWriter` if it belongs there.
4. Add a test to `tests/data/test_renderer.py`.
5. Update CI artifact lists and documentation.

## ADRs

Architectural decisions are recorded in the ADR table in `docs/ARCHITECTURE.md`.
When proposing a breaking change, add a new ADR entry and update `CHANGELOG.md`.

## CI / CD

Both GitHub Actions and GitLab CI run:

1. `ruff check`
2. `mypy --strict src/cybercity_data`
3. `pytest` with coverage ≥ 95%
4. `cybercity-data check .`
5. `cybercity-data build . --clean`

Coverage must stay at or above 95%.

## Pre-commit hooks

Install the local hooks:

```bash
uv run pre-commit install
```

The hooks run ruff, mypy, and pytest before each commit.
