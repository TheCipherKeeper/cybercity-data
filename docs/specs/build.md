# Спека модуля `build`

> Канон структуры — `<methodology-repo>`/docs/refs/SPEC.md (`<methodology-repo>` =
> [TheCipherKeeper/ai-project-template](https://github.com/TheCipherKeeper/ai-project-template)).

## Описание

Сборка артефактов города из декларативной модели: pipeline
`load → allocate → check → render → write → zip`. Оркестрируется
`use_cases/build.py` (handler), использует `data/` (IO-адаптеры) и `domain/`
(allocator/checker). После успешной сборки (TODO) публикует
`city.build.completed` в брокер.

## Интерфейсы

- **`BuildUseCase.execute(input: BuildInput) -> BuildResult`**
  — вход: путь к `organizations/`, выходной каталог, `--seed`, `--clean`,
  `--strict`, формат вывода; выход: `BuildResult` (пути артефактов, `CheckResult`,
  длительность). При ошибках `checker` рендеринг/сборка пропускаются.
- **`CheckUseCase.execute(input: CheckInput) -> CheckResult`** (см. `check.md`) —
  используется внутри build.

Output ports (актуальные и TODO):
- `OrganizationRepository` (загрузчик `organizations/` → `CityNetwork`) —
  реализован в `data/loader.py`.
- `ArtifactWriter` (запись в `build/`, очистка с `--clean`) — `data/filesystem.py`.
- `ArtifactRenderer` (генерация строк артефактов) — `data/renderer.py`.
- `ZipPacker` (сборка `engine.zip`) — `data/zip.py`.
- `GitDiffer` (дифф с предыдущей сборкой) — `data/git.py`.
- **`EventPublisher` (TODO, Phase 2)** — публикация `city.build.completed` в
  брокер; `Protocol`, реализуется Redpanda adapter в `adapters/`
  ([ADR-0010](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/0010-data-broker-producer.md)).

## Типы

```python
@dataclass(frozen=True)
class BuildInput: path: Path, out: Path, seed: int | None, clean: bool, strict: bool, json: bool
@dataclass(frozen=True)
class BuildResult: check: CheckResult, artifacts: BuildArtifacts, duration_ms: int
@dataclass(frozen=True)
class BuildArtifacts: network_json, network_md, schema_json, topology_json,
                     network_html, attack_surface_json, inventory_md,
                     changes_json, engine_zip: Path

# TODO ports/ (Phase 2)
class EventPublisher(Protocol):
    def publish(self, topic: str, payload: dict, *, correlation_id: str | None) -> None: ...
```

## Что есть

- Pipeline как именованные шаги: `_load`/`_allocate`/`_validate`/`_render`/
  `_write`; каждый шаг тестируется изолированно.
- 9 артефактов в `build/` (см. ARCHITECTURE.md → Артефакты); `engine.zip`
  генерируется всегда, даже без ассетов.
- `--clean` — пересоздание выходного каталога; `--seed` — воспроизводимая
  аллокация; `--strict` — warnings как errors.
- Слоистая архитектура: Controller (`controllers/handlers/build.py`) →
  Service (`services/build.py`) → UseCase (`use_cases/build.py`) →
  Data (`data/*`) + Domain (`domain/*`).
- Тесты: `tests/use_cases/test_build.py`, `tests/controllers/test_cli.py`,
  `tests/data/test_{filesystem,git,loader,renderer,zip}.py`.

## Что TODO

- **Broker-producer:** публикация `city.build.completed` после успешной сборки.
  Завести output port `EventPublisher` в `ports/` (Python `Protocol`),
  реализовать Redpanda adapter в `adapters/` (адрес `BROKER_ADDR` из env,
  `CONVENTIONS@v1` envelope). `BuildUseCase` оркестрирует публикацию.
  [ADR-0010](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/0010-data-broker-producer.md).
  Событие готовности — уведомление; файловые артефакты остаются out-of-band.
- **Швы MODULE.md:** формализовать `ports/` (выделить контракты IO) и
  `adapters/` (перенести реализации из `data/`), см. BACKLOG задача 4.

## Ограничения

- При ошибках `checker` рендеринг и сборка пропускаются (валидация-first).
- Не исполняет сценарии; не собирает образы из `overlays` (это `manage`).
- Публикация брокер-события — только после успешной сборки (Phase 2).
- `build/` в `.gitignore`; артефакты регенерируются CI.

## Зависимости

- Output ports: `OrganizationRepository`, `ArtifactWriter`, `ArtifactRenderer`,
  `ZipPacker`, `GitDiffer`, `EventPublisher` (TODO).
- Внутренние: `domain` (models/allocator/checker), `dto` (BuildResult/CheckResult/Counts).
- Внешние: `PyYAML>=6.0`, `pydantic>=2.7`, stdlib (`zipfile`, `json`, `pathlib`).
  Phase 2: Kafka-клиент (например `aiokafka`/`confluent-kafka`) для Redpanda adapter.