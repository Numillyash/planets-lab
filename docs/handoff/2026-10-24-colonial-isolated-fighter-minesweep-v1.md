# PR #294 — изолированная Colonial fighter-only очистка обычных мин

Дата 2026-10-24. Реализовано как отдельный условный **pure** счет, не фактическая фаза Host.

## Нормативный источник

- [Fighter Mine Sweep](https://help.planets.nu/adv-fighter-mine-sweep): Missing Colonies of Man имеют активное по умолчанию преимущество, включаемое миссией `Mine Sweep`. Каждый находящийся на борту истребитель может уничтожить **20 мин в каждом подходящем обычном поле за ход**. Дальность от носителя до ближайшего края 100 LY; web-поля НЕ очищаются. В отличие от beam sweep, Colonial fighters ДЕЙСТВУЮТ при нахождении центра поля внутри Ion Storm. Если у корабля есть лучи, документация допускает одновременную очистку лучами, но её последовательность/суммарная геометрия **здесь НЕ воспроизводится**.
- [Minefields → Mine Sweeping](https://help.planets.nu/minefields): общий порядок starships ascending ID и пересчёт размера полей после каждого; web/normal и поле владельца; оставление неизвестных специальных правил вне scope.
- [Host Order](https://help.planets.nu/host-order): документированный порядок фаз сам по себе не является независимо наблюдённым accepted execution.

## Реализованный контракт

`src/planets_lab/rules/mine_fighter_sweeping.py`: immutable `ColonialFighterSweeper`, `FighterSweepEvent`, `FighterSweepStep`, `FighterSweepSequence`; `simulate_isolated_colonial_fighter_sweeping`, `ColonialFighterSweepAbstain`.

Потребляет строго полный, типизированный **pre-sweep** roster всех normal/web полей и именно fighter-only кораблей с подтверждёнными Colonial entitlement +  `MINE_SWEEP` mission, точными ID/положениями и числом fighters; *beam_count должен быть ровно 0*, иначе ABSTAIN. Полная явная Boolean карта `confirmed_enemy_by_ship_field[(ship_id, field_id)]` требуема даже для своих/союзных полей; owner==owner и enemy=True противоречивы. Размеры полей capped standard radius 100/150 LY. Локальные защитные границы (до 100 ship, 5000 field, 1000 fighters per ship, integer coordinates) не заявлены лимитами реального Host.

Для каждого корабля по возрастанию ID применяет максимум `20 * fighter_count` к КАЖДОМУ вражескому normal полю, центр которого находится на расстоянии не более `floor(sqrt(units)) + 100` LY по точной целочисленной геометрии; если inside, тоже qualifies. Web field не очищается, даже в пределах дистанции. Ion Storm не блокирует Colonial fighter; поле естественно не двигается, а оставшиеся units и radius пересчитываются для следующего корабля. Записываются events и per-ship immutable BEFORE/AFTER rosters, уничтоженные поля исчезают только из следующего *условного* roster. Инвариант `initial_units == final_units + total_units_destroyed` проверяется для каждого шага и всей цепочки.

`fighter_count` используется как множитель, но модель **НЕ утверждает изменения fighter inventory**, их расход или гибель. Нет фактических server-mission receipts, реальной фазы Host, полного одновременного beam+fighter счета, Colonial combined carrier/beam sequencing, starbase fighter sweep, MSC, special custom advantages, новых field IDs или HostEngine integration. Признаки `*_confirmed=True` лишь caller-provided prerequisites; они НЕ верифицированы движком. Все выходные flags Host proof — false. **DOCUMENTED + TESTED conditional** только после exact CI; не CORPUS_OBSERVED / DIFF_VERIFIED.

`tests/test_mine_fighter_sweeping.py`: 20-per-fighter rate, per-field application, normal-only/web immune, граница <=100 LY from field edge, ion-center exception, ID-order recalculation, friendly/not-enemy, complete Boolean matrix, exact typed positive IDs/fighters, 100 LY limit, zero-field/zero-carrier no-ops, exhaustion, invariants/immutability, ambiguous/unsupported inputs ABSTAIN. Только synthetic CI; новый Host/corpus runner не требуется.

## Разграничение с предыдущими PR

#290 isolated decay, #291 torpedo UNALLOCATED quote, #292 spatial candidate, #293 beam-only sweeping и #294 fighter-only sweeping остаются независимыми. Нельзя суммировать #293 + #294 как действующий совместный Host sweep, добавлять decay/lay или судить об actual accepted orders без засвидетельствованного состояния и phase. Предыдущий PR #293 merged main `7c03729baa6bdcd184883621686f1757cfaf9686`, exact PR CI #1594 and postmerge main #1595 success.

#289 public PPQ 6-game frozen at CORPUS_OBSERVED, не перезапускать; issue #247 PARKED. `CURRENT` public68, prepared public100 26+GiB и sealed M2 heldout32 НЕ трогать. Private .trn/HAR/orders/IDs/access tokens запрещены в evidence. Для любого будущего **реального** Host/corpus эксперимента обязательно tracked short `bash tools/run-*-with-evidence.sh` via existing `tools/run-with-runtime-evidence.sh`, auto-publish sanitized outer logs/status/JSON/source SHA в `runtime-logs` даже ABSTAIN, assistant сам читает GitHub.

Каждый новый PR должен переписать весь `CONTINUE_HERE.md` с собственным номером, добавить `PR_CHANGELOG.md`, отдельный handoff/roadmap, exact-head PR CI green, merge и postmerge main CI. Общение с пользователем — на русском.
