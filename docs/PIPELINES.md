# CI/CD Pipelines

Репозиторий содержит готовые пайплайны для GitLab CI и GitHub Actions.
Оба проверяют полный цикл: линт → тесты → валидация → сборка артефактов.

## GitLab CI

Файл: `.gitlab-ci.yml`

Stages:

| Stage | Job | Что делает |
|---|---|---|
| lint | `lint` | `uv run ruff check` |
| typecheck | `typecheck` | `uv run mypy --strict src/cybercity_data` |
| test | `test` | `uv run pytest -q --cov=... --cov-fail-under=95` |
| validate | `check` | `uv run cybercity-data check .` |
| build | `build` | `uv run cybercity-data build . --clean` + артефакты |

Запускается на:
- merge request
- push в default branch
- push в любую ветку

### Кэш

`.uv-cache/` кэшируется по `uv.lock` + `pyproject.toml`.

## GitHub Actions

Файл: `.github/workflows/ci.yml`

Jobs:

| Job | Зависимости | Что делает |
|---|---|---|
| `lint` | — | `ruff check` |
| `typecheck` | `lint` | `mypy --strict src/cybercity_data` |
| `test` | `lint`, `typecheck` | `pytest` с coverage ≥ 95% |
| `check` | `lint`, `typecheck` | `cybercity-data check .` |
| `build` | `test`, `check` | `cybercity-data build . --clean` + upload artifacts |

Запускается на:
- push в `main`
- pull request в `main`
- manual dispatch

### Артефакты

GitHub Actions загружает `build/*.json`, `build/*.md`, `build/*.html` и `build/engine.zip`
как artifact с retention 7 дней.

## Exit codes

Оба пайплайна считают pipeline failed при любом ненулевом exit code:
- `ruff` → exit 1 на ошибки линтера
- `pytest --cov-fail-under=95` → exit 1 если coverage ниже 95%
- `cybercity-data check .` → exit 1 на ошибки данных
- `cybercity-data build .` → exit 1 на ошибки данных

## Артефакты не коммитятся

`build/` находится в `.gitignore`. CI генерирует их заново каждый раз.
