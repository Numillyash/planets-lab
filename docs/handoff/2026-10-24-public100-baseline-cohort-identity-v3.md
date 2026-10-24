# PR #311 — исправление ABSTAIN_BASELINE_MANIFEST_SHA без раскрытия sealed heldout32

Дата: 24.10.2026. Исторический PRE-PR `main` `e9d8fc6850f9f970de6c7d5e118ad80d9430a0af` (#310 merged, exact PR #1710 + main #1711 CI SUCCESS). Будущий HEAD только по GitHub.

## Реальный runtime-блокер

Пользователь выполнил `bash tools/run-public100-baseline68-deep-v2-with-evidence.sh` на локальном сервере. Evidence отдельной `runtime-logs` ветки:
`runtime-logs/public100-baseline68-deep-v2/20261024T164704Z_e9d8fc6850f9`.
Результат: `ABSTAIN_BASELINE_MANIFEST_SHA`, стадии build/pytest/M2 `NOT_RUN`. Отсутствует свидетельство порчи DuckDB и отсутствует попытка прочитать heldout32.

Причина ошибки #310: в `tools/run-public100-baseline68-deep-v2.sh` был **жёстко прописан исторический SHA256** локального manifest `validation/corpus/manifests/public-short-expansion-with-public36.jsonl`. Этот manifest не присутствует в отслеживаемых GitHub исходниках, хранится отдельно на сервере; его байты могут поменяться (например, экспорт/форматирование), даже при том же наборе базовых 68 игр. Ранее успешный SHA `942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d` описывает исторический файл, **не** обещает текущий SHA и не идентифицирует game-ID set сам по себе. Не подменять его вычисленным значением без проверки разрешённого состава.

## Новый fail-closed, read-only identity gate

`tools/diagnostics/public100_baseline68_cohort_guard_v3.py` перед любым entity reconstruction:

1. Проверяет `CURRENT` точно `generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb`; публичную базовую compact generation читает `read_only=True` и полностью пересчитывает опубликованный SHA256 `5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a` — **это стабильный независимый reference**.
2. Читает ЛОКАЛЬНЫЙ manifest (максимум 1 MiB), строгий JSONL `game_id` positive int без bool/дубликатов, **ровно 68** IDs. Добывает **только** `source_archives.game_id` metadata из базовой public68, проверяет 68 distinct games и 169569 source members; извлекает **только metadata** `source_archives.game_id` из explicit public100, проверяет 100 distinct games/224014 members. Никакие `typed_<section>` и raw .trn при этом не читаются.
3. Требует `manifest_ids == authenticated_public68_db_game_ids` **в точности**, а также `public68_ids subset public100_ids`. Если хотя бы 1 из sealed heldout ID попал вместо baseline game, даже при сохранённом числе 68 — **ABSTAIN**, ещё до Host/pytest/M2, без открытия чужой игровой записи.
4. Публикует отдельный allowlisted `artifacts/corpus/public100-baseline68-deep-v2/baseline-cohort-attestation.json` ТОЛЬКО если весь gate PASS. Отчёт содержит безопасные count/actual manifest SHA256/public68 canonical SHA, без списка или конкретных game/player IDs и без source path. Следующие стадии получают **актуальный SHA проверенных байтов**.
5. M2 source script `tools/diagnostics/m2_public_corpus_economy_coverage_v1.py` получил обратно-совместимый необязательный `--expected-baseline-manifest-sha256`: если байты manifest изменены после attestation, он отказывает **до entity sampling**. Final M2 aggregate дополнительно сравнивается с attested SHA **до публикации** через штатный строгий `m2_validate_corpus_aggregate_evidence_v1.py`. Даже форматно изменённый, но допустимый local manifest получает новые зафиксированные bytes и тот же verified game cohort.
6. `tools/run-public100-baseline68-deep-v2.sh` выполняет эту стадию ПОСЛЕ Docker build и ДО pytest/M2, выводит только safe statuses, а вся подробная ошибка остаётся в ignored `private-local`. `tools/run-public100-baseline68-deep-v2-with-evidence.sh` использует прежний `tools/run-with-runtime-evidence.sh` и публикует cohort attestation + прежние строго агрегированные stage-status/pytest-counts/M2. Даже ABSTAIN сохраняется с source SHA в `runtime-logs`.

`tests/test_public100_baseline68_cohort_guard_v3.py` — fake 2-game baseline/3-game universe + synthetic manifest: замена одного baseline game на heldout при равной кардинальности ABSTAIN, неверный public68 SHA ABSTAIN, отсутствие baseline в public100 ABSTAIN, unexpected CURRENT ABSTAIN, malformed JSONL/boolean ID/duplicate, изменение порядка/формата manifest без изменения cohort допустимо и даёт иной recorded bytes SHA. `tests/test_public100_deep_batch_safe_counts_v2.py` обновлён и больше не требует старый локальный SHA. Не читается реальная базовая DB в CI.

## Операционный запрос — ПОСЛЕ exact PR/main CI success

На сервере исполняется **та же команда**, больше не нужно исправлять manifest руками:

```bash
cd ~/projects/planets-lab && git pull --ff-only origin main && bash tools/run-public100-baseline68-deep-v2-with-evidence.sh
```

После host-run читать фактическую ветку `runtime-logs/public100-baseline68-deep-v2/<actual-run-id>/` в GitHub. Не придумывать статусы до server run, не запрашивать private raw outputs.

Область прохода неизменна: **public100 full metadata only**; содержимое T−1/T декодируется **только из exact approved baseline68**, до 16 пар/игру (не более1088), экономика/минералы/stock/residuals и весь pytest. Проверка реальных accepted NuHost orders и отдельных фаз НЕ выполняется, `CORPUS_OBSERVED descriptive` не `DIFF_VERIFIED`. #289 six-game PPQ frozen CLOSED, #247 accepted Host evidence OPEN/PARKED, 32 heldout sealed, CURRENT без переключения, C5/Horwasp и production IntelBoard untouched. Все новые PR: own full Russian CONTINUE_HERE, numbered PR_CHANGELOG, topic docs/ROADMAP, exact final PR HEAD CI success -> squash -> actual main SHA / postmerge main CI.