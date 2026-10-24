# PR #307 — единая ID-ordered ведомость трёх типов корабельной очистки

Дата: 2026-10-24. Исторический pre-PR `main` `ab6bb0b186b922643dbcdcae6e46c9bee1b047b1` (PR #306 merged, final PR CI #1678/main #1679 SUCCESS). Фактический будущий HEAD и CI следует проверять заново.

## Источники и новая механика

[Minefields → Mine Sweeping](https://help.planets.nu/minefields): очистка кораблями происходит в **порядке возрастания Ship ID**, после каждого отдельного корабля размер и радиус полей меняются. [Fighter Mine Sweep](https://help.planets.nu/adv-fighter-mine-sweep): Colonial fighter-only или смешанный fighter+beam carrier уничтожает обычные мины 20/fighter в пределах 100LY от края, включая ion storm; fighters НЕ уничтожают web mines. На смешанном carrier beams и fighters действуют **одновременно внутри ОДНОГО ship step**, не как отдельные корабли. Для beam-only сохраняются 10 стандартных beam family yields из #293, Ion Storm blocking, normal strict <5LY edge, web PRE-decay uncertain cell guard/ABSTAIN.

До этого #293 принимал много **beam-only** кораблей, #294 — отдельно много **fighter-only**, #306 — ровно один **mixed Colonial** carrier; пытаться вызвать их друг за другом для целых групп ломало бы глобальную ID-очередь. Новый `src/planets_lab/rules/ordered_ship_mine_sweeps.py` реализует **одну условную общую очередь из трёх канонических режимов** и не смешивает несколько ролей для одного ID.

## Контракт и алгоритм

API `quote_ordered_isolated_ship_mine_sweeps`, immutable `OrderedShipSweepStep`, `OrderedShipMineSweepLedger`, `OrderedShipMineSweepAbstain`. Вход — ровно один полный initial typed `LocatedMinefield` roster и до 100 полных `SweepingShip | ColonialFighterSweeper | MixedColonialCarrier` (exact class identity, one variant/ID), `max_radius`100/150, полный enemy pair map для **каждой исходной** пары ship/field, полный ion map для **всех исходных** полей, полный стандартный web-rate map для всех исходных web и полный explicit Colonial entitlement map для **каждого** fighter-only/mixed ship ID. Все значения exact bool, no truthy coercion. Каждый enabled flag о полном исходном состоянии/missions/loadouts/diplomacy/race/Ship-ID order/no MSC/no bases/no customs должен быть exact `True`; не является real Host receipt. Обязательна хотя бы одна запись корабля.

Шаг 1. Проверить и отсортировать полную initial field roster и все карты **до любых полевых уничтожений**. Отказ при дублировании Ship ID даже между типами, unknown input class, duplicate field ID, неуказанном field hostility, own field marked enemy, missing Crystal/Colonial entitlement или race/custom/MSC.

Шаг 2. Отсортировать всю смешанную очередь **по общему ship_id**. Для каждого корабля берутся только ещё существующие поля, а ранее полностью валидированные maps детерминированно сужаются до живых ID. Один шаг вызывает только соответствующий существующий модуль: #293 beam-only, #294 fighter-only или #306 mixed carrier; в mixed шаге beam+fighter potentials берутся от одного pre-step radius. Дальше весь результат только conditional quote. Сохраняется report underlying model, поля до/после, потерянные units. Запрещено появление нового field ID, смена owner/center/type или рост mine units; `before_units == after_units + swept`.

Шаг 3. Return final roster и ledger с `sum(initial) == sum(final)+sum(per_ship_swept)`, полная deterministic sorted-семантика. При любой неопределённости, в том числе web near-edge, отказ **АТОМАРНЫЙ** (не возвращает полувыполненную историю). `accepted_ship_missions_verified=False`, `actual_host_ship_sweep_stage_verified=False`, `exact_race_entitlement_from_host_verified=False`, `actual_field_roster_mutated=False`, `host_diff_verified=False`.

`tests/test_ordered_ship_mine_sweeps.py`: три класса в одной unordered входной очереди, normal 1000→996→956→932, shrink 100→36 меняет fighter reach x109 и последующий mixed beam eligibility, web fighter immune и beam sweeping, поле exhausted не воскресает, ion blocks beams но не fighter, own/distant roster, permutation determinism/immutability, проверка полных ORIGINAL maps даже если поле уничтожено первым кораблём, duplicate across variants, all bool/source gates, late-ship web boundary ABSTAIN.

**Статус:** только `DOCUMENTED + TESTED conditional` после exact FINAL PR CI. Нет фактических server-accepted приказов, идентичностей реальных кораблей, переходов Host-фазы и `CORPUS_OBSERVED/DIFF_VERIFIED`. Это pure synthetic code, не runtime experiment; tracked evidence launcher не требуется.

## Следующий реальный смысловой шаг

У нас теперь раздельно #305 beam-only ships → одна Campaign starbase и #307 все три ship modes. Их можно **в следующем PR** связать единым shared-roster gate при строгих `post_ship == pre_starbase`, complete map/time/race/advantage exclusions, не трогая MSC, fighter-starbase, multiple-base, нестандартные web rates и настоящий Host order. Либо перейти на документированную отдельную Campaign Starbase Fighter Sweeping после независимой source review; не утверждать полноценный Host turn.

#289 PPQ six-game CLOSED CORPUS_OBSERVED noncausal, issue #247 accepted Host order and phase evidence OPEN but PARKED, не требовать личные HAR. `CURRENT` public68 unchanged, prepared public100 >26GiB no rebuild/scan/read, sealed M2 heldout32 entity NEVER open; C5/Horwasp/production IntelBoard unchanged.

Любой новый **реальный** Host/corpus experiment сначала frozen hypothesis/source и tracked short `bash tools/run-*-with-evidence.sh` calling exact `tools/run-with-runtime-evidence.sh`, auto-publishing sanitized `runtime-logs` JSON/outer log/status/source SHA даже ABSTAIN. Private .trn/HAR/orders/IDs/keys никогда не публиковать. EVERY PR: rewrite ENTIRE `docs/CONTINUE_HERE.md` own actual #, numbered `docs/PR_CHANGELOG.md`, substantive handoff/roadmap/progress map, exact final PR head CI success → squash merge → actual postmerge main CI success. User-facing chat ONLY Russian.
