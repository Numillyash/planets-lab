# planets-lab — самостоятельное продолжение после PR #292

Источник истины: https://github.com/Numillyash/planets-lab, живой GitHub `main` и данный файл. Подготовлено 2026-10-24 для PR #292; указанные SHA до PR являются историческими, НЕ текущей головой после merge.

## Правила работы
Продолжай существенную разработку NuHost/Planets.nu simulation и PlanetDashboard research, **весь диалог с пользователем веди на русском языке**. Перед работой прочитай `AGENTS.md`, `docs/WORKFLOW.md`, `docs/ROADMAP.md`, `docs/PR_CHANGELOG.md`, `docs/COMPILED_CORPUS.md` и актуальные `docs/handoff/*.md`. Проверь фактические main HEAD, PR и CI GitHub. Несколько связанных существенных действий за сессию, один консолидированный итог.

Каждый PR ДО merge обязательно полностью переписывает `docs/CONTINUE_HERE.md` с собственным настоящим номером, обновляет `docs/PR_CHANGELOG.md`, отдельную содержательную документацию/roadmap. Нельзя обходить `tools/check_pr_handoff.py`. Создавай PR до финальной документации; проверяй CI точного FINAL PR SHA, только затем squash merge и проверь живой main SHA и postmerge CI. Не придумывай статусы CI/SHA.

Каждый НОВЫЙ эксперимент на сервере/corpus/Host требует tracked короткого `bash tools/run-*-with-evidence.sh`, использующего ТОЧНО существующий `tools/run-with-runtime-evidence.sh`, автоматически публикующего безопасные JSON/log/status/source SHA в отдельной ветке `runtime-logs` даже при ABSTAIN. Читай результат на GitHub сам; не проси пользователя копировать логи. Ни raw .trn/HAR, ни частные приказы, ID/секреты, ключи и персональные данные не публикуй. Только synthetic CI тесты такого runner не требуют.

## Проверенное основание
PR #290: `mine_natural_decay.py` — изолированный условный естественный распад normal/web, 5% или 15% Nebula +1 единица, `round(units*(.95/.85))-1`; строгая ABSTAIN точной .5, 1–12 turns, инварианты и cap100/150 LY; не фаза Host.
PR #291 **фактически merged** 2026-10-24, main SHA `684967df26a220dd3928b469c8a27b747ea11a2b`, финальный PR CI #1583 success, main CI #1584 success. `minelaying_conversion.py` даёт ТОЛЬКО UNALLOCATED число mine units за 11 стандартных семейств torpedo, MD0/MD1..9/MDA/ALL, Robot own normal4× и Crystal web entitlement, с жёсткими ABSTAIN. Не выделяет field ID, не меняет roster и не доказывает принятие приказа.
PR #289 закрыл ограниченное six-game PPQ public observational исследование: 48 квалифицированных перекрывающихся окон; 22 новых для наблюдателя owned ship ID; 17/17 full prior base hull+engine matches при unique base, 5 ABSTAIN; 12/97 old-ship reference, 8/9 pairing; PP unchanged16/increase6/decrease0; НЕ 17 verified Host builds, нет causal attribution. Заморожено `validation/research/pq-public-control12-observational-closure.v1.json`. Не перезапускай эту выборку для дополнительных posthoc корреляций.
`CURRENT` public68; prepared public100 >26GiB НЕ перестраивать. Sealed M2 heldout32 не открывать. `runtime-logs` отдельная ветка. User-dependent accepted Host orders/full inventory/phase issue #247 OPEN but **PARKED**, не требовать личных HAR/private orders. C5/Horwasp и production IntelBoard не трогать.

## ТЕКУЩИЙ PR #292
Ветка `feat/minefield-spatial-placement-candidate-v1`, PR https://github.com/Numillyash/planets-lab/pull/292. Новые `src/planets_lab/rules/minefield_placement_candidate.py`, `tests/test_minefield_placement_candidate.py`, `docs/handoff/2026-10-24-minefield-spatial-placement-candidate-v1.md`.
Чистый immutable conditional spatial *candidate*: полная typed pre-lay ведомость с ID, owner, normal/web, coords/units, место корабля; ближайший compatible same-owner+same-type field center, ties lowest ID, inside radius `isqrt(units)`; гипотетическое NEW или EXPAND; лимиты 100/150 LY, full cluster core disks + 10 LY separation, known soft500 condition. Atomic ABSTAIN при nonstandard/excess/intersections/unknown phase/roster. Нет allocated field ID, mutations, accepted orders, actual creation/merge, loss units, conflicts, sweeping, web drain, HostEngine integration. `DOCUMENTED + TESTED conditional` только ПОСЛЕ exact CI. Synthetic-only; никакого Host/corpus runtime эксперимента в #292.
**IMMEDIATE NEXT:** проверить финальный SHA и PR #292 CI, исправить недочёты/тесты не ослабляя fail-closed, merge только зелёное, проверить merged main HEAD и push CI.

## Следующие исследования
1. Правила реального Host полного placement/expansion/overflow, new field IDs, 500 soft limit and precise star-cluster loss: отдельно по документации и достоверному independent evidence; не принимать synthetic caller flag за серверное подтверждение.
2. Отдельный самостоятельный стандартный mine-sweep/scoop estimator с явной фазой/владельцами/дальность/боеприпасами, только при источнике. Нельзя сразу объединять #290 decay, #291 quote, #292 candidate как настоящий ход.
3. Не менять `CURRENT`, public100, M2 heldout32 или closed PPQ observational cohort. #247 PARKED.
4. Каждый следующий PR включает полный новый русский handoff, PR changelog, отдельную документацию и CI exact head + postmerge main.

Уровни `DOCUMENTED`, `TESTED`, `CORPUS_OBSERVED`, `DIFF_VERIFIED` не смешиваются. Русский язык общения закреплён в `AGENTS.md` и `docs/WORKFLOW.md`.
