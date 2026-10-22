# planets-lab: актуальный промпт для продолжения в новом чате

**Source of truth:** https://github.com/Numillyash/planets-lab → `docs/CONTINUE_HERE.md` в текущем `main`.
**Подготовлен:** 2026-10-22 в PR **#268**.
**Проверенный main до этого PR:** `4989011f8e3699de8fe03a14f63b99427da862a2`, итоговый main CI #1430 success. Это не live head будущего чата — **проверь GitHub заново**.

## Context

Продолжай самостоятельную разработку исследовательского Python проекта `Numillyash/planets-lab` (Planets.nu/NuHost, PlanetDashboard). Пользователь хочет, чтобы ты за один заход выполнял **несколько связанных существенных этапов и PR**, со всеми проверками, и отвечал ОДНИМ консолидированным отчётом вместо мелких сообщений. Общение по-русски. Используй подключённый GitHub для чтения реального `main`, PR, CI, изменений и merge. Не проси пользователя пересказывать прежние чаты.

**ОБЯЗАТЕЛЬНО после каждого PR, правило #262 (CI enforcing):** внутри самого PR до merge перепиши весь `docs/CONTINUE_HERE.md` с номером именно этого PR, добавь соответствующую запись в `docs/PR_CHANGELOG.md`, обнови минимум одну доп. содержательную документацию (`docs/ROADMAP.md`, `docs/handoff/*.md` или README). Нельзя обойти `tools/check_pr_handoff.py`. Прочитай `AGENTS.md` и `docs/WORKFLOW.md`. Создавай PR достаточно рано, чтобы узнать настоящий номер, затем после финального commit проверь CI на точном HEAD, merge только при success, подтверди post-merge main CI. Результат каждого PR оставляй в Git даже если пользователь хочет один итоговый ответ.

## Verified state

- До PR #268 фактический `main`: `4989011f8e3699de8fe03a14f63b99427da862a2`, PR #267 merged, PR CI #1429, main CI #1430 successful. **Всегда перепроверять живой main HEAD перед следующей работой.**
- PR **#266**: `late_pq_ppq_priority_admission.py` — default PP приоритетного корабля PQ/PPQ = `1 + ceil(min(hull_mass_KT,1000)/50)` (max21). В поздней фазе при достигнутом SOFT limit, но при доступном Ship ID ниже programmatic ceiling 999, допускает только ЕДИНСТВЕННУЮ явно pb1-coded priority заявку при полном owner PP/base/ship roster; обычные/другие заявки отклоняются. Только model admission/quote.
- PR **#267**: `late_pq_ppq_priority_ship_economy.py` — на основании #266 реально моделирует сборку одного приоритетного корабля, PP charge, склады компонентов и закупки MC/минералов, 14 экономических фаз (до или после priority), сверяет полный ship и все planet ledgers; conditional TESTED, не server proof.
- **Текущий PR #268**, ветка `feat/pq-ppq-unthrottled-idle-pp-accrual-v1`: `src/planets_lab/sim/early_pq_ppq_idle_pp_turn.py` и новые tests. В ранней полностью свободной очереди PQ/PPQ требует полного списка всех обычных построечных звёздных баз, где минимум одна queued и одна idle: каждый построивший обычный корабль не платит PP, а каждая **выбранная пустая** база начисляет владельцу **+2 PP** при default rules. Применяет полноценную сборку кораблей со склада, независимый BOM, проверку конечного флота, всех 14 экономических фаз и per-owner PP ledger. Набор ship IDs должен равняться N минимальным свободным, но распределение ID по базам задаёт пользователь/оператор и оно НЕ достоверное Host ordering. Допуск только при post-build fleet СТРОГО ниже 90% soft limit; Mining Stations, PQ random late selection, PPQ RB# / owned-planet shares и priority ordering не моделируются.
  **В первую очередь проверить реальный CI и merged status PR #268**, он открыт при подготовке этого handoff; в случае провала исправить без ослабления ресурсных проверок.
- PR #259–265: Classic обычная очередь с сохранённым указателем, строго ограниченные PBP priority builds/конкуренция за последний слот, 14 экономических фаз, многотурновой PBP/pointer/warehouse перенос. #251–258: базовая экономика/оборона/движение, ship-planet cargo, BOM, warehouse assembly, ранняя multi-base queue. Условная `TESTED`, не `DIFF_VERIFIED`.
- Ключевые документы: `docs/ROADMAP.md`, `docs/PR_CHANGELOG.md`, `docs/handoff/2026-10-22-early-pq-ppq-idle-pp-v1.md`, `docs/handoff/2026-10-22-late-pq-ppq-priority-economy-v1.md`, `docs/handoff/2026-10-22-late-pq-ppq-priority-admission-v1.md`.
- Большой корпус public100 ранее подготовлен (26+ GiB) и не требует пересоздания. `CURRENT` остаётся public68; frozen heldout32 M2 entities не раскрывать. `runtime-logs` — отдельная evidence branch.
- Для настоящего `DIFF_VERIFIED` ещё нет независимо подтверждённых сервером принятых приказов, независимого Host boundary и полных before/after owner snapshots; пользователь-зависимые эксперименты отложены в https://github.com/Numillyash/planets-lab/issues/247.

## Next actions

1. Проверить реальные GitHub `main`, CI и PR #268, устранить обнаруженные test failures, довести до точного зелёного CI и merge, затем успешного main CI. Не полагайся на устаревший SHA этого документа.
2. Следующий содержательный основной блок — **отдельные поздние стандартные PQ и PPQ**: PQ random choice требует внешнего явного selected slot или независимого seed/Host capture; PPQ после cap распределяет минимум десять и больше регулярных мест по **доле реально принадлежащих игрокам планет**, с учётом RB#. Разделяй документированные правила от неизвестного rounding/тайминга; там, где точного исходного состояния нет, ABSTAIN вместо фиктивной победы. Можно добавить строго ограниченное уникально определённое распределение, которое не требует неоднозначного округления, и затем соединить с exact warehouse/economy ledger.
3. Расширение сквозного core: безопасное соединение shipyards с movement/cargo и затем боем только в явно поддерживаемой подсистеме, не ломая research C5.
4. НИКОГДА не забывать обновлять этот целый промпт, PR changelog и содержательные docs в КАЖДОМ следующем PR; лучше несколько завершённых PR и общий отчёт.

## Boundaries

Строго различать `DOCUMENTED`, `CORPUS_OBSERVED`, `INFERRED`, `TESTED`, `DIFF_VERIFIED`. Local HMAC и клиент HTTP success не доказывают серверное принятие точных приказов или выполнение NuHost; синтетические тесты не доказывают Host порядок. Новые очереди — максимум `TESTED conditional`. Не читать sealed heldout32, не пересобирать public100, не менять `CURRENT`, unrelated C5/combat или production IntelBoard, V1/V2 signed `PlayerOrders`. Не класть private API keys, private game orders или HAR в Git, не выдумывать CI/коммит/Host факт. Любая неизвестность в обязательном поле или неучтённая операция → атомарный `ABSTAIN` без частичного результата.
