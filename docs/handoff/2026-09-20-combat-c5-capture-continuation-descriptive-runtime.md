# C5 capture continuation — descriptive runtime

Branch: `agent/combat-c5-host-phase`

Runtime source HEAD:

```text
9d7f974feee3f77e5b3ddf1382fd72567e5cfa8d
```

PR #28 remained open + draft. Game `591478` was excluded.

## Tests

User runtime:

```text
........... [100%]
```

## Population

Diagnostic v1:

```text
tools/diagnostics/combat_host_capture_continuation_audit.py
```

Ordinary same-turn same-location capture reappearances:

```text
capture_reappearance_transitions=23
hull_preserved=23/23
race_changed=23/23
race_changes_to_captor_exact=23/23
post_capture_side:left=22
post_capture_side:right=1

next_opponent_third_ship=8
next_opponent_unknown=15
```

Raw deterministic-terminal -> factual-next-start fields:

```text
damage:
  exact=22
  mismatch=1

crew:
  mismatch=23

torpedoes:
  exact=23

fighters:
  exact=23

shield:
  exact_carry=22
  mismatch=1
```

## Strong capture facts

Every observed captured ship which reappeared at the same site:

1. retained the same hull id;
2. changed factual VCR race id;
3. changed it exactly to the prior opponent/captor race;
4. continued into a later VCR in the same Host combat sequence.

The repeated recapture chain in `621896/T25 ship34` is especially informative:

```text
VCR49 -> VCR50: race9 captured by race2 -> next race2
VCR50 -> VCR52: race2 captured by race9 -> next race9
VCR52 -> VCR54: race9 captured by race2 -> next race2
```

This rejects treating combat capture as terminal queue removal.

## Prize crew

All 23 rows have deterministic combat terminal:

```text
crew=0
```

and factual next VCR:

```text
crew=10
```

Official Planets.nu Combat Basics independently documents that a combat-captured starship receives a 10-person prize crew.

This is therefore:

```text
DOCUMENTED + CORPUS_OBSERVED
```

before production differential.

## Shield residual

Only one row violates raw shield carry:

```text
621896/T14 ship36
race before=1
captor race=3
terminal shield=0
next VCR shield=25
```

Official Planets.nu differences documentation states that Federation shield recovery in NuHost occurs at the end of each battle. This fits the observed sequence if recovery is applied using the pre-capture Federation combat state before ownership/race transfer.

The production capture transition must therefore order:

```text
combat terminal
  -> pre-capture Federation end-of-battle recovery
  -> prize crew
  -> owner/race transfer
  -> next-owner combat bonuses
```

not infer Federation recovery from the captor race.

## Damage residual

Only one row violates raw damage carry:

```text
621253/T17 ship84
VCR39 -> VCR45
hull87
race10 -> captured by race8
replay terminal damage=11
factual next VCR damage=7
```

No generic capture repair rule is promoted from this singleton. It is isolated as an upstream deterministic-replay residual until separately explained.

## Next implementation

Production capture must remain fail-closed unless explicit captor owner/race metadata is supplied.

Bounded production state transition:

- preserve hull;
- carry deterministic terminal damage/ammunition;
- apply pre-capture Fed end-of-battle shield recovery;
- set prize crew=10;
- transfer owner/race to explicit captor;
- switch future Federation/Lizard combat bonus flags to explicit new-owner state;
- retain the captured ship in active queue.

The single known damage residual must not become a production special-case.
