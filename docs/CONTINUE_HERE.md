# Продолжение planets-lab / PlanetDashboard в новом чате

**Источник:** https://github.com/Numillyash/planets-lab — `docs/CONTINUE_HERE.md` в актуальном `main`. Этот текст подготовлен 22 октября 2026 года для **PR #266**. До него main был `e171a2acaead3664afcdfcbe97be16bf4c7ff585`, post-merge CI #1420 success; **перепроверь живой HEAD и CI**, потому что этот SHA — историческая исходная точка.

## Context

Ты продолжаешь Python-исследование NuHost/Planets.nu `Numillyash/planets-lab`: детерминированные модели правил, исторический корпус, консервативные доказательства. Пользователь предпочитает **несколько значимых связанных PR за один заход** и один итоговый отчёт, без постоянных коротких ответов. Общайся на русском, самостоятельно используй подключённый GitHub.

**Обязательный контракт с PR #262:** в КАЖДОМ PR в той же ветке до merge должны меняться (1) ВЕСЬ этот `docs/CONTINUE_HERE.md` с реальным номером PR, выполненным и следующим шагом; (2) `docs/PR_CHANGELOG.md` с номером текущего PR; (3) минимум ещё одна реальная документация (`docs/ROADMAP.md`, `docs/handoff/*.md`, README и т. п.). `tools/check_pr_handoff.py` блокирует CI без этих файлов. Смотри `AGENTS.md`, `docs/WORKFLOW.md`. Тестируй точный HEAD PR, merge только при success, потом проверяй main CI. Новый чат читает этот текст из Git, не требует пересылки истории.

## Verified state

- Последний подтверждённый до PR #266 `main`: `e171a2acaead3664afcdfcbe97be16bf4c7ff585`, CI #1420 success.
- #263: общий Classic PBP priority + standard pointer в одном условном ходе, независимые PBP/стандартный указатель/ship ID/склады и 14 экономических фаз. #264: условный Classic multi-turn с переносом PBP, pointer, warehouses, cap. #265: строго условное соперничество игроков по уникальному максимуму PBP за последний Classic слот; реальный NuHost ranking НЕ подтверждён.
- **Текущий PR #266** `feat/pq-ppq-priority-admission-v1`: `src/planets_lab/sim/late_pq_ppq_priority_admission.py` + новые tests, handoff и roadmap. В поздней PQ/PPQ при достигнутом soft ship cap (но до programmatic 999) рассчитывает стоимость одной полностью объявленной `pb1` priority заявки: `1 + ceil(min(hull_mass,1000)/50)` PP (при default rules). Все остальные базы должны быть явно idle, все PP владельцев и список баз/кораблей полны, никаких других priority или regular заявок/клонов. Возвращает условный PP-дебет и lowest available ID, **никакого корабля и Host turn здесь не создаёт**. Сначала проверь, прошёл ли PR #266 CI и был ли merged; не приписывай ему успех заранее.
- Документация по механике: `docs/handoff/2026-10-22-late-pq-ppq-priority-admission-v1.md`. История: `docs/PR_CHANGELOG.md`, `docs/ROADMAP.md`. Система подсчёта Classic PBP отличается от PQ/PPQ PP; нельзя смешивать формулы.
- Существующий стандартный конвейер: 14-фазная планетарная экономика, башни и базы, warehouse/BOM/кораблестроение, перенос и обычное движение, частичная Classic queue. Механики `TESTED` только в ограниченных сценариях.
- Неприкосновенный 26+ GiB public100 corpus уже подготовлен; `CURRENT` public68, frozen heldout32 M2 не читать. `runtime-logs` только для опубликованных безопасных runtime checks. Нет независимо подтверждённых server-accepted orders, Host boundary и полных pre/post owner snapshots; пользователь-зависимые эксперименты отложены в https://github.com/Numillyash/planets-lab/issues/247.

## Next actions

1. Проверить фактические `main` HEAD, PR #266, CI. Если нужен фикс — исправить, соблюдая per-PR handoff/changelog/docs; merge только после CI success, проверить последующий CI main.
2. Выполнить **следующий сквозной этап**: реализовать исполнение одного допущенного late PQ/PPQ priority ship из #266 с реальным model-only списанием складских деталей, MC/минералов, дебетом PP и полным 14-фазным экономическим ходом. Отличать soft cap от 999-лимита номеров, воспроизводить lowest-free ID; строго повторно проверять целиком получившийся корабль, другие корабли/базы, per-planet ledger, PP и склад. Два явных условных положения фазы до/после экономики. ABSTAIN на недостаточных ресурсах, неизвестных правилах, посторонних действиях.
3. Затем переходить к **отдельной** ограниченной обычной поздней очереди PPQ (распределение по контролируемым планетам, RB#) и PQ (рандомизация) — не выдавать их за один детерминированный порядок. Лучше ещё одна реальная механика, чем синтетическая инфраструктура ради инфраструктуры.
4. Каждый будущий PR: полный новый `CONTINUE_HERE.md`, запись PR number в `PR_CHANGELOG.md`, технические docs, CI exact HEAD, merge, post-merge CI и консолидированный отчёт.

## Boundaries

Строго разделять `DOCUMENTED`, `CORPUS_OBSERVED`, `INFERRED`, `TESTED` и `DIFF_VERIFIED`. HTTP success, локальный HMAC и модели без server receipts НЕ доказывают причинное выполнение NuHost. Все новые результаты — conditional `TESTED`, не `DIFF_VERIFIED`. Не перестраивать public100, не открывать heldout32, не трогать `CURRENT`, чужие C5 combat, IntelBoard prod или signed V1/V2 `PlayerOrders`. Не публиковать секреты, реальные частные приказы и HAR. Не выдумывать подтверждённые CI и Host порядок, неизвестные случаи возвращают целый `ABSTAIN`.
