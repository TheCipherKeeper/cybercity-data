# AGENTS.md — правила для AI-агентов и контрибьюторов CyberCity Data

## Иерархия документов (от старшего к младшему)

**Над репозиторием** — хаб `cybercity` держит системные документы:

- [`cybercity/COMPOSITION.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/COMPOSITION.md) — канон состава, контрактов, доверительной границы.
- [`cybercity/CONVENTIONS.md`](https://github.com/TheCipherKeeper/cybercity/blob/main/CONVENTIONS.md) — кросс-репо конвенции (язык, скелет репо, ADR-формат, event envelope).
- [`cybercity/adr/`](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/) — сквозные ADR (почему 6 репо, доверительная граница, Rust-коллектор).

**Внутри репозитория:**

1. `docs/adr/` — действующие архитектурные решения. ADR со статусом
   `superseded` не имеют силы.
2. `AGENTS.md` (этот файл) — операционные правила работы в репозитории.
3. `README.md` — краткое описание и quick start.
4. `docs/` — внутренняя документация репозитория
   (`ARCHITECTURE.md`, `DEVELOPMENT.md`, `DATA_FLOW.md`, `ORGANIZATIONS.md`,
   `PIPELINES.md`).
5. Код, тесты, конфиги — реализация принятых решений.

Если документы противоречат друг другу, побеждает старший. Любое расхождение —
повод создать новый ADR.

## Ключевые принципы

- **Data-as-code.** Декларативная YAML-модель города (`organizations/<org>/config.yml`)
  — исходник правды; код (`loader`/`checker`/`allocator`/`renderer`) её
  интерпретирует. Не наоборот.
- **Validation-first.** Валидатор (`checker`, 13 cross-field правил) —
  единственный контракт правды. Что не прошло `check`, не попадает в `build`
  и в `engine.zip`. Обходить валидатор нельзя.
- **Воспроизводимость аллокатора.** IP/CIDR генерируются `allocator.py`;
  одинаковый `--seed` даёт одинаковую адресацию. По умолчанию — случайная.
- **Data = source of truth для модели города.** `engine` исполняет, `ui`
  рисует, `manage` оркеструет инфру — но описание мира и сценариев авторит
  только `data`.
- **LLM — помощник, не хозяин.** LLM пишет YAML и код; валидаторы, тесты и
  линтеры решают. По одной сущности за итерацию, не «30 организаций сразу».

## Правила для AI-агентов

### Что агенту МОЖНО

- Писать YAML в `organizations/<org>/config.yml` (по одной организации за
  итерацию) и опциональные ассеты в `organizations/<org>/services/<svc-id>/`.
- Запускать `uv run ruff check`, `uv run mypy --strict src/cybercity_data`,
  `uv run pytest` (включая property-based `tests/test_property.py`).
- Запускать `uv run cybercity-data check .` и `uv run cybercity-data build .`.
- Создавать новые ADR в `docs/adr/`, если меняется архитектурное решение.
- Обновлять `README.md`, `AGENTS.md`, `docs/` при изменении структуры.

### Чего агенту НЕЛЬЗЯ

- Делать коммиты, пуши, PR — это делает человек.
- Редактировать существующие ADR без явного указания или создания нового ADR.
  Старые ADR помечаем `superseded`, не удаляем.
- Обходить валидатор: править код или YAML так, чтобы «замолчать» правило
  `checker.py`, вместо починки данных.
- Менять `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.python-version`,
  `.github/`, `.gitlab-ci.yml`, `.gitignore` без явного одобрения.
- Править `src/` или `tests/` в обход `ruff`/`mypy`/`pytest` (только если они зелёные).

## Структура репозитория

```
cybercity-data/
├── README.md                       # краткая сводка + quick start + 3 бейджа
├── AGENTS.md                       # этот файл
├── CONTRIBUTING.md                 # тонкий указатель → docs/DEVELOPMENT.md
├── CHANGELOG.md
├── LICENSE                         # MIT (код / YAML)
├── LICENSE-DOCS                    # CC BY 4.0 (документация)
├── pyproject.toml                  # пакет + CLI cybercity-data
├── uv.lock
├── organizations/                  # канонические данные города (46 org)
│   └── <org>/
│       ├── config.yml              # данные организации (v3.0 — только логика)
│       └── services/<svc-id>/      # опциональные ассеты сервисов
├── src/cybercity_data/
│   ├── domain/                     # чистая бизнес-логика
│   │   ├── models.py               # Pydantic v2 схема (декларативный слой)
│   │   ├── allocator.py            # автоматическая аллокация сетей / IP
│   │   └── checker.py             # cross-field правила
│   ├── data/                       # IO-адаптеры
│   │   ├── loader.py              # per-org → CityNetwork
│   │   ├── renderer.py            # генерация артефактов
│   │   ├── filesystem.py          # запись на диск / очистка
│   │   ├── git.py                 # чтение диффа с предыдущей сборкой
│   │   └── zip.py                 # сборщик engine.zip
│   ├── use_cases/                  # оркестрация
│   │   ├── check.py / build.py / init.py
│   │   └── validate_step.py       # общий pipeline load / allocate / check
│   ├── dto/                        # result DTO use-case'ов
│   ├── services/                   # application services (CLI facade)
│   │   ├── build.py / check.py / init.py
│   │   └── exceptions.py
│   ├── controllers/                # CLI + presenters
│   │   ├── app.py / commands.py / dependencies.py / responses.py
│   │   └── handlers/              # build / check / init
│   └── __init__.py                 # public API re-exports
├── tests/                         # pytest suite + property-based (hypothesis)
│   ├── data/ domain/ use_cases/ controllers/
│   └── test_property.py
└── build/                         # сгенерированные артефакты (gitignored)
```

## Рабочий цикл

1. Прочитать соответствующий ADR (`docs/adr/`) и текущий код/данные.
2. Внести изменение **по одной сущности** (одна организация / одно правило /
   один артефакт).
3. Запустить валидацию и сборку:
   ```bash
   uv run cybercity-data check .
   uv run cybercity-data build . --clean
   ```
4. Запустить проверки качества:
   ```bash
   uv run ruff check
   uv run mypy --strict src/cybercity_data
   uv run pytest -q
   ```
5. Показать результат пользователю. Не коммитить.

## Язык документации

Вся документация и ADR ведутся на русском языке. README может содержать
английские бейджи и ссылки, но основной текст — русский. Английский допустим
только для бейджей, идентификаторов кода, имён библиотек и значений поля
`Status:` ADR (`Accepted` / `Superseded` / `Amended`).