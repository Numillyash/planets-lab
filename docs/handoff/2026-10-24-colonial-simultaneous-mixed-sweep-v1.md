# PR #306 — изолированный одновременный Colonial fighter + beam mine sweep

24.10.2026. PRE-PR `main`: `d99001287f480bc417126e54cc78e0d8b940e0cd` (PR #305 merged, exact final PR CI #1669 and postmerge main #1670 SUCCESS). Это исторический SHA, не предполагаемый будущий main.

## Официальный источник и новое правило

[Planets.nu Fighter Mine Sweep](https://help.planets.nu/adv-fighter-mine-sweep) прямо говорит, что **один Colonial корабль** на миссии `Mine Sweep` может одновременно использовать имеющиеся лучи и истребители. Колониальные fighter-ы уничтожают по **20 обычных мин за истребитель в каждом подходящем поле** в пределах 100 LY от края, не могут уничтожать web-мины, **но** могут воздействовать на обычное поле с центром внутри Ion Storm. [Minefields → Mine Sweeping](https://help.planets.nu/minefields) подтверждает пересчёт радиуса после каждого корабля в ascending Ship ID order. Стандартные beam yields (normal/web) берутся из уже проверенного по документации #293; лучевая очистка заблокирована, если центр поля внутри Ion Storm. `web PRE_DECAY` растеризация неизвестна, прежняя #301 near-edge зона остаётся ABSTAIN.

Предыдущий #294 `mine_fighter_sweeping.py` сознательно отказывался от `beam_count>0`, а #293 `mine_beam_sweeping.py` вообще не содержит fighter-канал. Новый модуль **не изменяет** контракты старых модулей. Это отдельный pure scoped **one mixed ship / one Host ID step** расчёт, НЕ multi-ship Host sequence.

## Контракт

Новый `src/planets_lab/rules/colonial_mixed_beam_fighter_sweep.py` экспортирует immutable `MixedColonialCarrier`, `MixedColonialFieldQuote`, `MixedColonialSweepQuote`, исключение `ColonialMixedSweepAbstain` и `quote_isolated_colonial_mixed_sweep`.

На вход — **ровно один** carrier с typed ID/owner/position и `MINE_SWEEP`, `beam_count>0`, `fighter_count>0`, известным canonical beam family и `has_msc_scoop_friendly_code=False`. Обязательны самостоятельные exact True source flags для подтверждённой Missing Colonies расовой принадлежности и преимущества fighter sweeping, точной погрузки и координат, полного исходного roster, complete enemy/ion/standard web-rate flags и отсутствия иных ships, MSC, starbases, custom/racial modifiers. Поле normal/web строго типизировано, радиус стандартный 100 или150. Полные карты Boolean `enemy_by_field_id`, `ion_storm_contains_field_center_by_id`, `standard_web_beam_yield_by_field_id` проверяются **до** любого расчёта. Own field нельзя объявлять enemy. Объявленные флаги не являются независимо аутентифицированными host receipts.

Для КАЖДОГО поля **из одного исходного pre-step integer radius**:
- Beam: стандартная normal или web мощность `beam_count * yield`, только в диапазоне ship beam, не внутри Ion Storm. Normal range strict `distance < radius+5`; web via guarded `PRE_DECAY` range/edge ABSTAIN из #301. Beam может уничтожать normal и web.
- Fighter: если *normal*, `fighter_count*20` при `distance² <= (isqrt(units)+100)²`, включая Ion Storm. Если *web*, `WEB_IMMUNE_TO_FIGHTERS` и 0 независимо от расстояния.
- Total: `destroyed = min(units_before, beam_potential + fighter_potential)`, `remaining=units_before-destroyed`; оба канала считаются на **одном дофазовом радиусе**, поэтому нельзя произвольно переставить их в последовательность. При насыщении поля не утверждается, кому из двух каналов приписать каждую реально уничтоженную мину: `channel_attribution_verified=False` всегда. Синтетическая безопасная бухгалтерия `sum(before)=sum(after)+sum(destroyed)`; `fields_hypothetically_after` не мутирует исходный roster.

Все внешние Host флаги `actual_mission_accepted_verified=False`, `actual_beam_fighter_host_simultaneity_verified=False`, `actual_minefield_state_mutated=False`, `host_phase_order_verified=False`, `host_diff_verified=False`. Это не движение, не MSC, не Colonial starbase fighters, не настоящий Host, не full stage и не доказательство accepted orders.

`tests/test_colonial_mixed_beam_fighter_sweep.py` проверяют 10 standard beam families × normal/web, один общий потенциал и saturation без фиктивного channel attribution, Ion Storm beam blocked vs fighters allowed, web fighters immune, positive/negative fighter range 110/111 при радиусе10, web 11 LY near-edge ABSTAIN, четыре поля с ally/distant/web, deterministic sorting/input immutability, strict bool-as-int/typed loadout/diplomacy/phase/source failures и пустую ведомость.

**Evidence:** официальная документация + синтетические тесты после точного финального PR CI → `DOCUMENTED+TESTED conditional`. Нет независимого `CORPUS_OBSERVED` или `DIFF_VERIFIED`; не использовались реальные Host/on-host/corpus experiments и runtime launcher не нужен.

## Следующая задача

Следующий оправданный полноценный объём: объединённая **ordered per-Ship-ID последовательность**, в которой *каждый* корабль — ровно один из взаимоисключающих канонических контрактов `BEAM_ONLY`, `COLONIAL_FIGHTER_ONLY` или `COLONIAL_MIXED` с полным source-provenance roster и атрибутами, плюс опционально один Campaign base AFTER ships по #304. При этом нельзя дважды считать один carrier и допускать MSC/смешанные неизвестные типы, инварианты должны оставаться сквозными. Это ещё НЕ full Host turn.

#289 public PPQ observational six-game slice CLOSED `CORPUS_OBSERVED`, issue #247 accepted orders/user-dependent phase OPEN BUT **PARKED** (не требовать частного HAR). `CURRENT` public68, prepared public100 >26GiB не читать/перестраивать, sealed M2 heldout32 NEVER open; C5/Horwasp и production IntelBoard не затронуты. Любой **новый реальный** Host/corpus эксперимент только tracked short `bash tools/run-*-with-evidence.sh` reuse exact `tools/run-with-runtime-evidence.sh`, automatic sanitized `runtime-logs` JSON/outer log/status/source SHA даже ABSTAIN; private .trn/HAR/orders/IDs/keys никогда не выгружать.

Каждый PR переписывает **весь** `docs/CONTINUE_HERE.md` с собственным реальным номером, нумерованный `docs/PR_CHANGELOG.md`, содержательные handoff/roadmap/progress map, не обходит `tools/check_pr_handoff.py`. Final exact PR head CI success → squash merge → actual main SHA and postmerge push CI success. Весь чат с пользователем веди на русском.
