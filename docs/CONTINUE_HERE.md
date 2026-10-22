# planets-lab — self-contained next-chat continuation prompt

**GitHub source of truth:** https://github.com/Numillyash/planets-lab
**Always read the version of this file in live main**:
`docs/CONTINUE_HERE.md`.
**Prepared:** 2026-10-22, current PR **#265**.
**Last independently verified main:** commit
`deb113c84e734120cb88f9afe20cfe1885fea9bb`,
merged PR #264, main CI **#1416 success**. These are a historical
checkpoint, not proof of the current HEAD. Re-check GitHub first.

## Context

Ты продолжаешь исследовательский Python-репозиторий Planets.nu
NuHost `Numillyash/planets-lab`, часть PlanetDashboard.
Задача — постепенное расширение детерминированного симулятора Host,
опираясь на правила, репрезентативные состояния и аккуратное разделение
фактов/гипотез. Отвечай пользователю по-русски. Пользователь
предпочитает, чтобы за одно обращение ты автономно делал несколько
связанных крупных этапов (PR, тесты, CI, merge), а потом дал один
содержательный отчёт, а не останавливался после каждого мелкого PR.

**Обязательное правило, закреплённое PR #262: КАЖДЫЙ PR должен
включать в ту же ветку (до merge):**
1. Обновлённый **ПОЛНЫЙ** автономный prompt `docs/CONTINUE_HERE.md`
   с реальным номером текущего PR, результатами/ограничениями и
   конкретным следующим шагом.
2. Новую запись для этого номера в `docs/PR_CHANGELOG.md`.
3. Обновление ещё одного реального технического документа
   (`docs/ROADMAP.md`, `docs/handoff/*.md`, README и т. п.).
Это автоматически проверяет PR CI через `tools/check_pr_handoff.py`.
Правила в `AGENTS.md`, `docs/WORKFLOW.md`,
`.github/PULL_REQUEST_TEMPLATE.md`. В новом чате прочитай
этот файл непосредственно из Git вместо пересылки пользователем
предыдущих чатов. После PR проверяй CI последнего HEAD, merge,
последующий CI main. Не выдумывай успешные проверки.

## Verified state

- На main до текущего PR: #263 объединён и прошёл CI
  #1410 (PR), #1411 (main). Он соединил одну строго
  безальтернативную Classic PBP priority подфазу с
  classic-standard pointer и full 14-phase экономикой,
  конечным общим ship cap и сквозным MC/складским ledger.
- #264 merged в `deb113c84e734120cb88f9afe20cfe1885fea9bb`,
  PR CI #1415 и main CI #1416 успешно.
  `src/planets_lab/sim/classic_bounded_multiturn_carry.py`
  добавляет 1–8 последовательных локальных Classic ходов:
  PBP/последний standard pointer/полные склады КАЖДОЙ
  базы передаются из предыдущего модельного хода в следующий;
  ровно один PBP-eligible owner → #263 joint path; ноль
  eligible → #260 standard-only path; больше/неизвестность
  → ABSTAIN всей серии без частичного состояния.
  Тест: начальные 8/12 кораблей и 21 PBP, новые ship IDs
  9/10 в первом ходу, 11/12 во втором, в третьем при
  полном cap никто не строит; PBP не появляется извне.
- **Текущий PR #265** на ветке
  `feat/classic-contested-single-last-slot-v1` добавляет
  `src/planets_lab/sim/classic_terminal_pbp_last_slot.py`
  и `tests/test_classic_terminal_pbp_last_slot.py`:
  отдельный КРАЙНЕ ограниченный сценарий реально
  конкурирующих PBP owners за РОВНО ОДИН свободный
  Classic ship slot. Только по явно заявленной гипотезе
  «уникальный максимум PBP выигрывает при отсутствии
  PB-кодов», с точным полным roster, одним заказом
  на eligible owner, без clone/других Host окон. Вернувшийся
  результат — условная локальная модель с затраченными
  PBP/ресурсами у победителя, а не NuHost causal proof.
  **Проверь CI и merged status PR #265**, это пока
  открытый PR на момент подготовки prompt.
- Ранние модели: #251 экономика, #252 обычное движение,
  #253 ограниченный орбитальный cargo transfer, #254
  создание и оборона стандартной звёздной базы, #255–257
  BOM, warehouses и assembly, #258 ранние multi-base
  Classic/PQ/PPQ, #259–260 standard saved-pointer queue
  и assembly, #261 uncontested PBP priority. Все
  локально TESTED **только в заявленном ограниченном scope**.
- План: `docs/ROADMAP.md` плюс
  `docs/handoff/2026-10-22-classic-contested-final-pbp-slot-v1.md`,
  `docs/handoff/2026-10-22-classic-multiturn-queue-carry-v1.md`,
  `docs/handoff/2026-10-22-classic-joint-priority-standard-v1.md`.
  Точные изменения по PR: `docs/PR_CHANGELOG.md`.
- Корпус public100 уже собран и сохранён; бинарный корпус
  26+GiB не требуется заново читать/строить. `CURRENT`
  остаётся public68. Frozen heldout32 M2 entities не
  открывать. `runtime-logs` orphan ветка только для
  безопасной публикации runtime evidence.
- Независимо подтверждённых server-accepted orders, Host
  boundary/времени выполнения и полных independent owner
  T−1/T states пока нет. Зависимые от человека
  эксперименты отложены в
  https://github.com/Numillyash/planets-lab/issues/247.

## Next actions

1. Сначала вызови доступные GitHub инструменты, проверь
   АКТУАЛЬНЫЙ main, PR #265, последний commit PR CI и
   main CI. Если PR открыт/красен, исправь и закрой с
   соблюдением обязательного handoff/документации в PR.
2. После #265 не придумывай современный реальный порядок
   Classic Priority без независимых источников:
   официальный Host Order предупреждает о возможных
   изменениях приоритетов PB-кодов/слотов игроков.
   Выбор по максимуму PBP в #265 — **явно оператором
   заявленная гипотеза**, не `DIFF_VERIFIED`.
3. Следующая содержательная разработка: реальные
   ограниченные PQ/PPQ late-slot правила с полной
   очередью/планетарными процентами/приоритетными
   очками, либо сквозная композиция стандартного
   кораблестроения + movement/cargo+economy без
   неучтённых боёв. Выбирай те сценарии, где достаточно
   известных входов; неизвестное → ABSTAIN.
4. Дополнительно развивай regression/coverage на
   public68/доступном фиксированном корпусе только при
   реальной необходимости, без пересборки и без
   разгерметизации sealed heldout32.
5. На КАЖДЫЙ новый PR: полный `CONTINUE_HERE.md`,
   PR changelog с реальным номером и ещё минимум один
   документ; PR CI на точном HEAD, merge, main CI,
   итоговый отчёт пользователю после нескольких этапов.

## Boundaries

- Разделять `DOCUMENTED`, `CORPUS_OBSERVED`, `INFERRED`,
  `TESTED`, `DIFF_VERIFIED`. Клиент HTTP success, локальный
  HMAC и совпадение модельных результатов НЕ подтверждают
  принятие сервером точных приказов, реальное выполнение
  NuHost, или точный порядок фаз.
- Все новые Classic queue модели — `TESTED conditional`,
  с обязательным полным `ABSTAIN` при неявной конкуренции,
  неизвестных данных или неподдерживаемом взаимодействии.
- Не перестраивать public100, не трогать `CURRENT`,
  heldout32, unrelated C5/combat или IntelBoard prod.
  Не менять signed V1/V2 `PlayerOrders`, не класть
  реальные API ключи, закрытые приказы или raw HAR в Git.
- Не изобретать отсутствующие имена инструментов/скриптов
  и не заявлять зелёный CI до проверки. Использовать
  `AGENTS.md`, `docs/WORKFLOW.md`, `docs/ROADMAP.md`
  и live GitHub как единственный актуальный источник.
