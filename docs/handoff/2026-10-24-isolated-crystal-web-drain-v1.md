# PR #300 — отдельная условная фаза Crystal Web Drain (25 KT за поле)

Дата 2026-10-24. Основной первоисточник [Minefields → Web Drain](https://help.planets.nu/minefields) и [Laying As Another Player](https://help.planets.nu/minefields). Предыдущий #299 merged в `a03a2737694480e709af64ae6aa54141cfe2f730`, final PR CI #1629, push main CI #1630 успешны. Никаких реальных Host фаз в этом PR не запускалось.

## Документированная механика

Вражеский корабль внутри или менее 1 LY от **post-decay** окружности web-поля, принадлежащего **Crystal player**, расходует 25 KT Neutronium на поддержание щитов **за каждое** такое поле. В документации прямо указано, что отдельное сообщение web drain не генерируется. Если после web drain топлива нет, любая миссия кроме `Beam up Fuel` сбрасывается на `Explore`. Web-поля **не-Crystal owners** не имеют эффекта перехвата 25 KT per turn. Для игры с особыми датами Safe Passage / Full Alliance и специальных Friendly Codes статус enemy определяется **внешним авторитетным источником**, а не угадывается по ID.

Это НЕ попадание web-мины. Попадание расходует весь scheduled movement fuel и ещё `max(50, start_of_turn_fuel/6)` согласно #299. Не сложить два quote как реальный Host turn без independently witnessed phase inventories.

## Контракт

Новый `src/planets_lab/rules/web_drain_isolated_quote.py` экспортирует immutable `IsolatedCrystalWebDrainQuote`, `WebDrainQuoteAbstain`, функцию `quote_isolated_crystal_web_drain`.

Вход: полный **post-decay** typed roster `LocatedMinefield`, позиция корабля `Point`, owner ID, дофазовое Neutronium, canonical mission в подтверждённом ограниченном scope `EXPLORE`, `BEAM_UP_FUEL`, `MINE_SWEEP`, `CLOAK`; строго полная Boolean карта `enemy_web_by_field_id` **для каждого web field** и карта `crystal_owner_by_owner_id` **для каждого web-owner**. Ключи/значения exact types (bool не принимается как int). Поля normal учитываются для полноты ведомости, но не расходуют fuel. Капы field radius100/150, 128 entries, fuel до 1e6 KT, coords <=1e6 — **локальные guard**, не утверждения о физических Host-limit.

Полностью стандартные допущения, точное исходное fuel/mission, отсутствие иных одновременных/предшествующих влияний, полный post-decay roster, friend/foe (включая FC/diplomacy game era) и Crystal entitlement должны быть отдельно `*_confirmed=True`. Это **не самостоятельная проверка** пользовательских claims и не серверные accepted receipts.

Для enemy Crystal web проверяем **точное безопасное внутреннее подмножество**: если ship distance² <= `isqrt(units)²`, field qualifies. Если уже вне окружности, но distance² < `(isqrt(units)+2)²`, **atomic ABSTAIN** из-за 1 LY edge и точной cell/circle растеризации. Если дальше — безопасный no-drain. Выход перечисляет sorted unique field IDs и `requested_drain_neutronium_kt = 25 * len(fields)`. Если достаточного топлива нет, ABSTAIN — не выдумываем clipping/порядок исхода с нулём. Если дофазовый остаток покрывает расход, `hypothetical_neutronium_after=before-drain`. При drain>0, after==0 и mission!=BEAM_UP_FUEL условно рекомендуем `EXPLORE`; если BEAM_UP_FUEL — не меняем. При 0 подходящих fields даже при 0 топлива НЕ производим сброс mission, потому что web drain не происходил.

Все выходы имеют `ship_fuel_mutated=False`, `mission_actually_reset=False`, `web_mine_impact_calculated=False`, `field_roster_mutated=False`, `host_phase_order_verified=False`, `host_diff_verified=False`. Ни одна операция Host не выполняется; нет реальной позиции, inventory edit, movement engine или actual owner privacy data.

`tests/test_web_drain_isolated_quote.py`: one/two/three qualifying fields, owner/Crystal classification, nonCrystal and normal immune, explicit enemy map/own-web contradiction, post-decay geometry inclusive radius/near-edge abstain, zero-fuel mission-reset exception, partial clipping refusal, missing/malformed roster/diplomacy keys, duplicate IDs, frozen deterministic output and no Host claims. **Synthetic CI only**, уровень `DOCUMENTED + TESTED conditional` исключительно после точного CI финального PR HEAD; не `CORPUS_OBSERVED`/ `DIFF_VERIFIED`.

## Следующий этап и ограничения

Исследовать отдельно правильную near-edge post-decay растеризацию и реальные Host witnesses не используя private data. #299 web-hit fuel and #300 web drain должны оставаться изолированными, даже если обе механики влияют на Neutronium. #289 PPQ public six-game observational freeze CLOSED, issue #247 user-dependent accepted orders OPEN but PARKED, `CURRENT` public68, public100 >26 GiB immutable/no rebuild, sealed M2 heldout32 entity never open; C5/Horwasp, IntelBoard production untouched. Real experiments require tracked single `bash tools/run-*-with-evidence.sh` reusing exact `tools/run-with-runtime-evidence.sh`, sanitized GitHub `runtime-logs` evidence JSON/log/status/source SHA even ABSTAIN; no raw .trn/HAR/orders/identifiers/keys. Each PR complete own numbered `docs/CONTINUE_HERE.md`, `docs/PR_CHANGELOG.md`, separate handoff/roadmap; verify exact PR head CI → squash merge → main HEAD and postmerge push-main CI. Chat with user Russian.
