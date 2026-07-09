# Спека модуля `check`

> Канон структуры — `<methodology-repo>`/docs/refs/SPEC.md (`<methodology-repo>` =
> [TheCipherKeeper/ai-project-template](https://github.com/TheCipherKeeper/ai-project-template)).

## Описание

Валидация модели города без записи артефактов: pipeline `load → allocate →
check`. Оркестрируется `use_cases/check.py`; переиспользует общий шаг
`validate_step.py` (load/allocate/check). `check` — единственный контракт правды:
что не прошло `check`, не попадает в `build`/`engine.zip`.

## Интерфейсы

- **`CheckUseCase.execute(input: CheckInput) -> CheckResult`** — вход: путь к
  `organizations/`, `--seed`, `--strict`, формат вывода; выход: `CheckResult`
  (ok, findings, counts). Применяет 13 cross-field правил (см. ARCHITECTURE.md).

Output ports: `OrganizationRepository` (реализован в `data/loader.py`).

## Типы

```python
@dataclass(frozen=True)
class CheckInput: path: Path, seed: int | None, strict: bool, json: bool
@dataclass(frozen=True)
class CheckResult: ok: bool, findings: list[Finding], counts: Counts
# Finding/Counts — см. specs/model.md
```

## Что есть

- `CheckUseCase` (`use_cases/check.py`) — оркеструет load/allocate/check.
- `validate_step.py` — общий pipeline-шаг, переиспользуется `build`.
- 13 cross-field правил (`domain/checker.py`); не short-circuit'ят.
- CLI `cybercity-data check [PATH] [--json] [--strict] [--seed SEED]`.
- Тесты: `tests/use_cases/test_check.py`, `tests/controllers/test_cli.py`,
  `tests/domain/test_checker.py`.

## Что TODO

- Швы MODULE.md: формализовать `ports/` (контракт `OrganizationRepository`)
  и `adapters/` (`data/loader.py`), см. BACKLOG задача 4.

## Ограничения

- Не пишет артефакты (только валидация).
- Валидатор нельзя обходить.
- Без I/O в domain; I/O — только в `data/`.

## Зависимости

- Output ports: `OrganizationRepository`.
- Внутренние: `domain` (models/allocator/checker), `dto` (CheckResult/Counts).
- Внешние: `PyYAML`, `pydantic`.