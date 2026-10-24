# PR #295 — точная обратимая MSC-котировка полного поля (без Host-исполнения)

Дата: 2026-10-24. Этот этап отделён от #290–294. Официальная документация [Minefields → Mine Scooping](https://help.planets.nu/minefields), [Friendly Codes → MSC](https://help.planets.nu/friendly-codes), [Host Order](https://help.planets.nu/host-order) — источник описанной, но **не независимо принятой Host-приказом** механики.

## Что известно из первоисточника

MSC требует `Mine Sweep` + `MSC` (код без учёта регистра), одновременно лучевого оружия и торпедных аппаратов и **собственного** normal или web-поля в пределах поля либо <1 LY от края. Scoop преобразует mine units обратно в торпеды соответствующего типа, при этом расовый бонус на постановку инвертируется. Документированный пример: для 400 normal мин Mark 8 обычная раса получает 4 торпеды, Robots получают 1 (100 mine units per Mk8 ×4 для Robot). Mine sweep и scoop происходят в общей фазе по ID корабля; **эта цитата не доказывает фазу реального Host**.

## Точный безопасный subset

Новый независимый `src/planets_lab/rules/mine_scoop_full_field_quote.py` экспортирует `quote_exact_whole_field_msc`, immutable `FullFieldScoopQuote`, `MineScoopQuoteAbstain`, `EVIDENCE`.

Считается **только математическая котировка ПОЛНОГО извлечения одного поля** в случае, когда `field.units % (base_torpedo_mines * multiplier) == 0` и вместимость торпед судна гарантированно >= точного целого числа. Поддерживаются все 11 точно именованных стандартных торпед из #291; `multiplier=4` только для подтверждённого own-normal Robot контекста, для standard web только подтверждённый Crystal entitlement и multiplier1. Конверсия целиком обратима: `mine_units == recovered_torps * base_yield * multiplier`, `torpedoes_after == before + recovered <= declared_capacity`. Никакая часть поля не округляется, никакая частичная операция не утверждается.

Геометрия: обязательный complete immutable field roster из существующего `LocatedMinefield`/Point, owner==ship owner и уникальный target field ID. Судно должно находиться ВНУТРИ или точно на целочисленной окружности `floor(sqrt(units))`; внешняя зона <1 LY от края исключена из-за unresolved square/raster. Любое второе owned normal/web поле, способное коснуться корабля (консервативная +2 LY guard), делает выбор target неоднозначным => atomic ABSTAIN. Все поля typed с cap100/150 LY, ID int >0, координаты typed bounded; внешний caller отдельно подтверждает официальный каталог, стандартные racial conversion, отсутствие custom/dense и Host-interference, exact positions, before ammo, free torpedo capacity, mission + tube/beam. Внешние `*_confirmed=True` сами по себе **не удостоверяют** source reality.

Внешняя неполнота, неверный mission/MSC, web без Crystal, Robot web, отсутствующий ship ownership, неделимый остаток (неизвестное округление), недостаточная torpedo capacity (неизвестный partial Host path), multi-owned overlap, off-edge координаты, missing IDs, custom/campaign, взаимодействующие sweep/lay/scoop/movement/ion и недоказанная chronological pre-scoop фаза => ABSTAIN. `friendly_code` code-case-insensitive; `MINE_SWEEP` API sentinel строго каноничен. Локальные bounds 5000 fields, 10000 torpedoes и max координаты — test scope, не пределы NuHost.

Выход `FullFieldScoopQuote` с `proposed_torpedoes_recovered`, `field_mine_units_before`, `exact_mine_units_per_recovered_torpedo`, `proposed_torpedoes_after`, `whole_field_units_mathematically_accounted`, `would_exhaust_field_if_executed=True`. Последнее **только условное**, флаги `actual_torpedoes_transferred=False`, `actual_field_removed=False`, `field_roster_mutated=False`, `host_scoop_accepted_verified=False`, `host_phase_order_verified=False`, `host_diff_verified=False`. Нет изменения ship cargo или mine roster, target object stays same. Нельзя трактовать как запись фактического события либо как обратный Host-шаг для #291–294.

## Проверки и развитие

`tests/test_mine_scoop_full_field_quote.py`: 11 family yields × обычный/Robot нормальный bonus, exact 400→4/1, web entitlement, MSC case, immutable deterministic source, own/foreign ID, two owned overlaps, circle boundary, field max100/150, exact full-capacity acceptance, remainder and saturation ABSTAIN, invalid booleans/IDs/mission/source flags.

Статус **DOCUMENTED + TESTED conditional** исключительно после final exact CI, не `CORPUS_OBSERVED` и не `DIFF_VERIFIED`. Synthetic-only PR; отдельного реального Host/corpus эксперимента нет и runner не нужен. Следующий важный шаг — узнать independently verified partial MSC remainder/inventory rules и Host phase overlap, либо разработать отдельные coarse interaction *refusal* contracts; не превращать цитаты из документации в purported real Host receipts.

Предыдущий main до PR #295 `ce761528989ccc47c273c97b5f1d854e952794e4`, #294 PR CI #1600/main push #1601 green. Bounded six-game PPQ #289 closed at CORPUS_OBSERVED, issue #247 user-dependent Host proof OPEN but PARKED. `CURRENT` public68, prepared public100 >26GiB и sealed M2 heldout32 untouched; C5/Horwasp и production IntelBoard не трогать.

Каждый последующий PR — новый реальный номер, полный русскоязычный `docs/CONTINUE_HERE.md`, номерная `docs/PR_CHANGELOG.md` и отдельные проектные документы в том же PR, strict `tools/check_pr_handoff.py`, exact final PR CI → squash merge → main push CI. В случае нового реального Host/corpus эксперимента tracked `bash tools/run-*-with-evidence.sh` обёртка через уже существующий `tools/run-with-runtime-evidence.sh`, автопубликация sanitized JSON/log/exit/source SHA в `runtime-logs` даже при ABSTAIN; личные HAR/orders/.trn/keys никогда не публиковать. Общение в чате на русском.
