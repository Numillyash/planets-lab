# planets-lab — durable continuation prompt for the next ChatGPT chat

**Repository:** https://github.com/Numillyash/planets-lab
**Source:** `docs/CONTINUE_HERE.md` from actual GitHub `main`.
**Prepared 2026-10-22 in current PR #264.**
**Last verified merged main:** after #263 commit
`25c1176a711a1ae4f31045475efea0bc2fed4eaa`, main CI **#1411 success**.
**These are historical snapshots; ALWAYS query live HEAD, PR and CI first.**

## Context

Ты продолжаешь проект Planets.nu / NuHost `planets-lab`
(PlanetDashboard) на Python с собственным детерминированным
HostEngine, статическими правилами, историческим корпусом и
системой проверяемой уверенности. Общайся на русском. Пользователь
хочет автономно выполнять **несколько связанных значимых этапов
за один заход** и только один консолидированный итог, а не
останавливаться после каждого PR. Подключённый GitHub позволяет
получать файлы, создавать ветки/PR, отслеживать CI и merge.

**Обязательное правило каждого будущего PR** (введено #262,
CI enforced): В ТОЙ ЖЕ ветке до merge обновить полный текст
`docs/CONTINUE_HERE.md` (реальный номер PR), добавить запись
того PR в `docs/PR_CHANGELOG.md`, а также изменить ещё
минимум один смысловой документ (`docs/ROADMAP.md`,
`README.md`, `docs/handoff/*.md` или др.). При создании
PR узнаешь номер, доработаешь эти три типа файлов, проверишь
CI именно последнего HEAD, затем merge и последующий main CI.
Правило закреплено в `AGENTS.md`, `docs/WORKFLOW.md`,
`tools/check_pr_handoff.py`. Новый чат НЕ просит пользователя
переслать старую историю — сразу читает этот файл.

## Verified state

- **PR #263** уже merged в main:
  `25c1176a711a1ae4f31045475efea0bc2fed4eaa`,
  PR CI **#1410 success**, post-merge main CI **#1411 success**.
  Он добавил полную условную Classic очередь
  (одна безальтернативная priority PBP постройка + затем
  standard pointer сборки под одним лимитом и общей проверкой
  14 фаз экономики). Priority тратит PBP и не сдвигает
  standard pointer; standard фаза сдвигает pointer и выделяет
  следующие свободные ship IDs. PBP остаётся >=21 либо есть
  конкуренция/неясность — ABSTAIN.
- **Текущий PR #264**, ветка
  `feat/classic-bounded-multiturn-carry-v1`, добавляет
  `src/planets_lab/sim/classic_bounded_multiturn_carry.py`
  и `tests/test_classic_bounded_multiturn_carry.py`.
  Он моделирует 1–8 последовательных условных Classic ходов,
  передавая состояния игры, PBP, saved standard pointer,
  полный склад КАЖДОЙ базы (включая без заказов).
  Если ровно один владелец имеет >=21 PBP — вызывает
  #263 joint очередь; иначе #260 standard-only.
  На каждом ходе отдельная полная таблица приказов всех баз;
  никаких вне-модельных начислений PBP, завоза деталей,
  боя, специальных миссий и реконструкции Host.
  Если поздний ход неподдерживаем, ABSTAIN всей серии
  без частичных результатов. Сначала **проверь реальный
  CI/merge PR #264**; статус на момент этого промпта
  не заявлен как успешный.
- Другие core PR: #251–258 планетарная экономика, 14 фаз,
  структуры/звёздные базы, обычное движение, орбитальный
  грузоперенос, BOM/склады, одна сборка и ранняя очередь
  нескольких баз. #259 standard pointer, #260 его
  сборка/экономика, #261 узкая одиночная priority сборка.
  #262 ввёл обязательные handoff+docs+changelog для
  КАЖДОГО PR. Всё это имеет только доказанную локальную
  категорию `TESTED` в строгом поддерживаемом scope.
- Дорожная карта: `docs/ROADMAP.md`, детальные
  `docs/handoff/2026-10-22-classic-joint-priority-standard-v1.md`
  и `docs/handoff/2026-10-22-classic-multiturn-queue-carry-v1.md`.
  Историю по ранним этапам — `docs/PR_CHANGELOG.md`.
- 26+ GiB public100 корпус уже существует на сервере, его
  НЕ нужно перестраивать. `CURRENT` остаётся public68.
  Frozen heldout32 M2 entities не читать.
  `runtime-logs` — отдельная orphan ветка только для
  публикации чистых машинных доказательств.
- Человеко-зависимая реальная NuHost проверка содержимого
  принятых сервером приказов, времени старта Host и полных
  независимых before/after snapshots отложена в
  https://github.com/Numillyash/planets-lab/issues/247.

## Next actions

1. ПРОВЕРЬ GitHub actual main HEAD, PR #264, его CI.
   Если открыт или CI красный — исправь, перепроверь,
   merge после зелёного CI и затем дождись main CI.
   Следуй `AGENTS.md` и `docs/WORKFLOW.md`.
2. Затем выбери СЛЕДУЮЩУЮ содержательную Host механику,
   не ещё один искусственный микротест:
   либо расширение конкурирующих Classic PBP с доказуемым
   однозначным правилом приоритета, либо типовая PQ/PPQ
   ограниченная очередь после лимита со всеми явно
   объявленными входными состояниями, либо строго ограниченное
   объединение shipyard + движения/передачи/экономики.
   Помни о distinction Host очереди до/после боя.
3. Держи оставшиеся сомнительные/человеко-зависимые
   случаи в #247, не пытайся их «закрыть» фиктивными
   успешными синтетическими данными. Фокус — покрытие
   стандартных механик и экономических взаимодействий
   реального корпуса с явными `ABSTAIN`.
4. Для каждого нового PR обязательны: изменённый этот
   **полный standalone prompt** с его номером, новая запись
   PR changelog и другие обновлённые docs, проверенный CI
   на точном HEAD, merge, post-merge main CI.
   Несколько PR можно закрыть за один пользовательский шаг.

## Boundaries

- `DOCUMENTED`, `CORPUS_OBSERVED`, `INFERRED`,
  `TESTED`, `DIFF_VERIFIED` нельзя путать.
  HMAC, клиентский HTTP success и локальные равные
  состояния НЕ доказывают реальное NuHost исполнение,
  тайминг фаз или server-accepted orders.
- Только `TESTED` и conditional статус для
  перечисленных Classiс очередей; без независимого
  Host источника `DIFF_VERIFIED` ЗАПРЕЩЕНО.
- Не вскрывать sealed heldout32, не делать дорогой
  пересборки public100, не менять `CURRENT`,
  связанные C5/combat или production IntelBoard,
  signed owner `PlayerOrders` V1/V2 без отдельной
  подтверждённой причины. Не публиковать приватные
  API ключи, реальные приказы или сырые captures.
- Не выдумывать PR номера/коммиты/CI результаты,
  не пропускать gate `tools/check_pr_handoff.py`.
  Неизвестная семантика — `ABSTAIN` всей симуляции,
  не придуманное исполнение NuHost.
