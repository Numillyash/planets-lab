# PR #305 — conditional двухэтапный beam-only ship → один Campaign starbase Mine Sweep

Дата: 2026-10-24. Pre-PR `main` `43576a6834d385dfbcd604e288d042d91d9c9c56` — PR #304 merged, PR CI #1662/main push CI #1663 green. Это исторический SHA и НЕ предсказывает следующий live HEAD.

## Источники, новое поведение и ограничения

Официальные [Starbase Mine Sweeping](https://help.planets.nu/adv-starbase-mine-sweeping) и [Minefields → Mine Sweeping](https://help.planets.nu/minefields) описывают корабельную очистку и дополнительно однобазовое Campaign-преимущество Starbase Sweep Mines: использует все лучи планетарной+базовой защиты на максимальном buildable beam tech starbase, работает после корабельной очистки; его documented relative stage до scoop **не даёт** самостоятельно идентичность реального Host order. Нет разрешения на MSC, Colonial fighter, concurrent Starbase, multi-base order либо custom. Данное правило ***DOCUMENTED***, но actual NuHost по-прежнему не исполнялся при наших тестах.

Новый `src/planets_lab/rules/ship_starbase_sweep_ledger.py` экспортирует `quote_conditional_ship_then_starbase_mine_sweeps`, immutable `ConditionalShipStarbaseSweepLedger` и `ShipStarbaseMineSweepAbstain`.

На вход один полный typed PRE-SHIP roster `LocatedMinefield`, минимум один full typed beam-only SweepingShip, ровно одна `SweepingStarbase` со включённым Campaign advantage и каноническим `SWEEP_MINES`, полные Boolean карты enemy-by-ship-field (по EVERY ship/field), starbase enemy-by-field (EVERY field), ion-storm (EVERY field), standard web yield (EVERY web), explicit max radius100/150 и **все** source/phase/isolation flags exact True. Caller flags — условия котировки, НЕ верификация реальных заказов и фазы. Неподдерживаемые race/MSC/Colonial/fighter/multi-base/special campaign/interleaving/custom/no source → ABSTAIN.

Порядок вычисления:

1. **Сначала** строго валидировать поля и ВСЕ исходные карты перед потерей полей: исчезнувший field ID нельзя позволять скрыть неполные diplomacy/ion/web контексты. Затем #293 `simulate_isolated_standard_beam_sweeps` сортирует корабли по ID, рассчитывает normal/web beam-only sweep, в каждом шаге пересчитывает radius и проверяет `before = after + swept`.
2. Из `ship_sequence.fields_final` получить POST-SHIP roster: IDs лишь подмножество первоначальных, owner/center/is_web immutable, mine units не растут. Только этот результат передаётся #304 `quote_isolated_campaign_starbase_mine_sweep`, а полные initial starbase enemy/ion/web maps **детерминированно отфильтрованы до оставшихся полей**, без неявного status default. #304 требует настоящего Campaign-преимущества в гипотетическом контексте и рассчитывает one-base quote со строго неизменёнными правилами обычных и web-полей.
3. `ship.final_units == starbase.initial_units`; итог `initial_units == final_units + ship_swept + base_swept`. Возвращается immutable ledger с обоими исходными stage reports, тремя roster snapshots и общими суммами. При любой несовместимости атомарный ABSTAIN, нельзя получить частично вычисленную «середину хода».

Синтетические `tests/test_ship_starbase_sweep_ledger.py`: точная цепь 1000→996→988, уменьшение радиуса 100→36 после blaster закрывает прежнюю дальность starbase на дистанции12, поле полностью израсходовано кораблём не «возрождается», multiple ship IDs sorted, ally/ion, web pre-radius и near-edge ABSTAIN, order invariance и immutability, invalid source flags/maps/MSC/base orders/custom/unknown cap. Нет real host results; все `real_host_orders_accepted_verified=False`, `real_ship_phase_verified=False`, `real_starbase_phase_verified=False`, `real_host_phase_order_verified=False`, `actual_minefield_state_mutated=False`, `host_diff_verified=False`.

**Статус `DOCUMENTED+TESTED conditional` только после exact final PR CI; не `CORPUS_OBSERVED`/ `DIFF_VERIFIED`.** Это первая узкая физически осмысленная композиция beam-only ship+Campaign base, но НЕТ симуляции целого Host turn, нет MSC/fighters, actual orders, map integration or real Host stage proof. Отчёт #304 по одной базе независимо не был Host witnessed; композиция #305 не «улучшает» его evidence tier.

## Следующие зависимости

Для дальнейших значимых этапов — отдельная подтверждённая partial composition с Campaign starbase и отсутствующим MSC либо ограниченная контекстная проверка межфазного состава, но **не** speculative global HostEngine. При любом новом реальном Host/corpus experiment нужен tracked single `bash tools/run-*-with-evidence.sh` reuse EXACT `tools/run-with-runtime-evidence.sh`, авто sanitized `runtime-logs` JSON/outer log/status/source SHA even ABSTAIN. Без private HAR/.trn/orders/player IDs/API keys. Synthetic CI здесь не требует runner.

#289 six-game PPQ public observational closure CLOSED `CORPUS_OBSERVED`, #247 accepted owner Host orders OPEN but PARKED (не требовать HAR). `CURRENT` public68, prepared public100 >26GiB запрет rebuild/scan, sealed M2 heldout32 NEVER open, C5/Horwasp/production IntelBoard untouched.

Every PR: rewrite **entire** `docs/CONTINUE_HERE.md` with OWN actual PR#, append numbered `docs/PR_CHANGELOG.md`, update topic handoff/roadmap/progress map, never bypass `tools/check_pr_handoff.py`. Verify exact final PR HEAD CI SUCCESS before squash merge; then live main SHA and completed postmerge main push CI SUCCESS. Chat with user Russian.
