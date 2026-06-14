# Organizations

Карточки организаций в формате **1 папка = 1 организация**.
Внутри папки — один файл `config.yml`.

- [Architecture](../docs/ARCHITECTURE.md)
- [Main README](../README.md)

## Зачем отдельные файлы

- Правка одной org — diff в одном `config.yml`.
- LLM-агент читает один файл за раз.
- Люди ревьюят изменения по org.
- Loader собирает всё в `CityNetwork` в памяти.

## Layout

```
organizations/
├── city-hall/
│   ├── config.yml
│   └── services/            # опциональные ассеты сервисов
│       └── hall-web/
│           ├── nginx.conf
│           └── certs/
├── city-bank/
│   ├── config.yml
│   └── services/
│       └── bank-web/
│           ├── nginx.conf
│           └── certs/
└── _archive/               # underscore-папки игнорируются loader'ом
```

## Шаблон `config.yml`

```yaml
id: city-hospital            # должен совпадать с именем папки
name: "City General Hospital"
kind: healthcare             # government | healthcare | infra-utilities | finance |
                             # retail | media-telecom | education | msp
network_index: 10           # 1-255, городской уникальный второй октет

# Краткое описание (необязательно, но рекомендуется).
description: |
  Опиши в 2-4 строках роль, типичные сервисы и связи с другими org.

# Сети организации (ОБЯЗАТЕЛЬНЫ в v2.0).
# Loader не выделяет IP-диапазоны автоматически.
networks:
  - id: city-hospital-dmz
    kind: dmz
    cidr: 10.10.10.0/24
  - id: city-hospital-lan
    kind: lan
    cidr: 10.10.11.0/24
  - id: city-hospital-mgmt
    kind: mgmt
    cidr: 10.10.253.0/24

# Сервисы организации. `org_id` не пишется — loader подставляет из папки.
# `network_id` и `bind_ip` обязательны в v2.0.
services:
  - id: hosp-web
    name: "Hospital portal"
    description: "Публичный портал больницы"   # необязательно
    kind: web                  # web | api | pos | identity | db | file-share |
                               # rmm | vpn | ot | cctv | mail | dns | ntp |
                               # backup | log | erp | hrms | billing | tickets |
                               # wiki | crm | pharmacy-front | iot
    exposure: public           # public | intranet | ot | mgmt
    host: portal.city-hospital.corp
    network_id: city-hospital-dmz
    bind_ip: 10.10.10.10
    auth: sso
    data_classification: public
    criticality: high          # critical | high | medium | low
    software:
      vendor: nginx
      product: nginx
      version: "1.24.0"
      cve_id: "CVE-2023-1234"   # опционально, формат CVE-YYYY-NNNNN
    os_hint: linux
    ports: [tcp/443, tcp/80]

  # Имитационный сервис (массовка для симуляции).
  - id: mock-printer-01
    name: "Mock printer"
    kind: iot
    exposure: intranet
    host: mock-printer-01.city-hospital.corp
    network_id: city-hospital-lan
    bind_ip: 10.10.11.15
    criticality: low
    ports: [tcp/9100, tcp/80]
    decoy:
      kind: printer
      fingerprint: realistic
      os_hint: linux-embedded
      note: "simulation-only endpoint"

# Связи, в которых ЭТА организация - источник.
links:
  - from_service: hosp-web
    to_service: external-idp
    kind: auth                 # api-call | auth | db-read | db-write | log-sink |
                               # backup-of | trusts | vendor-vpn | dns-query | ntp-query
    protocol: tcp/443
    encryption: tls
    label: "federated authentication"
```

## Схема адресации

Каждая организация получает уникальный `network_index` (1-255) — второй октет
городского адресного пространства `10.0.0.0/8`. Все сети org должны лежать
внутри `10.<network_index>.0.0/16`:

```
10.<network_index>.<subnet>.<host>
```

Рекомендуемые договорённости внутри org:

- `dmz` — третий октет `0-127` (например `10.10.10.0/24`).
- `lan` / `ot` — третий октет `128-252` (например `10.10.129.0/24`).
- `mgmt` — третий октет `253` (например `10.10.253.0/24`).

Валидатор проверяет кодом `city-ip-scheme`, что каждая `cidr`
начинается с `10.<network_index>.`.

## Соглашения

- **1 папка = 1 организация.** Имя папки совпадает с `id` в `config.yml`.
- **`config.yml` — единственный файл данных** в папке.
- **`services[].org_id` не пишется.** Loader подставляет автоматически.
- **`networks` обязательны.** Loader не создаёт сети и не назначает IP.
- **`services[].network_id` и `services[].bind_ip` обязательны.** Валидатор поймает ошибки.
- **Опциональные ассеты сервисов** — в `services/<svc-id>/`. Имя папки должно
  совпадать с `id` сервиса из `config.yml`; иначе loader выдаст warning.
- **`decoy` — имитационный сервис.** Используется для плотности симуляции, не связан с security-слоем.
- **links живут в папке from-организации.**
- **Уникальность `(from, to, kind)`** для link'ов.
- **Underscore-папки игнорируются.** `_archive/`, `_draft/`, `_wip/`.
- **Сценарии и уязвимости** — в соседних репозиториях, потребляют эту модель.
- **Нет свободных narrative-полей у организации.** `description` — единственный
  человекочитаемый блок. Если нужны заметки, используй YAML-комментарии (`#`).
- **CLI помогает начать:** `cybercity-data init my-org --kind government --network-index 42`
  создаёт шаблон с примером сети и сервиса. Флаг `--empty` даёт пустой шаблон.
- **Сборка:** `cybercity-data build . --clean` пересоздаёт `build/` с актуальными
  артефактами (`network.json`, `attack-surface.json`, `inventory.md`, `changes.json`,
  `engine.zip` и др.).
