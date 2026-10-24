# PR #298 — самостоятельная котировка урона от одного попадания normal/web мины

Дата 2026-10-24. Принцип: **не симулировать фактическое попадание, маршрут и Host phase** без документированного RNG и независимого источника.

## Официальные правила

[Planets.nu Minefields → Mine Impact](https://help.planets.nu/minefields):

- Normal field: вероятность попадания **1% за световой год** обычного корабля, **0,5% за световой год** замаскированного корабля; web field: **5% за световой год**, независимо от маскировки. Это базовые локальные documented rates, **не накопленная вероятность за путь и не реальный RNG**.
- Damage для уже произошедшего ОДНОГО попадания normal `ceil(10000 / (hull_mass_kt + 1))` процентов; web `ceil(1000 / (hull_mass_kt + 1))` процентов. Масса — только корпус, без вооружения, груза и топлива. Всегда округлять урон ВВЕРХ. **Не обрезать результат до 100**: последствия уничтожения и специальные расы не рассчитаны.
- Корабль, перемещаемый буксиром, normal/web миной поражён быть не может.
- Для web дополнительно описаны остановка корабля, расход топлива по маршруту и дополнительный потерянный Neutronium `max(50 KT, 1/6...)`. Детали базовой массы топлива/округления/движения требуют отдельного источника, в этом PR **вообще не рассчитываются**.

## Кодовый контракт

`src/planets_lab/rules/mine_impact_single_quote.py` экспортирует `quote_one_documented_mine_impact`, immutable `SingleMineImpactQuote`, `MineImpactQuoteAbstain`.

Только канонические literal mine_kind=`NORMAL`/`WEB`, exact int `1<=hull_mass_kt<=1000000` (локальная граница расчёта, **не лимит Host**), exact bool `ship_cloaked`, `ship_under_tow=False`, explicit complete true assertions для чужого поля, массы *только корпуса*, обычных базовых settings, отсутствия расовых/custom modifiers, гипотетического **одного** попадания. Во всех остальных случаях атомарный `MineImpactQuoteAbstain`. Флаги источника — требования к вызывающей стороне, **не proof** server accepted orders.

Выход: exact rational base per-LY odds numerator/denominator 1/100 (normal), 1/200 (normal cloaked), 1/20 (web); damage numerator 10000 или 1000, denominator hull_mass+1, integer ceiling `(num+den-1)//den`, flag `damage_rounded_up` только при ненулевом остатке. Поле `damage_percent_if_one_hit` означает исключительно потенциальный сырой damage от одного удара. Выход всегда `damage_capped_to_100_percent=False`, `actual_mine_hit_verified=False`, `ship_destroyed_verified=False`, `cumulative_damage_calculated=False`, `web_fuel_burn_calculated=False`, `travel_route_or_movement_calculated=False`, `host_orders_accepted_verified=False`, `host_phase_order_verified=False`, `host_diff_verified=False`. Никаких изменений ship health/inventory/field roster.

Тесты `tests/test_mine_impact_single_quote.py` фиксируют известные 100KT корпуса normal=100% / web=10%, ceil на массах 500, 999 и маленьких массах, no cap100, все четыре вероятности normal/web × cloak с `Fraction`, tow ABSTAIN, exact typed settings/masses, no fuel/route/Host claims, repeatable immutable output. Это **DOCUMENTED + TESTED conditional** только после exact final PR CI; НЕ `DIFF_VERIFIED` и не история реальных mine hits.

## Контекст и будущее

#297 merged `33b8a9fa0454a6ea1c24ec89c038fbecbd8e1fc0`, exact PR CI #1617, postmerge main #1618 success. `mine_conflict_transition_audit.py` классифицирует hypothetical isolated two-field Host stage pre/post snapshots как compatible/conditional contradiction/ABSTAIN, не указывает формулу потерь. Старые #290–296 тоже условны, без независимой Host-phase верификации. Новая котировка **не соединяется** с движением, минами, tow, combat, fuel, связанными фазами или HostEngine. Следующие предметы для независимой работы: conditional single web impact fuel *quote* лишь если точное округление известно, либо private-data-free source adequacy/readiness для настоящих Host witnesses.

#289 public six-game PPQ observations заморожены на CORPUS_OBSERVED, issue #247 user-dependent Host accepted orders PARKED. `CURRENT` public68; prepared public100 >26GiB и sealed M2 heldout32 не читать/перестраивать, production IntelBoard/C5/Horwasp не трогать.

Только synthetic CI; реального Host/corpus эксперимента в #298 нет. Каждый НОВЫЙ реальный test требует tracked single `bash tools/run-*-with-evidence.sh` reusing exact `tools/run-with-runtime-evidence.sh`, автопубликующий sanitized JSON/log/exit/status/source SHA в `runtime-logs` даже ABSTAIN, без private HAR/.trn/orders/IDs/keys. Assistant читает GitHub сам, не просит пользователя копировать логи.

Каждый PR обновляет **полный** `docs/CONTINUE_HERE.md` с реальным номером, нумерованный changelog и отдельный handoff/roadmap; `tools/check_pr_handoff.py` не обходить, exact FINAL PR head CI → merge → проверить main SHA/CI. Пользовательский чат на русском.
