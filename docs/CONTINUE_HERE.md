# planets-lab: актуальный промпт для продолжения в новом чате

**Canonical repository:** https://github.com/Numillyash/planets-lab, файл `docs/CONTINUE_HERE.md` в действующем `main`.
**Подготовлено:** 2026-10-22, **PR #271**. Проверенный main перед PR = `15858286c3c9a4cc0190d262e642fdc02bc6bc10` — merge #270, PR CI #1445 и main push CI #1446 successful. **Никогда не принимать pinned SHA за live HEAD — перечитать GitHub**.

## Context

Продолжай автономную разработку Python исследовательского репозитория `Numillyash/planets-lab` (NuHost/Planets.nu, PlanetDashboard). Пользователь хочет несколько содержательных этапов/PR в одном сеансе, а затем один консолидированный ответ по-русски. Используй подключённый GitHub: реальный main, PR, проверки, merge; не проси пересылать старые чаты. Обязательно прочитай `AGENTS.md`, `docs/WORKFLOW.md`, `docs/ROADMAP.md`, `docs/PR_CHANGELOG.md` и свежие `docs/handoff/*.md`.

**Неизменное правило #262, CI-enforced**: в КАЖДОМ PR до merge обновить целиком `docs/CONTINUE_HERE.md` с фактическим номером именно этого PR, запись в `docs/PR_CHANGELOG.md` с тем же номером и ещё один содержательный README/ROADMAP/handoff. `tools/check_pr_handoff.py` нельзя обходить. Создавать PR рано, чтобы узнать правильный номер, тестировать CI на последнем точном HEAD, merge только после success, проверять реальный push main CI post-merge; сам prompt НЕ должен обещать ещё не подтверждённую проверку.

## Verified state

- Перед #271: PR **#270** merged в `15858286c3c9a4cc0190d262e642fdc02bc6bc10`, PR CI #1445 success и main CI #1446 success. Ещё раньше #269 merged (CI #1439/#1440 success), #268 merged (CI #1433/#1434 success). Перепроверять все будущие номера.
- **Текущий PR #271**, branch `feat/pq-late-external-selected-regular-economy-v1`: `src/planets_lab/sim/late_pq_external_regular_economy.py`, `tests/test_late_pq_external_regular_economy.py`. ПОЗДНЯЯ обычная Production Queue (**PQ, не PPQ**): ровно 1 свободный слот до soft cap, минимум две конкурирующие queued обычные базы, полный roster всех обычных build-capable старбаз и их warehouse, полной fleet/planet/economy, PP per-owner. **Выбранная случайно база задаётся ВНЕШНИМ caller-assertion, не NuHost RNG**. Проверяются ID самого малого свободного ship, точный компонентный BOM с сохранением warehouse у unselected, полная typed ship identity, экономические события и MC/минералы 14 фаз при двух явно условных before/after economy placement, отсутствие расхода PP на normal queued build; idle bases не зарабатывают PP в этой условной модели. Неподдержанные pbN, cloning, mining, special actions, неполные inputs, malformed stock, forgery → полный ABSTAIN. **TESTED conditional, не DIFF_VERIFIED и не доказательство Host выбора**. Handoff: `docs/handoff/2026-10-22-late-pq-external-regular-ship-economy-v1.md`. ПЕРВОЕ действие нового чата: проверить точный CI #271, исправить без ослабления resource/audit, merge, успешный post-merge main CI.
- PR #270: late PPQ с exact integral owned-planet quota Stage-1 (#269), отбор множества баз по RB1..RB9/hull mass, а затем 10+ реальных модельных кораблей с полным warehouse, ship IDs как операторской перестановкой, PP и 14-фазной экономикой. Soft cap допускается превысить, абсолютный ID ceiling 999; selected set и порядок ID не NuHost-proven. #269 дробные shares и Stage2/3 lottery ABSTAIN, потому нет настоящего rounding/Host RNG. #268: PQ/PPQ ранние queued+idle, начисление selected idle +2PP. #266–267: PQ/PPQ одиночный поздний приоритетный pb1 с default PP=1+ceil(min(hullmass,1000)/50) (макс21), assembler/economy. #259–265: Classic PBP и saved queue pointer, многотурновой перенос; #251–258: ship/planet economy, BOM/warehouses, movement/cargo.
- `CURRENT` canonical corpus — public68; public100 объёмом 26+GiB ранее подготовлен, не пересобирать. Frozen heldout32 M2 entities не читать и не раскрывать. `runtime-logs` — отдельная evidence branch.
- Настоящий `DIFF_VERIFIED` требует независимых server-accepted конкретных orders, Host boundary и полного before/after owner snapshot, чего пока нет. Пользователь-зависимые эксперименты отложены в https://github.com/Numillyash/planets-lab/issues/247.

## Next actions

1. Проверить PR #271 latest head и его CI, устранить все failures, merge только на зелёном final exact head и подтвердить post-merge main push CI. HEAD предыдущего сообщения может быть устаревшим.
2. Последующий существенный PR: bounded **multi-turn поздний PQ**: несколько последовательных условных полно-учётных случаев, на каждом шаге ВНЕШНЕ выбранная база и изменения полной очереди/warehouse/PP, без попытки выводить или сеять NuHost RNG; skip/ABSTAIN как только слот/инвентарь неоднозначен. Либо строго ограниченное соединение shipyard с movement/cargo, если source support достаточен. Обновить PR-specific prompt, changelog, технический handoff.
3. Долгосрочно: поздняя PPQ nonintegral shares Stage 2/3 lottery только при независимом доказательстве host selection или формальной уникальной границе; не переносить поведение PQ в PPQ. C5/combat/IntelBoard production не трогать.
4. Желательно закончить несколько PR за сеанс, но не жертвовать exact CI, ABSTAIN или реальными проверками ради числа PR.

## Boundaries

DOCUMENTED, CORPUS_OBSERVED, INFERRED, TESTED и DIFF_VERIFIED различны. Local HMAC/HTTP success и синтетический тест не доказывают NuHost accepted orders, время или RNG. Не выдумывать округление/тайминг, при неизвестном обязательном элементе — atomic ABSTAIN без частичного мира/очков/складов. Не читать sealed heldout32, не пересобирать public100, не менять CURRENT, unrelated C5/combat, production IntelBoard или V1/V2 signed PlayerOrders, не класть ключи/private orders/HAR в Git.
