# C5 Host combat — Privateer Rob initial-decision runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` stays excluded from ordinary promotion.

Runtime source:

```text
7cb29984bc09b241241a8e738f6b6701bc61d5b4
```

Artifact reported by the historical runtime:

```text
artifacts/combat-c5-privateer-rob-initial-decision-20260911-113816
```

Runtime result:

```text
tests rc=0
audit rc=0
payload_conflicts=0
opportunities=16

initial_pair_vcr=5
initial_skip_target_not_above_factual=5
initial_skip_target_outranks_factual=3
attacker_no_factual_vcr=1
later_pair_vcr=1
noninitial_attacker_context=1
```

Prior-cloak split:

```text
false:initial_pair_vcr=4
false:initial_skip_target_not_above_factual=1
false:attacker_no_factual_vcr=1

true:initial_pair_vcr=1
true:initial_skip_target_not_above_factual=4
true:initial_skip_target_outranks_factual=3
true:later_pair_vcr=1
true:noninitial_attacker_context=1
```

## Strong clean residuals

Exactly three independently reconstructed opportunities are clean first-decision blocker residuals:

```text
360690/T83 site 2374,2260
  target98 owner5 race5 hull46 Meteor mission9 Rob PE0 FC vjh
  T-1 fuel45 iscloaked=true
  attacker264 owner11 mission3 Kill! FC 1uP
  target priority (4,98,0)
  factual first target190 priority (4,190,0)
  factual pair [190,264]
  => target98 strictly outranks factual target but is skipped

360690/T57 site 2481,2445
  target46 owner5 race5 hull46 Meteor mission9 Rob PE0 FC 972
  T-1 fuel58 iscloaked=true
  attacker146 owner11 mission1 PE5 FC ntp
  target priority (0,972,46)
  factual first target184 priority (4,184,0)
  factual queue includes [146,184], [146,293]
  => target46 strictly outranks factual first target but is skipped

360690/T57 same site/attacker
  target280 owner5 race5 hull46 Meteor mission9 Rob PE0 FC 972
  T-1 fuel9 iscloaked=true
  target priority (0,972,280)
  factual first target184 priority (4,184,0)
  => target280 strictly outranks factual first target but is skipped
```

No earlier VCR can explain any of these three rows. They are genuine missing precombat eligibility/state residuals under the current candidate layer.

## Matched visible controls

The same two sites already contain strong within-site controls:

```text
360690/T83:
  ship98  hull46 / mission9 / PE0 / prior cloak=true  -> skipped
  ship190 hull46 / mission9 / PE0 / prior cloak=false -> factual pair [190,264]

360690/T57:
  ship46  hull46 / mission9 / PE0 / prior cloak=true  -> skipped
  ship280 hull46 / mission9 / PE0 / prior cloak=true  -> skipped
  ship293 hull46 / mission9 / PE0 / prior cloak=false -> factual pair [146,293]
```

This is substantially stronger than the earlier population-only correlation because attacker, site, owner race, hull, Rob mission and PE=0 are held constant within the factual combat site.

## Clean prior-true combat control

There is one clean initial prior-true pair:

```text
620694/T64 site 1371,2382
  target118 owner5 race5 hull46 Meteor mission9 Rob PE0 FC wds
  T-1 fuel5 iscloaked=true
  attacker134 owner3 hull17 mission10 PE5
  pair [118,134] is the attacker's first factual pair
  target118 is later absent / true_to_false attribution
```

Therefore raw T-1 `iscloaked=true` remains rejected as a direct blanket blocker. The next gate must explain whether target118 had a documented decloak context before combat (fuel exhaustion, Loki, damage, ion/mine/glory context, etc.) while the three clean skips did not.

## Evidence interpretation

Promoted from this runtime:

```text
initial queue/rank classification: TESTED
three clean initial skip residuals: CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
raw T-1 iscloaked blanket blocker: REJECTED
within-site true-vs-false Rob/Meteor target differential: CORPUS_OBSERVED
```

Not yet promoted:

```text
T-1 iscloaked=true => combat-effective cloak
Rob mission preserves cloak
any canonical cloak blocker in selection.py
```

The official Planets.nu cloak documentation says cloaked ships are protected from enemy attack, but also describes Host cloak state as dynamic and subject to damage, fuel loss, Loki, ion storms, mines and Glory Devices. This means the single prior-true fought control must be attributed before any rule promotion.

## Immediate next step

Run a narrow precombat state-context differential over exactly:

```text
prior-cloak=true + initial_skip_target_outranks_factual
prior-cloak=true + initial_pair_vcr
```

The diagnostic should compare target damage/fuel, reference movement fuel depletion, Rob-origin fuel-gain exposure, nearby Loki start/end context, and stable T attribution. It must remain diagnostic-only and must not modify canonical pair eligibility.
