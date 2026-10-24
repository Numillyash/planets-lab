# PR #297 — изолированный двухснимковый аудит конфликтов минных полей

Дата: 2026-10-24. Исходный merged main перед PR: `68c897ef57a2d97885eb19d53ab92ad338f73577`, #296 final PR CI #1612 и main CI #1613 success. Эти значения исторические: проверяй живой HEAD, PR и CI.

## Основание и критическое различие движков

Официальная [Planets.nu Minefields → Mine Destruction](https://help.planets.nu/minefields) говорит: пересекающиеся враждебные обычные поля детонируют, пока одно или другое не уничтожено полностью; проверки осуществляются по minefield ID. Тип web не уничтожается normal/web или web/web, mutual Safe Passage не даёт ordinary normal конфликту стать враждебным.

[Документация PHost о формулах mine-destroys-mine](https://planetscentral.com/doc.cgi/phost-4.1e/phost4-formula-mdm) действительно содержит сложный алгоритм при нескольких полях, численные итерации/rounding и альтернативные режимы. Но **PHost != NuHost**, поэтому НЕЛЬЗЯ переносить PHost алгоритм в `planets-lab` как формулу NuHost. В NuHost official help не зафиксированы количественная формула взаимного разрушения и округление при касательной, порядок вызовов с ограничениями Host-сервера. Две соседние хронологические публичные записи не доказывают границу «непосредственно до/после стадии» и accepted player orders.

## Реализованный контракт

Новый `src/planets_lab/rules/mine_conflict_transition_audit.py` экспортирует `audit_isolated_hostile_mine_transition`, immutable `IsolatedMineConflictTransitionAudit`, `MineConflictTransitionAbstain`, канонические identifiers `PRE_STAGE`, `POST_STAGE`.

- Требуется **полная, типизированная** ведомость всех полей непосредственно ПЕРЕД и непосредственно ПОСЛЕ единственной фазы mines-destroy-mines, один положительный строго целый номер хода, exact max radius 100/150, полный explicit `mutual_safe_passage_by_normal_owner_pair[(min_owner,max_owner)] -> bool`, точные неизменные owner/center/is_web для всех сохранившихся полей. Все caller-provenance booleans должны быть exact `True`: и до и после rosters, ни одной другой мутации, exact stable diplomacy, обычные правила без Horwasp/custom/dense, независимо удостоверенные host-phase receipts. Это **не проверка криптографической подлинности**: приложение трактует флаги как декларированные предусловия, Host causal/evidence flags остаются false.
- Граф `classify_conditional_mine_overlaps` из #296 требует **ровно одну** враждебную normal/normal пару и ровно один `ISOLATED_PAIR` component; 0, 2+, coupled-chain, exact tangent или non-hostile pair => atomic ABSTAIN. Истинная пара фиксирована в сортированном порядке ID, любые посторонние поля должны оставаться абсолютно неизменными. Новый field ID, дубликаты ID, координаты/тип/owner изменённого участника, missing source — ABSTAIN.
- Если исчезло **ровно одно** поле, второе стало строго меньше, результат `COMPATIBLE_ONE_ELIMINATED`. Это лишь логическая совместимость, **не** доказательство алгоритма/причины или точных Host потерь.
- Если обе исходные враждебные нормальные окружности существуют на выходе условной изолированной стадии, `CONTRADICTED_BOTH_SURVIVE`. Если одно поле исчезло, но оставшееся выросло, `CONTRADICTED_SURVIVOR_GROWTH`. **«Противоречие» только условное** — прежде чем обвинять NuHost, необходимо отдельно проверить классификацию границы стадии, дипломатии и полноту данных.
- Если **оба** поля исчезли, или один исчез, а второй остался совершенно неизменным — **ABSTAIN**, потому что точный Host dual elimination, leftover rounding и количественная процедура не установлены. Никаких прогнозов погибших мин, суммируемых причинно потерь или последовательности операций не строится.
- `observed_net_unit_change_by_field` — арифметическое отличие двух *предоставленных* снимков, а не causal `mines_destroyed`. Возвращаемые `host_unit_loss_formula_verified=False`, `actual_host_collision_causally_verified=False`, `host_diff_verified=False`, `state_mutated=False` всегда false. В `HostEngine` ничего не подключено.

## Тесты и уровень свидетельств

`tests/test_mine_conflict_transition_audit.py`: one winner either side, различные значения потери surviving (без выбора «правильной» формулы), both survive conditional contradiction, survivor growth, dual disappearance/unchanged survivor ABSTAIN, unaffected normal/web unchanged controls, source order invariance, immutability, wrong phase tags, missing/invalid Boolean evidence/turn IDs, source missing, private-looking extra IDs, wrong owner/center/web, exact tangency, safe passage, nonhostile web, chain и independent pair abstain. Synthetic only, no Host or corpus probe. `DOCUMENTED + TESTED conditional` только после финального CI #297; `CORPUS_OBSERVED` и `DIFF_VERIFIED` не присвоены.

## Границы и следующие исследования

Статические conditional source fields **не превращают** архивы публичных ходов в реальные Host-phase witnessed states. В отсутствие явной пары phase-authenticated source snapshots инструмент должен отказываться, а не изобретать факт. Это не алгоритм loss resolution, не перенос PHost формулы и не интеграция #290–296 в полный ход. Из следующего: разработать строго независимую source sufficiency классификацию без сырых private данных, либо отыскать легальный публичный postconflict event с явным attribution и создать заранее замороженную гипотезу/selection и experiment runner. Для каждого НОВОГО реального Host/corpus эксперимента — tracked короткий `bash tools/run-*-with-evidence.sh` с повторным использованием именно `tools/run-with-runtime-evidence.sh`, авто публикация sanitized JSON/status/outer log/source SHA в отдельный `runtime-logs` даже ABSTAIN; assistant сам читает GitHub. Никаких raw .trn/HAR/private orders, player IDs, access keys в репозитории и логах.

Frozen #289 public six PPQ games (48 не-iid окон, 17/17 unique site-match, 5 ABSTAIN, 12/97 persistent) CLOSED at CORPUS_OBSERVED, никаких повторных posthoc тестов на той же выборке. User-dependent Host issue #247 OPEN but PARKED. `CURRENT` public68; prepared public100 >26GiB запрещено перестраивать; sealed M2 heldout32 NEVER read, C5/Horwasp и production IntelBoard untouched.

Каждый PR — полностью переписанный `docs/CONTINUE_HERE.md` с реальным номером, `docs/PR_CHANGELOG.md`, отдельный содержательный handoff/roadmap, без обхода `tools/check_pr_handoff.py`; exact FINAL PR CI success → squash merge → реальный HEAD main и main push CI. Общение с пользователем только на русском.
