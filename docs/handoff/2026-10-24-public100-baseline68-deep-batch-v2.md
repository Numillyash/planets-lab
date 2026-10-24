# PR #310 — полный публичный public100 metadata census + deep baseline68 owner-current M2 и весь pytest за один запуск

Дата 24.10.2026. Исторический main до PR: `55faf7417b6d0255b7f6dfe60ca2695a7b3db459`; PR #309 merged, CI PR #1703/main #1704 SUCCESS. Любые будущие HEAD проверять по GitHub live.

## Зачем изменили запуск

В #309 один server run `public68-broad-readonly-census-v1` фактически подтвердил 68 games / 169569 snapshots / 16 typed sections / 168397 adjacent archive observations, но это был преимущественно SQL COUNT и temporal census, а не глубокая механика. `synthetic_test_exit=1` и `COUNT_NOT_AVAILABLE` без санитарной классификации; локальный pytest log не опубликован. Ошибка pytest **не связана доказанно с повреждением DB**. Пользователь справедливо просил максимально полезный долгий проход и напомнил о публичном corpus 100.

5 октября уже построена, полностью сверена 224014/224014 и оставлена неизменной `public100` generation:
`generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb`, SHA256 `3c9604f0691e3fa0d13c1c7e789a855f390f4c9e1df0d8ff97900cedbd064f0c`, 100 games / 224014 members / 26.651 GiB. Прежние 100 `game-*.zip` были удалены после точной сверки (15.665 GiB), **не** DuckDB. `CURRENT` оставлен pointing `public68` deliberately для baseline. 32 heldout games являются SEALED для новой оценки механик, поэтому по всем 100 разрешён ТОЛЬКО metadata census, а entity/snapshot decoding разрешён **только** baseline68.

## Новый пакетный контракт

- `tools/run-public100-baseline68-deep-v2-with-evidence.sh` — единственный командный entrypoint, использует **точно существующий** `tools/run-with-runtime-evidence.sh` и включает в `runtime-logs` только 3 фиксированных JSON: `stage-status.json`, `pytest-counts.json`, `m2-deep-coverage.json`, плюс штатные sanitized outer metadata, status, source SHA и gate.log. ABSTAIN, failed pytest или failed corpus возвращают ненулевой exit и публикуют доступный status без raw traces.
- `tools/run-public100-baseline68-deep-v2.sh` — проверяет clean main, `git fetch origin main` и actual SHA, CURRENT public68 без переключения, наличие явной public100 generation, exact baseline68 manifest `validation/corpus/manifests/public-short-expansion-with-public36.jsonl` с ранее runtime-verified SHA256 `942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d`, docker compose доступность. Lab container получает `/corpus-db:ro`, никакие writers/importers не стартуют. Реальный public100 checksum проверяет существующий read-only diagnostic #226/#228 before member reconstruction. Docker/test/build/diagnostic подробности пишутся только в `artifacts/corpus/public100-baseline68-deep-v2/private-local/`, этот каталог никогда НЕ included в runtime evidence.
- Параллельные по назначению последовательные стадии: Docker lab build; **полный** pytest с локальным JUnit XML; затем **даже при ошибке pytest** большая M2 стадия читает метаданные всех 100 игр и выбирает детерминированную pre-reconstruction frozen selection из 68 baseline игр, `--pairs-per-game 16 --max-games 68` → верхняя граница **1088** разных пар на baseline. Это в восемь раз шире прежнего лимита 136, фактическая выборка зависит от числа исходных соседних пар. Каждый выбранный T-1/T payload декодируется только внутри baseline68 и проходит проверку actual current-owner, perspective, infoturn. Отчёт содержит агрегированную экономику, MC/supplies/minerals surface/underground, structures/taxes, trans-uranium/mineral conditional checks и residual context — без game/player IDs или сырых entity values. Нет новых причинных Host формул.
- Перед публикацией M2-отчёта запускается уже существующий строгий `tools/diagnostics/m2_validate_corpus_aggregate_evidence_v1.py`. При неудаче невалидный JSON **удаляется** из include; сохраняется safe status. Фиксированный count-only helper `tools/diagnostics/public100_pytest_safe_counts_v2.py` считывает ЛОКАЛЬНЫЙ JUnit, публикует лишь counts tests/failures/errors/skipped и fixed categories `PASS`, `FAILED_TESTS`, `COLLECTION_OR_EXECUTION_ERRORS`, `MISSING_OR_INVALID_JUNIT`, `PYTEST_NONZERO_NO_FAILURE_DETAILS` и `NO_TESTS`. Ни test names, ни traceback, ни sample content не экспортируются.
- `tests/test_public100_deep_batch_safe_counts_v2.py` проверяют фейковые JUnit success/failure/errors, нечувствительность к секретным строкам, malformed JUnit, no-tests/exit misalignment, 2 suites and strict source-pins/one launcher include allowlist. Все тесты CI synthetic-only; это не выполнение локальной DB.

## ONE COMMAND после merge + postmerge main CI

```bash
cd ~/projects/planets-lab && git pull --ff-only origin main && bash tools/run-public100-baseline68-deep-v2-with-evidence.sh
```

После пользовательского host-run найти Гитхаб **runtime-logs/public100-baseline68-deep-v2/<actual-run-stamp_SHA>** (не угадывать timestamp). Прочитать сами файлы из GitHub: `gate.log`, `metadata.json`, `artifacts/corpus/public100-baseline68-deep-v2/stage-status.json`, `pytest-counts.json`, `m2-deep-coverage.json`. Не просить пользователя copy/paste локальные подробности. При `pytest` fail у нас будет безопасный счётчик/категория, но не конкретный тестовый traceback: если понадобится, отдельным PR сделать безопасный фильтр точных имен заранее проверенного allowlist.

## Evidence boundary и ограничения

Ни один archive T-1/T snapshot, even current-owner, не является independently authenticated before/after одной Host-фазы и не подтверждает accepted Host orders. Статус реального M2 результата `CORPUS_OBSERVED descriptive + conditional mineral mass-balance`, **не** `DIFF_VERIFIED`. Синтетические mine #290–308 и Engine остаются DOCUMENTED+TESTED conditional. Не делать full sweep mine differential по T-1/T без доказательств host stage; сохранены issue #247 PARKED, closed #289 PPQ observational, sealed M2 heldout32, C5/Horwasp и production IntelBoard untouched. Отдельно не удалять DuckDB, не перестраивать общеизвестную canonical public100 и не менять CURRENT.

**Every PR**: own complete `CONTINUE_HERE.md` with exact PR#, numbered `PR_CHANGELOG.md`, topic handoff/roadmap, no weakening `tools/check_pr_handoff.py`. Exact FINAL PR head CI green → squash merge → live main SHA + postmerge push CI. User chat Russian.
