# CyberCity Data — Руководство разработчика

## Канонические импорты

Код и тесты импортируют сущности по полному пути внутри `city_model`. Корневые
переэкспорты `cybercity_data` удалены и не являются частью нового контракта.
Например, модель импортируется из
`cybercity_data.city_model.adapters.inbound.domain.models`, а CLI — из
`cybercity_data.city_model.adapters.inbound.controllers`.

## Быстрый старт

```bash
cd /path/to/cybercity-data
uv sync
uv run ruff check
uv run mypy --strict src/cybercity_data
uv run pytest -q
uv run cybercity-data check .
uv run cybercity-data build . --clean
```

## Структура проекта

- `src/cybercity_data/city_model/adapters/inbound/domain/models.py` — Pydantic v2 схема (декларативный слой).
- `src/cybercity_data/city_model/adapters/inbound/domain/allocator.py` — автоматическая аллокация сетей/IP.
- `src/cybercity_data/city_model/adapters/inbound/domain/checker.py` — cross-field правила валидации.
- `src/cybercity_data/city_model/adapters/inbound/data/loader.py` — сборка `CityNetwork` из
  `organizations/<org>/config.yml`.
- `src/cybercity_data/city_model/adapters/inbound/data/renderer.py` — генерация артефактов.
- `src/cybercity_data/city_model/adapters/inbound/use_cases/build.py` — оркестрация сборки.
- `src/cybercity_data/city_model/adapters/inbound/controllers/` — CLI-команды `check`, `build`, `init`.
- `organizations/` — канонические данные города (46 организаций).
- `tests/` — pytest suite, включая property-based тесты на `hypothesis`.

Полное дерево — в [ARCHITECTURE.md](ARCHITECTURE.md).

## Рецепты

### Добавление организации

```bash
uv run cybercity-data init my-org --kind government --network-index 42
```

Создаёт `organizations/my-org/config.yml` с примером DMZ и web-сервиса. Для
минимального шаблона используйте `--empty`. Подробнее о формате `config.yml` —
в [ORGANIZATIONS.md](ORGANIZATIONS.md).

### Добавление правила валидации

1. Добавить метод в `NetworkChecker` в `src/cybercity_data/city_model/adapters/inbound/domain/checker.py`.
2. Вызвать его из `NetworkChecker.check()`.
3. Добавить тест в `tests/domain/test_checker.py`.
4. Обновить таблицу cross-field правил в [ARCHITECTURE.md](ARCHITECTURE.md).

Правила должны:

- Возвращать `list[Issue]`.
- Не short-circuit'ить: собирать все находки.
- Использовать семантические коды (`ids`, `ip-in-network`, `honeypot-write-real`).

### Добавление артефакта сборки

1. Добавить метод `_build_*` в `ArtifactRenderer` в
   `src/cybercity_data/city_model/adapters/inbound/data/renderer.py`.
2. Включить его в `ArtifactRenderer.render()`.
3. Добавить в `EngineZipWriter`, если артефакт принадлежит `engine.zip`.
4. Добавить тест в `tests/data/test_renderer.py`.
5. Обновить списки артефактов в CI и в [ARCHITECTURE.md](ARCHITECTURE.md).

## Тестирование

```bash
# Все тесты
uv run pytest -q

# С покрытием и порогом 95%
uv run pytest --cov=cybercity_data --cov-fail-under=95

# Подробный вывод
uv run pytest -v

# Конкретный слой
uv run pytest tests/domain -v
```

Тесты разложены по слоям, зеркально к `src/`:

- `tests/domain/` — `test_allocator.py`, `test_checker.py`, `test_models.py`.
- `tests/data/` — `test_loader.py`, `test_renderer.py`, `test_filesystem.py`,
  `test_git.py`, `test_zip.py`.
- `tests/use_cases/` — `test_build.py`, `test_check.py`, `test_init.py`.
- `tests/controllers/` — `test_cli.py`.
- `tests/test_property.py` — property-based тесты на **hypothesis**:
  инварианты модели и аллокатора (воспроизводимость `--seed`, уникальность IP
  внутри сети, согласованность ссылок).

Покрытие должно оставаться **не ниже 95%** — это закреплено в CI флагом
`--cov-fail-under=95`. Перед коммитом также запускается `mypy --strict`
(см. ниже): никакие `Any`-эскейпы без явного `# type: ignore` не допускаются.

## Линтинг и статическая проверка типов

```bash
uv run ruff check
uv run mypy --strict src/cybercity_data
```

Конфигурация `ruff` и `mypy` — в `pyproject.toml` (правила `E,F,I,B,UP`,
`target-version = "py312"`, `strict = true`).

## CI / CD

GitHub Actions и GitLab CI запускают один и тот же цикл (подробности — в
[PIPELINES.md](PIPELINES.md)):

1. `ruff check`
2. `mypy --strict src/cybercity_data`
3. `pytest` с покрытием ≥ 95 %
4. `cybercity-data check .`
5. `cybercity-data build . --clean` (+ upload артефактов)

Любой ненулевой exit code проваливает пайплайн.

## Pre-commit

Локальные хуки запускают ruff, mypy и pytest перед каждым коммитом:

```bash
uv run pre-commit install
```

## Стиль коммитов

Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`,
`chore:`, `adr:` (для ADR). Тело коммита — на русском; summary line —
английский допустим. Breaking changes включают `BREAKING CHANGE:` в теле.

## Процесс ADR

ADR живут только в хабе `cybercity/adr/` (см.
[ADR-0005](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/0005-adr-centralized-in-hub.md));
локального каталога `docs/adr/` в этом репозитории нет. Если изменение
затрагивает архитектурное решение:

1. Написать или обновить ADR в хабе `cybercity/adr/` (формат — в
   [`cybercity/CONVENTIONS.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/CONVENTIONS.md)).
2. Сослаться на него из `docs/ARCHITECTURE.md`.
3. Старые ADR помечать `superseded`, а не удалять.

## Связанные документы

- [`AGENTS.md`](../AGENTS.md) — правила для AI-агентов.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — внутренняя архитектура, модель данных и поток данных.
- [`ORGANIZATIONS.md`](ORGANIZATIONS.md) — per-org layout conventions.
- [`PIPELINES.md`](PIPELINES.md) — CI/CD-пайплайны.
