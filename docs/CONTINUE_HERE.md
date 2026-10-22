# planets-lab: актуальный промпт для продолжения в новом чате

**Source of truth:** https://github.com/Numillyash/planets-lab `main` → `docs/CONTINUE_HERE.md`.
**Подготовлен:** 2026-10-22, **PR #270**.
**Проверенный main до этого PR:** `a2c387407f45c824ea542b0bb7d777fae129eaff` (PR #269 merged, PR CI #1439 и main push CI #1440 success). Это НЕ обещание о будущем live HEAD: GitHub main, PR, CI обязательно перепроверять.

## Context

Продолжай самостоятельную разработку Python проекта `Numillyash/planets-lab` (NuHost/Planets.nu, PlanetDashboard). Работай несколькими связанными значительными PR за один заход, не проси повторять контекст из чата и отвечай одним консолидированным отчётом по-русски. Проверь подключённый GitHub, текущий `main`, CI, обязательно прочитай `AGENTS.md`, `docs/WORKFLOW.md`, `docs/ROADMAP.md`, `docs/PR_CHANGELOG.md` и релевантные `docs/handoff/*.md`.

**Обязательное правило PR #262:** КАЖДЫЙ PR до объединения должен содержать полностью новый `docs/CONTINUE_HERE.md` с номером ЭТОГО PR, запись с тем же номером в `docs/PR_CHANGELOG.md` и минимум одно другое содержательное изменение README, ROADMAP или handoff. `tools/check_pr_handoff.py` — обязательный CI gate, не обходить и не ослаблять. Создать PR достаточно рано для получения реального номера, после финального коммита проверить CI на точном HEAD, merge только при success, затем проверить настоящий `main` HEAD и post-merge push CI. Никогда не выдумывать зеленый CI или SHA.

## Verified state

- PR **#269** merged, фактический `main` перед #270 = `a2c387407f45c824ea542b0bb7d777fae129eaff`. PR CI #1439 successful и main push CI #1440 successful.
- **Текущий PR #270**, ветка `feat/ppq-integral-stage1-warehouse-economy-v1`. Добавлены `src/planets_lab/sim/late_ppq_integral_stage1_economy.py` и `tests/test_late_ppq_integral_stage1_economy.py`, расширение #269: строго условная поздняя PPQ с ЦЕЛОЧИСЛЕННЫМИ shares по реально принадлежащим планетам (Stage 1, без lottery). Количество N=max(10, soft ship limit - текущий флот), гарантированные целые owner shares исчерпывают N, выбирается однозначный SET queued баз по RB1..RB9 и массе корпуса. Каждая выбранная база строит реальный модельный корабль с exact BOM, складским расходом и MC/mineral debit. Требует полного списка всех баз и warehouse включая unselected, полной синтетической очереди, разрешённых hulls, match hull mass с #269 и явно **caller-asserted** уникальную bijection выбранных баз ↔ N минимальных свободных Ship ID. Технический cap старого assembler = **999 программный**, не soft cap — десять поздних regular кораблей могут перевалить soft. Две гипотезы положения строительства относительно интактной **14-phase** планетной экономики; независимо сверяются ship identities, warehouses, экономические события/ресурсы и полный per-owner PP sidecar. Для обычных selected queued кораблей PP не расходуются; другие источники PP исключены. Любая неизвестность → АТОМАРНЫЙ ABSTAIN. Синтетические тесты проверяют 19→29 при soft cap20, 6:4 allocation, full economy и forged events. Это `TESTED conditional`, **не DIFF_VERIFIED/Host proof**. Подробно: `docs/handoff/2026-10-22-ppq-integral-stage1-ship-economy-v1.md`. **Первое действие: проверить точный PR #270 CI и merge, исправить любые тестовые failures без ослабления ledger, затем main CI**.
- PR #269: `late_ppq_integer_stage1_allocation.py`, exact integer owned-planet Stage1 quota с уникально определёнными base SET, lowest-free ship IDs как нераспределённым pool. Stage 2/3 fractional shares/lottery и Host seed не реализованы. #268: ранние PQ/PPQ, queued builds без PP и idle selected bases с +2PP, complete warehouses/14 фаз. #266–267: одно pb1 приоритетное PQ/PPQ строительство с PP=1+ceil(min(hull_mass_KT,1000)/50), до21, 14 фаз. #259–265: Classic PBP/regular saved pointer, competing/final cap, multiturn carry; #251–258: основа economy, cargo/movement, BOM и shipyards.
- public100 26+GiB подготовлен отдельно; **не пересобирать**. `CURRENT` остаётся public68; sealed M2 heldout32 entity records не читать. `runtime-logs` — отдельная evidence branch.
- Нет независимо подтверждённых server-accepted orders, independent Host boundary и полного real before/after owner snapshot для `DIFF_VERIFIED`; отложенные пользовательские эксперименты — https://github.com/Numillyash/planets-lab/issues/247.

## Next actions

1. Проверить actual #270 head PR tests/CI, исправить обнаруженные падения, получить success на точном HEAD, merge и проверить post-merge main CI, зафиксировать main SHA из GitHub; не полагаться на устаревший SHA.
2. Следующий содержательный PR: **отдельный поздний PQ** с явно внешне выбранной одной regular starbase (не пытаться угадать Host RNG), полным roster idle/queued, полным warehouse и economic + PP ledger, аналогично #270. Не подменять PQ random планетными долями PPQ или Host seed. Можно усилить независимые инварианты для late PPQ.
3. Затем bounded multi-turn PPQ sidecar carry или безопасное соединение shipyard с cargo/movement; выбор из реально поддерживаемых контекстов. Далёкие rounding Stage2/3 PPQ и неснятые real Host cases оставь issue #247/roadmap, если нет проверяемой модели.
4. Для КАЖДОГО нового PR свежий full continuation + change log + substantitive docs; несколько PR и один итоговый отчёт пользователю.

## Boundaries

DOCUMENTED ≠ CORPUS_OBSERVED ≠ INFERRED ≠ TESTED ≠ DIFF_VERIFIED. Синтетические тесты, HMAC, HTTP success не доказывают server-accepted orders или фазы NuHost. Не выдумывать ordering, RNG, округление или тайминг; нет обязательного контекста, необъяснимое действие/расход → целый ABSTAIN, никаких частичных обновлений. Не читать heldout32 и не пересоздавать public100, не менять CURRENT, unrelated C5/combat, production IntelBoard или V1/V2 signed PlayerOrders, не публиковать keys, private orders и HAR.
