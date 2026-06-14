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
│   └── config.yml
├── city-bank/
│   └── config.yml
└── _archive/               # underscore-папки игнорируются loader'ом
```

## Шаблон `config.yml`

```yaml
id: city-hospital            # должен совпадать с именем папки
name: "City General Hospital"
kind: healthcare             # government | healthcare | infra-utilities | finance |
                             # retail | media-telecom | education | msp
segment: corp                # corp | ot | mgmt | public

# Краткое описание.
description: |
  Опиши в 2-4 строках роль, типичные сервисы и связи с другими org.

# Вендоры / MSP / 3rd-party.
third_party:
  - name: MedSoft MSP
    role: rmm
    note: имеет VPN-доступ к ОТ-сегменту

# Заметки для агентов и сценариев (не валидируются).
notes:
  - "OCS Inventory публично отдаёт hostname всех АРМ"
  - "POS-касса №3 - точка интеграции с банком"

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
    cidr: 10.30.10.0/24

# Сервисы организации. `org_id` не пишется — loader подставляет из папки.
# `network_id` и `bind_ip` обязательны в v2.0.
services:
  - id: hosp-web
    name: "Hospital portal"
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
    software:
      vendor: nginx
      product: nginx
      version: "1.24.0"
    ports: [tcp/443, tcp/80]

  # Имитационный сервис (массовка для симуляции).
  - id: mock-printer-01
    name: "Mock printer"
    kind: iot
    exposure: intranet
    host: mock-printer-01.city-hospital.corp
    network_id: city-hospital-lan
    bind_ip: 10.10.11.15
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
                               # backup-of | trusts | lateral | m2m | vendor-vpn
    protocol: tcp/443
    encryption: tls
    label: "federated authentication"
```

## Соглашения

- **1 папка = 1 организация.** Имя папки совпадает с `id` в `config.yml`.
- **`config.yml` — единственный файл данных** в папке.
- **`services[].org_id` не пишется.** Loader подставляет автоматически.
- **`networks` обязательны.** Loader не создаёт сети и не назначает IP.
- **`services[].network_id` и `services[].bind_ip` обязательны.** Валидатор поймает ошибки.
- **`decoy` — имитационный сервис.** Используется для плотности симуляции, не связан с security-слоем.
- **links живут в папке from-организации.**
- **Уникальность `(from, to, kind)`** для link'ов.
- **Underscore-папки игнорируются.** `_archive/`, `_draft/`, `_wip/`.
- **Сценарии и уязвимости** — в соседних репозиториях, потребляют эту модель.
