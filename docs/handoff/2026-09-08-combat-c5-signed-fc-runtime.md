# C5 signed numeric Friendly Code runtime — 2026-09-08

GitHub is the source of truth. Read together with:

- `docs/handoff/2026-09-08-combat-c5-host-phase-current.md`

At runtime the user ran the signed-FC hypothesis gate on `agent/combat-c5-host-phase` after the handoff/docs commit. The hypothesis tool was:

```text
tools/diagnostics/combat_host_signed_numeric_fc_hypothesis_audit.py
```

Hypothesis:

```text
exactly three-character Friendly Codes matching [+/-][0-9][0-9]
are parsed as signed numeric combat-priority values
```

## Ordinary runtime result

Baseline conservative isolated ship-vs-ship population:

```text
comparable: 420
right_higher_priority: 417
left_higher_priority: 3
```

Signed-FC hypothesis result:

```text
comparable: 420
right_higher_priority: 419
left_higher_priority: 1
```

Delta:

```text
right_higher_priority: +2
left_higher_priority:  -2
```

No new ordinary residuals appeared. The two prior residuals containing right-side Friendly Codes `-54` and `-52` were removed exactly as predicted.

Therefore signed three-character FC parsing has strong ordinary-corpus support and is `CORPUS_OBSERVED + DIFF_VERIFIED`, but NOT `DOCUMENTED`; current public Planets.nu documentation describes numeric battle Friendly Codes as `001..999` and does not document signed values.

Do not silently broaden this to arbitrary-length signed strings. The tested hypothesis is specifically exact three-character `[+/-][0-9][0-9]`.

## Only remaining ordinary isolated standard-side residual

```text
game=621253
turn=10
vcr=8
slice=standard_same_group

left:
  ship=50
  hull=37  # Ill Wind Class Battlecruiser
  owner=4
  mission=0
  enemy=3
  fc='wxd'
  priority=[3,50,0]

right:
  ship=57
  hull=29  # Dark Wing Class Battleship
  owner=3
  mission=20
  enemy=4
  fc='osq'
  priority=[3,57,0]
```

Both simplified Kill/PE checks report initiative, yet factual right side is ship 57 while lower Ship ID 50 would have higher standard-group priority under the current model.

Gorbie forced-left was already ruled out: neither side is hull 70.

## Immediate next gate

Inspect pre-combat diplomacy for game `621253`, VCR turn `10`, so orders/diplomacy snapshot turn `9`, owners `4 <-> 3`.

Current simplified `_can_initiate()` ignores diplomacy. Official Order of Battle says an attacker does not fight a player to whom it grants Safe Passage or higher; asymmetric diplomacy may therefore explain the remaining residual.

Do not guess numeric relation semantics. First inspect raw Relations Object records for owners 3 and 4 at turn 9 and establish the field/value schema. Candidate raw fields include:

```text
playerid
playertoid
relationto
relationfrom
conflictlevel
```

Build a narrow read-only diagnostic if needed. Keep special game `591478` separate and do not tune ordinary rules from it.

## Evidence boundary

- `mission 3 = Kill!`: documented causal rule + ordinary `CORPUS_OBSERVED` numeric mapping.
- `enemy = Primary Enemy`: ordinary `CORPUS_OBSERVED`.
- standard priority -> factual right side: now 419/420 on the conservative ordinary isolated subset under signed-FC hypothesis.
- signed exact-three-character `[+/-][0-9][0-9]` FC parsing: `CORPUS_OBSERVED + DIFF_VERIFIED`, not documented.
- remaining game 621253/T10/VCR8 cause: unresolved; diplomacy is the next hypothesis, not yet evidence.

PR #28 remains draft.
