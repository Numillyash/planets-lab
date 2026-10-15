# C5 V21: THREE research experiments in ONE server/evidence run

**User workflow requirement:** avoid one PR/SSH invocation per scientific
observation. Three independently checked analyses are now committed
and runnable by a SINGLE server command. One evidence wrapper publishes
three phase reports + a SHA256-indexed manifest atomically as a group
when they all succeed. No further manual task switching between phases.
Do not claim any remote command has run until user publishes evidence.

Canonical `Numillyash/planets-lab` main. Do not modify production
`planets-intel`, combat executor, draft PR #28, external-engine
branch, or corpus `CURRENT`.

## Grounded V20 source

Published run:
`runtime-logs/combat-c5-chunnel-stabilization-provenance-v20/20261015T201935Z_74acf3fd509c`,
exit_code=0, source
`74acf3fd509c1ab910ac789b50f65f14e882676c`.
Pinned V20 published Git blob:
`3d5e1d5aeb6b0138c01bab3ec81185d0685233c0`.
Pinned V19 blob:
`572d14d348235694402148273c7085d212301eac`.

V20 frozen 13 single-distance-gate controls over 9 windows:
4 geometrically discriminative, 9 same-coordinate tautologies.
Two candidate T−1 Stargate fields inside radius, eleven
stabilization states ABSTAIN. For G467386/T75 actor Firecloud
#467 (Cyborg owner #6), source (1141,1459), target #80
(1126,1439), separation 25LY, T−1 Dungeon Class Stargate
**#446**, same owner, at (1279,1931), engine 9, documentary
radius 550LY. Distance to #467 source is **491.7601LY**
and target is also expected inside radius. At T after Host,
#467 and same-owner colocated #193/#235/#405 are at #80.
Actor net fuel 51->3 (-48KT), target +2KT, three escorts +2KT
each. This is consistent with official Chunnel Stabilizer
mechanics but is NOT proof it activated in Host.

Official rules:
https://help.planets.nu/abil-chunnel-stabilizer
https://help.planets.nu/short-format
https://help.planets.nu/mis-warp-chunnel

CORRECTION: Standard Chunnel allows same-owner Warp9 ships
to participate. Warp9 escorts alone do not establish Short
Format rules. V20 has NO explicit Short Format setting flag.

## Three V21 independent diagnostic phases

**A — `geometry.json`:** exact T−1 re-observation of all 13
short edges and historical Dungeon hull/engine. Recompute source
AND target distance to every archived candidate stabilizer
and signed radius margin. Near-boundary source and target
coverage should not be conflated. This phase deliberately
does NOT read T.

**B — `persistence.json`:** for each Stargate ship T−1
appearance across all 9 windows, freeze exact hull108/engine/
position before ANY post-Host T read. Then compare each
Stargate's T owner-current identity, engine and position.
A stable Dungeon is supportive context but **not a Host
Chunnel-phase activation log**.

**C — `escorts.json`:** for ALL four *geometrically distinct*
V17 short-edge episodes, freeze every ship colocated with
its initiator at T−1, including allied ships at nonzero Warp.
Then compare every one against owner-current post-Host T
position and fuel changes. Never count multiple escorts
in the same episode as independent activations. Do not
infer unknown mine or intervening movement causes.

Every experiment uses exact pinned V19/V20 published JSON
and SHA256-pinned immutable read-only public100. Each phase
has a strict T−1-before-T barrier where T is applicable.
**All three phases are runnable together:** the script exits
nonzero on any phase error, manifest refuses absent/tampered
reports, and evidence publication records the combined
result rather than asking the user to initiate three runs.

Reports under:
`artifacts/combat/c5-stabilization-batch-v21/published/`
with `geometry.json`, `persistence.json`, `escorts.json`,
`manifest.json`.

## ONE server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-stabilization-batch-v21-with-evidence.sh
```

Evidence branch path:
`runtime-logs/combat-c5-stabilization-batch-v21/<UTC>_<SHA>/`.

## Future without manual round trips

For subsequent multi-stage work, plan and commit a batch of
outcome-blind experiments in advance. If later stages depend on
the first one's RESULT, either implement declared deterministic
decision branches within the single batch, with recorded skipped
branches, or separate only when scientific preregistration
or intervention genuinely requires a new input. Never treat
repeated same-corpus posthoc probes as independent validation.
