# Продолжение planets-lab — полностью автономный промпт для нового чата

**Репозиторий и источник:** https://github.com/Numillyash/planets-lab, файл `docs/CONTINUE_HERE.md` в актуальном GitHub `main`.
**Подготовлено:** 22 октября 2026 года, **PR #267**.
**Последний подтверждённый main до текущего PR:** `28baec30d88ce209d8ff691de06147e6bdcabd55`, #266 merged, main CI **#1426 success**. Это историческая точка; **каждый новый чат сначала заново проверяет живой HEAD/PR/CI.**

## Context

Продолжай инженерно-исследовательский проект Planets.nu / NuHost — Python-репозиторий `Numillyash/planets-lab` (PlanetDashboard). Задача — последовательно приближать стандартный Host-симулятор к поддерживаемой механике с чётко проверяемыми инвариантами и источниками. Общайся с пользователем на русском. Он предпочитает автономно закрывать **несколько связанных этапов/PR за один заход**, с одним консолидированным ответом в конце, без остановки после каждой промежуточной мелочи.

**Обязательный Git-контракт для каждого PR из #262:** В той же ветке до merge должны обновляться сразу три вида файлов: (1) ВЕСЬ этот standalone `docs/CONTINUE_HERE.md`, с РЕАЛЬНЫМ номером PR, выполненным и дальнейшим планом; (2) соответствующая запись того же PR в `docs/PR_CHANGELOG.md`; (3) минимум одна дополнительная смысловая документация (`docs/ROADMAP.md`, `docs/handoff/*.md`, `README.md` и пр.). GitHub CI enforce через `tools/check_pr_handoff.py`; подробнее `AGENTS.md`, `docs/WORKFLOW.md`. После каждого PR проверяй финальный PR HEAD CI, делай merge только при success и проверяй postmerge CI на точном `main`. Для нового чата не проси вручную копировать прошлые сообщения.

## Verified state

- До #267 main `28baec30d88ce209d8ff691de06147e6bdcabd55`, postmerge main CI #1426 success.
- #263–265: Classic priority+standard queue в одном условном ходе, многотурновой перенос PBP/standard-pointer/склада, узкая условная борьба PBP-владельцев за последний слот. #251–262: 14 экономических фаз, нормальное движение, перенос корабль-планета, starbase facilities, BOM/склады, кораблестроение и документируемые очереди. Все `TESTED conditional`, не реальное исполнение NuHost.
- #266 merged: `src/planets_lab/sim/late_pq_ppq_priority_admission.py`, стандартный PP quote для PQ/PPQ `1 + ceil(min(hull_mass_KT,1000)/50)`, max21 PP, только одна полностью объявленная `pb1` заявка после SOFT cap. Поддерживает программные ID до 999, но НЕ исполняет корабль; все остальные базы должны быть idle, полный roster/PP/условия default rules и отсутствие иных влияний.
- **Текущий PR #267**, ветка `feat/pq-ppq-priority-ship-economy-v1`: `src/planets_lab/sim/late_pq_ppq_priority_ship_economy.py` и `tests/test_late_pq_ppq_priority_ship_economy.py`. На основании строго допущенной #266 заявки делает **одну настоящую модельную priority-сборку** с созданием нового Ship, закупкой отсутствующих компонентов со склада, списанием MC/минералов и Priority Points у владельца, затем 14-фазную планетарную экономику. Возвращает отдельные PP/warehouse/ship/economy ledgers; сверяет финальные характеристики корабля и все планеты, а при ошибке ABSTAIN целого хода. Soft cap и 999 programmatic max различны; обе расстановки до/после экономики являются **условными**. Сначала проверь статус CI и merge **PR #267**, не утверждай их успех без проверки!
- Документация: `docs/handoff/2026-10-22-late-pq-ppq-priority-economy-v1.md`, `docs/handoff/2026-10-22-late-pq-ppq-priority-admission-v1.md`, `docs/ROADMAP.md`, `docs/PR_CHANGELOG.md`. Актуальные GitHub PR обязательнее исторического chat context.
- Не перестраивать 26+ GiB public100 корпус, не открывать frozen heldout32 M2 entity data, `CURRENT` остаётся public68. `runtime-logs` — отдельная evidence ветка, не источник кода.
- Реальные независимо заверенные server-accepted orders, Host boundary и полные independent pre/post snapshots отсутствуют. Пользователь-зависимые замеры отложены в https://github.com/Numillyash/planets-lab/issues/247.

## Next actions

1. Получи через GitHub live main HEAD/CI/PR #267. Если открыт/CI красный, доведи весь #267 до успешного exact-head PR CI, merge и successful main CI (не ослабляй ресурсный аудитор под тесты).
2. Следующий содержательный независимый этап: поздняя **обычная** PPQ очередь — явно полный набор owned planets, распределение слотов и возможные `RB#` особенности (сохранить условный статус, неизвестное → ABSTAIN). Поздняя **обычная PQ** отличается: случайный выбор среди допустимых баз. Не придумывай детерминированный NuHost winner для PQ; нужен seed/извне заданный выбранный слот либо самостоятельный policy branch. При необходимости сначала ввести strict source/slot roster, потом исполнение с существующим независимым BOM/economy аудитором.
3. Далее объединить модели строительства с cargo transfers/движением и последствиями сражений, не затрагивая чужие исследовательские C5 модули. Сосредоточиться на повышении покрытия основного стандартного корпуса, а не только на синтетике.
4. Каждый будущий PR — обязательный обновлённый **полный** этот промпт с его номером, changelog и дополнительные docs, тесты, CI по точному HEAD, merge и main CI. Несколько таких PR за один пользовательский запрос приветствуются.

## Boundaries

Не смешивать `DOCUMENTED`, `CORPUS_OBSERVED`, `INFERRED`, `TESTED` и `DIFF_VERIFIED`. Локальные HMAC, успешный HTTP save, модельные точные совпадения, источник-only игровой доход не доказывают причинное NuHost исполнение или порядок фаз; все новые результаты — максимум `TESTED` условной модели. Не менять `CURRENT`, sealed heldout32, corpus generation public100, unrelated C5 combat, IntelBoard production и signed owner V1/V2 `PlayerOrders`. Нельзя публиковать API ключи, секреты, реальные частные приказы/HAR. Не выдумывать PR/CI/Host semantics; неоднозначные модели должны давать полный `ABSTAIN`.
