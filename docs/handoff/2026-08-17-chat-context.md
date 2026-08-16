# Full chat handoff — movement validation, compiled corpus and Horwasp Mite research

Date: 2026-08-17

Repository: `Numillyash/planets-lab`

This document is a durable handoff of the long working session that led from ordinary movement validation and warp-well handling to the current Horwasp Red Mite tracking investigation. It is intentionally detailed so a new chat can continue without reconstructing the reasoning from old messages.

## 1. Project purpose

`planets-lab` is the deterministic Planets.nu simulator and AI/ML research environment. The long-term goals are:

- one canonical game-state representation;
- deterministic and testable Host mechanics;
- rule/specification and differential-validation tooling;
- historical Planets.nu corpora;
- player-limited observations / fog of war;
- scripted bots, self-play and ML/RL experiments.

The current work is not merely “make the simulator move ships”. The practical objective is to infer and validate enough real Host behavior from historical games that the environment can later generate trustworthy data and support agent training.

## 2. Source-of-truth hierarchy

Use these layers in this order:

1. **GitHub `main`** is the source of truth for code and durable documentation.
2. **Raw historical `/loadall` ZIP archives** are the immutable evidence source for game data.
3. Prepared caches, Parquet, DuckDB and derived labels are deterministic local derivatives and may always be rebuilt.
4. Planets.nu documentation may motivate or support a hypothesis, but historical corpus evidence must remain distinguishable from documented rules and from inference.
5. Never silently turn a correlation into a simulator rule. Preserve “observed”, “strongly explained”, “weak evidence” and “hypothesis” as different categories.

Current raw archive location:

```text
validation/corpus/cache/loadall/game-<id>.zip
```

Current prepared cache:

```text
validation/corpus/cache/prepared-v1/game-<id>.pickle
```

Current compiled corpus:

```text
validation/corpus/compiled/v1/
```

See `docs/COMPILED_CORPUS.md` for the formal layer contract.

## 3. Machines and workflow

### Remote server

Historically most work ran on the remote Linux server:

```text
/opt/planets-lab
```

The server is much weaker than the desktop machine. It remains useful for canonical deployment/sync and smaller checks, but corpus compilation, large differential runs and future ML work should preferentially run on the local PC.

### Local PC / WSL2

Current heavy-work machine:

```text
host: GEORGUL-GAMER
WSL2: Ubuntu 22.04.5 LTS
repo: ~/projects/planets-lab
CPU visible to WSL/Docker: 16
RAM visible to WSL/Docker: ~31 GiB
swap: 8 GiB
Docker Desktop + Docker Compose
```

GitHub SSH access is configured in WSL. Do not copy or expose SSH key material in docs/chat.

The 12 raw loadall archives were copied from the server to the PC with `rsync`; total size was about 541.7 MiB.

### User workflow preferences that matter

- **GitHub is the source of truth.** If a diagnostic requires a substantial script, create it under `tools/diagnostics/` and push it. Do not paste a 300-line one-off script into chat unless explicitly requested.
- The user will normally `git pull` and run the committed diagnostic.
- Large commands should be given as **separate command blocks**. In this environment, a combined “pull/build/run everything” paste has repeatedly behaved badly: later commands may not execute after a long build.
- Heavy validation runs belong on the PC unless there is a concrete reason to use the server.
- When schema names are uncertain, inspect the real DuckDB schema instead of guessing field names.

## 4. Docker Desktop failure that already occurred

There was a misleading period where `docker compose run` appeared to hang randomly. Diagnosis showed:

```text
docker desktop status -> paused
```

From WSL, the Docker client could open `/var/run/docker.sock`, but daemon calls such as `docker info` and `docker ps` timed out. The `docker-desktop` WSL distro itself was alive.

Important conclusions:

- if Docker commands hang again, check Docker Desktop status in Windows first;
- a **paused Docker Desktop** can look like a code/container deadlock;
- resume/unpause Docker Desktop from the Windows side before debugging the repository;
- `docker desktop restart` from inside this WSL installation failed because `/opt/docker-desktop/bin/com.docker.backend` was not present there, so do not rely on that WSL command;
- a separate BuildKit/containerd snapshot inconsistency once produced `parent snapshot ... does not exist`; removing the local `planets-lab-lab:latest` image, pruning build cache and rebuilding with `--no-cache` recovered it.

## 5. Why the compiled corpus exists

Initial historical validation repeatedly re-read large ZIP archives and rebuilt Python object graphs. On the remote server, one full movement pipeline run over 12 games at `--jobs 1` took about 595 seconds.

On the local PC a cached `--jobs 4` run dropped wall time to about 122 seconds, but RAM rose to roughly 15 GiB. That was already much better, yet still wasteful for repeated mechanics research and obviously unsuitable as the inner loop for ML training.

The solution was a layered compiled corpus:

```text
L0 raw ZIP -> prepared-v1 cache -> L1 movement Parquet -> L2 context-label Parquet -> DuckDB views
```

The raw ZIP remains canonical evidence. DuckDB is primarily a catalog/query layer over Parquet, not a replacement truth store.

### Current 12-game movement accounting

The expected invariant counts are:

```text
move_most_candidates            227468
baseline_explained              207896
baseline_unresolved              19572
external_context_explained       11699
post_external_residual            7873

chunnel_explained                 1387
post_chunnel_residual              6486
horwasp_strong_explained            234
post_horwasp_strong_residual        6252
```

Current compiled catalog views include:

```text
games
movement_transitions
move_most
movement_residual
movement_context_labels
movement_labeled_residual
movement_post_chunnel_residual
movement_post_horwasp_strong_residual
```

The context-label layer deliberately remains separate from L1 movement rows.

### Useful build commands

Build/refresh L1:

```bash
docker compose run --rm -T --interactive=false lab \
  python -m planets_lab.corpus.compiled_movement_corpus_cli \
  validation/corpus/manifests/accounts-recent-finished.jsonl \
  --jobs 4 \
  --output-dir validation/corpus/compiled/v1
```

Build/refresh L2:

```bash
docker compose run --rm -T --interactive=false lab \
  python -u -m planets_lab.corpus.compiled_movement_labels_corpus_cli \
  validation/corpus/manifests/accounts-recent-finished.jsonl \
  --jobs 4 \
  --compiled-dir validation/corpus/compiled/v1
```

The initial full compile was expensive, but rebuilding/querying the derived corpus became fast enough for iterative research. A later 12-game label compile with four workers completed in about a minute; cached single-game operations are much faster.

## 6. Warp-well discovery and correction

A major early question was whether normal movement was being compared to exact planet coordinates even though ships can enter a planet’s gravitational/warp well and stop a few light-years from the planet.

The corpus investigation established that warp-well context is real and must be modeled. Historical audit over the 12-game corpus found:

```text
move_most_candidates             227468
warp_well_matches                 36162
valid_ordinary_planet_matches     36161
invalid_debris_planet_matches         1
disabled_warp_well_matches            0
unknown_context_matches               0
```

Game settings consistently exposed `nowarpwells=false` in the audited games. `debrisdisk` was also inspected so debris objects were not silently accepted as normal planet wells. Game `591478` contained debris-disk objects and supplied the one rejected invalid match.

Conclusion: **do not regress to exact planet-coordinate-only movement reasoning.** Warp-well eligibility is already a first-class historical context and is part of the current differential pipeline.

## 7. Movement residual narrowing before the Mite work

The baseline movement differential handled ordinary geometry, shorter movement, partial Host major/minor cases and warp wells. External context then explained known non-ordinary movement such as tow/gravitonic contexts. Chunnel labels were added separately.

After those stages the residual was 6,486 rows, then Horwasp strong ballistic context explained 234, leaving 6,252 strong residual rows.

The remaining hull distribution immediately showed a special concentration in Horwasp game `591478`. In particular:

```text
hull 213 Red Mite: 786 residual rows
```

All Red Mite residual rows were in game `591478`.

This led to the current Mite-specific investigation.

## 8. Game 591478 / Horwasp context

Relevant facts discovered from the historical payload:

```text
mapwidth  = 2150
mapheight = 2150
mapshape  = 1
sphere    = true
```

Relevant players included:

```text
player 3  -> Privateers
player 6  -> Horwasp
player 7  -> Empire
player 12 -> Fascists/Fury
```

Important hulls:

```text
202 Nest
203 Armoured Nest
204 Farm
205 Accelerator
206 Protofield
207 Duranium Rock
208 Tritanium Rock
209 Molybdenum Rock
210 Stinger
211 Dunghill
213 Red Mite
214 Blue Mite
215 Green Mite
```

Do not confuse entity ID `206` below with hull ID 206 (`Protofield`). The important target ship **ID 206** is a Deth Specula with hull ID **1033**.

## 9. What was learned about Red Mite raw state

Red Mites in this game expose a useful state machine through ordinary ship fields.

Typical active tracking state:

```text
mission = 7
mission1target = target ship id
podhullid = target ship id
```

After loss, several raw states appear. `podhullid` often retains the historic target after `mission1target` is cleared, so `podhullid` is useful history/evidence but must not be treated as the current lock by itself.

The final 786 Red Mite residual rows were mostly inactive/stale state, which is why simply reading `podhullid` as a live target initially failed.

The historical `history` field was inspected. Its beginning behaves like recent positional history, but it was not itself a sufficiently accurate next-step predictor. A naive previous-step direction predictor was only about 65.5% accurate.

## 10. Active Mite target-turn dataset

A cleaner dataset was built from transitions where a Red Mite is actively tracking a positive `mission1target` and the target identity remains comparable.

A representative aggregation produced:

```text
active transition rows: 1040
retained: 944
lost:      96
```

Grouping Mites by `(before turn, after turn, owner, target)` was important. The same target-turn cluster never mixed retained/lost Mites in the examined sample; outcomes were cluster-consistent. This suggests target/Host context, not random per-Mite behavior, dominates lock loss.

One later cluster view contained 694 target-turn clusters, with 62 all-lost and 632 all-retained.

## 11. Strong causes / decompositions already found

### 11.1 Cloak

Cloak is by far the strongest general target-state signal found so far.

One cluster analysis found:

```text
cloak_before=False  total 650  lost 19
cloak_before=True   total 39   lost 38
cloak_before=None   total 5    lost 5
```

There are timing subtleties and a small number of edge cases, but ordinary observed cloak clearly explains a large share of Mite lock loss.

### 11.2 Chunnel

Three target clusters were identified as Chunnel initiators, all lost. Those belong to the existing Chunnel context pipeline, not an unknown Mite mechanic.

### 11.3 Identity break / missing target / ID reuse

Some apparent losses are not a continuous same-ship target at all. The investigation classified:

- hull changes;
- target missing after the transition;
- ID reuse after a gap;
- same ID with changed owner/hull.

These must be filtered before attributing a new mechanic to Mite tracking.

## 12. Scanner-coverage hypothesis: useful but not a complete rule

A recurring hypothesis was that Mite tracking is retained only while the target remains within roughly 150 ly of some Horwasp scanner source.

Multiple audits were run with:

- all ships;
- non-Mite ships;
- pods excluded;
- planets only;
- combinations of sources;
- self-exclusion of the pursuing Mite;
- temporal before/after coverage.

Coverage does correlate with some `target_clear_pending` cases, but there are retained controls outside the tested coverage and losses while coverage remains present.

Example self-excluded transitions included both retained and pending cases when coverage changed `True -> False`.

Conclusion: **do not encode a simple “outside 150 ly => lose Mite target” rule.** Snapshot geometry also may not line up exactly with the Host phase that determines scan visibility.

## 13. Infection / `podcargo` hypothesis: rejected as direct lock-loss cause

The target field `podcargo` behaves like an infection-like counter in the examined game. It can rise from zero and then decay while damage increases.

However infection itself does not explain Mite target loss. One analysis found roughly:

```text
infected_before: 53 total, 51 retained
new_infection:    7 total, with retained and already-explained losses
```

The key target 206 becomes infected/damaged while its Mite target is still retained for that transition.

Conclusion: preserve infection as useful observed target state, but **do not use it as a direct Mite lock-loss reason**.

## 14. Planet / Horwasp-planet hypothesis: mostly rejected as a general rule

Several increasingly narrow planet hypotheses were tested:

- target inside a warp well;
- target exactly on a Horwasp planet;
- target leaves that planet;
- nearby Horwasp planet changes owner;
- the exact planet under the target changes owner;
- planetary combat/capture on the same Host.

There are many retained controls. In particular, target `522 VICTORIOUS` can participate in capture of a Horwasp planet and retain its Mite lock.

Therefore “planet captured”, “target leaves Horwasp planet”, or “nearby Horwasp planet changes owner” are not sufficient general causes.

These investigations were still valuable because they isolated target 206’s timing and ruled out a large false lead.

## 15. Case 206 — DETH SPECULA

This is one of the two central unresolved/near-resolved anomalies.

Entity:

```text
ship id:   206
owner:     12 (Fury/Fascists)
hull id:   1033
hull:      Deth Specula Armoured Frigate
cancloak:  true
```

Critical timeline:

```text
turn 64:
  ship 206 at (2329,2239)
  mission 6
  damage 0

turn 65:
  ship 206 at (2346,2283)
  mission 9
  iscloaked False
  damage 0
  Red Mite 1167 tracking waypoint is current

turn 66:
  ship 206 at (2334,2329), exactly planet 452
  mission 1
  iscloaked False
  damage 1
  podcargo 8
  Mite 1167 still has mission 7 / target 206,
  but its target waypoint has become stale (matches target position from two turns earlier)

turn 67:
  ship 206 back at (2346,2283)
  mission 2
  damage 2
  podcargo 7
  Mite 1167 performs full clear: mission 0 / target 0
```

At turn 66 planet 452 was Horwasp-owned. It was captured during 66->67, but raw VCR/message audit showed that another Fury ship (`VICTORIOUS #182`) performed the relevant planetary combat/capture, not Deth Specula 206. Ship 206 had no nonzero `transfer*` cargo amounts; `transfertargetid=452` was not evidence that 206 captured the planet.

The more important event is therefore **65->66**, when Mite tracking stops updating, not the visible full clear on 66->67.

### Current 206 hypothesis: transient cloak interrupted by damage

Observed facts:

- hull 1033 can cloak;
- turn 65 raw mission is 9 while end-of-turn `iscloaked=False`;
- on 65->66 damage increases `0 -> 1` and infection-like `podcargo 0 -> 8`;
- the Mite waypoint ceases to update and becomes strict stale;
- full clear follows one snapshot later.

A corpus query for “mission 9 while currently uncloaked, ends uncloaked, and new damage appears” found **only this case** in the inspected game.

Plausible but not yet proven causal narrative:

```text
cloak/order phase temporarily makes target untrackable
-> Mite waypoint stops receiving target updates
-> later Host damage/Protofield effect removes cloak before snapshot
-> snapshot shows target uncloaked but Mite tracking is already stale
-> next snapshot clears the Mite target
```

This is a **strong hypothesis**, not yet a simulator rule. Raw numeric `mission=9` has intentionally not been hard-coded in these diagnostics as “Cloak” without empirical/documented confirmation.

## 16. The stale-waypoint discovery

This is one of the strongest empirical discoveries of the whole session.

For each active Mite, its `(targetx,targety)` was compared to the target’s current and recent positions.

Topology-aware results in the main sample:

```text
current            total 932   retained 926   immediate 0   pending 6
no_match_0_4       total 18    retained 12    immediate 6   pending 0
strict_stale_1     total 7     retained 0     immediate 7
strict_stale_2     total 26    retained 0     immediate 26
strict_stale_3     total 14    retained 0     immediate 14
strict_stale_4     total 9     retained 0     immediate 9
```

Cluster-level results were similarly clean: all-strict-stale clusters were all immediate-loss.

The earlier onset audit found:

```text
current -> strict stale: 51 events, all leading to immediate_full_clear
from no_match -> stale:   5 events, all leading to immediate_full_clear
```

Interpretation:

- **stale waypoint is an observed internal tracking state / very strong predictor**;
- it is probably not the root cause itself;
- the causal event happens when the waypoint first stops updating;
- the visible `mission1target` clear can lag that event by a snapshot.

This insight moved the investigation one Host transition earlier for both 206 and 329.

### Topology check

Because game 591478 is spherical, raw coordinate equality was suspected of producing false stale states near the wrap boundary. The classifier was rewritten using the sphere-aware `_vector(..., topology)` distance.

Result: the important `current / no_match / strict_stale` classifications remained materially unchanged. The 329 anomaly below is therefore not merely a raw-coordinate wrap bug in the diagnostic.

## 17. Case 329 — RU30 GUNBOATS

This is the main remaining unexplained Mite case and the current focus.

Entity:

```text
ship id: 329
owner:   3 (Privateers)
hull id: 2071
name:    RU30 GUNBOATS
cancloak: false
```

Critical timeline:

```text
turn 54:
  target 329 = (3060,2201)
  Mite 1185 waypoint = (3060,2201)
  waypoint state = current

turn 55:
  target 329 = (941,2331)
  target raw mission = 7
  mission1target = -1096
  Mite waypoint = (3111,2331)
  topology-aware error is about 20 ly
  waypoint state = no_match_0_4
  Mite still retained

turn 56:
  target 329 = (915,2331)
  target mission = 8
  Mite waypoint = (3060,2201), matching target position two turns earlier
  waypoint state = strict_stale_2

turn 57:
  target 329 = (923,2345)
  target mission = 1
  Mite 1185 full-clears target
```

Unlike 206, target 329 cannot cloak, so transient cloak is not a credible explanation.

The jump from `(3060,2201)` to `(941,2331)` has a huge raw-coordinate displacement but a much smaller sphere-topology displacement, so sphere-wrap mechanics and interaction with another ship/order became the next candidate.

The negative `mission1target=-1096` is also unusual and its semantics must be inferred rather than guessed.

## 18. Current diagnostic scripts

Durable one-off research scripts are under:

```text
tools/diagnostics/
```

Current relevant files, in historical order:

```text
mite_exact_hw_planet_audit.py
mite_206_raw_event_schema_audit.py
mite_206_transfer_message_audit.py
mite_mission_tracking_lag_audit.py
mite_stale_waypoint_onset_audit.py
mite_transient_cloak_topology_audit.py
mite_206_cloak_329_intercept_audit.py
mite_329_wrap_tow_audit.py
```

The first seven generated the evidence summarized above. Do not recreate them in chat; inspect or modify the committed versions.

## 19. CURRENT HEAD AND IMMEDIATE NEXT STEP

At the moment this handoff was prepared, `main` was at:

```text
b7e0c9d add Mite 329 sphere-wrap and tow interaction audit
```

The parent is:

```text
850b639 add Mite 206 cloak timing and 329 intercept audit
```

The newest script is:

```text
tools/diagnostics/mite_329_wrap_tow_audit.py
```

It was created specifically to test the next 329 hypotheses. It does the following:

1. looks for **sphere-wrap-like target moves**: huge raw displacement but short topology-aware movement;
2. looks for candidate **mission-6 targeters** colocated with the target and checks whether they co-move to the same next position (tow-like evidence without blindly assigning a mission name);
3. cross-tabulates wrap/tow-like context with Mite current/no-match/stale/outcome;
4. audits all **negative `mission1target`** records, especially the `-1096` state around target 329;
5. examines target mission 8 while an active Mite tracks an uncloaked target;
6. prints focused state for entities around the 329 event, including IDs `329`, `446`, `311`, `1096`, `1102`, `1185`;
7. prints the Mite 1185 state chain for turns 53..57;
8. also includes a same-ship mission-9 replication check for target 206 so the two open branches remain comparable.

### Next command to run on the PC

Pull first:

```bash
cd ~/projects/planets-lab
git pull --ff-only origin main
```

Then run the current diagnostic as a separate command:

```bash
docker compose run --rm -T lab \
  python -u tools/diagnostics/mite_329_wrap_tow_audit.py \
  | tee /tmp/mite_329_wrap_tow_audit.log
```

The next assistant should analyze that output before inventing another hypothesis.

## 20. What not to repeat

The following directions have already been tested enough that a new chat should not restart from them without new evidence:

- exact planet coordinate instead of warp wells — already fixed/audited;
- “debris disk is just another warp-well planet” — false; eligibility matters;
- simple 150-ly scanner coverage as the universal Mite-loss rule — counterexamples exist;
- infection/`podcargo` as direct Mite-loss cause — counterexamples exist;
- Horwasp planet ownership change alone — many retained controls;
- planetary capture/combat alone — retained control exists;
- sphere raw-coordinate mismatch as the explanation for 329 stale state — topology-aware audit did not remove it;
- treating `podhullid` as the live Mite target — it persists as history after target clear;
- assuming numeric mission names without verifying them from corpus/docs.

## 21. Evidence discipline for future work

When adding a candidate rule, try to build a case/control table rather than presenting one anecdote.

Preferred labels:

- **observed fact**: directly present in historical raw/compiled data;
- **derived fact**: deterministic geometry/state relation computed from raw data;
- **strong explanation**: context is sufficient and has been validated against controls;
- **weak/observed-context explanation**: plausible same-transition match retained for evidence only;
- **hypothesis**: causal story not yet proven.

Do not use future information to label an earlier state unless the feature is explicitly retrospective and marked as such. The final AI environment eventually needs player-limited, temporally valid observations.

## 22. Useful DuckDB checks

Count the residual stages:

```bash
docker compose run --rm -T lab python - <<'PY'
import duckdb

con = duckdb.connect(
    "validation/corpus/compiled/v1/corpus.duckdb",
    read_only=True,
)

for view in (
    "movement_residual",
    "movement_context_labels",
    "movement_post_chunnel_residual",
    "movement_post_horwasp_strong_residual",
):
    print(view, con.execute(f"SELECT count(*) FROM {view}").fetchone()[0])

con.close()
PY
```

Expected current counts:

```text
movement_residual                        7873
movement_context_labels                  7873
movement_post_chunnel_residual           6486
movement_post_horwasp_strong_residual    6252
```

Top unresolved hulls after strong Horwasp labels historically began with:

```text
213  786
17   555
79   506
16   479
210  ~383
46   315
23   269
94   191
202  ~188
```

The exact non-Mite counts can shift slightly if label semantics are intentionally updated; preserve the documented invariants or explain why they changed.

## 23. Repo/history milestones from this session

Not every commit is listed, but these are useful landmarks:

```text
7653d87  persistent prepared corpus cache
71681e6  compiled movement corpus / DuckDB
 d524263 columnar I/O optimization
6e1564b  compiled movement context labels
adff04a  exact Horwasp planet Mite audit
e3a81d9  raw event schema audit for case 206
59a7ed1  transfer/system-message audit
8984b89  mission/tracking lag diagnostic
f623c6b  stale waypoint onset diagnostic
cd47f05  transient cloak + topology-aware audit
850b639  206 cloak timing + 329 intercept audit
b7e0c9d  329 sphere-wrap + tow interaction audit
```

Use current `main`, not these historical SHAs, unless bisecting.

## 24. Communication/work style for the next chat

The most productive pattern in this session was:

1. inspect GitHub/current data first;
2. formulate one narrow falsifiable question;
3. commit a reusable diagnostic under `tools/diagnostics/`;
4. user pulls and runs it on the PC;
5. analyze the output and explicitly reject or strengthen a hypothesis;
6. only then modify simulator/compiled-label semantics.

Avoid giving five speculative branches and five giant commands at once. The user is comfortable running technical diagnostics, but the research loop should remain reproducible and narrow.

## 25. Current research state in one paragraph

Ordinary movement plus warp wells, external contexts and Chunnel are already represented in the historical validation pipeline, and a compiled Parquet/DuckDB corpus now makes repeated analysis fast enough for PC-based research and eventual ML use. The remaining Horwasp Red Mite investigation found that Mite `(targetx,targety)` becoming a strict match to an older target position is an extremely strong pre-clear state: strict-stale rows in the examined sample all lead to immediate target clear. Most such events are explained by cloak or recent cloak. Ship 206 (Deth Specula) is a strong transient-cloak-interrupted-by-damage candidate, because its tracking goes stale during a unique mission-9/uncloaked/new-damage transition. Ship 329 (RU30 Gunboats) cannot cloak and remains the main unexplained anomaly: tracking first becomes approximate/no-match during a sphere-wrap-like move with `mission1target=-1096`, then becomes strict stale and clears. The current HEAD contains `mite_329_wrap_tow_audit.py` to test sphere-wrap, tow-like co-movement and negative mission-target semantics. Run and analyze that before proceeding.
