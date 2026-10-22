# planets-lab: актуальный промпт для продолжения в новом чате

**Source of truth:** https://github.com/Numillyash/planets-lab → `docs/CONTINUE_HERE.md` в текущем `main`.
**Подготовлен:** 2026-10-22, PR **#269**. До него проверенный main = `96f4054fd57e2583556d39b21a4fc24f903fe388`, PR #268 merged, PR CI #1433 success, push main CI #1434 success. Это исторические сведения: **проверь live GitHub**.

## Context

Продолжай самостоятельную многопоточную разработку исследовательского Python проекта `Numillyash/planets-lab` (Planets.nu/NuHost/PlanetDashboard). Пользователь предпочитает несколько содержательных связанных этапов и PR за один сеанс, с одним консолидированным итогом. Общение по-русски. Используй подключённый GitHub, никогда не изобретай CI или SHA. Прочитай `AGENTS.md`, `docs/WORKFLOW.md`, `docs/ROADMAP.md`, `docs/PR_CHANGELOG.md`, соответствующие `docs/handoff/*.md`.

**Обязательный per-PR contract #262 (CI-enforced):** в КАЖДОМ PR до merge ПОЛНОСТЬЮ переписать `docs/CONTINUE_HERE.md` с настоящим номером текущего PR, внести запись в `docs/PR_CHANGELOG.md` и обновить ещё один содержательный документ. НЕ обходить `tools/check_pr_handoff.py`. PR создаётся до последней правки документации, чтобы известен был номер. После фиксации финального HEAD проверить именно его PR CI, merge только при success, подтвердить успешный main push CI. Готовый итог каждого PR сохраняется в Git, независимо от одного общего ответа.

## Verified state

- PR #268 фактически merged: merge SHA `96f4054fd57e2583556d39b21a4fc24f903fe388`, PR CI #1433 success, main push CI #1434 success. Всегда проверить GitHub повторно перед новым PR.
- **Текущий PR #269**, branch `feat/ppq-exact-integer-stage1-regular-allocation-v1`: `src/planets_lab/sim/late_ppq_integer_stage1_allocation.py` и `tests/test_late_ppq_integer_stage1_allocation.py`. Новая отдельно ограниченная ПОЗДНЯЯ PPQ обычная подфаза. Сначала рассчитывает N=max(10, soft_limit - fleet count), доли по **всем реально принадлежащим** игрокам планетам. Допускает только когда N * owned_by_player / total_owned — целое для КАЖДОГО владельца (точные квоты заполняют N, Stage 2/3 random lottery не нужен). Требует полной явно подтверждённой planet/base/fleet/queue/RB/hull roster, нужного количества queued slots у каждого владельца. Для каждого владельца выбирает строго определённое множество баз по RB1..RB9 или убыванию hull mass; если ничья на границе — атомарный ABSTAIN. Возвращает наборы выбранных баз и N минимальных свободных Ship ID как ПУЛ, но **не назначает ID базам и не строит корабли**. Непроверенные Host selection/order/RNG/тайминг, custom rules, Stage 2/3, missing data, priority/cloning/Mining Stations → ABSTAIN. ТОЛЬКО conditional TESTED, не DIFF_VERIFIED. Релевантный handoff: `docs/handoff/2026-10-22-late-ppq-integral-stage1-allocation-v1.md`. Сначала проверить CI этого PR на точном HEAD и merge; в случае ошибок исправить тесты/модель, не ослабляя проверки.
- PR #266: поздняя PQ/PPQ единственная pb1 priority заявка, default PP = 1 + ceil(min(hull_mass_KT,1000)/50), до 21 PP, строго complete context, без Host proof; #267: её ship/warehouse/economy интеграция и 14-фазная экономика. #268: ранняя PQ/PPQ очередь с queued и idle базами, обычные корабли за 0 PP, **выбранные idle базы +2 PP**, complete warehouse/14 фазы; ship ID set подтверждён исключительно от input, порядок по базам не Host-proven. #259–265: Classic saved pointer, PBP priority, competition, многотурновой перенос. #251–258: экономические фазы, BOM/warehouses и cargo/movement.
- public100 объёмом 26+GiB уже подготовлен, не пересобирать. `CURRENT` = public68. Не раскрывать sealed heldout32 M2 entities. `runtime-logs` отдельная evidence branch.
- Для DIFF_VERIFIED отсутствуют независимо сервером подтверждённые принятые приказы, Host boundary и полные before/after owner snapshots. Пользователь-зависимые проверки отложены в https://github.com/Numillyash/planets-lab/issues/247.

## Next actions

1. Проверить status PR #269, настоящий HEAD GitHub, CI на точном последнем commit, устранить всё, что упало, только затем merge и проверить post-merge main CI. Вновь получить живой main перед каждым PR.
2. Следующий большой этап: сквозная экономика для **точно определённого** позднего PPQ stage1 selected set. Для всех выбранных строек использовать строгую проверку warehouse/BOM и экономических 14 фаз, full fleet, planet resources и per-owner PP, при наличии полного input и явного caller-asserted bijection выбранных баз на N минимальных Ship IDs. НЕ приписывать этот порядок NuHost. При недостающей информации — ABSTAIN. Отдельный PR со своим собственным handoff.
3. Отдельная поздняя PQ randomized ordinary selection, только при **внешнем явно выбранном** base/slot либо независимом доказанном Host seed/capture; затем строгий ship/economy ledger. Не объединять логику случайной PQ с PPQ owned-planet shares и RB ordering.
4. Затем связать shipyards с movement/cargo в строго поддержанном ограниченном core, не затронув unrelated C5 или production IntelBoard. Выполняй несколько PR в одном сеансе, каждый с per-PR документацией; пользователю — один итог.

## Boundaries

Строго разграничивай DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED. Синтетический pytest не доказывает NuHost Host ordering и acceptance. Local HMAC или HTTP response не доказывают принятые конкретные заказы. Никакого фиктивного округления и выдуманного Host RNG/времени. Не читать sealed heldout32 и не пересобирать public100, не менять CURRENT, unrelated C5/combat и IntelBoard production, V1/V2 signed PlayerOrders. Не публиковать private keys/orders/HAR. Недостающий обязательный input и неучтённые операции → атомарный ABSTAIN без частичных результатов.
