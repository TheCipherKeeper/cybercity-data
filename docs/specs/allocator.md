# Спека модуля `allocator`

> Канон структуры — `<methodology-repo>`/docs/ARCHITECTURE.md (`<methodology-repo>` =
> [TheCipherKeeper/addm](https://github.com/TheCipherKeeper/addm)).

## Описание

Генерация сетевой адресации (IP/CIDR) по декларативной модели. Чистая доменная
функция без I/O; вызывается шагом `_allocate` общего pipeline. Реализован в
`src/cybercity_data/domain/allocator.py` (часть `domain`, выделен в отдельную
спеку из-за самостоятельной роли и воспроизводимости).

## Интерфейсы

- **`allocate(network: CityNetwork, *, seed: int | None = None) -> Allocation`**
  — генерирует `org_index` (второй октет городского `10.0.0.0/8`), `net_cidr`
  (CIDR на сеть по `kind`: `dmz`/`lan`/`ot`/`mgmt`/`internet`), `svc_ip`
  (`bind_ip` сервиса внутри сети, начиная с `.10`).

Output ports: нет (чистая функция, детерминированная при фиксированном `seed`).

## Типы

```python
@dataclass(frozen=True)
class Allocation:
    org_index: dict[str, int]   # network_index на org
    net_cidr: dict[str, str]    # CIDR на network_id
    svc_ip: dict[str, str]      # bind_ip на service_id
```

## Что есть

- Воспроизводимая аллокация через `seed` (один `seed` → одинаковая адресация);
  без `seed` — свежая случайная на каждой сборке.
- Сети по `kind`: каждому `kind` — свой CIDR-размер; CIDR лежат под
  `10.<org_index>.x.x` (правило `ip-scheme`).
- `bind_ip` уникален внутри сети (`ip-unique`) и лежит внутри CIDR
  (`ip-in-network`); CIDR не пересекаются (`network-overlap`).
- Тесты: `tests/domain/test_allocator.py`, `tests/test_property.py`
  (property-based инварианты).

## Что TODO

- — (стабилен; новые требования — через BACKLOG).

## Ограничения

- Не декларирует IP — только генерирует.
- Не присваивает адреса вне `10.0.0.0/8`.
- Без I/O; не пишет на диск.

## Зависимости

- Внешние: стандартная библиотека Python (`ipaddress`, `random`).
- Внутренние: `domain/models` (типы `CityNetwork`, `Network`, `Service`).
  Вызывающие: `use_cases/validate_step`, `use_cases/check`, `use_cases/build`.