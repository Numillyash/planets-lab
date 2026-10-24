# PR #302 — условный аудит полной mine-decay phase pair и pre/post web geometry

Дата: 2026-10-24. Pre-PR GitHub `main` `bf20cca2dd0d9e4e18865a6481d72b750a5e73a0`; PR #301 CI #1642, postmerge main CI #1643 SUCCESS. Historical baseline, NOT future main HEAD.

## Зачем нужен отдельный gate

В документации [Minefields](https://help.planets.nu/minefields) распад normal/web поля — `round(units*.95)-1` либо `round(units*.85)-1` при Nebula. [Minefield Examples](https://help.planets.nu/minefields-examples) показывают, что web-sweep ориентируется на PRE-decay circle, а пассивный Crystal web drain — на POST-decay circle. При переходе, например, `100 -> 94` mine units целочисленный радиус изменяется `10 -> 9`; точка корабля (10,0) формально находится внутри pre-decay окружности, но после распада попадает в недоказанную cell/square пограничную область. Нельзя из этого выводить actual server web sweep/drain.

Публичные `T-1 -> T` архивы **не являются фазовыми снапшотами**: между ними возможны laying, sweeping, scooping, combat, ship movement и изменения owners. Без независимо подтверждённого stage boundary они не должны проходить проверку изолированного распада. Нельзя передавать `PUBLIC_ARCHIVAL_T_MINUS_1_TO_T` как `source_kind`; поддерживаются строго типизированные `SYNTHETIC_ISOLATED_PHASE_ASSERTION` и `EXTERNAL_PHASE_BOUNDARY_ASSERTION_NOT_AUTHENTICATED`. Второй вариант **не проверяет** подлинность документа или цифровую подпись; все Host proof flags всегда false.

## Новый контракт

`src/planets_lab/rules/mine_decay_web_phase_audit.py` экспортирует `audit_conditional_natural_decay_web_phase_pair`, immutable `MineDecayFieldDelta`/`MineDecayWebPhaseAudit`, `MineDecayPhaseAuditAbstain`.

- Complete bounded pre/post `LocatedMinefield` rosters (<=128, строго typed positive ID/owner/units, exact Point integer coords, exact Boolean web flag, max radius100/150). Новый post-stage field ID, повторный ID, изменение center/type/owner любого сохранившегося поля: **atomic ABSTAIN**. Исчезновение и изменение числа mine units допустимы как *возможный* результат и отдельно сверяются.
- Полная per-field Boolean `nebula_intersects_by_field_id` в привязке к **pre roster**; no extra/missing keys. Все caller `*_confirmed` флаги должны быть exact True: complete rosters, единственная фаза isolated natural decay, static identities, точная Nebula, standard density и отсутствие custom. Они являются условиями расчёта, **не аутентификацией**.
- Вычисляет ровно один условный ход через существующий модуль #290 `simulate_isolated_natural_mine_decay`; неопределённый tie `.5` возвращает ABSTAIN. Сохраняет expected/observed mine units для каждого field, общего количества до/после и теоретических потерь. `EXACT_MATCH` означает совпадение *двух поданных снимков с условным расчётом*, `SOURCE_MISMATCH` означает только несогласие входа с условной формулой, НЕ ошибку NuHost. Без самостоятельных реальных фазовых свидетельств невозможна причинная атрибуция.
- **Только при полном совпадении roster** вызывает #301 `classify_web_circle_envelope` для одной выбранной web-field и позиции корабля: `PRE_DECAY` и, если поле сохранилось, `POST_DECAY`. `EDGE_ABSTAIN` сохраняется как отдельный `geometry_outcome` (нет вывода web sweep или drain); если field exhausted, `FIELD_EXHAUSTED`; если source arithmetic mismatch, никакая геометрия не продвигается (`NOT_EVALUATED_MISMATCH`).
- Все выходные `source_phase_authenticated=False`, `actual_host_decay_verified=False`, `actual_web_sweep_verified=False`, `actual_web_drain_verified=False`, `host_diff_verified=False`, `source_or_host_state_mutated=False`. Не строит фактическое состояние Host, не добавляет в HostEngine и не утверждает server accepted orders.

## Тесты, свидетельства, следующие шаги

`tests/test_mine_decay_web_phase_audit.py` покрывает full-roster normal/web 100->94, 400->379, Nebula 100->84, exhausted web 1->0, exact pre-inside/post-edge, разные unit-mismatches, отсутствующее неистощённое поле, одинаковость порядка входных records, immutable output, invalid owner/coordinates/field identity, extra/invalid Nebula, half-tie ABSTAIN, source window vs phase, all confirmation flags.

Статус **DOCUMENTED + TESTED conditional только после exact финального CI**. Synthetic-only PR: не использует public corpus, Host orders или runtime. Следующий содержательный этап — source-provenance sufficiency checklist/typed manifest для *законных публичных* потенциальных phase witnesses, а не попытка заставить full-turn archives работать как phase snapshots. Для любого НОВОГО on-host/Host/corpus experiment требуется tracked короткая `bash tools/run-*-with-evidence.sh` через существующий `tools/run-with-runtime-evidence.sh`, автопубликация sanitized JSON/outer log/status/source SHA в `runtime-logs` даже ABSTAIN; личные HAR/.trn/orders/player IDs/keys запрещены. В этом PR runner не нужен.

Независимая PPQ six-game closure #289 frozen at CORPUS_OBSERVED, issue #247 real Host accepted order/phase proof **OPEN but PARKED**. `CURRENT` public68, prepared public100 >26GiB no rebuild/scan, sealed M2 heldout32 entity records never open; C5/Horwasp and production IntelBoard untouched. Все PR требуют full own numbered `docs/CONTINUE_HERE.md`, `docs/PR_CHANGELOG.md`, substantive topic docs/roadmap and progress map where appropriate, exact PR head CI → squash merge → postmerge main CI. User-facing chat на русском.
