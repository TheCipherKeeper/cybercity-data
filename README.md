# CyberCity — City Data

[![Part of CyberCity](https://img.shields.io/badge/CyberCity-composition-blueviolet)](#)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey)](LICENSE-DOCS)

Единственный канонический YAML с описанием города: **30 организаций,
95 сервисов, decoy-хосты** (ADR-0007). Используется [core-валидатором](https://github.com/TheCipherKeeper/cybercity)
и проецируется в K8s-манифесты.

> Смотреть глазами — [`network.md`](network.md) (человекочитаемая проекция).
> Править руками — `network.yml`. После правки прогонять
> `go run ./cmd/validate-network` в [`cybercity-core`](https://github.com/TheCipherKeeper/cybercity).

## Что внутри

- `network.yml` — каноническое декларативное описание города
- `network.md` — человекочитаемая проекция для ревью и обсуждения
- `organizations/` — детальные карточки организаций (по мере наполнения)
- `decoys/` — decoy-хосты (фон масштаба, чтобы `nmap /24` выглядел реалистично)

## Модель

```
kind сервиса:    web, api, pos, identity, db, file-share, rmm, vpn, ot,
                 cctv, mail, dns, ntp, backup, log
exposure:        public | intranet | ot | mgmt
сегмент:         corp | ot | mgmt | public
```

Три организации помечены как эталонные (`[*]`) и описываются руками.
Остальные генерируются LLM-агентом **по одной за итерацию** с обязательной
валидацией.

## Сводка v1.0

| Блок | Организаций | Сервисов |
|---|---|---|
| Government | 8 | 26 |
| Healthcare | 4 | 13 |
| Infrastructure & Utilities | 5 | 17 |
| Finance | 4 | 11 |
| Retail | 3 | 10 |
| Media & Telecom | 2 | 5 |
| Education | 2 | 7 |
| MSP / провайдеры | 2 | 6 |
| **Итого** | **30** | **95** |

## Композиция CyberCity

| Слой | Репозиторий |
|---|---|
| Профиль / витрина | [TheCipherKeeper](https://github.com/TheCipherKeeper/TheCipherKeeper) |
| Сайт | [thecipherkeeper.github.io](https://github.com/TheCipherKeeper/thecipherkeeper.github.io) |
| Core | [cybercity](https://github.com/TheCipherKeeper/cybercity) |
| **Данные (этот репо)** | **cybercity-data** |
| Сценарии | [cybercity-scenarios](https://github.com/TheCipherKeeper/cybercity-scenarios) |
| UI | [cybercity-ui](https://github.com/TheCipherKeeper/cybercity-ui) |
| Агенты | [cybercity-agents](https://github.com/TheCipherKeeper/cybercity-agents) |
| Blueprints | [cybercity-blueprints](https://github.com/TheCipherKeeper/cybercity-blueprints) |

## Лицензия

- Код / YAML: [MIT](LICENSE)
- Документация (`network.md` и пр.): [CC BY 4.0](LICENSE-DOCS)
