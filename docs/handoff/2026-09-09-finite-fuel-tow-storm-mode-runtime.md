# Finite-fuel Tow storm-mode runtime checkpoint — 2026-09-09

This file records the completed server runtime of the bounded storm-mode
resolution gate for the finite-fuel Tow residual investigation.

## Runtime provenance

- repository: `Numillyash/planets-lab`
- candidate: `4589d412104c22ac69c42f7027ba033a117e45e2`
- source external-context gate:
  `logs/finite-fuel-tow-external-20260909T171801Z-2c5d841f-20098`
- collected storm-mode gate:
  `logs/finite-fuel-tow-storm-mode-20260909T204843Z-4589d412-8435`
- transport: proxy-only `PlanetsNuPublicApi`

All runner stages completed `0/0`:

```text
inputs                  0 0
tooling                 0 0
storm-mode-resolution   0 0
summary                 0 0
```

## Public loadinfo result

All three residual games resolved successfully through public `game/loadinfo`:

```text
clean_residual_input=53
unique_games=3
loadinfo_attempts=3
loadinfo_success=3
loadinfo_error=0
proxy_client_error=0
mode_true_games=0
mode_false_games=3
mode_unknown_games=0
mode_missing_games=0
mode_unparsed_games=0
mode_conflict_games=0
```

Per-game setting:

```text
360690  $.settings.nuionstorms = false
511506  $.settings.nuionstorms = false
620694  $.settings.nuionstorms = false
```

Each game also exposed the same related settings in this request:

```text
maxions=4
maxioncloudsperstorm=10
nebulas=0
stars=0
```

## Evidence reconciliation

This resolves the mode discriminator left open by the preceding classic-storm
membership audit.

The already verified residual evidence was:

- 53 clean finite-fuel Tow residual rows after known context/transfer filtering;
- 44/53 rows have a complete integer residual vector exactly equal to an actual
  historical after-turn root ion-storm drag vector;
- all 44 of those vector-matched rows qualify at Tow origin under classic
  constant-voltage root-circle membership;
- the bounded Nu-cloud persisted/transient local-voltage variants qualify none
  of those 44 Tow causal points;
- the classic-storm membership audit previously could not promote the classic
  explanation because archived mechanics payloads did not contain
  `nuionstorms`.

Public loadinfo now resolves `nuionstorms=false` for every game contributing to
the 44-row family. Therefore the 44 rows are mode-consistent with the classic
ion-storm model as well as matching both its integer drag vector and its origin
membership predicate.

For evidence mining, these 44 rows should now be treated as attributable
classic ion-storm confounders rather than as unexplained Tow fuel-proration
residuals. This is a reconciliation of the historical residual population; it
is not a new general Tow fuel rule and does not establish the finite-fuel Tow
cost basis.

The remaining bounded population is therefore nine clean rows with no exact
after-turn single-root storm-vector match. Those nine rows are the next useful
finite-fuel Tow residual target and should remain separate from the resolved
classic-storm family.

## Decision

- classic ion-storm attribution for the 44-row residual family:
  `CORPUS_OBSERVED + TESTED` within the exact historical gate scope;
- finite-fuel Tow cost basis: **OPEN**;
- no nominal-vs-rasterized Tow fuel discriminator was created by this gate;
- no `planets-intel` production transfer is implied or authorized by this
  checkpoint.

Next bounded step: reclassify the 44 mode-consistent classic-storm rows out of
the Tow residual population and inspect the exact nine remaining clean rows for
special relocation / passenger Chunnel / other non-fuel context before doing
any additional Tow fuel inference.
