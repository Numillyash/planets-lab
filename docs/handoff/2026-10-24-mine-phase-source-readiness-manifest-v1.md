# PR #303 — privacy-safe metadata gate пригодности источников для mine-decay Host-phase

Дата: 2026-10-24. Pre-PR `main` `dbdf03b1c3bb3ad332e3e645c7e098a3474d9db2` (PR #302 merged, final PR CI #1648, postmerge main #1649 success). Этот SHA исторический, при следующем PR обязательно проверять live main.

## Зачем этот компонент

До #302 имеется условный аудитор полного `before -> after` roster вокруг **изолированного** распада мин. Но обычные исторические снимки `T-1/T` могут включать наложение множества фаз; приём client-save и HMAC не означает выполнение приказов сервером. Нельзя допустить, чтобы синтетическая арифметическая точность стала фальшивой `DIFF_VERIFIED`.

Новая чистая `src/planets_lab/rules/mine_phase_source_readiness.py` экспортирует `MinePhaseSourceManifest`, `MinePhaseSourceAssessment`, `MinePhaseSourceMetadataAbstain`, `assess_mine_decay_phase_source`. **Никакие реальные identity / orders / .trn / HAR / API keys, координаты, mine units или raw snapshot bytes не вводятся.** Структура содержит только bounded positive/zero counts <=128, точные stage labels и true/false перечисления source completeness и provenance.

Четыре строго поддержанных типа источников:

- `PUBLIC_ARCHIVAL_CONSECUTIVE_TURNS`: отказ `ARCHIVAL_TURNS_NOT_PHASE_BOUNDARIES` всегда, даже когда caller falsely marks every proof Boolean true.
- `CLIENT_SAVE_ACKNOWLEDGEMENT`: отказ `CLIENT_SAVE_ACK_NOT_SERVER_HOST_EXECUTION` всегда; save acknowledgement не подтверждает accepted Host execution.
- `SYNTHETIC_ISOLATED_PHASE_BOUNDARY`: при полном наборе корректных полей только `SYNTHETIC_CONDITIONAL_ONLY`; нет фактического Host.
- `EXTERNALLY_ASSERTED_HOST_PHASE_RECEIPT`: при декларированных exact same turn/stage pair, полных roster, идентичности и Nebula, standard settings, отсутствующих intermediate phases, полноте server-accepted orders metadata и external integrity check результат `DECLARED_COMPLETE_NEEDS_INDEPENDENT_AUTHENTICATION`, **не Host proof**. Если что-либо не подтверждено — `NOT_READY` с причинами.

Контракт строго проверяет exact bool (нет bool-as-int), точные source enums, границы `IMMEDIATELY_BEFORE_NATURAL_DECAY` и `IMMEDIATELY_AFTER_NATURAL_DECAY`, `SAME_HOST_TURN`, полные owner/center/type, Nebula, game settings, phase adjacency, full roster, отсутствие нового поля после *только decay* (post_count <= pre_count). Для неполноты возвращает машинно-читаемые `blockers` в устойчивом порядке. Для некорректного типа данных — atomic `MinePhaseSourceMetadataAbstain`.

Даже **идеально заявленный** Host-phase manifest остаётся `any_real_host_receipt_authenticated=False`, `real_server_orders_accepted_verified=False`, `real_host_phase_boundary_verified=False`, `host_diff_verified=False`. Ценность модели — не «автоматическая верификация Host», а строгая структура требований к будущему легальному исследованию. `can_consider_for_conditional_isolated_audit=True` означает только декларативную пригодность для *условного* #302, без предоставления реального доступа к фазе.

`tests/test_mine_phase_source_readiness.py` покрывает публичные архивы и client-save с ложными позитивными флагами, полностью заявленные external receipts без ложной promotion, synthetic-only, все обязательные причины блокировки, серверный receipt/integrity metadata, невозможное создание новых полей при единственном decay, время/этапы, strict booleans/type/counts и immutable output. **Synthetic CI only**, уровень `TESTED source-metadata classification` после exact CI, НЕ `CORPUS_OBSERVED/DIFF_VERIFIED`; никаких настоящих Host/corpus данных не читает и HostEngine не меняет.

## Дальше

Сохранять #302 conditional transition и #303 metadata gate независимыми. Повысить evidence tier можно только с законными, независимо удостоверенными `server-accepted` order receipts и полной фазовой ведомостью; user-dependent issue #247 **OPEN but PARKED** — не запрашивать private data. Новое реальное исследование допускается лишь с замороженной гипотезой, tracked single `bash tools/run-*-with-evidence.sh` через точный существующий `tools/run-with-runtime-evidence.sh`, auto sanitized JSON/log/status/source SHA в отдельной ветке `runtime-logs` даже ABSTAIN; никаких raw .trn/HAR/private IDs/orders/keys.

#289 six-game PPQ observational frozen, `CURRENT` public68, prepared public100 >26GiB не rebuild/read, sealed M2 heldout32 NEVER open, C5/Horwasp and IntelBoard production unchanged. Любой новый PR обновляет полный русский `docs/CONTINUE_HERE.md` со своим номером, нумерованный `docs/PR_CHANGELOG.md`, содержательный roadmap/handoff, green exact final PR CI → squash merge → postmerge main CI. Пользовательский диалог только на русском.
