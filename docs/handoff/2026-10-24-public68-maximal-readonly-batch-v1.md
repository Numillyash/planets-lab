# PR #309 — однокомандный длительный read-only public68 audit (корпус + вся регрессия)

24 октября 2026. Historical PRE-PR `main` `274e6bc6d448fadebb5d02bb91f9acf92458afef` (#308 merged; final PR CI #1695, main CI #1696 SUCCESS). Этот SHA не будущий HEAD. Источник истины — actual GitHub main.

## Цель и источник

Пользователь запросил «максимально много за один долгий запуск по локальной базе сервера». Выполнить реальное чтение локальной БД из GitHub CI нельзя; поэтому PR готовит **одну короткую команду для сервера**, с публикацией проверенных агрегатов на отдельную ветку `runtime-logs`. Реальный Host/accepted order мы **не запускаем** и не симулируем как подтверждённый.

Поддерживается **ТОЛЬКО canonical CURRENT public68**, хронология подготовлена и ранее проверена:
- `generations/corpus-v2compact-public68-20261004T095236Z-09f71721b77c.duckdb`;
- SHA256 `5ae0d6fe1190d5f7cd4a90895f3c5ebf995280ad0b716e0960273a8a55e8f43a`;
- 68 исходных публичных игр, **169569 source member** records, `planets-lab.corpus-db.v2.compact1`;
- `public100` (>26 GiB), sealed 32 M2 entity holdout, исходные zip/.trn, приватные accepted orders — **НЕ ОТКРЫВАЮТСЯ**; `CURRENT` не меняется.

Новые файлы:
- `tools/diagnostics/public68_broad_readonly_census_v1.py`: синтаксически проверяет строку `CURRENT` на строго закреплённое имя, открывает только через `connect_current_compact_read_only`, проверяет exact schema и **полный SHA256**, ожидаемые 68 игр/169569 снимков, uniqueness archive/member ID. Всю опубликованную `source_members` просматривает агрегатно: game/archive counts, decoded bytes, отношения archive vs embedded turn, **временные пары** по (game, perspective) и число несовпадающих/пропущенных turns без утечки идентификаторов. Полный `zip_members`, `member_fields` census, а также `typed_<section>` row counts по **всем** допустимым известным секциям, member coverage для ключевых семейств minefields/ships/planets/starbases/VCRs/ion/nebulas. Механики сгруппированы в 8 family scopes (movement, combat, economy, shipyard PQ/PPQ, mine placement/decay, ship sweep, starbase sweep, web drain). Это **source section availability** и scoped `ABSTAIN_NO_AUTHENTICATED_HOST_PHASE_OR_ACCEPTED_ORDERS`, не реальный Host/diff. SQL table identifiers только из `KNOWN_ENTITY_SECTIONS`, никаких значения raw entities ни в Python/JSON/stdout. Read-only DB с memory limit 4 GB, threads=3. После чтения повторно проверяются CURRENT и размер/mtime immutable generation.
- `tests/test_public68_broad_readonly_census_v1.py`: создаёт полностью ИСКУССТВЕННУЮ 2-game 5-member DuckDB, pin/source count, metadata temporal gap/duplicate/offset, typed section/full scan, SHA check, immutability, source family no-promotion, wrong CURRENT and wrong count/sha ABSTAIN. **Никаких локальных пользовательских файлов в CI.**
- `tools/run-public68-broad-readonly-v1.sh`: host-side orchestration: from tracked **clean main** matching fetched origin/main, pinned CURRENT and available Docker, uses `docker compose -f compose.yaml -f compose.corpus-db.yaml` lab with read-only `/corpus-db` mount, rebuilds image only, runs **FULL `python -m pytest -q --tb=no`** and then DB scan even if pytest fails, writes local unreported details under `artifacts/corpus/public68-broad-readonly-v1/local-*.log`. Into public output forwards ONLY whitelisted counters/status, never stdout/stderr from potentially raw tools. Saves fixed-path sanitized `report.json` and `suite-status.json`. No corpus rebuild, no importer service, no network Planets API.
- `tools/run-public68-broad-readonly-v1-with-evidence.sh`: dedicated short launch command uses **EXACT existing** `tools/run-with-runtime-evidence.sh` with two allowlisted aggregate `--include` files. Existing generic evidence wrapper automatically records full **sanitized** stdout/log, source commit/status/exit and publishes to orphan branch `runtime-logs` EVEN if partial stage fails/ABSTAIN. Hostname in generic metadata is existing tool behavior, do not add additional private identifiers.

## Реальный запуск — ПОСЛЕ green PR/merge/main CI

На сервере с существующим checkout, без доступа к private game captures:

```bash
cd ~/projects/planets-lab && git pull --ff-only origin main && bash tools/run-public68-broad-readonly-v1-with-evidence.sh
```

Это одна строка, которая обновит только checkout исходников перед измерением и запустит отдельно отслеживаемый долгий gate. Ассистент читает с GitHub `runtime-logs/public68-broad-readonly-census-v1/<run-id>/metadata.json`, `gate.log`, `artifacts/corpus/public68-broad-readonly-v1/report.json` и `suite-status.json` (путь фактически формирует wrapper; не выдумывать run-id). Не просить пользователя вставлять логи.

**Что будет и чего не будет:** source/meta/schema corpus parity and source-readiness + регрессия всех протестированных условных моделей; без независимых Host phase receipts мы **не можем** объявить результаты #290–308 `DIFF_VERIFIED`. Пары архивов T-1/T являются observational, не соседними Host-подфазами. Нет реальной последовательности accepted mine orders; ни одного настоящего Host turn.

## Ограничения и дальнейшие шаги

Оценка потребления зависит от фактического диска/CPU сервера: полный SHA + сканы каждого typed section по public68 + pytest могут быть долгими. Не утверждать точное время/количество результатов до runtime. Исключение по DB/schema/source печатается в публичный лог только как ограниченный `ABSTAIN` reason code; локальный подробный лог Docker не публикуется. Если запуск не смог начаться, generic wrapper всё равно публикует статус и safe outer log (subject to GitHub push access). Этот gate НЕ является повторным построением feature index, подготовленной базы или нарушением frozen M2.

Evidence classification до реального серверного запуска: **TESTED synthetic gate only**. После запуска: `CORPUS_OBSERVED descriptive source coverage` по осмотренным разделам/агрегатам, если report verified. Это не causal experimental Host verification.

#289 public PPQ six-game observational closure остаётся CLOSED; #247 user-dependent host order evidence остаётся OPEN/PARKED. CURRENT public68 pinned; prepared public100 >26GiB no rebuild/read; sealed M2 heldout32 unopened, C5/Horwasp and production IntelBoard not touched. Каждый будущий PR полностью переписывает `docs/CONTINUE_HERE.md` со своим номером и четырьмя обязательными англоязычными headings, обновляет `docs/PR_CHANGELOG.md` и отдельный docs/roadmap; exact final PR CI green перед squash merge, postmerge main CI проверяется. Чат только русский.
