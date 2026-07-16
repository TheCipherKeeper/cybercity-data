# Спека модуля `scenario`

> Канон структуры — `<methodology-repo>`/docs/ARCHITECTURE.md (`<methodology-repo>` =
> [TheCipherKeeper/addm](https://github.com/TheCipherKeeper/addm)).

> **Статус: WIP** (в работе). Спека-заглушка с заполненным «Что TODO»; код
> модуля заводится по задаче BACKLOG 1. Не выдавать stub за реализацию.

## Описание

Авторинг сценариев учений как декларации (контракт **data → engine**,
out-of-band): цели, injects, флаги, scoring-rubric, timebox. `data` порождает
декларацию; `engine` исполняет. Декларативный, как и модель города (YAML).

## Интерфейсы

- **`ScenarioUseCase.execute(input: ScenarioInput) -> ScenarioResult`** (TODO) —
  парсинг манифеста сценария → валидация → рендер артефакта сценария для engine.
- **`ValidateScenarioUseCase.execute(input) -> CheckResult`** (TODO) —
  валидация сценария (ссылки на существующие сервисы/сети, формат флагов,
  scoring-rubric).

Output ports (TODO): `ScenarioRepository` (чтение `scenarios/<id>/manifest.yml`),
`ScenarioRenderer` (генерация артефакта сценария).

## Типы

```python
# TODO (завести при реализации; набросок по ADR/COMPOSITION):
@dataclass(frozen=True)
class ScenarioManifest:
    id: str
    objectives: list[Objective]
    injects: list[Inject]          # scheduled события/команды
    flags: list[Flag]
    scoring_rubric: ScoringRubric   # события/компрометации → очки
    timebox: Timebox
```

## Что есть

- — (модуль не формализован; авторинг сценариев в работе по COMPOSITION →
  *Статус реализации*).

## Что TODO

- Завести пакет `src/cybercity_data/city_model/adapters/inbound/scenario/` по швам MODULE.md
  (usecases/ports/domain/adapters).
- Pydantic-схему манифеста сценария (цели, injects, флаги, scoring-rubric, timebox).
- Валидатор (cross-field: ссылки на существующие сервисы/сети модели города,
  формат флагов, непротиворечивость scoring-rubric).
- Рендер артефакта сценария (контракт data → engine, out-of-band) + интеграция
  в `build` (см. `build.md`).
- CLI-команду `cybercity-data scenario ...` (init/check/build).
- Тесты: `tests/scenario/` — парсинг, валидация, рендер; property-based.

## Ограничения

- `data` только порождает декларацию; не исполняет сценарий (`engine` исполняет).
- Не считает scoring (это `engine` на доверенном потоке).
- Без I/O в domain; I/O — только в adapters.

## Зависимости

- Внутренние: `domain/models` (ссылки на сервисы/сети), `dto`.
- Внешние: `pydantic`, `PyYAML`.