# EXAMPLE — шаблон спеки модуля

<!--
  Канон структуры спеки — <methodology-repo>/docs/ARCHITECTURE.md.
  Процедура заведения модуля — <methodology-repo>/docs/ARCHITECTURE.md.
  Внутренняя архитектура модуля (usecases/ports/domain/adapters) —
  <methodology-repo>/docs/ARCHITECTURE.md.
  `<methodology-repo>` =
  [TheCipherKeeper/addm](https://github.com/TheCipherKeeper/addm).

  СКОПИРУЙ этот файл под docs/specs/<module>.md и заполни 7 секций ниже
  (Описание / Интерфейсы / Типы / Что есть / Что TODO / Ограничения / Зависимости).
  Спека описывает КОНТРАКТ (что) каждого юзкейса, не реализацию (как).
-->

## Описание

<один-два предложения: роль модуля, границы ответственности>

## Интерфейсы

<юзкейсы модуля; на каждый — input port (сигнатура `execute(In) -> Out`/ошибки)
и потребляемые output ports (из ports/)>

## Типы

<доменные типы и per-usecase DTO в синтаксисе Python (dataclass/Protocol/Pydantic);
ошибки — здесь же>

## Что есть

<реализованное поведение, ПО ЮЗКЕЙСАМ; каждый пункт → тест>

## Что TODO

<не реализовано, по юзкейсам; переезжает в «Что есть» по мере реализации,
а в BACKLOG.md ставится [x]>

## Ограничения

<чего модуль не делает; явные запреты>

## Зависимости

<output ports + внутренние модули + внешние библиотеки (pydantic, PyYAML, typer, …)>