# PR #301 — Phase-qualified conservative web-circle envelope + карта прогресса

Дата 2026-10-24, branch \`feat/web-circle-phase-confidence-gate-v1\`. Prior merged HEAD \`8feba1d956283826fc3db177f2993e1da523e9b9\`, #300 final CI #1634 and main #1635 success (historical only).

## Предпосылки и архитектура

Официальные [Minefields → Mine Sweeping](https://help.planets.nu/minefields) и [Examples → Movement](https://help.planets.nu/minefields-examples) различают **pre-decay** окружность для web sweep и **post-decay** окружность для пассивного Crystal web drain. И web sweep, и drain допускают близость к границе менее 1 LY, при этом для sweep прямо указано касание квадрата местоположения корабля. Точная реализация cell anchor / raster Host не доказана. Нельзя объявлять окружность с радиусом +2 LY формулой реального NuHost.

Новый чистый \`src/planets_lab/rules/web_circle_phase_envelope.py\`: typed \`classify_web_circle_envelope\` с явным \`PRE_DECAY\` или \`POST_DECAY\`, допустимыми strictly int координатами \`Point\`, положительными стандартными units ≤22500 и proof-assertion Boolean. Возвращает immutable \`WebCircleEnvelopeResult\` с source phase, distance squared, floor isqrt radius и консервативным outer guard \`r+2\`. Три класса:
- \`INSIDE_CONFIRMED\`: squared distance ≤ \`r²\`; внутри целочисленной документированной окружности. Только алгоритмическая conditional геометрия.
- \`EDGE_ABSTAIN\`: \`r² < dist² < (r+2)²\`. Возможное web-касание, нельзя выдавать True или False.
- \`OUTSIDE_CONFIRMED\`: \`dist² ≥ (r+2)²\`; далёкая безопасная отрицательная классификация внутри ограниченных стандартных предпосылок.

\`r+2\` — консервативная защитная оболочка для 1 LY возле края и недоказанной raster grid-corner семантики, **НЕ** заявленная дальность NuHost. Умышленно нет входного grid anchor: пока он не найден и не засвидетельствован, near edge остаётся abstention. \`actual_host_selection_verified=False\`, \`exact_web_cell_raster_verified=False\`, \`host_diff_verified=False\` всегда.

Рефакторинг существующих независимых \`mine_beam_sweeping.py\` (вызов с \`PRE_DECAY\`) и \`web_drain_isolated_quote.py\` (вызов с \`POST_DECAY\`) использует этот gate, **не расширяя** множества случаев. Внешние подтверждения полного roster, current owner, enemy/diplomacy и Host phase не заменяются этим модулем. \`tests/test_web_circle_phase_envelope.py\`: exhaustive lattice parity ±35 по x/y на единицах 1/2/9/99/100/101/22500 и обеих фазах, граничные diagonal/symmetry, strict typed source, immutability, optional booleans. Прежние тесты beam/web drain также остаются обязательными.

## Продуктовая обзорная карта

Новый [PROJECT_PROGRESS_MAP.md](../PROJECT_PROGRESS_MAP.md) содержит два Mermaid flowchart, матрицу M0–M6 и подсистем movement, combat, M2 economy, Classic/PQ/PPQ, mines, race/campaign, corpus, end-to-end Host и отдельный статус PlanetDashboard/IntelBoard как ВНЕШНЕГО продукта. Каждый компонент имеет отдельную ось **code maturity** / **source evidence**, чтобы нельзя было принять существование synthetic tests за реальную фазу Host. Старые 2026-09-11 оценки 45–50% total Host surface/60–65% ordinary understanding помечены как исторические, без новых выдуманных процентов. [README](../../README.md) и [ROADMAP](../ROADMAP.md) ссылаются на карту; обновлять при настоящих evidence promotions.

## Evidence/guardrails

\`DOCUMENTED + TESTED conditional\` после exact CI; НЕ \`CORPUS_OBSERVED\`/ \`DIFF_VERIFIED\`, ни одного нового on-host/corpus/Host run. Новое реальное исследование потребует отдельного tracked short \`bash tools/run-*-with-evidence.sh\`, вызывающего существующий \`tools/run-with-runtime-evidence.sh\`, автоматически публикующего sanitized JSON/full log/status/SHA в \`runtime-logs\` даже ABSTAIN. Без private HAR/.trn/owner orders/IDs/keys.

#289 public six-game PPQ observational slice CLOSED, issue #247 server-accepted orders/phase receipts OPEN but PARKED, CURRENT public68 unchanged, prepared public100 >26 GiB no rebuild, sealed M2 heldout32 NEVER open; no C5/Horwasp or production IntelBoard changes. До merge #301: проверить exact final head CI success, затем squash merge, затем actual main SHA + postmerge CI. Каждый будущий PR свой full Russian CONTINUE_HERE+PR_CHANGELOG+topic docs, never bypass \`tools/check_pr_handoff.py\`. Пользовательский чат русский.
