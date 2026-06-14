# Organizations

Карточки организаций в формате **1 папка = 1 организация**.
Внутри папки — один файл `config.yml`. Городские метаданные живут в
`organizations/city.yml`.

- [Architecture](../docs/ARCHITECTURE.md)
- [Main README](../README.md)

## Зачем отдельные файлы

- Правка одной org — diff в одном `config.yml`.
- LLM-агент читает один файл за раз.
- Люди ревьюют изменения по org.
- Loader собирает всё в `CityNetwork` в памяти.

## Layout

```
organizations/
├── city.yml
├── city-hall/
│   └── config.yml
├── city-bank/
│   └── config.yml
└── _archive/               # underscore-папки игнорируются loader'ом
```

## `city.yml`

```yaml
version: "1.0.0"
meta:
  city: cybercity
  allocation:
    corp: 10.10.0.0/16
    ot: 10.20.0.0/16
    mgmt: 10.30.0.0/16
    internet: 203.0.113.0/24
```

`allocation` — базовые диапазоны, из которых loader выделяет сети org.

## Шаблон `config.yml`

```yaml
id: city-hospital            # должен совпадать с именем папки
name: "City General Hospital"
kind: healthcare             # government | healthcare | infra-utilities | finance |
                             # retail | media-telecom | education | msp
segment: corp                # corp | ot | mgmt | public

# Краткое описание.
description: |
  Опиши в 2-4 строках роль, типичные сервисы и известные слабости.

# Вендоры / MSP / 3rd-party.
third_party:
  - name: MedSoft MSP
    role: rmm
    note: имеет VPN-доступ к ОТ-сегменту

# Заметки для агентов и сценариев (не валидируются).
notes:
  - "OCS Inventory публично отдаёт hostname всех АРМ"
  - "Слабый пароль на POS-кассе №3 - entry point в сценарии 04"

# Явные сети (опционально). Если не указаны, loader выделит дефолтные
# по сегменту: corp → dmz/lan/mgmt, ot → ot/mgmt, и т.д.
networks:
  - id: city-hospital-dmz
    kind: dmz
    cidr: 10.10.10.0/24
  - id: city-hospital-lan
    kind: lan
    cidr: 10.10.11.0/24

# Сервисы организации. `org_id` не указывается - loader подставляет из папки.
# `network_id` и `bind_ip` тоже опциональны; loader выберет сеть по exposure
# и назначит первый свободный IP.
services:
  - id: hosp-web
    name: "Hospital portal"
    kind: web                  # web | api | pos | identity | db | file-share |
                               # rmm | vpn | ot | cctv | mail | dns | ntp |
                               # backup | log | erp | hrms | billing | tickets |
                               # wiki | crm | pharmacy-front | iot
    exposure: public           # public | intranet | ot | mgmt
    host: portal.city-hospital.corp
    auth: sso
    data_classification: public
    software:
      vendor: nginx
      product: nginx
      version: "1.24.0"
    ports: [tcp/443, tcp/80]

  # Decoy-хост — это обычный сервис с блоком decoy.
  - id: decoy-printer-01
    name: "Decoy printer"
    kind: iot
    exposure: intranet
    host: decoy-printer-01.city-hospital.corp
    ports: [tcp/9100, tcp/80]
    decoy:
      kind: printer
      fingerprint: default-creds
      os_hint: linux-embedded

# Связи, в которых ЭТА организация - источник.
links:
  - from_service: hosp-web
    to_service: external-idp
    kind: auth                 # api-call | auth | db-read | db-write | log-sink |
                               # backup-of | trusts | lateral | m2m | vendor-vpn |
                               # phishing-source | watering-hole
    protocol: tcp/443
    encryption: tls
```

## Соглашения

- **1 папка = 1 организация.** Имя папки совпадает с `id` в `config.yml`.
- **`config.yml` — единственный файл данных** в папке.
- **`services[].org_id` не пишется.** Loader подставляет автоматически.
- **Сети и IP можно не объявлять.** Loader создаст дефолтные по `segment`.
- **links живут в папке from-организации.**
- **Уникальность `(from, to, kind)`** для link'ов.
- **Underscore-папки игнорируются.** `_archive/`, `_draft/`, `_wip/`.
- **Сценарии** — в соседнем репозитории `cybercity-scenarios`.
