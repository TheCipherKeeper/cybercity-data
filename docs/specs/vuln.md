# Спека модуля `vuln`

> Канон структуры — `<methodology-repo>`/docs/ARCHITECTURE.md (`<methodology-repo>` =
> [TheCipherKeeper/addm](https://github.com/TheCipherKeeper/addm)).

> **Статус: TODO** (не начат). Спека-заглушка с заполненным «Что TODO»; код
> модуля заводится по задаче BACKLOG 2. Не выдавать stub за реализацию.

## Описание

Авторинг уязвимостей как first-class сущности: манифест + overlay-исходники
рядом (один PR = одна vuln), `realism ∈ {real, narrative}`; `cve_id` живёт в
vuln-сущности, не в дескрипторе сервиса
([ADR-0006](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/0006-vulnerability-declarative-overlay-realism.md)).
Сборка `overlays`-артефакта (контракт **data → manage** out-of-band).

## Интерфейсы

- **`VulnUseCase.execute(input: VulnInput) -> VulnResult`** (TODO) — парсинг
  манифеста уязвимости + overlay-исходников → валидация → сборка overlay-тарболла.
- **`ValidateVulnUseCase.execute(input) -> CheckResult`** (TODO) — валидация
  vuln: `requires`-предусловие (V2 валиден только если V1 уже эксплуатируется),
  ссылки на сервис, формат `cve_id`.

Output ports (TODO): `VulnRepository` (чтение `vulns/<id>/manifest.yml` +
`vulns/<id>/overlay/`), `OverlayPacker` (сборка overlay-тарболла).

## Типы

```python
# TODO (завести при реализации; набросок по ADR-0006):
@dataclass(frozen=True)
class VulnManifest:
    id: str
    service_id: str          # целевой сервис модели города
    cve_id: str               # CVE-YYYY-NNNNN
    realism: str              # "real" | "narrative"
    requires: list[str]       # id vuln, которые должны быть эксплуатируемы
    overlay: OverlaySpec      # ассеты/скрипты для manage
```

## Что есть

- — (модуль не начат; COMPOSITION → *Статус реализации*: «не начат»).

## Что TODO

- Завести пакет `src/cybercity_data/vuln/` по швам MODULE.md.
- Pydantic-схему манифеста уязвимости (`cve_id`, `realism`, `requires`,
  overlay-спека).
- Валидатор: `requires`-предусловие, ссылки на сервис модели, формат `cve_id`.
- Сборка `overlays`-артефакта (каталог уязвимостей + tarball overlay-плейбуков)
  — контракт data → manage out-of-band.
- Перевод `cve_id` из дескриптора сервиса в vuln-сущность (см. `model.md` → Что TODO).
- CLI-команду `cybercity-data vuln ...` (init/check/build).
- Тесты: `tests/vuln/` — парсинг, валидация `requires`, сборка overlay-тарболла;
  одна vuln на фикс-ветке как пример.

## Ограничения

- `data` только порождает декларацию и overlay-исходники; не собирает образы
  (это `manage`, generic consumer `overlays`-артефакта).
- `cve_id` — в vuln-сущности, не в дескрипторе сервиса (ADR-0006).
- `manage` не владеет семантикой vuln.
- Без I/O в domain; I/O — только в adapters.

## Зависимости

- Внутренние: `domain/models` (ссылка на `service_id`), `dto`.
- Внешние: `pydantic`, `PyYAML`.