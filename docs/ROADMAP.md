> **2026-10-24 UTC PR #315 — real v5 source identity readout and offline fail-closed source-readiness classification.** Previous #314 v5 on-host `runtime-logs/public100-baseline68-identity-v5/20261024T215211Z_0c527a79cc53` completed in **32m22s** with 3707 total pytest cases/0 failures/errors/26 skipped, full immutable public100 100/224014 metadata and exact baseline68 subset, 8550 frozen archival T−1/T pairs, sealed32 excluded, CURRENT unchanged. Identity pairs across repeated perspectives: minefields sameID **887224**, fresh-own **138864**, stable-owner/center changed units **536703**; ships sameID **916904**, fresh-own **347831**; starbases sameID **346222** but owner untyped all; VCR sameID **ZERO** (generic cross-turn ID unsuitable); storms sameID **95130**, owner criterion inapplicable. Source-only review [handoff](handoff/2026-10-24-v5-nonplanet-source-readiness-evidence-review-v1.md) and [committed scorecard](../validation/research/public100-baseline68-nonplanet-v5-source-readiness.v1.json) prove that the **intersection** of fresh mine observations and stable-center changed units is NOT observed and is only bounded between **0 and 138864** (cannot infer any sweep/decay). New offline `nonplanet_v5_evidence_review.py` validates source SHA/allowlist/frozen sample and all integer conservation, categorizes starbases/VCRs/storms with explicit ABSTAIN/ID_ONLY, with no new user on-host scan. Evidence `CORPUS_OBSERVED descriptive` not NuHost `DIFF_VERIFIED`; #247 parked, #289 frozen, C5/Horwasp and production IntelBoard untouched.

> **2026-10-24 PR #314 — strict source identity/freshness audit on precisely the prior frozen 8550 archived observation pairs.** Existing #312 on-host public100 metadata/68-game sampled T−1/T `8550` pairs and five nonplanet section row counts only showed *observability*, not uniqueness, owner freshness or Host events. New `nonplanet_archive_pair_readiness.py` atomically rejects duplicate/bool/missing entity IDs, compares exact same ID across T−1/T for five sections (minefields, ships, starbases, vcrs, ionstorms), separates stable vs changed owner and fresh same-owner exactly matched `infoturn` vs missing/stale. Minefield `units` changed with stable owner/center is an archive **candidate observation**, NOT a proved decay, sweep, MSC or combat event. Strict aggregate numeric only; SHA256 pin of predeclared selection `4432542b37c51f1bd94f27f9c061a8e27a850ecb08714ff55662928cb54ea659` verified **before** any reconstruction. Dedicated after-merge on-host launcher `bash tools/run-public100-baseline68-identity-v5-with-evidence.sh` retains public100 SHA/read-only, vetted baseline68 exact manifest ID set and 32 sealed holdout exclusion; publishes safe evidence even ABSTAIN, NOT yet a runtime study. [Detailed handoff](handoff/2026-10-24-frozen-archive-nonplanet-identity-readiness-v1.md), [project progress map](PROJECT_PROGRESS_MAP.md). Host order/phase `DIFF_VERIFIED` remains absent, #247 parked, #289 PPQ frozen, CURRENT and production IntelBoard unchanged.

> **2026-10-24 PR #313 — real 27m54s public100/baseline68 v4 run and Docker test parity fix.** Actual published `runtime-logs/public100-baseline68-expanded128-v4/20261024T185839Z_3f539501db2a`: 100/224014 metadata, approved sealed baseline68 8550 adjacent archive pairs, 317255 owner-current same planet pairs, 58938 any mineral surface-residual planet windows, 6870 opposite cargo *candidates*, mine/ship/VCR/ion/base section coverage; safe M2 aggregate PASS **CORPUS_OBSERVED descriptive**, not NuHost DIFF_VERIFIED. Five on-host Docker pytest failures (3697 total/3666 passed/26 skipped) are exactly four `test_runtime_evidence_wrapper` and one `test_site_combat_state_runtime_fallback`. Repo Dockerfile based on python:3.12-slim omitted Git but these suites rely on git subprocess; now add Git to Docker image, actual Docker CI parity smoke for both suites, and fail-fast Git/Bash preflight in v4 runner. Check exact CI before assuming actual on-host fix; no changes to checksum/CURRENT/heldout32 or private orders. [Tech evidence handoff](handoff/2026-10-24-public100-v4-runtime-and-docker-git-root-cause-v1.md), [project progress map](PROJECT_PROGRESS_MAP.md). #247 PARKED, #289 frozen.

> **2026-10-24 PR #312 — genuinely wider one-command baseline68 read-only corpus audit.** Actual previous local public100 metadata/68 content audit [runtime-logs/public100-baseline68-deep-v2] selected 1088 pairs (16/game), finished in 7m56s and found 5 local pytest failures / 3692 cases, M2 deep stage PASS. New [v4 handoff](handoff/2026-10-24-public100-baseline68-expanded128-multifamily-v4.md): raise MAX_PAIRS_PER_GAME to 128 and bound to at most **8704** deterministic T-1/T baseline68 archive pairs, maintain independent SHA-pinned public68 68-ID cohort attestation and full public100 100-game metadata, CURRENT/heldout32 untouched. Report owner-current planetary economics/mineral residuals as before, plus **archive section observability** only for minefields, ships, starbases, VCRs and Ion Storms. New safe JUnit classifier attributes counts to exact Git-tracked failing pytest modules without raw test names, traceback or local paths. User host command after exact PR/main CI: `bash tools/run-public100-baseline68-expanded128-v4-with-evidence.sh`; uploads only sanitized report/count/status/source SHA. Nonplanet list counts do NOT prove mine/combat Host mechanics, M2 historical pairs are NOT causal Host phase witnesses. #247 PARKED, #289 closed, 32 heldout sealed, no public100 rebuild.

> **24.10.2026 PR #311 — исправлен реальный блокер запуска public100-baseline68-deep-v2: ABSTAIN_BASELINE_MANIFEST_SHA.** Ранее ошибочно сравнивали серверный НЕ отслеживаемый Git manifest с историческим SHA файла. Теперь перед любой реконструкцией нужен SHA256-verified immutable public68 DB + точное равенство 68 IDs manifest и approved game set из public68 `source_archives` + subset из public100 100-game metadata и корректные числа source members. Смена форматирования manifest без смены игровой выборки допустима, подмена одного ID игрой из sealed heldout32 при том же числе элементов → ABSTAIN. Actual manifest SHA фиксируется между gate и M2 decoder и проверяется перед публикацией. Все операции строго read-only, без Host DIFF_VERIFIED. После green merge повторить ту же команду `bash tools/run-public100-baseline68-deep-v2-with-evidence.sh`. [Handoff](handoff/2026-10-24-public100-baseline-cohort-identity-v3.md), [project map](PROJECT_PROGRESS_MAP.md), closed #289 / parked #247 и sealed heldout32 неизменны.

> **2026-10-24 PR #310 — corrected one-command public100 metadata + deep baseline68 M2.** New tracked read-only runner opens SHA-pinned public100 metadata for all 100 games and samples only allowed baseline68 entities, up to 16 adjacent pairs per game (1088 maximum), while preserving CURRENT public68 and sealed heldout32. Runs full pytest with only sanitized JUnit counts published; existing M2 validator gates aggregate output. Earlier #309 server result had a successful public68 census and failed pytest with insufficient diagnostics. New results will be CORPUS_OBSERVED descriptive, NOT independent Host DIFF_VERIFIED. [Detailed handoff](handoff/2026-10-24-public100-baseline68-deep-batch-v2.md) and [progress map](PROJECT_PROGRESS_MAP.md).

> **2026-10-24 PR #309 — один длительный безопасный серверный проход по pinned public68.** Dedicated `bash tools/run-public68-broad-readonly-v1-with-evidence.sh` uses existing `tools/run-with-runtime-evidence.sh` to auto-publish sanitized JSON/log/status/SHA even ABSTAIN. The runner verifies clean current GitHub `main`, immutable `CURRENT` public68, fully hashes active DB, scans all 68 public games/169569 source member metadata and all available known typed-section counts, coarser source-readiness for 8 families (movement, combat, economy, shipyard, mine lifecycle), and runs complete pytest suite. **No** raw game IDs/players/orders or post-Host phases, prepared public100 >26GiB, sealed M2 heldout32, private .trn/HAR, corpus rebuild/write, or server causal promotion. GitHub CI covers synthetic fake DB only; actual local server run must be launched by user once the PR and postmerge CI are green. [Technical handoff](handoff/2026-10-24-public68-maximal-readonly-batch-v1.md), [project progress map](PROJECT_PROGRESS_MAP.md). #247 stays PARKED, #289 frozen. This is a long **DESCRIPTIVE** observational census, NOT a new mine `DIFF_VERIFIED` result.

> **2026-10-24 PR #308 — canonical ship variants → one Campaign starbase source-conditional sweep ledger.** `canonical_ship_starbase_sweep_ledger.py` composes existing #307 all three mutually exclusive ascending-ID ship sweeping modes with #304 one Campaign starbase **after ships**, from one complete original field roster, with all original hostility/ion/web/Colonial entitlement maps validated before field exhaustion. Exact transition and total mine-unit conservation, no field resurrection/owner shift, near-edge web ABSTAIN and regression parity with old #305 beam-only pipeline. Official [minefields](https://help.planets.nu/minefields) and [Starbase Mine Sweeping](https://help.planets.nu/adv-starbase-mine-sweeping) document order, but real server-accepted orders, Host phase and exact web raster NOT DIFF_VERIFIED; scope excludes MSC, starbase fighter sweep, multiple bases and custom. Synthetic-only `DOCUMENTED+TESTED conditional` after exact PR CI. [Topic handoff](handoff/2026-10-24-canonical-ships-one-campaign-starbase-ledger-v1.md), [project map](PROJECT_PROGRESS_MAP.md). #247 PARKED, #289 frozen; protected corpus and IntelBoard unchanged.

> **2026-10-24 PR #307 — общая ID-ordered ведомость корабельной mine sweeping, включая Colonial mixed carrier.** Новый `ordered_ship_mine_sweeps.py` объединяет существующие самостоятельные bounded варианты #293 beam-only, #294 Colonial fighter-only и #306 simultaneous mixed Colonial в ОДНУ общую очередь ascending Ship ID с пересчётом радиуса после каждого корабля. Полный исходный roster и все первоначальные enemy ship×field, ion, web rate, Colonial entitlement Boolean maps проверяются до фильтрации исчерпанных полей. Каждый ship stage использует только оставшиеся поля; проверяется неизменность identity/owner/type/center и полный баланс мин. MSC, Campaign base и настоящие Host accepted orders не интегрированы; `DOCUMENTED+TESTED conditional` только после exact final CI, не DIFF_VERIFIED. [Handoff](handoff/2026-10-24-ordered-canonical-ship-sweep-ledger-v1.md) и [Progress Map](PROJECT_PROGRESS_MAP.md). Closed #289, parked #247, CURRENT/public100/sealed heldout32 unchanged.

> **2026-10-24 PR #306 — one Colonial carrier simultaneous fighter + beam mine sweep.** Official [Fighter Mine Sweep](https://help.planets.nu/adv-fighter-mine-sweep): beam-equipped Colonial carriers use fighters and beams simultaneously. New `colonial_mixed_beam_fighter_sweep.py`/synthetic tests compute fighter-only normal 20 units/fighter within 100LY including Ion Storm, plus normal/web standard beam rates (beam ion-blocked, PRE_DECAY web edge remains ABSTAIN), both potentials on same pre-step radius and combined `min(field_units, beam+fighter)` without invented saturated channel attribution. Strict typed one carrier/full field/diplomacy/mission/source; no MSC, other ships or starbases, Host accepted orders/DIFF flags false. [Handoff](handoff/2026-10-24-colonial-simultaneous-mixed-sweep-v1.md), [progress map](PROJECT_PROGRESS_MAP.md); no new Host/corpus run, #289 frozen, #247 parked, public100/heldout32 untouched.

> **2026-10-24 PR #305 — conditional beam-only ship → one Campaign starbase mine-sweep shared-roster ledger.** Uses existing #293 ascending-ship-ID beam sweeps and #304 one enabled Campaign starbase post-ship quote. Complete original roster and ALL diplomatic/ion/web maps validated before field filtering; previous ship results are the ONLY starbase input. Enforce exact stage boundary and global mine conservation; shrinking radius can remove a base from sweep range, consumed fields never reappear. No MSC/Colonial fighters, multiple bases, custom modifiers or real Host accepted orders, so still `DOCUMENTED + TESTED conditional` after exact CI, **not** DIFF_VERIFIED. [Topic handoff](handoff/2026-10-24-ship-to-starbase-conditional-sweep-ledger-v1.md), [visual project map](PROJECT_PROGRESS_MAP.md); #247 PARKED, #289 frozen and public100/heldout32 untouched.

> **2026-10-24 PR #304 — изолированная Campaign Starbase Mine Sweeping котировка.** Official [advantage rules](https://help.planets.nu/adv-starbase-mine-sweeping): requires enabled Campaign advantage + Sweep Mines primary order, all planetary and starbase defensive beams sweep at **highest starbase-buildable beam type**, after ship sweep and before scoop. New `starbase_mine_sweeping.py` and tests calculate one conditional base's full post-ship/pre-base roster, per-field normal/web standard beam loss, ion/owner/geometry ABSTAIN, exact mine conservation. No actual Host accepted order, inter-base order, MSC or full-turn composition. Synthetic-only DOCUMENTED+TESTED after final PR CI. [Technical handoff](handoff/2026-10-24-campaign-starbase-mine-sweep-quote-v1.md), [general map](PROJECT_PROGRESS_MAP.md). Issue #247 remains PARKED; frozen PPQ/public100/heldout32/current and production IntelBoard unchanged.

> **2026-10-24 PR #303 — безопасный declarative source-readiness manifest для подтверждения минных фаз.** `mine_phase_source_readiness.py` distinguishes public archival turn pairs and client-save acknowledgements (always NOT_READY for real Host-phase proof) from synthetic isolated cases and externally *asserted*, still **unauthenticated**, stage receipts. Typed metadata-only counts/booleans/stage labels, deterministic blocker codes for incomplete rosters/identity/Nebula/settings/accepted-order declarations, no private IDs/raw snapshots. No Host authentication or DIFF_VERIFIED claim; evidence `TESTED source-metadata classification` after CI only. [Technical handoff](handoff/2026-10-24-mine-phase-source-readiness-manifest-v1.md), [project progress map](PROJECT_PROGRESS_MAP.md); source #247 remains PARKED, frozen #289 and public100/heldout32 unchanged.

> **2026-10-24 PR #302 — full-roster conditional mine decay phase-pair audit.** New `mine_decay_web_phase_audit.py` and synthetic tests require complete typed before/after isolated natural-decay field rosters, per-field Nebula flags and fixed owner/type/centers. Independently compare #290 exact conditional decay events with supplied post roster; only on full match use #301 PRE/POST-decay web envelope to identify safe inside/outside or guard EDGE_ABSTAIN. Source mismatch is NOT a NuHost counterexample; archival T-1→T cannot substitute stage receipts. No full Host turn, no corpus run, all Host causal flags false. [Technical handoff](handoff/2026-10-24-isolated-decay-web-phase-pair-audit-v1.md), [project progress map](PROJECT_PROGRESS_MAP.md). #247 parked, #289 closed, public100/M2 heldout32 protected.

> **2026-10-24 PR #301 — phase-qualified conservative web-circle envelope and live progress map.** Consolidates documented PRE_DECAY beam web sweep and POST_DECAY Crystal web drain geometry in `web_circle_phase_envelope.py`, preserves all previous inside/uncertain/outside classifications with exhaustive parity tests and no Host raster claim. New [Project Progress Map](PROJECT_PROGRESS_MAP.md) includes Mermaid dependency diagram + evidence-separated per-category status, without fictitious completion percentages. #247 PARKED; no real Host/corpus experiment or changes to CURRENT/public100/heldout32.

> **2026-10-24 PR #300 — independent conditional post-decay Crystal web drain quote.** Official [Web Drain](https://help.planets.nu/minefields): **25KT per qualifying enemy Crystal-owned web field** near post-decay radius, zero-fuel mission reset to Explore except Beam up Fuel; fields owned by nonCrystals have no 25KT passive drain. `web_drain_isolated_quote.py` with synthetic tests consumes complete typed post-decay roster, exact hostile/Crystal owner maps and conservative circle geometry, ABSTAIN near 1LY edge/cell ambiguity, unknown diplomacy/current inventory or clipping. Returns immutable fuel and conditional mission quotes, no real Host web drain/mine hit/ship state changes. Distinct from #299 hypothetical already-hit web mine fuel penalty. [Handoff](handoff/2026-10-24-isolated-crystal-web-drain-v1.md). After exact CI `DOCUMENTED+TESTED conditional` only; next examine near-edge raster or source sufficiency, not full Host integration. #289/#247 and CURRENT/public100/heldout32/IntelBoard unchanged.

> **2026-10-24 PR #299 — isolated conditional web-hit fuel expense, exact-only subset.** Official [Minefields → Web Mines](https://help.planets.nu/minefields): one web mine hit expends *entire* externally known scheduled fuel plus `max(50 KT, start-of-turn fuel / 6)`, Warp0. No documented fractional-sixth rounding; new `web_mine_hit_fuel_quote.py` and synthetic tests calculate only unambiguous cases `F<=300` or `F%6==0`, only when entire loss affordable, known no other phases/drain/tow/custom, else ABSTAIN. Pure immutable quote, no actual RNG, movement, fuel inventory or Host phase. [Handoff](handoff/2026-10-24-web-hit-fuel-exact-subset-v1.md). Conditional DOCUMENTED+TESTED after CI, not DIFF_VERIFIED; next independent Web Drain 25KT per enemy Crystal web post-decay field, no host-stage composition. Frozen #289/#247 and CURRENT/public100/heldout32 untouched.

> **2026-10-24 PR #298 — isolated hypothetical ONE normal/web mine impact damage + per-LY odds quote.** Official [Minefields → Mine Impact](https://help.planets.nu/minefields): per-hit normal `ceil(10000/(hull-only mass+1))`, web `ceil(1000/(hull-only mass+1))`; per-LY base odds normal 1% (cloaked 0.5%), web 5%; towed ships immune. New standalone `mine_impact_single_quote.py` plus synthetic tests returns exact integer-ceiling raw damage, rational base odds, strict owner/hull/tow/settings/one-hit source assumptions and immutable non-Host output. NO RNG/path aggregation, cumulative damage, destruction, web fuel, movement, accepted orders or HostEngine. Conditional DOCUMENTED+TESTED only after exact CI. [Handoff](handoff/2026-10-24-single-normal-web-mine-impact-quote-v1.md). No corpus work, #247 PARKED, public100/heldout32/CURRENT untouched. Next independently source web-hit fuel penalty rounding or Host-phase mine conflict witness, NOT turn-wide speculative simulation.

> **2026-10-24 PR #297 — source-bounded isolated hostile minefield transition audit, NOT numeric Host loss model.** Official [Mine Destruction](https://help.planets.nu/minefields) states hostile normal overlap detonates until at least one is eliminated. PHost has detailed [different numerical formulas](https://planetscentral.com/doc.cgi/phost-4.1e/phost4-formula-mdm) but cannot be transplanted into NuHost. New `mine_conflict_transition_audit.py` + synthetic tests require complete typed phase-adjacent PRE and POST fields, exact diplomacy and one isolated #296 candidate pair, other fields stable. Classifies one eliminated+survivor shrinks as **COMPATIBLE**, both persist / survivor grows as **CONDITIONAL CONTRADICTION**, dual disappearance/no survivor loss/third coupled/custom/tangent/missing authenticated context as **ABSTAIN**. Never claims real accepted orders, Host causal unit losses, numeric formula or DIFF_VERIFIED. [Technical handoff](handoff/2026-10-24-mine-conflict-isolated-stage-witness-audit-v1.md). Synthetic-only, no public100 rebuild / sealed M2 open / #247 reopening. Next: independent legally public pre/post Host-phase source sufficiency discriminator; new real runs require tracked auto-evidence launcher, not private raw captures.

> **2026-10-24 PR #296 — conservative normal/web minefield hostile-overlap candidate graph.** Documented [Mine Destruction](https://help.planets.nu/minefields): normal/web and web/web never mutually detonate, own normal fields and different normal owners with mutual Safe Passage do not detonate, other normal/normal overlaps are Host **candidates**. New `mine_overlap_candidate_graph.py` needs typed full pre-conflict roster and strict complete mutual Safe Passage owner-pair map, compares squared distance with sum of integer radii; exact tangent/ambiguous phase/custom settings ABSTAIN. Stable edge list and components distinguish isolated two-field candidate from coupled multi-field cascade. No mine loss/field removal, Host phase/order, or global simulator insertion. [Handoff](handoff/2026-10-24-minefield-hostile-overlap-graph-v1.md), synthetic tests, conditional DOCUMENTED+TESTED once CI passes; no Host experiment, #247 PARKED; prepared public100/heldout32/CURRENT/IntelBoard unchanged. Next: independently sourced hostile collision discriminator, never invent per-field destroyed units.

> **2026-10-24 PR #295 — isolated exact FULL-FIELD MSC torpedo recovery mathematical quote.** [Official Mine Scooping](https://help.planets.nu/minefields) documents `MSC`+Mine Sweep, own minefield, beam+tubes, inverted Robot×4 (400 Mark8 mines → 4 torps ordinary/1 Robot), both normal and Crystal web. New `mine_scoop_full_field_quote.py` reuses standard 11 torpedo yields but only exact whole-field multiple, free ammo capacity, uniquely reachable owner-current typed field; no field removal or torpedo inventory mutation. Unknown Host remainder/partial cargo, near-edge square, overlapping own field target, custom/dense, concurrent sweep/lay/phase => `ABSTAIN`. New synthetic tests and [topic handoff](handoff/2026-10-24-msc-exact-full-field-scoop-quote-v1.md). `DOCUMENTED+TESTED conditional` after final PR CI, not Host DIFF_VERIFIED. #290–294 standalone; #247 PARKED, no public100/M2/current/production modification. Next meaningful research source-guided partial MSC or static cross-mechanic composition boundary; no fake Host acceptance.

> **2026-10-24 PR #294 — isolated Colonial fighter-only mine sweeping (DOCUMENTED + TESTED conditional after CI).** Official [Fighter Mine Sweep](https://help.planets.nu/adv-fighter-mine-sweep): 20 normal mines destroyed per fighter per eligible enemy field, ship within 100LY nearest-edge reach, web fields immune, ion storms do NOT block Colonial fighter sweep. New strict fully typed snapshot/explicit enemy matrix and Colonial mission proof flags, fighter-only zero beam, ascending ship-ID conditional after-radius ledger, exhaustion/conservation/atomic ABSTAIN. Not a real Host phase, not composable with #293 beam sweeping or #290–292 lay/decay without independently sourced phase ordering. [Handoff](handoff/2026-10-24-colonial-isolated-fighter-minesweep-v1.md). No real host/corpus command, CURRENT/public100/heldout32 unchanged, #247 PARKED; next bounded study MSC scoop or precise mixed beam+fighter order, not private logs.

> **2026-10-24 PR #293 — independent standard beam-only minesweeping ledger.** Extends standalone minefield research after #290 natural decay / #291 torpedo UNALLOCATED quote / #292 hypothetical spatial placement. Official [Minefields](https://help.planets.nu/minefields) and [Weapon Technical Details](https://help.planets.nu/weapon-destruction-power) supply 10 standard beam rates normal/web, beam sweep range and ID-order. New pure `mine_beam_sweeping.py` plus tests: typed full pre-sweep rosters, explicit enemy and ion flags/web-rate assertion, all-affected fields per ship, ascending ship ID, per-ship radius update, exhaustion and exact conservation; ambiguous web near-edge raster, non-Crystal web, MSC scoop, fighter/starbase sweeping, custom rules and unverified Host phases **ABSTAIN**. `DOCUMENTED + TESTED conditional` only after exact CI, not Host DIFF_VERIFIED. [Technical handoff](handoff/2026-10-24-standard-isolated-beam-minesweep-v1.md). Synthetic-only; no corpus/Host experiment, no CURRENT/public100/heldout32 change, #247 PARKED. Next isolated candidate MSC scoop or Colonial fighter sweep; never join components into Host turn without accepted orders/phase/source.

> **2026-10-24 PR #292 — standard minefield spatial placement CANDIDATE (synthetic-only).** Conditional nearest compatible same-owner/same-type field center with lower-ID tie, strict inclusive integer radius, immutable NEW/EXPAND proposal, full roster/cluster core (+10 LY) assumptions, 100/150 LY cap and soft500/overcapacity fail-closed; **no Host field ID, no actual creation/expansion, phase, inventory mutation or acceptance**. Strict typed inputs and tests. [Technical handoff](handoff/2026-10-24-minefield-spatial-placement-candidate-v1.md). Russian-language conversation rule now durable in AGENTS/WORKFLOW. Verify exact #292 final SHA CI before merge, main push CI afterward; no Host/corpus experiment, #247 PARKED.

> **2026-10-24 PR #291 — standard torpedo->UNALLOCATED mine quote.** Extend [natural decay #290](handoff/2026-10-24-minefield-isolated-natural-decay-v1.md) with independent pure quote of all 11 documented standard torpedo mine yields, MD1..9/MD0=100/MDA-unrestricted drop limits, typed ammo conservation, explicit Robot own normal-field ×4 and Crystal web permission, single 100/150 LY field capacity warning. It does NOT actually create/expand a minefield or allocate IDs, settle overcapacity/geometry, accept orders or place Host phases. MDH/MDQ and redirected miN remain explicit ABSTAIN. [Official minefields](https://help.planets.nu/minefields), [handoff](handoff/2026-10-24-minelaying-torpedo-unallocated-quote-v1.md). DOCUMENTED+TESTED conditional only after CI; next meaningful work source-bound field placement and phase interactions. No public100 rebuild, sealed M2 access or parked #247 reopening.\n\n> **2026-10-24 PR #290 — begin independent standard minefield lifecycle after scoped PPQ observational closure.** Official [Minefields documentation](https://help.planets.nu/minefields) gives normal/web natural `round(units*0.95)-1`, with Nebula `round(units*0.85)-1`, radius `floor(sqrt(units))`. New pure immutable isolated 1–12 turn natural-decay/removed-field event ledger with fully explicit typed normal/web roster and Nebula membership, exact conservation, 100/150 LY cap and fail-closed on dense/custom/missing context, interactions or unresolved exact .5 rounding. **DOCUMENTED formula + TESTED conditional only**, not verified Host phase/acceptance. No insertion in HostEngine until phase ordering and interactions independently controlled. New [handoff](handoff/2026-10-24-minefield-isolated-natural-decay-v1.md), tests; no host archive rerun, no re-opening [#247](https://github.com/Numillyash/planets-lab/issues/247), PPQ public six-game scope stays closed by #289.\n\n> **2026-10-23 PR #289 — scoped PPQ public observational research CLOSED at CORPUS_OBSERVED; causal Host proof remains PARKED.** Final real [20261023T145257Z_a0f7ca22ec07](https://github.com/Numillyash/planets-lab/tree/runtime-logs/runtime-logs/pq-paired-template-specificity-control12-p1-first48-max8/20261023T145257Z_a0f7ca22ec07) run (source `a0f7ca22...`, exit0) verified 48 genuinely embedded-consecutive typed owned-current windows from six frozen public PPQ games. 22 exploratory own-ship identity appearances; 17/17 unique current prior base hull+engine full matches, five ambiguous ABSTAIN; **paired same-window** eight new-ship full matches and zero persistent-ship matches, nine where some persistent ships also match. Existing reference 12/97 ship–window comparisons; PP unchanged16/increased6/decreased0. **Never call these 17 Host builds or iid statistical proof.** Commit durable privacy-minimal checkpoint `validation/research/pq-public-control12-observational-closure.v1.json`, coherence tests and [scientific closure + controlled Host prerequisites](handoff/2026-10-23-pq-public-observational-closure-host-readiness-v1.md). No more reflexive replays or posthoc mini-correlations on this exact cohort; continue other standard public research. Real accepted orders, component inventory, full PP and Host timing stay explicitly PARKED user-dependent [#247](https://github.com/Numillyash/planets-lab/issues/247); no new host run or private data needed now.

> **2026-10-23 PR #288 — actual persistent ship template reference weakly matches while new observations 17/17 match.** Published `runtime-logs/pq-existing-ship-template-reference-control12-p1-first48-max8/20261023T135439Z_88759c16285c` verifies 17/17 new-own-ship and uniquely owner-current prior base hull+engine matches; compare actual existing continuously-owned ship–window observations: 10/64 matches in 17 with-appearance windows, 2/33 in nine no-appearance windows, 12/97 overall, with many additional source abstentions. New strict within-SAME-window pairing counts whether newly appearing ship matches while zero or some persistent ships match, refuses ambiguous cases, reports only safe categorical counts. Not independent samples, no p-values, accepted orders or Host build attribution. One command `bash tools/run-pq-paired-specificity-with-evidence.sh` publishes bounded six-game real categories to separate `runtime-logs` after green PR+main CI; [handoff](handoff/2026-10-23-pq-paired-within-window-specificity-v1.md).\n\n> **2026-10-23 PR #287 — persistent-own-ship within-window template reference after 17/17 new-ship associations.** Real `runtime-logs/pq-appearance-correlates-control12-p1-first48-max8/20261023T124858Z_4dd63aa4cf59` on frozen six PPQ games: of 22 posthoc fresh own ship appearances, 17/17 qualifying uniquely current single-base prebuild hull+engine matches; 5 ambiguous site abstains. Observed `prioritypoints` unchanged 16, increased 6, decreased 0; this does NOT prove accepted Host orders, PP spend or 17 real builds. To test descriptive specificity, new bounded comparison of previously existing **persistent owner-current** ship hull+engine against same BEFORE base template, stratified appearance vs no-appearance windows, count matches/mismatches/unknown without raw IDs/values. Reference is **not independent sample**, ships repeat across windows. One command `bash tools/run-pq-existing-ship-reference-with-evidence.sh` publishes sanitized real aggregate to `runtime-logs` after PR green CI and merge. [Handoff](handoff/2026-10-23-pq-existing-ship-template-reference-v1.md).\n\n> **2026-10-23 PR #286 — exploratory *noncausal* starbase template/PP direction observations:** New immutable evidence `runtime-logs/pq-ship-candidate-fields-control12-p1-first48-max8/20261023T123217Z_cfc651f1106c` was fully published (exit0, no interrupt despite later terminal `^C`). Its 22 newly visible owned-fresh ship ID appearance observations in five approved PPQ games have typed ship hull+engine, player prioritypoints both endpoints and base configured build hull+engine fields (25 base row observations); **none of direct hull/engine/beam/torp inventory keys appear among those 25 rows**. New privacy-minimal strict single-base/single-new-ship hull+engine compatibility enum and PP trend direction; multiple/missing/ambiguous base or key => explicit ABSTAIN. No IDs, raw values, orders, warehouses, accepted Host plans or causal construction claims. After CI merge, `bash tools/run-pq-appearance-correlates-with-evidence.sh` automatically publishes real categorical counts to `runtime-logs`. [Technical handoff](handoff/2026-10-23-pq-appearance-template-pp-associations-v1.md).

> **2026-10-23 PR #285 — actual 22 PPQ source-qualified *identity appearance* events, now audit actual field availability:** Published `runtime-logs/pq-control12-ppq-multigame-p1-first48-max8/20261023T121122Z_333a480ed93b` genuinely examined 58 archive filename pairs across 6 frozen PPQ games; 48 qualifying embedded consecutive windows, 5 repeats + 5 skips; 22 newly visible own-fresh ship ID observations across 5 games (not 22 actual builds), 4 disappeared observations. New `pq_ship_appearance_fields.py` emits only typedness/key-presence counters for owned-current planet stocks, unique current bases' queue/parts/tech, newly visible ship hull/weapons and perspective player PP field names, with explicit unverified Host order/PP/warehouse/build sentinels. Existing six-game survey now reports bounded exploratory per-window sources (archive+embedded turns) for positive candidates; this is *posthoc discovery*, NOT independently tested Host formula. New one-command automatic evidence runner `bash tools/run-pq-ship-candidate-fields-with-evidence.sh`, prebuilt Docker & `runtime-logs`. Next read actual archived field coverage and distinguish missing source vs real Host requirements. [Handoff](handoff/2026-10-23-pq-ship-appearance-source-fields-v1.md).

> **2026-10-23 PR #284 — frozen-control12 PPQ multi-game source survey:** From actual immutable `runtime-logs/pq-window-selection-g620917-p1-from1/20261023T115343Z_705f8398f517`, five owner-current PPQ windows have exactly 2 unchanged owned fresh ship IDs, one current planet-linked base, 2→3→4→6→6→6 own fresh planets: **no newly visible owned ship within those five windows**, not a no-build Host proof. New bounded six-game PPQ observational survey across the existing frozen public-control12 only (max 48 filename pairs, 8 admitted windows/game), aggregated owner-current source-qualified ship/base/planet identity appearance/persistence, missingness and no entity/private values; one-command `bash tools/run-pq-control-multigame-with-evidence.sh` auto-publishes sanitized JSON/log into `runtime-logs`. Pending real host run; no Host causal parity or PP/warehouse proof. [Handoff](handoff/2026-10-23-pq-control12-multigame-identity-survey-v1.md).

> **2026-10-23 PR #283 — real base ownership source verified; next identity observables:** New published `runtime-logs/pq-window-selection-g620917-p1-from1/20261023T103725Z_15f627933064` confirms all five consecutive PPQ windows contain exactly one current base, owned via unique fresh planet link even though base ownerid key is absent, with fresh base infoturn and no conflict. New strict privacy-minimal per-window T−1→T planet/ship/base owner-current ID *intersections* count retained/newly visible/no longer visible, never call these builds/losses or global completeness; duplicates/missing source ABSTAIN. Run existing one-command automatic evidence wrapper after merge to get real observed signatures. [Handoff](handoff/2026-10-23-pq-observed-owner-identity-transitions-v1.md).\n\n> **2026-10-22 PR #282 — base owner provenance after actual archived window evidence:** From real `runtime-logs/pq-window-selection-g620917-p1-from1/20261022T185133Z_412db3d34b32`, five strictly consecutive embedded windows in first seven filenames; zero direct owner-current base rows despite one visible starbase/80 planets. Existing Nu importer can derive missing base owner from linked planet. New strict per-window `starbase_provenance` reports unique typed planet↔base own-fresh links, independently typed **base** infoturn, missing/stale/conflicting owner, and allowlisted raw mechanical key *presence* only. No missing infoturn promotion, warehouse/queue assumptions or Host parity. Rerun existing `bash tools/run-pq-window-selection-with-evidence.sh` and read GitHub evidence; [handoff](handoff/2026-10-22-pq-starbase-owner-planet-link-v1.md).\n\n> **2026-10-22 PR #281:** Real runtime-logs evidence confirms `game620917/p1/fileT1→T2` ABSTAIN because embedded turns aren't consecutive. Bounded allowed-game/player selector now classifies repeating/reversed/skipped embedded turns and admits ONLY exact +1 windows, tries at most 48 adjacent pairs and publishes up to five privacy-minimal shape reports. One-command `bash tools/run-pq-window-selection-with-evidence.sh` uses prebuilt Docker plus existing automatic immutable `runtime-logs` publication even for failure. **No real shape/Host success claimed before next on-host evidence.** [Handoff](handoff/2026-10-22-pq-bounded-embedded-turn-window-selection-v1.md).\n\n> **2026-10-22 PR #280:** First actual PQ public archive window (game 620917, player 1, filename T1→T2) ABSTAINED on embedded identity mismatch. Existing corpus normalizer distinguishes archive numbering from embedded `game.turn`; bounded probe now enforces typed game/player identity and consecutive embedded turns, reports archive→embedded offset and computes infoturn freshness against the correct embedded counter. *Actual cause remains to be verified on rerun.* New one-command launcher `bash tools/run-pq-public-window-with-evidence.sh` runs prebuilt Docker and automatically publishes privacy-minimal JSON/logs (including failures) to separate `runtime-logs` using existing worktree wrapper; no more manual terminal report relay. Test on approved real window next, then multiwindow field-sufficiency, still not Host parity. [Technical handoff](handoff/2026-10-22-pq-runtime-evidence-turn-offset-v1.md).\n\n> **2026-10-22 PR #279 — first strictly bounded archive-window source reader:** After #278 frozen-cohort PQ/PPQ metadata triage, `pq_window_field_sufficiency.py` gates exactly ONE allowed public game/perspective/adjacent turn pair, reads only TWO .trn members, reports aggregate owner-current vs no-infoturn coverage of planet/base/ship arrays and missingness; never prints entity/private values. No Host accepted orders, PP/warehouse global completeness or queue causality inferred. Offline synthetic ZIP tests do not mean actual public68 runtime was accessed. Next execute approved archived windows on corpus host (no 26+GiB scan) and aggregate observable field sufficiency. [Handoff](handoff/2026-10-22-pq-two-member-archival-window-v1.md).\n\n> **2026-10-22 PR #278 — pivot to historical corpus:** A read-only **PQ/PPQ readiness gate** now classifies an explicit pre-frozen *permitted* game-ID cohort against existing feature-index Parquet: queue settings, completed status, available archive and adjacent transition coverage, UNKNOWN vs excluded, hashes, and always-zero Host causal proof. No 26+GiB rescans, no sealed M2 heldout32, no CURRENT changes, and no implied real queue parity. Next target: actual T−1→T shipyard/warehouse/PP field-sufficiency and observability in already approved public slices. [Handoff](handoff/2026-10-22-pq-corpus-readiness-v1.md).\n\n> **2026-10-22 PR #277:** New whole-calendar late PQ conditional composition: 2–8 no-build capped waiting+economy, exactly ONE operator-provided full preturn snapshot matching last modeled state minus one inert/cargo-empty ship, **unchanged complete queue during ship-only loss**, one externally selected queued base's exact ship BOM/warehouse and 14-phase economy, then 2–6 capped existing-fleet cargo/full movement+planet economy turns. Strict PP/ship ID/warehouse/planet resource continuity; later failure ABSTAINs whole history. **TESTED conditional, NOT causal NuHost proof.** [Handoff](handoff/2026-10-22-pq-mixed-wait-loss-build-fleet-v1.md).\n\n> **2026-10-22 PR #276:** At soft PQ cap, model 2–6 complete ordinary waiting turns with one explicitly ordered existing ship's own-planet orbital cargo load/unload and ordinary full normal move per turn while all other ships have explicit no-op orders; run 14-phase economy every turn. Exact ship count and queue no-build, unchanged PP and warehouses, verified fuel/cargo/event/planet inventories. Strict all-or-nothing ABSTAIN, synthetic `TESTED conditional`, NOT witnessed NuHost order/phase placement. Next mixed capped waiting ↔ externally asserted loss/build calendar. [Technical handoff](handoff/2026-10-22-pq-capped-existing-fleet-cargo-v1.md).

> **2026-10-22 PR #275:** Two distinct modeled turns: late PQ ordinary ship build with exact warehouse/BOM/PP and 14-phase economy on T; only on T+1 load own-planet cargo/fuel, make fully supported normal move, and run second 14-phase planetary economy. Transfer/order/planet/ship/fuel ledgers independently audited, unchanged old fleet and stock; no external interturn effects. **Conditional TESTED only**, not authenticated Host phase timing or accepted orders. Next capped-wait + cargo/movement. [Handoff](handoff/2026-10-22-pq-new-ship-next-turn-movement-v1.md).

> **2026-10-22 PR #274:** Conditional **late PQ newly assembled ship → own-planet fuel/cargo load → fully fueled short ordinary movement** using existing transfer/movement stages and #271 exact BOM+14-phase economic turn. No second turn increment; full source/destination/fuel, cargo conservation and event checks, old fleet/warehouse/PP unchanged. **This is a hypothetical post-build subphase, not real NuHost phase placement.** Missing/unsupported route or receipt ABSTAIN. Next check real timing or build safe next-turn movement/cargo link. [Handoff](handoff/2026-10-22-pq-built-ship-cargo-move-v1.md).

> **2026-10-22 PR #273:** Complement late PQ external-loss carry (#272) with **2–8 consecutive at-soft-cap no-regular-build periods**: complete queued+idle base rosters, unchanged fleet, PP and warehouses, economic-only intact 14-phase planet ledger each turn. Explicitly exclude priority/clone/Mining Station/custom actions; unsupported queue or unaccounted effects atomically ABSTAIN. Conditional TESTED only, no NuHost causal no-build proof. Next mixed capped/loss calendar or bounded shipyard+movement/cargo composition. [Handoff](handoff/2026-10-22-late-pq-capped-no-build-carry-v1.md).\n\n> **2026-10-22 PR #272:** Strict 2–6-turn late PQ conditional carry across explicit *external* single empty/inert ship-loss boundaries, with full supplied preturn snapshots, queue orders, complete warehouses, PP and #271 ship BOM/14-phase economy at every turn. One loss snapshot per next turn must be EXACT previous modeled state minus only the known ship; no Host combat/recycle inference. Any gap or unexplained mutation yields atomic sequence ABSTAIN. No real RNG or DIFF_VERIFIED. Next investigate shipyard+movement/cargo bounded composition. [Technical handoff](handoff/2026-10-22-late-pq-external-loss-multiturn-v1.md).\n\n> **2026-10-22 PR #271:** Separate **late PQ** single contested normal-slot economic turn: RANDOM Host-selected base only caller-supplied, at least two eligible queued competitors, complete base/warehouse/player PP sidecars, lowest free ID, audited ship BOM/warehouse/material purchase, whole 14-phase economic ledger before/after. Missing data or unexplained effects ABSTAIN. This is not a NuHost RNG reconstruction or DIFF_VERIFIED. Next bounded PQ multi-turn carry or movement+cargo. [Handoff](handoff/2026-10-22-late-pq-external-regular-ship-economy-v1.md).\n\n> **2026-10-22 PR #270:** Composed #269 late PPQ integral-share Stage-1 with audited 10-ship warehouse assembly, owner PP unchanged and full 14-phase planet economy in either explicit order hypothesis. Ten may exceed soft cap; component assembly only uses programmatic 999 ID ceiling. Complete queue, warehouse, hull rights, ship ID **caller permutation**, and event/resource checks required; all unknowns ABSTAIN. TESTED conditional, never server proof. Next: separate externally selected late PQ regular queue, then cargo/movement or multi-turn PPQ. [Technical handoff](handoff/2026-10-22-ppq-integral-stage1-ship-economy-v1.md).\n\n> **Update 2026-10-22, PR #269:** bounded **late PPQ exact-integer Stage-1** regular quota selector: complete owned-planets counts + full base/queue roster, only all-integer shares and unique RB/hull-mass cutoff. Emits selected base sets and unassigned lowest ship-ID pool, **not ships or Host proof**. Fractional shares (Stage 2/3 lotteries), ties, incomplete roster → atomic ABSTAIN. Next: audited warehouse+14-phase economy composition with externally asserted ID assignment, then separate late PQ externally selected regular phase. See [handoff](handoff/2026-10-22-late-ppq-integral-stage1-allocation-v1.md).\n\n# Roadmap

This file is the operational roadmap for `planets-lab`. Architecture boundaries remain defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

Current durable checkpoints:

- finite-fuel Tow documented reconciliation: [`handoff/2026-09-11-finite-fuel-tow-documented-reconciliation-runtime.md`](handoff/2026-09-11-finite-fuel-tow-documented-reconciliation-runtime.md);
- verified partial-fuel historical gate: [`handoff/2026-09-09-partial-fuel-historical-gate-verified.md`](handoff/2026-09-09-partial-fuel-historical-gate-verified.md);
- movement: [`handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md`](handoff/2026-09-07-movement-checkpoint-scaled-mine-closed.md);
- Classic combat replay coverage: [`handoff/2026-09-07-combat-c2-classic-replay-coverage.md`](handoff/2026-09-07-combat-c2-classic-replay-coverage.md);
- ship battle sequences: [`handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md`](handoff/2026-09-07-combat-c3-ship-sequence-diff-verified.md);
- planet/starbase sequences: [`handoff/2026-09-07-combat-c4-planet-sequence-checkpoint.md`](handoff/2026-09-07-combat-c4-planet-sequence-checkpoint.md).
- external client/plugin mechanics references: [`handoff/2026-09-27-external-planets-tools-mechanics-reference.md`](handoff/2026-09-27-external-planets-tools-mechanics-reference.md).
- engine-core internet research pass: [`research/2026-09-28-engine-core-internet-research-pass.md`](research/2026-09-28-engine-core-internet-research-pass.md).

## Evidence policy

Mechanics are promoted only with explicit evidence status:

- `DOCUMENTED` — primary Planets.nu documentation;
- `CORPUS_OBSERVED` — directly observed in historical/current Nu data;
- `INFERRED` — reconstructed from observations or secondary evidence;
- `TESTED` — covered by deterministic local regression/scenario tests;
- `DIFF_VERIFIED` — matched against clean attributable NuHost transitions.

Unknown mechanics fail closed. Raw facts and evidence-scoped effective interpretations remain separate.

External implementations are candidate generators only. Kecupo VCR Sim,
nu-replayer, c2nu, nupilot, McNimble plugins, SitRep, T-Continuum Analyser and
similar projects may identify formulas, edge cases, API fields or public games
worth testing, but they do not create evidence labels by themselves. See the
2026-09-27 external reference catalog for the source-by-source boundary.

## PR-to-PR continuation and documentation rule (2026-10-22)

**MANDATORY IN EVERY PR:** update the canonical
[copy-ready new-chat prompt](CONTINUE_HERE.md), add the same actual
PR number to [PR_CHANGELOG.md](PR_CHANGELOG.md), and update at least
one more meaningful project document (this roadmap, README,
WORKFLOW, or a relevant handoff). CI checks the *exact* PR base/head
diff and requires all three; see [AGENTS.md](../AGENTS.md),
[WORKFLOW.md](WORKFLOW.md) and `tools/check_pr_handoff.py`.
The updated prompt must carry enough context for a successor to
continue without pasted conversation history. After merge, verify
live `main` and post-merge CI. Multiple related PRs may be completed
per user-requested work session with one consolidated final report.

Current coding focus after the #259–261 Classic queue subphase chain:
conditionally compose a genuinely noncontested PBP priority purchase
with selected saved-pointer standard builds under one explicit cap,
preserving separate PBP and standard-pointer ledgers; then bounded
late PQ/PPQ and further movement/shipyard/combat compositions.
**Do not** treat these local tests as NuHost phase-order validation:
real Host acceptance and independent before/after evidence remain
parked in [issue #247](https://github.com/Numillyash/planets-lab/issues/247).

## Current focus

**Early unthrottled PQ/PPQ: ordinary ships AND idle-starbase PP (#268, 2026-10-22):**
Extend #258's only-all-queued early model with an exhaustive
all-ordinary-starbase roster that admits at least one queued
and one idle base. In fully unthrottled intervals below 90%
of the soft cap, every ordinary eligible base is caller
asserted selected: queued base builds at ZERO PP cost,
unoccupied build slot awards default +2 PP to its owner.
Run audited multi-base warehouse ship construction and
full 14-phase economy, verify final blueprint identities,
old fleet/base preservation, per-planet resource/event
ledgers and idle owner PP receipts. The set of new ship
IDs must exactly equal N **lowest available** legal IDs;
assignment of IDs to bases remains caller asserted rather
than falsely recovering PQ/PPQ randomized order.
Unknown custom PP awards, Mining Stations, priority codes,
missing idle stock or softcap contention ABSTAIN. Detailed
[early idle-PP handoff](handoff/2026-10-22-early-pq-ppq-idle-pp-v1.md).
Next: separately bounded PPQ throttled regular slots
(owned-planet proportions/RB#) and PQ random regular slots;
then compose core shipyards with safe movement/cargo phases.


**Late PQ/PPQ single priority ship construction and full economy (#267, 2026-10-22):**
Extend #266 model admission/PP quote into real
model-only one-ship warehouse assembly + 14-phase
economic turn. Soft ship count can be at/above the PQ/PPQ
configured threshold; 999 is the distinct programmatic
ship-ID ceiling for the assembler. A complete single
pb1 priority request can spend documented default PP and
only newly purchased hull/engine/weapon BOM costs, keeping
PP in a sidecar. Reverify full final ship specs, unchanged
old ships and bases and per-planet tax/mining/economy ledgers,
for explicit before/after economic placements. Fail closed
on unknown PP competition, regular queue, custom rules,
other ship activity and forged receipts. [Full handoff](handoff/2026-10-22-late-pq-ppq-priority-economy-v1.md).
Next genuine new mechanism: separate bounded PPQ **regular**
late slots (allocation depends on planet shares/RB#) versus
PQ randomized regular slots; do not conflate the two or
claim independently Host-verified priority timings.


**Late PQ / PPQ single priority admission / PP quote (#266, 2026-10-22):**
Separate soft cap (500 default, custom configurable), hard
programmatic ID cap (999) and Classic PBP hard limit.
Compute default PQ/PPQ 1 + ceil(min(hull KT,1000)/50) PP
cost (21 PP maximum). Require a complete owner PP/base/fleet
roster, exactly one pb1 priority request, no other normal
or priority builds in this bounded stage, no clone/custom
price; assert soft cap reached and ID remains below 999.
Return ONLY a conditional quote and lowest free ID, NO
server acceptance and NO ship execution. Unknown PPQ RB
allocation/planet shares, PQ random selection, pb2..pb9,
ties/custom game settings ABSTAIN. Details:
[late priority admission](handoff/2026-10-22-late-pq-ppq-priority-admission-v1.md).
Next mainline: compose this with strict BOM/warehouse ship
assembly and full 14-phase economy, both placement hypotheses,
and add per-owner PP/resource controls.


**Classic PBP unique-highest contender for LAST hard-cap ship slot (2026-10-22):**
Add a *distinct bounded conditional ranking-policy hypothesis*
for a genuine two-player PBP contest with ONLY ONE legal
ship slot left. Complete base/PBP/ship roster, two or more
eligible players with >=21 PBP, a unique highest score,
exactly one queued base per eligible player and NO PB codes,
clones or other Host windows. Only the winner spends capped
hull-mass PBP and purchases components; last standard-pointer,
other PBP totals and unselected warehouses remain unchanged.
Before-/after-economy hypotheses and full final ship plus
planet ledger checks; reject ties, multi-slot, unknown policy,
modern ranking uncertainty and missing inputs with ABSTAIN.
Official Host Order warns ranking precedence may vary, so
this is **NOT** contemporary NuHost ordering verification.
[Detailed terminal-slot restrictions](handoff/2026-10-22-classic-contested-final-pbp-slot-v1.md).
Next: handle real multi-owner priority scheduling only under a
verified explicit policy snapshot, or advance to separately
bounded late PQ/PPQ and cross-system Host composition.


**Bounded consecutive Classic queue/pointer/PBP/warehouse carry (2026-10-22):**
Continue the joint full priority+standard #263 turn into a
*multi-turn* model sequence. On each next turn use exactly
one explicitly operator-asserted queue row for every base;
carry modeled current fleet, complete warehouse inventory
including idle bases, per-owner PBP balances and saved
standard-pointer as distinct sidecars. Dispatch the #263
joint path iff one player remains PBP eligible; otherwise
use #260 standard-only branch. Abort whole sequence with NO
partial game/receipt if a later turn is unsupported,
materials/priority/warehouses are ambiguous or any external
PBP/stock/combat effect is needed. No Host queue causality,
PBx tie ranking or canonical signed order schema change.
[Consecutive queue-state handoff](handoff/2026-10-22-classic-multiturn-queue-carry-v1.md).
Next: bounded documented competitive queue arbitration or
late PQ/PPQ admission and cross-system integrated Host turns;
external Host evidence still parked #247.


**Classic priority + standard in one fully audited conditional turn (2026-10-22):**
Compose one uncontested Classic PBP priority build from #261
with the #259 standard pointer/queue and #260 stock-checked
ship assembly, with a SHARED full fleet/hard cap and lowest
unused IDs. Subtract mass-dependent PBP cost only for the
priority ship; clear its ordinary slot without changing the
standard pointer; run the standard circular selector on the
remaining fleet and eligible bases, recording its pointer
separately. If the priority owner still has >=21 PBP or
multiple priority candidates exist, ABSTAIN rather than
skip unexecuted priority builds. Hypothetical before/after
14-phase economy, independently reconciled material,
warehouse, full ship and planetary event ledgers; no
partial state on failure. [Detailed bounded joint Classic
handoff](handoff/2026-10-22-classic-joint-priority-standard-v1.md).
Next: a genuine scoped multi-turn carry test and a separate
typed queue-state contract for contested Classic or PQ/PPQ.
User-dependent Host causal evidence remains parked in #247.


**Classic uncontested PBP priority purchase (2026-10-21):**
After #259 regular pointer and #260 selected standard builds,
implement the **separate** restricted Classic priority subphase:
exact hull mass, 1 PBP per ceil(50 KT) capped at 20,
21-PBP eligibility, known entire owner balance and base
queue roster. Only one PBP-eligible owner and exactly one
queued starbase permitted; any competing points, pbN code,
clone, missing queue state, exhausted hard cap ABSTAINS.
Reuse warehouse/cost/new-ship audit and conditional lowest
unused ID; report updated points in an isolated phase state
without claiming authentic PBP receipt or Host timing.
[Separate uncontested priority phase](handoff/2026-10-21-classic-uncontested-pbp-priority-v1.md).
Next: typed priority-then-standard Classic phase composition,
strict pointer/PBP separation and independent HMAC/Host gates.


**Classic standard pointer–ordered shipbuilding × economy (2026-10-21):**
Compose #259's exact standard-only Classic pointer selection
with complete caller-asserted per-base warehouse ship designs,
conditional **lowest-free ship ID** allocation in saved-pointer
order, and #257/#258 independently checked component and planet
economy ledgers. A selected second base failing must ABSTAIN the
whole turn; idle and unselected bases remain untouched. This is
the Classic nonpriority standard subphase ONLY: <21 PBP on all
owners, no pbN/cloning, no unknown queue state or Host timing.
Before-/after-14-economic-phase placement remains conditional.
[Full bounded interface and provenance](handoff/2026-10-21-classic-pointer-standard-ship-economy-v1.md).
Next core: staged priority PBP selection and post-combat build
windows **separately**, then PQ/PPQ late allocation and larger
movement/combat Host composition. No real queue proof until #247.


**Classic PBP standard subphase / persistent pointer (2026-10-21):**
In the first near-limit/late Classic queue unit, separate the
STANDARD regular subphase from priority builds and cloning.
Require an exact caller-asserted last standard build planet
pointer, complete base/owner/PBP roster (all PBP <21),
prior priority subphase resolved and no clone or pbN codes.
Walk circular ascending planet IDs, skip idle bases, return
up to explicit available hard-limit slots, preserve pointer
on zero builds, and update only to last selected standard
base. This SELECTS bases, not ship IDs, Host timing, or
authentic priorities. ABSTAIN for missing pointer, unknown
PBP/owner, pbN, cloning and exhausted causal context.
[Pointer unit and explicit provenance](handoff/2026-10-21-classic-standard-pointer-subphase-v1.md).
Next combine independently guarded selected standard subset with
per-base ship assembly and planet economy without claiming
real PBP priority/scheduler Host parity.


**Common unthrottled early multiple-starbase queue (2026-10-21):**
After #257 selected single-base ship/economy turn,
compose 2–64 ordinary *fully queued* bases from ALL owners.
Support only common PBP/PQ/PPQ early/all-slots-open interval
with **post-build fleet count strictly below 90%** of asserted
global limit; full base/warehouse/ID scope and explicit no
priority/cloning/other actions. Build each independent base,
audit component draw/cost/new ship from previous state and
reconcile ALL planets against unchanged 14-phase economy,
before/after models. Missing base, duplicate ID, one failed
purchaser, cap contention or invented priority ABSTAIN
entire batch with no partial ships or receipts.
[Scope, source rules and queue exclusions](handoff/2026-10-21-core-unthrottled-multibase-queue-v1.md).
Next: separate Classic middle/late PBP state and PQ/PPQ
late allocation with externally specified priority/queue
state; no Host causal claims until issue #247 witnesses.


**Selected ship assembly × standard planet economy (2026-10-21):**
Following #256's conditional one-ship intermediate stage,
execute one real **modeled turn** containing precisely one
caller-selected uncontested PRELIMIT warehouse ship assembly
and the unchanged 14-phase planetary economy, with an
explicit before-/after-economy hypothesis. Independently
reconcile entire assembled ship identity, surface MC/mineral
debits, stock component unit balances, any existing ship/base
changes and every planet's taxes/factory/mineral economy delta.
A missing source/queue/ID/receipt or unexplained inventory
causes all-or-nothing ABSTAIN. This does not run PBP/PQ/PPQ/PLS
arbitration or authenticate NuHost phase order.
[Integration/evidence boundaries](handoff/2026-10-21-core-selected-ship-economy-integration-v1.md).
Next mainline: explicit standard queue selection and
multiple-base resource/priority contention before larger
movement/combat integration; keep live external proof #247 deferred.


**Core one-starship warehouse/queue-selected assembly (2026-10-21):**
Following #255's exact new-component BOM quote, model per-base
stored hulls/engines/beams/launchers in a typed sidecar; require
an explicitly asserted selected PRELIMIT standard build slot,
complete ship roster and one caller-provided free ship ID. Draw
in-stock components, purchase only missing units, debit MC/minerals
atomically, and create one model-only intermediate assembled ship.
No fabricated Host queue arbitration, ship-ID allocator, actual
receipt or independent phase placement. Missing source stock,
priority or nonstandard queue context ABSTAIN.
[Inventory, one-build scope and hard queue limitations](handoff/2026-10-21-core-selected-ship-warehouse-assembly-v1.md).
Next: integrate conditional assembly with planet-side resource phases
and other base purchases while retaining a strict global accounting
and explicit provisional Host timing.
Manual server-evidence experiments remain parked in #247.


**Core standard ship NEW-component cost quote (2026-10-21):**
After ordinary starbase facility construction #254,
add an explicit one-ship bill-of-materials quote using the
existing NuStaticSpecs hull + all engines + fitted
beam/torpedo launchers, enforcing known starbase tech,
component slots, a caller-declared eligible hull set
and complete immutable surface resources. Return exact costs,
deficits and affordability as a **quote only**, NOT an
accepted order, new ship, reserved component warehouse or
a build slot. Ship-limit, queue/priority points, race
licensing provenance, component stock and ship-ID allocation
still ABSTAIN for real execution.
[Quote implementation, strict gates and next storage/queue model](handoff/2026-10-21-core-standard-ship-bom-v1.md).


**Standard starbase facilities core (2026-10-21):**
After #253's orbital cargo + movement + economy composition,
implement documented ordinary **starbase creation**, starbase
defense posts and base fighters (resource-conserving, bounded).
Prices: base 900 MC/120 Dur/402 Tri/340 Mol; each base defense
10 MC/1 Dur, each base fighter 100 MC/3 Tri/2 Mol; normal caps
200 defense and 60 fighters. Add complete owner-scoped facility
targets and conditional before-/after-planetary economy placement;
check every receipt, base state and planetary resource ledger.
Existing 14-phase economy, PlayerOrders V1/V2 HMAC, corpus and
heldout remain unchanged. Unsupported special stations, simultaneous
creation+equipment on one planet, queues and shipbuilding ABSTAIN.
[Scoped starbase implementation and shipbuilding prerequisites](handoff/2026-10-21-core-standard-starbase-facilities-v1.md).
Continue with complete shipbuilding bill-of-materials and inventory/
queue eligibility once represented explicitly; do NOT create ships
from a hull price alone. Real Host experiments remain parked in #247.


**Core orbital transfer × normal movement × standard economy (2026-10-21):**
Extend PR #252's fuel-checked ship movement and economy with
the existing PlanetCargoTransferPhase, under an explicit local
transfer-before-/after-move placement plus move/economy and
construction/economy choices. Only same-owner nonzero transfers
at the currently valid orbital site; capacity and fuel tank
remain enforced. Audit transfer event/typed-order equality and
independent ship + planetary inventory ledgers; forged/missing
receipts or source/owner ambiguity ABSTAIN for the whole turn.
All orders remain caller-asserted, no V1/V2 HMAC changes,
no NuHost execution or phase-order promotion.
[Cross-system cargo handoff](handoff/2026-10-21-core-orbital-cargo-composition-v1.md).
Do not rerun public100 or consume heldout32 M2 entity states;
manual/independent Host evidence remains parked in #247.


**Executable ordinary-movement + standard economy turn (2026-10-20):**
After #251's multi-planet/multi-turn planetary ledger, add the
first cross-subsystem HostEngine composition: ordinary reachable
normal movement + explicitly scoped building + unchanged 14
planet economy phases. Require a separate explicit order per
ship, every owner represented, full hull/engine/fuel inputs,
two transparent (not NuHost-verified) movement placements,
and no unmodeled special/combat/foreign-planet interactions.
Independently reconcile each ship's fuel/position and each
planet's supplies, taxes, construction spending, surface/ground
minerals and structures, ABSTAIN with **zero partial output**
on any unsupported interaction or ledger mismatch.
[Coverage inventory and scoped integration](handoff/2026-10-20-core-standard-host-composition-v1.md).
Continue toward explicitly ordered orbital cargo transfer next;
keep signed orders, phase causality and live game requirements
parked in [#247](https://github.com/Numillyash/planets-lab/issues/247).


**Core multi-turn economy contract (2026-10-20):**
Extend PR #250's synthetic structure/economy one-turn slice
to a bounded 1–8-turn explicit plan across multiple owned planets.
For each turn, independently reconcile per-planet factory supplies,
tax receipts, MC/supply structure spending and sale, mineral
extraction, ground mutation and structure counts (including decay).
Any unexplained balance or later failed turn ABSTAINS the
**whole sequence** with no partial checkpoints. Preserve unchanged
14-phase economy, exact explicit owner coverage and optional
before/after build placement. This checks internal standard-model
consistency, not observed NuHost causality; the external evidence
dependency stays parked in #247.
[Multiturn research contract](handoff/2026-10-20-core-multiturn-planetary-economy-ledger-v1.md).


**Standard construction + 14-phase economy conditional integration (2026-10-20):**
After #249, test both fully explicit structure placements relative
to the existing intact planetary economy using a separate,
owner-complete **research target map**, not a new unsigned field in
V1/V2 signed PlayerOrders. Enforce rule-mode and context gates,
ABSTAIN on missing owners, ships/bases/storms, preserve original
state and canonical HostEngine/phase definitions. A constructed
factory may contribute to same-turn supplies ONLY in the chosen
before-economy hypothesis; this is a distinguishable local model,
NOT observed NuHost phase ordering. External evidence remains
parked in #247.
[Conditional whole-turn integration handoff](handoff/2026-10-20-core-structure-economy-conditional-turn-v1.md).


**Core standard structure construction V2 (2026-10-20):**
Continue PR #248's strict fully funded construction with a
SEPARATE, opt-in normal-rule priority simulator. Official
structure targets execute defense, factories, then mines;
one supply per unit, 10/3/4 MC, and an explicit option to sell
surplus supplies for MC at 1:1. Partial funding and target clipping
are reported as conditional partial outcomes with exact ledgers;
unsupported rules and malformed inputs ABSTAIN.
Preserve the V1 API and do not yet add new unsigned fields to
PlayerOrders or place construction silently inside canonical
Host phases. No raw private inputs, no corpus scan.
[Implementation and scope](handoff/2026-10-20-core-standard-structure-priority-v2.md).


**ACTIVE CORE MAINLINE — human-dependent mechanics deferred (2026-10-20).**
GitHub [issue #247](https://github.com/Numillyash/planets-lab/issues/247)
parks independent NuHost accepted-order receipts, verified all-owner
T−1/T submissions, Host boundary, prospective C5 capture O/C, and
special Chunnel/Horwasp experiments **until the end**. No new
player-led experiments, HAR, synthetic-only rerun loops or fabricated
DIFF_VERIFIED claims while autonomous core work remains.

Do not conflate **public100 storage completion** (224014 / 224014
semantic-parity snapshot members; 100 games) with verified
end-to-end Host mechanics. M2 uses frozen baseline68/136 pairs;
fresh32 were opened for separate prospective capture-side research
but remain excluded from M2 entity sampling. CURRENT stays public68.
Continue documented and testable standard mechanics, starting with
bounded **planet mines/factories/defense construction** (1795/3769
structure-family net changes) without inferring orders from T−1/T
stock differences. Keep unsupported funding, campaign modifiers
and unknown phase placement ABSTAIN.
[Full scope and staged autonomous priorities](handoff/2026-10-20-core-corpus-mainline-and-deferred-evidence.md).


**M2 Host differential admission boundary (2026-10-20):**
Published local client-sequence audit runtime
`20261020T135946Z_98d857cc3b62` completed at exit=0 with
one synthetic save→ready candidate and one repeated-ready
ABSTAIN. No actual accepted Host orders were observed.
Add an aggregate-only local readiness check linking existing
bounded T-1→T state validation, full-owner V2 HMAC envelopes
and conditional six-way technology phase comparison. Optional
atomic client metadata proves only same-source consistency.
Never promote local signatures, caller-supplied Host time or
matching synthetic states to DIFF_VERIFIED. Three external
blockers remain: independently authenticated server acceptance
of the specific orders, independently witnessed Host boundary
and independently sourced complete pre/post owner-current state.
[Exact evidence admission and missing-data contract](handoff/2026-10-20-m2-host-differential-evidence-readiness-gate.md).


**M2 client chronology one-save-window and independent audit (2026-10-20):**
The previous metadata-only runtime `20261020T134314Z_1d0f3cfafa32`
passed its synthetic tests but did not test repeated-ready reuse
of a single earlier successful save. Require a fresh, complete,
non-overlapping save batch between **successive** turnready requests,
ABSTAIN for mixed success/failure, in-flight saves or invalid clock
ordering. Add atomic metadata-only `bundle()` and a strict Python
cross-language consistency audit, with optional local chmod600
private-bundle mode. Public runtime evidence uses fake browser
data **only**. This does not authenticate server order acceptance
or actual NuHost execution.
[Correctness and privacy boundary](handoff/2026-10-20-m2-save-ready-one-window-and-independent-audit.md).


**M2 passive client save/ready chronology metadata (2026-10-20):**
After clean local-save-readiness runtime at
`20261019T234441Z_2bf7ed40e76d`, add a separate **metadata-only**
observer for original /game/save and /game/turnready calls.
Retain only bounded in-memory route/method, client-clock timing,
HTTP status and response success flag, with explicit overflow and
in-flight/overlap ABSTAIN. Only an ordered client-visible response
sequence can be claimed; server acceptance of *specific* orders,
external Host-start clock, independently accepted order submission
and actual NuHost execution remain unverified. Publish only a
fake-browser Node.js test result, never real turn/order payloads.
[Scope, privacy and limitations](handoff/2026-10-20-m2-client-save-ready-metadata-v1.md).


**M2 local-only /game/save evidence readiness (2026-10-20):**
Synthetic phase-identifiability runtime 20261019T210532Z_608b76519061
completed successfully: 96 candidates, 24 complete six-way cases with
one identical end state each; 72 have unsupported model paths. The
current grid cannot identify phase ordering. Next, evaluate the
EXISTING passive owner-approved /game/save capture as **client
transport** only: classify syntactically complete captures, app-level
and HTTP responses and bounded buffer omissions without emitting
private orders, IDs, notes, URL strings or secrets. A local-only
Unix chmod600 CLI refuses inputs inside the repository, while the
public runtime-evidence wrapper runs fixed SYNTHETIC input only.
No HTTP success or turnready counter is promoted to NuHost order
acknowledgement, independently witnessed Host time or causal parity.
[Research and privacy boundary](handoff/2026-10-20-m2-local-save-evidence-readiness-v1.md).


**M2 six-way phase identifiability preflight (2026-10-19):**
PR #241 completed the six conditional placements but did not ask
whether they produce six distinguishable post-Host states.
Add an offline, fake-input-only phase-equivalence audit comparing
the entire modeled T state across all six, with 96 bounded
deterministic fixture variants and aggregate-only runtime evidence.
Prefer experiments where every hypothesis is supported; do not
interpret an unsupported conditional model as a NuHost rejection,
and do not claim phase order from model-internal traces.
[Implementation and evidence limits](handoff/2026-10-19-m2-synthetic-phase-identifiability-v1.md).


**M2 complete six-way phase ordering (2026-10-19):** After PR #239
standard starbase-tech spending and PR #240 signed V2 owner orders,
the research slice still omitted the two valid relative placements
where technology lies between planet cargo transfer and the fixed
14-phase economy block. Add the third explicitly named tech slot,
enumerate all six permutations without inventing a real Host ordering,
and compare them against the SAME bounded full states and genuinely
present tech orders. Retain exact phase-resource conservation,
ABSTAIN on incomplete provenance and every negative control, and
keep source HMAC distinct from server acceptance.
[Six-way simulation evidence and limitations](handoff/2026-10-19-m2-six-phase-order-exhaustive-v1.md).


**M2 validated V3 + explicit standard-price starbase-tech simulation (2026-10-19):**
The actual V3 runtime `20261019T143058Z_1f0721ca1186` has exit 0,
unchanged CURRENT, frozen baseline68, no heldout32 entity reads:
915 surface residual mineral comparisons split into 65 single-only,
36 overlapping single+multiship, 7 multiship-only, 807 neither.
These are only 108 unique cargo mineral comparisons and 65 cargo-candidate
planet windows among 315 residual planet windows. Only 15 such windows
show weak-linked base-tech changes; just 1 combines a tech change and
cargo candidate. No Host execution is confirmed. Next implementation
adds opt-in, explicitly ordered *standard* starbase technology purchases,
documented MC pricing, owner and eligibility gates, phase resource balances,
and conditional full-state Tminus1->T reconciliation. It does not invent
base owners for archival ownerless rows or accept signed V1 order capture of
tech orders. [Validated V3 and research simulator scope](handoff/2026-10-19-m2-v3-validated-starbase-tech-integration.md).


**M2 cargo hypothesis overlap and planet-window dedup V3 (2026-10-18):**
Published V2 baseline68 from runtime-logs has 915 surface-only
residual mineral comparisons, 101 single-ship and 43 multi-ship
opposite cargo DELTA candidates, 802 weak base planet links and
52 weak-base tech changes. **101+43 may DOUBLE COUNT**. V3
adds a true disjoint four-way partition (single-only, multiship-
only, both, neither), qualified signed residual × tech-change
joint counts, and mineral-multiplicity-aware unique planet-window
event counters. Preserve 68-game zero-inclusive distributions,
match exactly the frozen 136-pair selection and existing 915
mineral residuals. Default Host mining/transactions NOT promoted;
all ship/base associations are observational. All artifacts
aggregate-only via runtime-logs.
[Full V3 evidence and next one-pass runner](handoff/2026-10-18-m2-disjoint-ship-cargo-and-planet-window-v3.md).

**M2 baseline68 V2 contextual mineral residual follow-up (2026-10-18):**
Recovered prior aggregate/runtime-logs triage established 915
ground-exact/surface-only residual mineral observations, 652 with
same-site own ship both snapshots, 101 single same-ID cargo
opposition candidates, and 12224 starbase rows with missing
ownerid. V2 preserves strict explicit-base-owner abstentions but
adds a distinct WEAK co-observed base.planetid -> authenticated
owner-current planet link, never treating missing owner as proven.
Also adds 2+ co-site ship **summed** opposite cargo candidates,
only with same observed ship ID set and complete numeric cargo,
and zero-inclusive 68-game context-clustering histograms. Offline
triage validates qualified denominators. All source evidence
remains observational, heldout32 SEALED and CURRENT unmodified.
[Full new V2 experimental gates and one evidence command](handoff/2026-10-18-m2-ownerless-starbase-and-multiship-residual-v2.md).

**M2 actual surface-context runtime and no-recompute recovery
(2026-10-18):** User ran PR #231/#232 context analysis on existing
26.65-GiB immutable public100 DB; aggregate report succeeded and
was published on runtime-logs, but host-side offline `triage.json`
failed because importing `planets_lab.corpus` transitively
requires DuckDB (only installed in Docker). From the published
aggregate, **652/915 = 71.26%** of ground-exact/surface-residual
observations had own ship at site at both turns versus **3316/11813
=28.07%** of fully-exact observations; **101** residuals had a
single opposite same-ID co-site ship cargo change candidate.
These are correlations, NOT executed cargo orders, and
`ABSTAIN_STARBASE_OWNER_MISSING=12224` means base attribution
is currently unavailable. Fix offline CLI to run stdlib only
and add --complete-existing to produce/publish derived triage
WITHOUT rerunning the 26.65-GiB corpus scan. Original failed
runtime evidence preserved. 
[Actual evidence and recovery](handoff/2026-10-18-m2-surface-context-recovery-without-duckdb-v1.md).

**M2 one-pass context measurement + automatic 915-residual triage
(2026-10-18):** Extend the baseline68 surface residual covariate
profiler with fail-closed **68-game zero-inclusive cluster counts**,
an offline aggregate triage validating EXACT published per-mineral
11,813/915/33/262 class totals and known frozen selection,
ship-site observation completeness, cargo opposition freshness,
starbase co-presence and qualified denominators. One specialized
run-with-evidence wrapper automatically publishes original
aggregate report, derived compact triage, full log and source
provenance to runtime-logs with one 26.65-GiB corpus checksum/read.
No historical ship orders or NuHost causality inferred, sealed
heldout32 remains unexamined. Source/CI only until actual server
report; do not fabricate ship association rates.
[Full automatic runner and interpretation](handoff/2026-10-18-m2-context-triage-dual-evidence-v1.md).

**M2 surface-residual contextual stratification (2026-10-18):**
Existing published mineral residual 2×2 includes 915 observations
where default model matches ground stock but misses surface stock
(against 33 reverse-only and 262 joint mismatches). Add a
one-pass, baseline68-only classifier joining SAME frozen planet-pair
sample to observed owner-ship co-site positions, same-ID numeric
cargo opposition candidates, explicit planetid-linked own starbases,
starbase tech changes, stable structures/taxes and per-game
residual count *buckets* (no game IDs disclosed). Missing coordinates,
stale/ambiguous ship IDs, missing infoturn and absent starbase
planet link abstain; no unseen actions are ruled out. Fail-closed
per-mineral class totals against existing mining model and permit only
aggregate-count output via runtime-logs validator. Source CI
synthetic; require explicit server runtime before reporting actual
ship/base correlation results.
[Scientific handoff and automatic evidence run](handoff/2026-10-18-m2-public68-surface-residual-context-v1.md).

**M2 pinned runtime mineral residual reconciliation (2026-10-18):**
Retrieved the user's successfully published aggregate report directly
from runtime-logs, no 26.65 GiB corpus rerun or copy-pasted logs.
On the same metadata-frozen baseline68/136-pair sample, 13,023
conditional mineral×planet-pair comparisons decompose into
**11,813 both surface+ground exact, 915 ground-only exact,
33 surface-only exact, 262 neither**. Of 1,210 mismatches,
75.62% match underground but have a surface-stock residual.
Prioritize testing co-observed surface cargo/ship/base context,
not prematurely changing the inferred mining formula.
A standalone offline aggregate reconciler validates SHA256,
selection identity and disjoint 2×2 counter identities.
Correlation across 136 selected transitions and unobserved
TurnOrders prevents Host causality promotion.
[Evidence and residual taxonomy](handoff/2026-10-18-m2-published-mineral-residual-tetrad-v1.md).

**M2 runtime evidence publication restored (2026-10-18):**
Prior corpus coverage runners were missing the existing
*-with-evidence.sh workflow, causing unnecessary large server
output pasted to chat. Add wrapper to publish future complete
logs and aggregate JSON to independent runtime-logs branch.
For the existing already completed mineral report, the
--publish-existing mode validates and publishes only aggregate
report.json WITHOUT repeating the 26.65 GiB SHA256 scan.
Strictly gate known schema, immutable corpus SHA, CURRENT unchanged,
baseline68-only entity sample/heldout32 excluded and noncausal
Host flags; reject all raw state/note/auth data.
[Workflow and command](handoff/2026-10-18-m2-corpus-runtime-evidence-publishing-v1.md).

**M2 baseline68 mineral mass-balance hypothesis check (2026-10-18):**
Second REAL public100 baseline68 owner-current census (same 136
metadata-frozen pairs; 3769 comparable planets) reveals that
surface minerals increased while corresponding underground
deposits stayed unchanged in 2793 N, 2801 D, 2739 T and
2835 M comparisons. This is not by itself evidence of
mining or material creation. Add conditional default
mining + published trans-uranium replenishment arithmetic,
gated on stable mineral densities, unchanged mine counts
and authenticated race identity, with separate surface/ground
delta checks and mass-balance residual histograms.
Unseen ship actions, transfers and campaign powers remain
unattributed; exact model matches do NOT prove Host phases.
Keep sealed 32-game heldout unread, original
M2 coverage reports untouched, no simulator model changes.
[Mass-balance handoff](handoff/2026-10-18-m2-baseline68-mineral-mass-balance-v1.md).

**M2 published public100 corpus actual server result (2026-10-18):**
The real read-only corpus census succeeded against immutable public100
at verified SHA256. All 100 games: 224014 source perspectives,
222536 valid identities, 1478 invalid/embedded-turn mismatch,
221091 adjacent same-perspective pairs, no duplicate identities.
Entity reconstruction stayed in baseline68 (sealed holdout32
unread); exactly 136 metadata-frozen T-1/T pairs all had valid
payload identities. These provided **3769 same-owner, owner-current
planet-ID pairs**. Broad net-change family counts:
MC/supplies 3670, surface minerals 3631, underground minerals
1467, populations 2605, structures 1795, and tax/happiness
716 of 3767 qualified. These are NET state differences, not
causally identified orders or Host mechanics.
Extending the same frozen selection with field-specific
increase/decrease/unchanged counts, ground-vs-surface mineral sign
patterns, and observable structure+tax rate stability is the
next conservative evidence gate. Keep the original V1 result
unaltered, write a distinct follow-up report.
[Observed evidence and run instructions](handoff/2026-10-18-m2-public100-real-coverage-directional-v1.md).

**M2 reuse of published giant corpus (October 18, 2026):**
Instead of relying only on 555 local HAR saves, add read-only
coverage census of immutable public100: **100 games, 224014
perspective-turn members, 541348959 typed entity rows** (~26.65 GiB).
Verify exact database SHA256 before opening, scan ALL source-member
metadata for adjacent same-perspective T-1/T potential pairs, and
freeze bounded sample of owner-current planet/ship/starbase coverage.
**Sealed 32-game prospective holdout remains metadata-only**:
actual game entities are sampled only from the existing baseline
public68 manifest after exact 68-game validation. Untrusted or stale
perspectives abstain; cross-turn stock changes are NOT independent
player orders or Host-phase proof. One-command Docker runner uses
published DuckDB read-only with CURRENT unchanged, no corpus
rebuild. [Full workflow](handoff/2026-10-18-m2-public100-economy-coverage-v1.md).
Follow-on requires real runtime report and owner-current qualified
denominators, not simulated corpus-level success.

**M2 official wiki price crosscheck (2026-10-17):**
The user pointed out the already published Race 1 hull cost table.
Official Planets.nu Help separately publishes the default engine,
beam, torpedo launcher and starbase tech prices and /static/all.
Using only these documented prices, client observed resource
spending independently matches exactly for three built designs:
Vendetta + 2 Transwarp + 4 X-Ray + 4 Gamma: 802/56/37/131;
Medium Deep Space Freighter + Transwarp: 365/20/7/41;
Large Deep Space Freighter + 2 Quantum: 500/91/13/38.
The documented 7→10 technology upgrade costs exactly **2400 MC**.
A candidate Nebula build for client Hull5 predicts 1270/104/75/251
against observed 1190/104/75/235, so do not equate IDs blindly.
Add cost/slot-based **candidate** hull discovery from independently
SHA256-pinned public /static/all without requiring a manual mapping;
still label identity and Host execution unverified.
[Public-price crosscheck](handoff/2026-10-17-m2-official-component-price-crosscheck-v1.md).
No raw capture in git; production/C5/corpus frozen.

**M2 ship-build marginal cost calibration (2026-10-17):**
From 20 same-request Starbase-build/Planet-spending witnesses,
19 lack recorded tech changes, 1 includes EngineTechLevel 7→10
and +2400 MC compared with identical no-tech-change recipe.
There are 6 stable game-scoped recipes and only 2 independent
single-component price contrasts: Beam2→6 (+11 MC,+12 D,0 T,+1 M)
and Launcher4→6 (+14 MC,+1 D,0 T,0 M) per component.
The exact rational design matrix has 4 *unidentified* degrees
of freedom even when hull+engine is treated as a composite bundle.
Add a fail-closed offline calibration module and CLI, with optional
SHA256-pinned /static/all and verified per-game BuildHullId→catalog
hull ID mapping. No assumed hull namespace identity, no tech-price
subtraction into components, no claim of Host execution or
`DIFF_VERIFIED`.
[Calibration handoff](handoff/2026-10-17-m2-client-ship-build-cost-calibration-v1.md).
No real game CSV, HAR, note or player ID committed.

**M2 client economic witness layer (October 17, 2026):**
A read-only offline event extractor now consumes existing sanitized
HAR bundles and separates client pending `Transfer*` state/balanced
reservations from co-saved ship/planet available-stock changes,
Starbase build selection with unique simultaneous Planet
MC/D/T/M spending, and tax/happiness client preview changes.
Missing pre-action entity baselines and ambiguous cost matches
abstain; overlapping game/player/turn groups from different HAR
files sort by actual timestamps only when independently ordered.
Every event is explicitly `CLIENT_SAVE_COHANGE_ONLY_NOT_HOST_VERIFIED`.
Includes a single offline diagnostic CLI, synthetic negative tests
and a [dedicated evidence handoff](handoff/2026-10-17-m2-client-economic-witness-layer-v1.md).
Do not promote to a Host `TurnOrders` command, `DIFF_VERIFIED` parity
or NuHost phase causality without independent verified boundaries.
Real game captures and notes stay local, C5/production/PR #28 frozen.

**M2 follow-up HAR (2026-10-17): two sanitized captures, 555 saves:**
151 new HTTP 200, success:true client saves add 29 readiness calls
and extend existing games to 26 and 47 observed turns;
90 unique game/player/turn windows across 5 games.
All 555 preserve 1,689 serialized records, 340 within-turn field
changes, 10 nonempty Waypoints observations, and 12 nonzero
TransferClans snapshots unchanged from the first capture.
**Critical correction:** StarbaseN numeric ID != PlanetN numeric ID:
real Starbase1 co-saves with Planet8 in one sector. The same-request,
unique four-resource client deduction rule recovers 11 build cost
pairs in the original data and 9 more in the new data (20 total),
with exact multi-turn recipe replication; ambiguous pairs abstain.
This is *client-saved cochange*, not an accepted Host order or
NuHost causal proof. [Follow-up handoff](handoff/2026-10-17-m2-har-continuation-151-v1.md).
No private captures, user note bodies, or live game IDs in git.

**M2 HAR empirical evidence: 404 saves, 5 games, 62 windows (October 17, 2026):**
The player's opt-in locally redacted HAR bundle contains
404/404 successfully extracted save requests (HTTP 200,
`success:true`), 60 category-only Turn Ready calls, and 1,161
legacy records across Note, Planet, Ship, Starbase and Stock.
There are 221 *within-turn* repeated-field changes, of which
39 are private Note.Body edits. Critically, 12 saved Ship snapshots
have nonzero `TransferClans` (11 distinct signatures), and a
same-turn cancellation restores ship Clans and MC by exactly the
formerly queued quantities. Eleven Ship-building client events
include paired same-request planet resource deductions, with
repeated exact costs and an extra 2,400 MC alongside EngineTechUp=3
in one build. Two tax changes update NativeHappyChange preview.
The offline parser now recognizes StockNN and NoteNN without
mistaking the note key suffix for its embedded Id, and emits
cross-window aggregate evidence counts. **Still client evidence,
not NuHost phase causality or authenticated per-order execution.**
[Detailed results](handoff/2026-10-17-m2-har-empirical-404-v1.md).
Never commit real game captures.

**M2 low-touch real game session capture (HAR, October 17, 2026):**
The owner reports that repeatedly installing browser probes and manually
coordinating individual UI actions is disruptive to normal play.
Adopt one ordinary Chrome/Edge DevTools Network session with Preserve log:
play naturally, export one LOCAL HAR at the end, convert offline using
a standalone stdlib-only script. Only exact Planets.nu POST /game/save
bodies are retained, partitioned per game/player/turn, with known
auth/cookie/key/token fields removed; /game/turnready is counted,
other HTTP traffic is discarded, and no extra network requests occur.
The redacted bundle is compatible with our existing read-only
last-seen ShipN/PlanetN/StarbaseN field analyzer. No 10-snapshot limit.
Raw HAR always remains local and must never enter GitHub or chat.
[Windows single-session HAR workflow](handoff/2026-10-17-m2-devtools-har-session-capture-v1.md).
No independent NuHost causal order proof yet.

**M2 real `/game/save` wire grammar decoded (October 17, 2026; parser CI pending):**
An owner-provided full game-data capture contains **10 retained** XHR
POST saves (12 counted in browser, earliest 2 evicted) with
`ShipN`/`PlanetN`/`StarbaseN` form entries. Each is a legacy
`Field:::value|||Field:::value` string, **not** nested JSON
within `turn` (which is the actual turn number). Last-seen
object comparisons expose `Planet1.Clans 914→814` and
`Ship4.TargetX/Y 1965,1956→2004,2035`; `Ship3` first
appears with 100 clans, but no before baseline for that ship exists.
`keycount` matches form-key count. All retained responses are
HTTP 200, `saveIndex=2`, **`success:null`**, not confirmed
`success:true` acknowledgements. Implement a fail-closed offline
legacy wire parser with partial-save semantics, no invented
`TurnOrders`, and local-only analysis output.
[Detailed evidence & next controlled cargo-transfer gate](handoff/2026-10-17-m2-real-save-wire-decoder-v1.md).
Never commit private live captures.

**M2 real game-data save capture and client differential (implementation / CI pending):**
Six user-observed real `/game/save` XHR saves returned HTTP 200 with
`success:true`; all arrived before a `/game/turnready` request.
Unknown form fields appear as 4/4/4/4/5/5 (three numeric-text and
one/two opaque-text). These shape-only reports still do not establish
any per-entity save-command mapping. The owner explicitly authorized
collecting game data from Home Sector or a test game: the new
`tools/client/planets_nu_save_payload_capture_v1.js` is a separate
opt-in full game-field capture + two-save differential instrument,
while recursively redacting known credentials and omitting query
strings/headers. Review all output manually for unexpected secrets;
never commit real captures. No independent NuHost acceptance, Host
phase ordering or historical `DIFF_VERIFIED` claimed. Next: one
genuine owner-approved redacted full request and bounded field
mapping, not further opaque counting.
[Protocol](handoff/2026-10-17-m2-real-save-payload-capture-v1.md).

**M2 live autosave observation (tax-rate edits; follow-up v1.3):**
The authorized player observed four XHR `POST /game/save` responses
(HTTP 200, `success=true`) during several own-planet tax adjustments,
plus one `game_turnready` call. There is **no separate Save button**
in this game UI; Turn Ready navigates to the dashboard. Requests showed
5,5,4,4 anonymous form parameters beyond the safe allowlist.
V1.2's single `unknown_key_count=1` and `outer_type:null` are an
observer placeholder bug, NOT a factual one-field/null-value finding.
V1.3 repairs that count and profiles coarse encodings of all bounded
unknown fields, not just the first two. The timing of each save vs.
each tax edit, server-side order acceptance and NuHost phase semantics
remain unverified. No more forced Ready toggles for research.
Handoff: [empirical save schema](handoff/2026-10-17-m2-save-schema-reconnaissance-v1.md).

**M2 first positive ordinary `/game/save` observation (October 17, 2026):**
The owner-supplied privacy-redacted browser report contains exactly one
XHR `POST /game/save` with HTTP 200 and response `success:true`.
Observed request field types: `gameid`, `playerid`, `turn` are
strings, with 2 secret-masked keys and **1 additional unknown key**.
Also observed one `/game/turnready` and two account API calls by
category only. This is a real positive save API response,
**NOT** a field-level authenticated cargo order nor Host parity.
The v1.2 observer can now inspect type/allowlisted nested structure of
the unknown value without retaining its name, actual values or secrets.
**Next:** one ordinary, authorized UI save with v1.2 and evaluate only
its sanitized opaque value profile. See
[API capture handoff](handoff/2026-10-17-m2-save-schema-reconnaissance-v1.md).
Keep C5 frozen and historical causal comparisons fail-closed.

**M2 live save transport checkpoint (zero qualifying observations):**
The first owner-authorized passive DevTools probe returned
`observed_save_calls=0`. This is **not** proof that nothing was saved,
nor a reason to invent /game/save request fields. Probe v1.1 adds
privacy-safe *counts only* of same-origin fetch/XHR route categories,
so a future single ordinary save can distinguish no visible traffic
from different routes; no raw URLs, values or credentials are retained.
No NuHost order acceptance has yet been authenticated. See
[save schema handoff](handoff/2026-10-17-m2-save-schema-reconnaissance-v1.md).

**M2 /game/save empirical schema reconnaissance (October 17, 2026):**
Owner-scoped pre-Host bundle server runtime succeeded at clean source
`1f5ee1db6ad82a15791981f3384ef2101d327e1d`,
`exit_code=0`, no missing artifacts; report Git blob
`62667e5fc3b415d7d9e22170883727ef94c688f4`.
All eight ABSTAIN controls passed, but there is still **no actual
NuHost-acknowledged save command** in the evidence corpus.

Do not add more purely synthetic owner-signing layers without new real
evidence. The next blocker is field-level client `/game/save`
transport semantics and proof of whether own-planet cargo transfers are
persisted as pre-applied client state. A consent-only browser schema
observer, `tools/client/planets_nu_save_schema_probe_v1.js`,
now permits inspection of names/types **without** recording raw
payloads, credentials or submitting new saves. Its output is not
order-authenticated. Next: one ordinary owner-authorized save, review
safe schema, then a bounded mapping and proper acknowledgement witness.
Handoff: [save-schema reconnaissance](handoff/2026-10-17-m2-save-schema-reconnaissance-v1.md).

**M2 owner-scoped pre-Host observation integration (CI/runtime pending):**
The preceding synthetic operator HMAC intake succeeded at runtime on
`53206e40e5da48c0f29cad16c5eae0de78e83766` (`exit_code=0`,
missing artifacts `[]`, 8/8 abstentions; report Git blob
`c59a24dca535feefa16408555bfb74b36fda2e62`).
Since the original intake required impossible cross-player capture by a
single owner, a new signed **per-owner** observation and strictly
complete aggregation interface is under test. Missing owner data remains
`ABSTAIN`, never an invented empty order. Operator signatures are not
authenticated `/game/save` acknowledgements or causal NuHost parity.
See [owner-scoped capture handoff](handoff/2026-10-17-m2-owner-scoped-prehost-capture-v1.md).
Next: authorized successful-save capture and real order-field mapping, not
more synthetic passes or unbounded historical residual fitting.

**M2 pre-Host capture admission V1 (implementation; runtime still pending):**
Research-only `planetary_order_capture.py` now supplies exact pre-state
fingerprinting, operator HMAC integrity, complete declared-player coverage,
external Host-start witness requirement and a fail-closed admission path into
the existing order-aware simulator. This is **operator attestation**, not
evidence that NuHost actually accepted the orders. No genuine real-game
submission captures or historical causal comparison have been acquired.
A bounded capture CLI tests this gate with synthetic data only, then
the next requirement is independently witnessed, authorized, genuinely
submitted pre-Host orders. See
[pre-Host capture V1 handoff](handoff/2026-10-17-m2-prehost-order-capture-v1.md).

**M2 October 17, 2026 — order-aware vertical slice runtime VERIFIED.**
PRs #208 and #209 have merged and main CI #1268 passed (1175 tests).
The server evidence `runtime-logs/planetary-order-aware-slice-v1/20261016T211423Z_894240fad1c4`
is clean with `exit_code=0`, all requested artifacts, both three-turn
hypothetical phase placements, 15 phase balances/turn and eight
fail-closed controls. Trace SHA256:
`327af515dc6b3f4bf4ea87764469640f4d60c1db47553d38fa494dbf42b40ef1`.
Source commit `894240fad1c42db2cba868de3ec228a72a19fc83`.
The integration is **TESTED on synthetic orders, NOT NuHost DIFF_VERIFIED**.
The historical corpus's mechanics projection provides snapshots but no
independently authenticated `PlanetCargoTransferOrder` submission record:
`TurnOrders.empty()` does not establish the absence of actual player orders.
**Next:** acquire independent pre-Host order captures and implement a
provenance/coverage gate before any order-aware archival comparison; otherwise
ABSTAIN. No return to per-residual historical fitting or C5.
Handoff: [server-verified order-aware M2](handoff/2026-10-17-m2-order-aware-runtime-verified.md).

**M2 update — October 16, 2026: historical triangulation complete; implementation next.**
The complete three-report `planetary-evidence-triangulation-v1` runtime
was independently verified on `runtime-logs`, with source
`ab80e84d4c23ca4190f1a73c5d071e65cc8aa5e5`,
`exit_code=0` and all artifacts published. Across 617 qualified
historical T−1/T planet observations, 215 match all four conditional
stock families; 592 have unchanged-vs-model exact underground mineral
stocks. These are observational NET-stock comparisons, **not causal
confirmation** of taxation, mining, growth or any player order.

**Next deliverable:** integrate existing `PlanetCargoTransferPhase` and
`PlanetaryHostPipeline` into a testable explicit-order, multi-turn
research simulation slice. Reuse existing `TurnOrders`; test
conservation, phase interactions and fail-closed support boundaries.
Do not spend further runs hunting single historical stock residuals.
Handoff: [verified M2 runtime and next implementation](handoff/2026-10-16-m2-triangulation-runtime-verified-next-implementation.md).
Keep C5 frozen, public corpus CURRENT unchanged, PR #28 draft,
and production `planets-intel` untouched.

**October 16, 2026 priority reset — C5 bounded freeze / M2 active.**
After the V27 archival Chunnel/visibility retrospective, further serial
C5 short-Chunnel and Horwasp residue chasing is PAUSED. The previously
verified ordinary non-capture queue remains bounded at 22/22 held-out
next-VCR comparisons, but complete Host queue, capture O-branch LEFT/RIGHT,
unresolved site arrivals and mixed ship/planet combat remain open and
fail closed. No new universal Host activation rule is promoted.

**Active implementation work is now M2 planetary economy/production
integration and independent historical validation.** Reuse the already
implemented `PlanetaryHostPipeline` instead of restarting formula research.
First operational checkpoint:
`docs/handoff/2026-10-16-c5-bounded-freeze-m2-active.md`
and the 3-turn deterministic `planetary_multiturn_baseline_v1`
runner. That internal baseline has **zero NuHost historical differential
claims**; the next M2 acceptance must explicitly evaluate real
owner-current T-1/T planet snapshots and abstain on unattributable Host
and player-order interactions.

Historical corpus infrastructure **M5** remains available as the
research data foundation, not a reason to block M2 while explaining
individual Chunnel episodes. Production `planets-intel`, main combat
executor, immutable corpus CURRENT, and draft PR #28 remain untouched.


**October 14, 2026 scope decision:** temporarily park Horwasp-specific
postcombat mass, clan losses, fighter-feedback activation and VCR-order
micro-investigations. The evidence is retained as unresolved, not promoted.
Resume the broader ordinary **non-Horwasp C5 Host combat queue** integration,
prioritizing capture/parent-queue continuation and genuinely held-out next-VCR
selection before returning to exotic combat physics. Keep the existing
`combat-planar-no-horwasp` FeatureScope rather than adding ad hoc
per-example exclusions. Full handoff:
[`2026-10-14-horwasp-park-c5-restart.md`](handoff/2026-10-14-horwasp-park-c5-restart.md).

Movement, including the base finite-fuel Tow mass/proration rule, Classic pairwise replay, ordinary ship battle-sequence carry-over, and the attributable ordinary repeated-planet persistence layer now have explicit subsystem checkpoints.

The immediate combat work is the missing **Host combat phase around the resolver**:

- engagement eligibility;
- battle ordering / queues;
- side assignment;
- Priority Intercept / Primary Enemy / mission interaction;
- diplomacy / Safe Passage / alliance effects;
- capture continuation;
- planet/base participation in the full multi-player queue;
- the documented ship-to-planet phase boundary, including between-phase repair.

Do not reopen bounded movement, ordinary ship-sequence, or plain-planet sequence residual hunting unless a contradiction blocks a larger Host subsystem. The base finite-fuel Tow movement rule is closed; Tow contests/chains/cycles and mine/web/Chunnel/storm interaction ordering remain separately scoped and fail closed where unresolved.

The external-tool survey creates a bounded supporting backlog alongside the
combat-order work, without replacing it:

- compare Kecupo VCR Sim and nu-replayer against the existing combat resolver to
  identify concrete disagreements worth historical discrimination;
- mine immutable archive messages using nuWebBounty/nuSweepFC signatures for
  Crystal Web and Safe Passage/mine-scan evidence;
- use c2nu/PMS as parser/API shape cross-checks;
- use T-Continuum Analyser only to discover candidate public games that fill
  explicit Feature Index gaps, then ingest through official Planets.nu sources.

These are opportunistic evidence accelerators, not a new top-level milestone.

The 2026-09-28 engine-core search identified c2ng as the strongest currently
available independent rules implementation and JHOST/JPHost as a high-priority
server-side PHost-derived source-recovery target. These remain REFERENCE ONLY:
use them to enumerate candidate rules and discriminators, never to promote NuHost
mechanics without the normal documentation/corpus/test/differential chain.

## Planning progress snapshot — 2026-09-11

These are approximate planning estimates, **not evidence labels** and not substitutes for differential validation:

- ordinary/Classic movement core: roughly **90%** reconstructed at the rule level; remaining work is dominated by bounded interactions and special/campaign mechanics rather than basic movement geometry/fuel;
- Classic pairwise combat plus ordinary survivor/planet persistence: roughly **75–80%** of the low-level combat state-transition layer; the pairwise resolver is strong, but Host still has to decide who fights whom, in what order, and on which side;
- full Host combat engagement/order layer: roughly **30–35%**; factual VCR replay is mature, predictive queue generation is not yet reconstructed end-to-end;
- overall reverse-engineering understanding of the ordinary Classic core: roughly **60–65%**;
- overall high-fidelity end-to-end Host surface needed before serious self-play: roughly **45–50%**.

The apparent gap between the last two numbers is intentional: several mechanics are understood in isolation but are not yet integrated into a complete Host-order prediction pipeline. Large breadth items still remain after combat ordering: planetary production, complete minefield lifecycle, general missions and special abilities, diplomacy, race-specific rules, observer/visibility semantics and complete-turn differential validation.

## Runtime-verified movement accounting

The recorded compiled-layer counters remain the latest L1/L2 rebuild checkpoint. A later bounded server gate at candidate `f68a31376ff41810d72df0f3fadc165ff55e1017` validated the continuous nominal one-turn fuel basis against the existing 12-game historical corpus without rebuilding L1/L2.

The planner candidate introduced by `993e76046c3ffaa40acf4b0aa7286d5bd9573480` is now scoped:

```text
Move Most + Intercept true-partial normal movement
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Key gate results:

```text
pytest                                      371 passed
Move Most true partial rows                  15560
Move Most differing cost basis                2927
Move Most discriminators                         1
nominal-support discriminators                    1
projected-support discriminators                  0
Intercept fuel-limited support             1 -> 2
Intercept contradictions                   1 -> 1
missing archives                                0
```

The independent discriminators are `360690/T164/ship41` (Move Most) and `620694/T73/ship278` (Intercept). Targeted confounder checks found no already-modelled mine/storm/damage/Tow/Chunnel explanation for the supporting cases.

The separate finite-fuel Tow chain is now also closed for its base movement rule. Runtime candidate `bc3b767330dc23ed09303eed766365fa53877209` produced one cleaned discriminator at `360690/T41`:

```text
pre-Alchemy combined exact       0
post-Alchemy combined exact      1
post-Alchemy tower-only exact    0
Alchemy mass-basis discriminator 1
combined-mass discriminator      1
```

The factual endpoint `(2183,2688)` is reproduced only by post-Alchemy combined tower+towed mass (`2163 KT`) with `124/131` proportional insufficient-fuel movement. Official Nu documentation independently specifies towed-mass inclusion, post-Alchemy movement-mass evaluation and proportional insufficient-fuel distance. Scoped status:

```text
base finite-fuel Tow movement
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

This does not promote unresolved Tow topology or external interaction ordering. Snapshot fuel remains pre-Host evidence and is not automatically movement-phase fuel outside attributable cases. A later `planets-intel` transfer must preserve those boundaries.

```text
move_most_candidates              227468
baseline_explained                209574
baseline_unresolved                17894
external_context_explained         13970
post_external_residual              3924
chunnel_explained                   1421
post_chunnel_residual               2503
horwasp_strong_explained             240
post_horwasp_strong_residual        2263
mine_strong_explained                 60
post_mine_strong_residual           2203
fuel_proration_explained               6
post_fuel_proration_residual        2197
label_issues                           0
```

Current movement schemas:

```text
prepared cache:            planets-lab.prepared-game-cache.v1
L1 movement:               planets-lab.compiled-movement.v3
L1 context semantics:      planets-lab.compiled-movement-storm-context.v3
L2 context labels:         planets-lab.compiled-movement-context-labels.v6
```

## Verified movement closures

- ordinary movement / Host major-minor geometry;
- warp-well ordering — `TESTED + DIFF_VERIFIED`;
- route-equivalent owner-visible Tow — `TESTED + DIFF_VERIFIED`;
- base finite-fuel Tow post-Alchemy combined-mass proportional movement — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- route-equivalent Chunnel multiplicity — `TESTED + DIFF_VERIFIED`;
- classic/cloudy ion storms — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- scoped effective sphere topology for game `591478` — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict mine/web interruption v5 — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict damage-limited maximum warp — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- strict Nu waypoint-distance fuel proration v6 — `DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- continuous nominal one-turn fuel basis for true-partial Move Most / Intercept — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`;
- short-waypoint normal-mine scaled-floor exact classifier — `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`; the low-tech slowdown itself is `DOCUMENTED`;
- Red Mite tracking/fallback — research closed absent new evidence.

Current generic movement residual landscape:

```text
final_residual_rows       2197
closed_mite_rows           786
known_horwasp_hull_rows   1457
generic_rows               740
generic_games               12
generic_hulls               75
```

Largest coarse family:

```text
113  warp7-9 <0.5x observed=other same_line_forward
```

Largest detailed member:

```text
89  warp7-9 reachable_other <0.5x observed=other same_line_forward non-gravitonic
```

These remain bounded evidence-mining targets, not a requirement to reach zero residuals before continuing the simulator.

## Combat integration checkpoint

### C1 — Classic resolver extraction

Completed:

- imported the deterministic Classic VCR resolver into `rules/combat`;
- preserved c2ng/PCC2 BSD attribution;
- kept dashboard DB/API/UI dependencies out of the canonical mechanics layer;
- added independent unit tests.

### C2 — Nu adapter and historical replay coverage

Current historical corpus:

```text
archives                   12
raw_vcr_observations     22256
unique_vcrs               6469
replay_supported          6469
replay_unsupported           0
payload_conflicts            0
replay_result_conflicts      0
malformed_members            0
```

Battle-shape population from C2:

```text
ship_vs_planet  3719
ship_vs_ship    2750
```

Raw `combatrng` is available in factual RST for all processed turn members; no inferred settings manifest is needed.

C2 evidence status:

```text
CORPUS_OBSERVED + TESTED
```

C2 alone is replay coverage, not an independent terminal-state proof.

### C3 — ordinary ship battle sequences

C3 compares deterministic terminal state from factual VCR N against factual start state in the next same-turn/same-location appearance of the same ship.

Final corpus sanity:

```text
raw_vcr_observations      22256
unique_vcrs                6469
replay_supported           6469
ship_appearances           9219
candidate_ship_turn_chains 1015
same_location_transitions  1485
metadata_conflicts            0
```

Phase distribution:

```text
ship_vs_ship -> ship_vs_ship      938
ship_vs_ship -> ship_vs_planet    544
ship_vs_planet -> ship_vs_planet    3
```

Strong ordinary same-phase survivor oracle:

```text
ship_vs_ship -> ship_vs_ship
transitions  764
match        764
mismatch       0
```

Per-field:

```text
damage      764 / 764 exact
crew        764 / 764 exact
torpedoes   764 / 764 exact
fighters    764 / 764 exact
shield      764 / 764 exact-carry or scoped Federation recovery
```

Strongest globally adjacent subset:

```text
VCR gap = 1
transitions  751
match        751
mismatch       0
```

This promotes ordinary Classic ship battle sequence carry-over to:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

### Federation recovery closure

Historical race-1 chains reject the imported `25% of missing shields` interpretation. The current corpus supports:

```text
next_shield = min(100 - damage, shield + 25)
```

Across 48 race-1 transitions:

```text
exact/both             28
federation_candidate   20
shield mismatch          0
```

Scoped evidence status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

### Exact-zero shield crew correction

C3 exposed a port mismatch against upstream c2ng `HostAlgorithm::hit()`: a hit that takes positive shields exactly to zero does not apply crew damage on that same hit. Correcting Nu replay ordering removed all 20 crew-only mismatches from the strict ordinary ship-to-ship survivor subset.

### Capture and special-game boundary

Across the full C3 chain population:

```text
terminal survived    1431
terminal captured      25
terminal destroyed     29
```

All 25 captured reappearances change owner. True `destroyed -> reappeared` transitions are confined to special/campaign/Horwasp-heavy game `591478`, so they are not generalized into ordinary Classic carry-over.

### Ship-to-planet phase boundary

Ordinary `ship_vs_ship -> ship_vs_planet` transitions retain eight damage-only mismatches after C3 cleanup:

```text
transitions                  397
match                        374
reappearance_after_capture    15
mismatch                       8
problem signature         damage
```

This boundary has a separate Host repair step and is not a strict same-phase carry oracle. Do not patch the Classic pairwise resolver to force these rows closed.

### C4 — ordinary planet/starbase battle sequences

C4 compares replay terminal planet/base state from factual VCR N against the factual start state of the same planet in VCR N+1.

Corpus population:

```text
raw_vcr_observations               22256
unique_vcrs                         6469
replay_supported                    6469
planet_appearances                  3719
candidate_same_turn_planet_chains    110
same_location_transitions            136
```

Ordinary population excluding game `591478`:

```text
transitions             103
match                   102
not_comparable            1
mismatch                  0
starbase                  92
no_starbase               11
shield carry match       103 / 103
```

#### Plain-planet exact carry

For factual `hasstarbase=false`, C4 infers candidate persistent DP as:

```text
planet_defense = combat_mass - 100
```

The inferred state must reproduce the factual first VCR before it is accepted into the carry oracle.

Final ordinary no-starbase result after correcting native planet beam-tech rounding:

```text
transitions                      11
exact next-state match           10
start reconstruction mismatch     1
next-state mismatch               0
shield carry match               11 / 11
```

The ten comparable rows reproduce the entire next factual combatant. Supported carry includes proportional DP damage, generated planetary fighter losses reducing DP, drained shield persistence and re-derived combat state.

Evidence status for the supported ordinary plain-planet path:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

The sole remaining non-comparable ordinary row has zero active beams and differs only in inactive `beamid` metadata (`0` vs `1`); it is not promoted as a combat mismatch and the strict audit is left unchanged.

#### Native planet beam tech

The first C4 gate showed six ordinary rows whose only mismatch was factual `beamid = imported_value + 1`. The corpus supports nearest-integer native beam tech:

```text
ROUND(SQRT(DP / 2))
```

with tech clamped to the supported 1..10 range for positive DP. Threshold regressions are covered by tests.

#### Starbase shield persistence

All ordinary repeated starbase defenders preserve terminal shield into the next factual VCR:

```text
92 / 92 exact
```

Evidence status:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

This does **not** promote hidden post-hull-damage starbase defense state.

#### Starbase fail-closed boundary

A surviving starbase with non-zero planet hull damage remains fail-closed because factual VCR state does not uniquely expose the resulting persistent:

```text
starbase defense
starbase beam tech
starbase accumulated damage
```

The zero-hull-damage starbase carry helper is `TESTED`; the hidden damaged-base branch remains unresolved.

#### Special game 591478

Game `591478` remains separated from ordinary promotion:

```text
transitions                    33
match                          17
not_comparable                  9
mismatch                        4
reappearance_after_defeat       3
shield match                   28
shield mismatch                 2
```

Do not generalize these special/campaign/Horwasp residuals into ordinary Classic planet rules.

## Corpus feature index and historical-game selector — v1 implemented

The M5 corpus now has a deterministic Game / Host Feature Index:

```text
schema: planets-lab.game-feature-index.v1
storage: normalized typed Parquet + DuckDB view game_features
```

Sources remain factual and attributable: tracked `/game/loadinfo` manifests,
immutable `/game/loadall` archives and compatible existing compiled metadata.
Third-party analyzers are discovery/UX references only.

The index preserves strict unknown semantics and per-feature provenance. Current
12-game manifest settings include factual Sphere/topology, Production Queue,
PLS/ship-limit values, combat RNG, Cloak+Intercept, campaign/diplomacy switches,
cloning and relevant race/special flags.

The settings-strict named selector `ordinary-classic` currently selects:

```text
360690
511506
620694
```

It excludes Standard-style, custom/campaign, Sphere and Horwasp populations by
explicit factual predicates and reports every mismatch/UNKNOWN predicate.

One existing diagnostic, Classic combat corpus parity, now accepts optional
feature-index preselection. `all-indexed` is an integration control and must
produce identical evidence-bearing output to the baseline.

Tracked gate:

```bash
bash tools/run-corpus-feature-index-gate.sh
```

The index remains selection infrastructure, not a new evidence label or mechanic
observation.

Detailed state:
`docs/handoff/2026-09-21-corpus-feature-index-v1.md`.

Archive-enriched v1 gate is now runtime-verified on all 12 immutable cached games:

```text
rows=1152
known=1116
unknown=36
deterministic rebuild exact
ordinary-classic=360690,511506,620694
combat parity integration exact=true
```

Runtime:
`docs/handoff/2026-09-21-corpus-feature-index-v1-runtime.md`.


Feature Index is now also being integrated into mechanics diagnostics. A separate
`combat-planar-no-horwasp` profile preserves the historical 11-game C3/C4
scope without hardcoding a special game id. Planet-chain, ship-chain phase and
ship-chain cluster diagnostics now use selector-backed selected/excluded/UNKNOWN
partitions.

Archive continuity gate is now verified exactly:

```text
selector partition shared            true
C3 checkpoint preserved              true
C4 checkpoint preserved              true
cluster partition preserved          true
failures                              []
```

Durable runtime:
`docs/handoff/2026-09-21-combat-feature-scope-selector-runtime.md`.

Combat diagnostics now share `src/planets_lab/corpus/feature_scope.py`; the
selector contract explicitly separates selected, known-excluded and UNKNOWN
games. The continuity gate checks those partitions for overlap in addition to
the historical C3/C4 counters.

## Immediate next work — Host combat phase

Current transition handoff:

`docs/handoff/2026-09-21-new-chat-combat-engagement-order.md`

The first bounded action in the next session is the final archive-host rerun of
`tools/run-combat-feature-scope-gate.sh` against actual GitHub `main`. If the
shared `FeatureScope` path preserves the previously accepted C3/C4 populations
and disjoint selector partitions, close selector plumbing and return immediately
to substantive Host engagement/order reconstruction.

Proceed in this order:

1. reconstruct full factual combat queues by turn/location from ordered VCRs;
2. determine engagement eligibility and opponent selection for ordinary Classic cases;
3. reconstruct side assignment / left-right rules separately from pairwise resolution;
4. integrate Priority Intercept / Primary Enemy / mission semantics only where IDs and behavior are established;
5. incorporate diplomacy, Safe Passage and alliance/team effects;
6. model capture continuation in the same Host phase rather than as a pairwise resolver property;
7. place the documented ship-to-planet repair boundary between ship and planet combat phases;
8. integrate planet/base participation using the C4 persistence layer while keeping hidden damaged-starbase state fail-closed;
9. keep game `591478` and other special/campaign mechanics separately labeled until attributable.

The next goal is not merely to replay an already supplied VCR. It is to predict the **set, order and sides of VCRs Host will generate** from the factual co-located game state.

## Host reconstruction order after combat sequence checkpoints

Proceed in this order unless evidence forces a dependency change:

1. **Movement checkpoint** — substantially reconstructed, including the base finite-fuel Tow mass/proration rule; reopen only for bounded contradictions/interactions.
2. **Classic pairwise combat C1/C2** — extracted and complete for current replay corpus.
3. **Ordinary ship battle sequences C3** — `DIFF_VERIFIED` on clean same-phase historical chains.
4. **Planet/starbase sequences C4** — attributable ordinary plain-planet carry and starbase shield persistence checkpointed; hidden damaged-starbase state remains fail-closed.
5. **Full Host combat ordering / engagement selection** — current immediate focus: eligibility, queues, side assignment, PE/mission/diplomacy and capture continuation.
6. **Planet economy + starbases + ship production**.
7. **Minefield lifecycle** — laying, decay, sweep, web drain, visibility, diplomacy/FC interactions and ordering.
8. **General missions + special ship abilities**.
9. **Diplomacy / Safe Passage / alliance / team semantics across all subsystems**.
10. **Race-specific mechanics**, integrated vertically rather than as an isolated final pass.
11. **Observer / visibility / fog-of-war / shared intel** for player-safe agent input.
12. **End-to-end Host-order differential validation** over complete turns.
13. **Training environment and AI** — historical baselines first, then simulator/self-play once the required Host surface is sufficiently complete.

The target remains a high-fidelity NuHost-compatible simulator suitable for real-game evaluation and later self-play. Do not shortcut unresolved Host rules merely to begin training sooner.

## Wider milestones

- **M0 deterministic skeleton:** substantially complete.
- **M1 minimal sandbox:** largely implemented.
- **M2 economy/planetary Host:** in progress.
- **M3 warfare:** materially advanced: ordinary movement including base finite-fuel Tow, Classic pairwise replay, ordinary ship sequences and attributable ordinary repeated-planet persistence are canonical in `planets-lab`; full Host engagement ordering remains open.
- **M4 race mechanics:** partial; Federation shield recovery has scoped differential evidence.
- **M5A historical corpus:** active and operational; deterministic Game / Host Feature Index v1 is implemented for bounded corpus selection.
- **M5B Nu compatibility matrix:** active; movement, base finite-fuel Tow and ordinary Classic combat sequence checkpoints are explicit.
- **M6 training/AI:** later, after required simulation/observer surfaces are sufficiently faithful.


### Active combat gate: selector-backed predictive ship queue

Current integration restores the previously validated C5 canonical primitives
for engagement/order, initial STANDARD selection, occurrence-aware side
assignment, mutable survivor/capture state and post-mutation selection.

The immediate runtime gate is now one command:

```bash
bash tools/run-combat-predictive-queue-gate.sh
```

It must first preserve the shared FeatureScope C3/C4 checkpoints, then reproduce
the historical held-out ordinary queue population with zero next-VCR mismatches.
Do not advance to broader complete-site or mixed planet ownership mechanics if
that gate is not exact.


### Predictive ordinary ship queue — runtime closed

Archive-host runtime at `21435cd15c9744e00d958e0e271b9b8a8fd483ad`
passed the combined shared-scope + held-out queue gate.

For both strict and conditional exact-set profiles:

```text
23 multi-VCR sites
16 exact sites
7 capture-predecessor exclusions
22 compared transitions
22 exact
0 mismatch
```

Shared FeatureScope continuity remained exact with no failures.

Status for the bounded non-capture ordinary plain-STANDARD predictive queue:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

Durable runtime:
`docs/handoff/2026-09-22-combat-predictive-queue-runtime.md`.

The immediate residual is post-capture candidate-graph reconstruction after
owner/race transfer; do not reopen the already exact non-capture queue path.


### Active capture residual — LEFT/RIGHT only

The capture path has advanced beyond the earlier reintegration checkpoint.

Closed observed ship-capture layers now include:

```text
capture continuation identity/state       closed
special Tow/Intercept geometry             2 / 2 exact
post-capture candidate graph               8 / 8 exact
post-capture active membership             8 / 8 exact
post-capture pair eligibility/phase        8 / 8 resolved
pair phase                                 8 / 8 STANDARD
captured-FC phase sensitivity              8 / 8 invariant
```

The remaining bounded ship-to-ship capture blocker is post-capture
**LEFT/RIGHT side assignment**. Current independent controls are not universal:

```text
opponent_initiator_right                   7 / 8 exact
neutral captured orders + fresh FC         6 / 8 exact
sticky capture side                        4 / 8 exact
frozen T-1 priority                        4 / 8 exact
neutral orders + preserved FC              4 / 8 exact
```

Do not promote a side rule from the current eight observations. The next primary
mechanics action is to enlarge the independent public archive population, harvest
additional attributable ship-capture continuations, split them into discovery
and held-out validation subsets, and only then freeze/test a side rule.

Current checkpoints:

`docs/handoff/2026-09-28-main-combat-corpus-checkpoint.md`

`docs/handoff/2026-09-28-main-public-corpus-backfill-round1-runtime.md`.

The second canonical automatic backfill runtime increased the compatible public
corpus to 32 / 36 indexed games. Four newly selected replacements remain
legacy/binary `.trn` failures. The acquisition runner now performs bounded
multi-round backfill within one invocation, reusing the existing 159-game
loadinfo candidate pool and immutable archive cache until the target converges,
the candidate supply cannot restore it, or `MAX_BACKFILL_ROUNDS` is reached.
Do not rediscover the candidate pool.

Current corpus runtime:
`docs/handoff/2026-09-28-main-public-corpus-backfill-round2-runtime.md`.

Detailed capture runtime:
`docs/handoff/2026-09-24-combat-capture-runtime.md`.

### Public corpus ingest performance checkpoint

The 2026-09-29 storage/runtime benchmark rejected full extracted-archive caching
as a useful optimization: game 233558 improved only from 1:40.74 to 1:36.61 for
the read+JSON pass while requiring 8.91 GiB extracted from a 0.64 GiB ZIP.
The selected corpus would require about 123.95 GiB block-rounded.

The primary bottleneck was repeated derivation across backfill rounds. Ingest now
reuses compatible previous per-game index records for immutable cached archives,
and the archive normalizer uses one CRC-checking member pass. Full rebuild
remains available with `--no-reuse-index`.

Checkpoint:
`docs/handoff/2026-09-29-public-corpus-ingest-benchmark.md`.

The first full-pipeline reuse validation completed six backfill rounds in 2m52s,
with all 35 successful games served from `index-cache`. Six replacement
archives were independently rejected as legacy/binary and the corpus remained
35 / 36. Since replacement failures are now cheap, the default bounded
`MAX_BACKFILL_ROUNDS` is 24 rather than 6; selection policy itself is
unchanged.

### Public validation corpus stabilized — 36 / 36

Canonical runtime
`runtime-logs/public-validation-corpus/20260929T150456Z_253258f5f870`
closed the acquisition gate on backfill round 15. Game `306971` supplied the
final compatible slot:

```text
games indexed        36 / 36
games failed          0
snapshots        126418
transitions      125862
settings hashes      36
```

Do not continue public-corpus backfill for the active C5 blocker. The immediate
next action is the deterministic **discovery-only** public capture-side harvest;
held-out rows remain sealed until a candidate LEFT/RIGHT rule is frozen.

Checkpoint:
`docs/handoff/2026-09-29-public-corpus-stabilized-runtime.md`.

### Public capture-side discovery: 50 ship continuations

Canonical runtime
`runtime-logs/public-capture-side-discovery/20260929T212837Z_745a7bbe4976`
scanned only the deterministic discovery partition: 20 games scanned, 16
held-out games unscanned.

The discovery population contains 61 post-capture continuations, including 50
ship→ship cases. Factual prize sides are LEFT 37 / RIGHT 13; 46 / 50 are first
occurrences of the prize/opponent pair. The generic opponent-initiator-right
control is only 37 / 50 and sticky capture side is only 22 / 50, so neither is
promoted.

The next discovery pass enriches those same cases with targeted T-1 order/FC
priority context and re-evaluates the earlier C5 priority controls. It reads only
the required owner-perspective T-1 members, not full prepared-game caches.
Held-out remains sealed.

Checkpoint:
`docs/handoff/2026-09-30-public-capture-side-discovery-runtime.md`.

## Corpus DB v1 infrastructure workstream

Branch feature/corpus-db-v1 owns a separate storage migration prototype.

The objective is to retain ZIP/TRN as immutable evidence while mirroring the
same player/perspective/entity semantics into a shared DuckDB generation stored
outside both research checkouts and readable concurrently by both normal and
external-reference containers.

The first gate is game-233558 only: direct mirror, no deltas or semantic dedup.
It must pass full member-level semantic parity and disk/runtime/RSS/concurrent
reader benchmarks before scaling to the 36-game public corpus.

See docs/corpus-db/ARCHITECTURE.md, SHARED_ACCESS.md, WORKSTREAM.md and
NEW_CHAT_START.md.



### Corpus DB v1 prototype implementation checkpoint — 2026-09-30

The dedicated `feature/corpus-db-v1` branch now contains the first direct
ZIP/TRN -> DuckDB implementation for the game-233558 gate. The importer is
member-streaming rather than whole-game snapshot based, preserves full source
semantics through lossless JSON fallback rows, records archive/member provenance,
and refuses publication unless archive integrity plus type-sensitive full-member
round-trip parity are green.

Shared storage is exposed through `PLANETS_CORPUS_DB_ROOT` mounted at
`/corpus-db`; the normal and external research containers use the same
immutable published generation read-only. Tracked runners also measure fresh-
process T-1/T and VCR/site query wall time/RSS and concurrent two-container
reads.

The corrected typed1 game-233558 runtime is now green end-to-end:
6710 / 6710 full semantic parity, native typed entity storage, 3.06 GB DuckDB
from 9.57 GB decoded JSON, bounded indexed queries, and simultaneous read-only
access from both research containers. This is a 74.23% reduction versus the
first 11.87 GB v1 physical layout and removes the per-entity JSON duplication
that caused the earlier regression.

The storage workstream has since advanced through typed1 and compact public36
to the ACTIVE compact public68 backend. Canonical active runtime:

```text
68 archives
169569 / 169569 exact semantic parity
17847300096-byte DuckDB (~16.622 GiB)
no entity_rows
no decoded member fallback blob
no secondary indexes
shared normal/external read PASS
```

The current storage optimization milestone is complete. The guarded CURRENT
switch has activated public68; retain compact public36 as the first rollback.
Further physical improvements are deferred in
`docs/corpus-db/FUTURE_OPTIMIZATIONS.md`; do not spend mechanics time on
additional compression unless a documented reopen criterion is met.

Canonical runtime:
`docs/handoff/2026-10-02-corpus-db-compact-public36-runtime.md`.


### Compact CURRENT activation completed — public68 active 2026-10-04

The accepted combined compact public68 generation is now active through
`CURRENT`:

```text
corpus-v2compact-public68-20261004T095236Z-09f71721b77c
169569 / 169569 exact parity
shared normal/external read PASS
```

The previous compact public36 generation remains available as the first
rollback. The corpus DB storage milestone is closed; resume NuHost mechanics on
the new independent population. Deferred storage ideas remain in
`docs/corpus-db/FUTURE_OPTIMIZATIONS.md`.

Activation checkpoint:
`docs/handoff/2026-10-04-corpus-db-public68-current-activation.md`.

## Public capture side held-out result

The pre-heldout capture-side candidate was frozen at
`cd87f9505472e5e396db28a7d6f7c67c561f9c64` and independently tested against
the sealed public held-out partition.

Result: **FAILED** — 27/29 exact, 1 mismatch, 1 unresolved.

The mismatch is game 476380 turn 223: a reachable captured-LEFT prize flips to
RIGHT. The unresolved row is a same-turn repeated-capture chain in game 257776
turn 230, where the intermediate owner has no valid T-1 source state; mutable
post-capture order state must be carried from the prior capture.

Do not change the old frozen rule and call the gate passed. Any replacement
candidate is held-out-informed and requires a new independent evidence
population before promotion.

See
`docs/handoff/2026-10-03-public-capture-side-heldout-result.md`.

## Post-heldout capture-side candidate

The frozen pre-heldout capture-side rule failed independently at 27/29 exact
with one real mismatch and one repeated-capture unresolved row.

After opening the former held-out population, a new research-only candidate
fits all 60 adjacent rows:

```text
reachable sticky                    20/20
nonreachable neutral/fresh-FC       38/38
second-occurrence reversal           1/1
reachable numeric-opponent override  1/1
                                     -----
                                     60/60
```

This is not validation. The new numeric-opponent and repeated-capture branches
are heldout-informed. Canonical promotion now requires a new independent
population, preferably prospective private game 686764 and/or public games not
present in public36.

See:

`docs/handoff/2026-10-03-postheldout-capture-side-candidate.md`.

### Public68 independent capture-side validation — failed candidate

The frozen post-heldout candidate was independently tested against the new
short32 population after public68 activation.

Independent gate:

```text
short32 games                         32
overlap with public36                  0
adjacent capture continuations        22
candidate exact                       21
candidate mismatch                     1
candidate unresolved                   0

reachable sticky                       9
nonreachable neutral/fresh-FC          6
second-occurrence reversal             1
reachable numeric-opponent override    6

status                       FAILED_MISMATCH
promotion_ready                        false
```

The counterexample is game `341336`, turn `75`, VCR `338 -> 339`:
captured ship `211` remains LEFT against ship `369`, despite opponent
numeric priority `[0, 4, 369]`. The opponent has mission `3` (Kill).

The previous numeric-group-0 override is therefore rejected as universal.

After opening short32, a Kill-sensitive research candidate fits the combined
82 / 82 adjacent rows: reachable numeric group-0 opponents preserve LEFT when
the opponent is Kill, while the two observed numeric LEFT -> RIGHT flips are
non-Kill mission-1 cases. This new candidate is post-independent-informed and
is explicitly NOT canonical.

Implementation:

`tools/diagnostics/combat_public_capture_side_postindependent_candidate.py`

Checkpoint:

`docs/handoff/2026-10-05-public68-capture-side-independent-result.md`.

### Prospective post-independent validation corpus

The replacement Kill-sensitive capture-side candidate is frozen at
`46bcb08c2f0d3f0449b97921edb03ab6647f7d3b`.

The next validation population is a second independent public short corpus that
excludes all 68 games already open in public68. Acquisition is predeclared as:

```text
final turn         80..180
slots               8..16
loadinfo probes       320
selected games         32
baseline games         68
```

Runner:

`tools/run-public-postindependent-validation-acquisition-with-evidence.sh`

The future validation gate must not claim promotion merely from zero mismatches.
It requires fresh independent coverage of both changed numeric-LEFT
discriminators: group-0 Kill and group-0 non-Kill. Missing either yields
`INSUFFICIENT_DISCRIMINATOR_COVERAGE`.

The new games will be built into a separate exact-parity compact generation;
canonical public68 `CURRENT` remains unchanged during validation.

Handoff:

`docs/handoff/2026-10-05-postindependent-validation-acquisition-ready.md`.

### Public100 prospective capture-side validation — failed C proxy

The frozen Kill-sensitive post-independent candidate was tested against the
second fresh 32-game population using the explicit exact-parity public100
generation.

```text
fresh games                         32
adjacent capture rows               20
candidate exact                     19
candidate mismatch                   1
candidate unresolved                 0

fresh numeric Kill LEFT              1
fresh numeric non-Kill LEFT          1

status                  FAILED_MISMATCH
promotion_ready                   false
```

Both numeric Kill/non-Kill discriminators passed. The failure is instead the
first LEFT-oriented O-not-reachable row:

```text
game 597079 T19 VCR17 -> 18
captured ship14
capture LEFT
factual next side RIGHT
identity-anchored order [14, 172, 185]
prize < factual opponent < capture target
```

This demonstrates that the old
`O-not-reachable -> neutral orders + fresh symbolic FC` branch was a proxy.
All earlier such cases were RIGHT -> LEFT, so the proxy never saw the opposite
orientation.

Across the now-open 102 adjacent rows, the minimal structural replacement is:

```text
O reachable:
    retain the existing post-independent O-side rules

O not reachable / capture-created C order:
    prize side = opposite(capture side)
```

The C-order side flip fits 58 / 58 open C rows:

```text
RIGHT -> LEFT  57
LEFT  -> RIGHT  1
```

The complete post-prospective bounded candidate fits 102 / 102 open adjacent
rows but is explicitly NOT canonical because public100 prospective evidence
informed the replacement rule.

Implementation:

`tools/diagnostics/combat_public_capture_side_postprospective_candidate.py`

Checkpoint:

`docs/handoff/2026-10-05-public100-capture-side-prospective-result.md`

Next validation should be controlled rather than another broad random public
corpus. Private game `686764` is the preferred prospective oracle: force a
LEFT capture followed by a C-forward continuation, freeze the candidate first,
and validate the predicted RIGHT side. Private/live data must remain separate
from immutable public100.

Immediate mechanics priority is new prospective/independent discrimination of
numeric group-0 Kill versus non-Kill post-capture side behavior. Do not reuse
public68/short32 as validation for the new candidate.

