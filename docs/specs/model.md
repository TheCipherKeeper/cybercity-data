# Спека модуля `model`

> Канон структуры — `<methodology-repo>`/docs/refs/SPEC.md (`<methodology-repo>` =
> [TheCipherKeeper/ai-project-template](https://github.com/TheCipherKeeper/ai-project-template)).

## Описание

Чистая доменная модель города: Pydantic v2-схема (`domain/models.py`),
автоматическая аллокация сетей/IP (`domain/allocator.py`) и cross-field
валидатор (`domain/checker.py`). Без I/O; только данные и правила.

## Интерфейсы

- **`allocate(network: CityNetwork, *, seed: int | None) -> Allocation`**
  (чистая функция): генерирует `org_index`/`net_cidr`/`svc_ip` по `kind` сети и
  позиции сервиса. Воспроизводимо при фиксированном `seed`, иначе случайно.
- **`check(network: CityNetwork, allocation: Allocation, *, strict: bool) -> CheckResult`**
  (чистая функция): применяет 13 cross-field правил; не short-circuit'ит —
  собирает все находки. `strict=True` — предупреждения считаются ошибками.

Output ports: нет (чистый domain).

## Типы

```python
# domain/models.py (Pydantic v2, extra="forbid")
class Organization: id, name, kind, description, networks[]
class Network: id, org_id, name, kind, description   # kind ∈ {dmz,lan,ot,mgmt,internet}
class Service: id, org_id, name, description?, kind, exposure, host,
              network_id, software{vendor,product,version?,cve_id?},
              auth, data_classification, criticality, ports, os_hint,
              honeypot?{kind,fingerprint,os_hint,note}
class Link: from_service, to_service, kind, protocol?, encryption, label  # направленные
class CityNetwork: version, organizations[], services[], links[]

# domain/allocator.py
@dataclass(frozen=True)
class Allocation: org_index: dict[str,int], net_cidr: dict[str,str], svc_ip: dict[str,str]

# domain/checker.py + dto/check_result.py
@dataclass(frozen=True)
class Finding: code, level  # level ∈ {error, warning}
@dataclass(frozen=True)
class CheckResult: ok: bool, findings: list[Finding], counts: Counts
```

`SCHEMA_VERSION` — константа версии схемы в коде.

## Что есть

- `models.py` — полная Pydantic v2-схема v3.0 (organization/network/service/link/city).
  `extra="forbid"`. Тесты: `tests/domain/test_models.py`.
- `allocator.py` — генерация адресации: `org_index` (второй октет `10.0.0.0/8`),
  `net_cidr` (по `kind` сети), `svc_ip` (с `.10`). Воспроизводимо через `seed`.
  Тесты: `tests/domain/test_allocator.py`, `tests/test_property.py`.
- `checker.py` — 13 cross-field правил (см. ARCHITECTURE.md → Cross-field правила).
  Тесты: `tests/domain/test_checker.py`, property-based.

## Что TODO

- Перевод `cve_id` из дескриптора сервиса в vuln-сущность
  ([ADR-0006](https://github.com/TheCipherKeeper/cybercity/blob/main/adr/0006-vulnerability-declarative-overlay-realism.md))
  — поле в модели станет опциональным/устаревшим после заведения модуля `vuln`.

## Ограничения

- Никакого I/O: модель не читает файлы и не пишет на диск.
- Связи всегда направленные; двунаправленная связь — две явные.
- IP-адресация не декларируется — только генерируется аллокатором.
- `checker` нельзя обходить («замолчать» правило вместо починки данных).

## Зависимости

- Внешние: `pydantic>=2.7`.
- Внутренние: `dto` (result DTO). Вызывающие: `use_cases`, `scenario` (WIP),
  `vuln` (TODO).