# PR #323 — реальный VCR temporal/source scorecard, 26 октября 2026

## Context

Единственный источник истины — живой GitHub `main`, не прежние сообщения. Исторический `main` до PR #323: `67a21319e2876280480dcb6d9fb149127b033cfb`. PR #322 merged, финальный PR CI #1839 и postmerge push-main CI #1840 `completed/success`. Новый [PR #323](https://github.com/Numillyash/planets-lab/pull/323), branch `research/vcr-real-temporal-source-scorecard-v1`; его фактический CI, merge, финальный SHA нужно проверять отдельно.

## Verified state

Из GitHub orphan `runtime-logs/public100-baseline68-vcr-temporal-v1/20261026T173212Z_67a21319e287` независимо прочитаны `metadata.json`, `gate.log`, `stage-status.json`, `pytest-counts.json` и полный уже разрешённый **обезличенный** `m2-deep-coverage.json`. Настоящий запуск 2026-10-26 17:32:12–18:14:44 UTC (**42m32s**), `source_commit=67a21319e2876280480dcb6d9fb149127b033cfb`, outer `exit_code=0`. Docker build PASS после устранения локальной неполадки Docker, Git/Bash PASS, exact baseline68 cohort PASS, host-validator self-test PASS, 3845 pytest cases/0 failures/0 errors/26 skipped, `PASS_NONCAUSAL_READONLY` и `PASS_VALIDATED_AGGREGATE`. Отсутствующий optional `build-failure-diagnostic.json` в runtime metadata ожидаем при успешной сборке и не является отказом.

Immutable `public100` SHA `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`, 100 games/224014 member metadata; entity content **только** SHA-pinned baseline68 игр, frozen **8550** T−1/T observer-archive pairs selection digest `4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659`, baseline manifest SHA `942eb61741664835cc600bb1e2148daaa1c009462827b238f13227c5937899d9`. Heldout32 не декодировался, `CURRENT` не менялся, DB READ_ONLY.

Точные счётчики *повторяющихся наблюдений*, **не уникальных боёв**:
- `before_vcr_rows=21918`, `after_vcr_rows=22414`, итого **44332** записи.
- `before_turn_exact=21918`, `after_turn_exact=22414`; earlier/future/missing/invalid **0** на обоих ходах.
- Оба положительных typed `left.objectid/right.objectid` — **44332/44332**; оба `leftownerid/rightownerid` — **44331/44332**. Одна запись в after-архиве не прошла критерий типизированной пары владельцев. Не утверждать, что конкретное поле отсутствовало: различий в count-only агрегате нет.
- Exact turn+both typed participants **44332**, ещё и оба владельца **44331**, неполных по владельцам **1**.
- `same_id_across_adjacent_archives_not_battle_link=0` при 8550 qualified archive pairs; в 3748 парах оба списка VCR пусты. Нулевое пересечение generic `vcr.id` между ходами НЕ означает, что не было боёв. Существующий боевой replay runtime использует `(battle_turn,vcr_id)` **в пределах одного хода**, а не межходовой ID.
- Точный предыдущий safe v6 source projection (включая minefield joint) совпал со всеми старым полями нового реального VCR отчёта — **zero drift**. Но опциональный старый starbase link section в данном VCR-runner НЕ был включён: **нельзя** ложно требовать или заявлять его присутствие. Starbase-результаты ранее independently подтверждены в другом запуске.

## Implementation

- `tests/fixtures/public100_baseline68_vcr_temporal_v1_safe_projection.json` — только разрешённая проекция прежнего v6 full source **один-в-один**, и точно 20 заранее объявленных VCR счётчиков, плюс подтверждённая безопасная идентичность runtime/status/test. Без game/player/VCR/ship IDs, координат, строк orders/HAR или source payload.
- `src/planets_lab/corpus/vcr_temporal_v1_observation_readout.py` — чистый offline stdlib gate, вызывает прежний верифицированный v5/v6 source reviewer через фиксированный path (без `planets_lab.corpus.__init__`/DuckDB). Pin real VCR run SHA/status, сравнивает полностью предыдущий frozen v6 source projection, допускает только 20 VCR counters, проверяет каждую T−1/T temporal partition, typed participant/owner monotonicity и нулевой межходовой generic ID. Не выводит идентичности или causal Host conclusion.
- `tools/diagnostics/review_vcr_temporal_v1_observations.py` — isolated `python3 -I -S`, три count-only фикстуры (v5/v6/new VCR), результат исключительно JSON в новый отсутствующий файл, вывод не содержит untrusted input или stacktrace. `validation/research/public100-baseline68-vcr-temporal-v1-source-scorecard.json` — проверяемый итог.
- `tests/test_vcr_temporal_v1_observation_readout.py`: реальный deterministic replay, malicious tamper старых и новых source counters/Host/status/generation, strict bool/int, попытка инъекции raw identifiers и isolated host no-pip CLI.
- Это исключительно **повторный offline-анализ уже опубликованного санитарного агрегата**. Нового on-host исследования, corpus read или нового dedicated runner не требуется; уже исполнявшийся #321 runner остаётся.

## Next actions

1. Завершить PR #323: проверить точный FINAL PR HEAD `completed/success` Actions, squash merge с `expected_head_sha`, получить фактический merged main SHA и успешный postmerge push-main Actions. Не ослаблять `tools/check_pr_handoff.py`.
2. Далее разумнее исследовать **внутри одного battle_turn** многоракурсные наблюдения `(game, battle_turn, vcr_id)` на уже доступной infrastructure `combat_vcr_runtime.py`: количества подтверждённых повторных наблюдений и конфликтов входов. Разработать строго источник-правильные criteria без raw IDs, только затем новый bounded research runner, **если** действительно потребуется новая on-host выборка. Не приписывать этому этапу Host combat results.
3. Независимые подтверждённые accepted Host orders и phase receipts остаются в #247 **OPEN/PARKED**, не уравнивать source VCR с реальным боем; C5/Horwasp и отдельный production IntelBoard не трогать.

## Boundaries

`CURRENT`=public68 SHA `5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a`, explicit immutable public100 only metadata all100, sealed heldout32 entity access=false, PPQ #289 frozen, no source DB writes, no private HAR/.trn/Host orders. Коррелированные наблюдения не независимые битвы. `DOCUMENTED`, `TESTED`, `CORPUS_OBSERVED`, `DIFF_VERIFIED` не смешивать, не назначать выдуманный общий процент готовности.
