# Changelog

Все заметные изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
проект следует [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `engine.zip` теперь генерируется при каждой сборке, даже когда ассеты
  сервисов отсутствуют.
- Новые артефакты сборки:
  - `attack-surface.json` — публично открытые сервисы и их метаданные
    CVE/criticality.
  - `inventory.md` — обнаруженные каталоги ассетов сервисов.
  - `changes.json` — git-дифф текущей модели города относительно предыдущей
    сборки.
- Новые cross-field правила валидации:
  - `ip-unique` — запрещает дубли `bind_ip` внутри одной сети.
  - `decoy-criticality` — decoy-сервисы не могут быть помечены `critical`.
  - `decoy-write-real` — decoy-сервисы не могут выполнять `db-write` или
    `backup-of` против реальных сервисов.
- Улучшения CLI:
  - `cybercity-data build --clean` удаляет выходной каталог перед рендерингом.
  - `cybercity-data init` теперь по умолчанию скаффолдит пример сети и сервиса;
    `--empty` возвращает предыдущий минимальный шаблон.
- Улучшения интерактивного HTML-просмотрщика:
  - Фильтр по организации.
  - Гало критичности и легенда.
  - Подсветка поиска и кнопка сброса фильтров.
- Статическая проверка типов `mypy --strict` в CI и pre-commit хуках.
- Property-based тесты на `hypothesis`.
- GitHub Release workflow для тегированных версий.

### Changed
- CLI загружает модель города один раз и передаёт обнаруженные ассеты напрямую
  в builder.
- GitHub Actions и GitLab CI теперь включают job typecheck и загружают все
  новые артефакты.

## [0.4.0] — 2026-06-14

### Changed
- Связи теперь всегда направленные; двунаправленные и many-to-many связи
  удалены.
- Модель `Service` переструктурирована: `network_id` и `bind_ip` обязательны,
  `known_weakness` удалён.
- Схема организации упрощена: narrativные поля удалены, остались только
  структурные.
- Городская IP-схема изменена: `network_index` заменяет `segment`, все
  организации перенумерованы под `10.<index>.x.x`.

## [0.3.0] — ранее

### Added
- Pydantic v2 модели с `extra="forbid"`.
- Per-organization layout с инъекцией `org_id` loader'ом.
- Явные сети и IP-адреса в v2.0.
- `Service.decoy` для simulation-only mock-сервисов.
- CLI-команды: `check`, `build`, `init`.
- Артефакты сборки: `network.json`, `network.md`, `schema.json`,
  `topology.json`, `network.html`, `engine.zip`.
- Флаг `--strict`, считающий предупреждения ошибками.