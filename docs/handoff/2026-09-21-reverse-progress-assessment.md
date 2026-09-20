# NuHost reverse progress assessment — 2026-09-21

This is an engineering planning estimate, not an evidence label.

Source checkpoint:

```text
active C5 runtime HEAD:
  370ecaf5de029fadfd0acafd1107e1fb35c9cb54

C5 mixed batch:
  v6
  10/10 stages rc=0

PR #28:
  open
  draft
  unmerged
```

Game `591478` remains isolated from ordinary promotion.

## Executive estimate

```text
combat mechanics reconstruction (C1-C5 knowledge):       ~90-93%
movement ordinary-core reconstruction:                    ~80-90%
warfare subsystem overall:                                ~75-82%
historical corpus / compatibility pipeline (M5A/M5B):     ~80-88%
whole NuHost reverse across the roadmap:                  ~45-55%
```

Independent historical ship-combat candidate coverage remains:

```text
428 / 1986 factual unique ship pairs = 21.6%
```

This is a coverage boundary, not a combat-completion percentage.

## Why combat knowledge moved above the previous 85-90%

Since the 2026-09-20 assessment, the mixed ship/planet boundary closed several major mechanics questions:

1. ordinary ship combat always precedes the planet block in the observed ordinary mixed population;
2. planet/base is on RIGHT in all observed ordinary mixed VCRs;
3. ordinary repeated planet attackers follow production STANDARD Combat Priority;
4. capture-generated planet orders preserve Friendly Code priority while clearing old Mission / Primary Enemy aggression priority;
5. this capture priority is production differential verified;
6. interphase supply repair is production differential verified;
7. all 2406 ordinary ship-vs-planet VCRs have a basic independently attributable ship or planet initiator when historical combat-time ownership is known;
8. the remaining apparent planet-initiation residuals were traced to earlier Host planet ownership mutation, not a new combat exception;
9. ownership mutation was narrowed to 59 unique precombat planet-turn changes;
10. 42 positive-owner reversal timelines all have a co-located future-defender ship at T-1;
11. the source objects expose explicit `transferclans/transfertargetid/transfertargettype` orders, including cases where onboard `clans` is already zero.

Thus the main mixed-queue unknown has moved upstream from combat ordering into cargo-drop / ground-combat ownership state.

## What remains before a strong ordinary combat simulator

The principal remaining C5 engineering blocks are:

1. reconstruct precombat planet ownership mutation from directed clan-transfer / ground-combat operations;
2. compose that ownership into independent planet targetability;
3. broaden independent position/candidate coverage beyond the current 21.6% factual ship-pair boundary;
4. close generic Advanced Cloak production behavior;
5. run complete-site and complete-turn mixed combat differential validation;
6. keep isolated game `591478` out of ordinary promotion.

Mechanics knowledge remaining is roughly:

```text
~7-10% of C1-C5
```

but engineering/coverage work remaining for robust historical full-combat replay is materially larger.

## Why whole NuHost remains ~45-55%

Combat was already one of the most advanced subsystems.

Large blocks outside combat still remain:

- economy / planetary Host;
- starbase and ship production;
- minefield lifecycle;
- general missions and special abilities in Host order;
- cross-subsystem diplomacy / alliance / Safe Passage semantics;
- vertical race-specific integration;
- observer / visibility / fog / shared intel;
- end-to-end complete-turn Host differential validation.

Therefore the substantial C5 progress does not justify calling the whole NuHost project much more than approximately half complete.

## Current state in one sentence

```text
The ordinary combat machine is now mostly understood and locally differential-verified;
the main remaining combat work is independently reconstructing all of the state that feeds it,
especially precombat planet ownership and broader candidate coverage.
```
