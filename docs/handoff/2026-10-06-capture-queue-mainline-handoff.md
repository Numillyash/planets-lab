# Capture queue mainline handoff — 2026-10-06

## Repository boundary correction

The O/C selector work originated in:

    research/external-engine-analysis

because that workstream was initially comparing independent external engines
and freezing candidate queue geometries.

That branch is not the canonical development branch for NuHost reconstruction.

From this checkpoint forward:

    canonical mechanics development = main
    external-engine-analysis         = historical/comparative evidence only

Do not require the external checkout to continue the main NuHost combat work.

## Imported bounded evidence

The independently tested O->C selector core is now present in mainline
diagnostics:

    tools/diagnostics/combat_postcapture_o_c_forward_selector.py

Its independently observed fresh32 C-branch evidence is preserved as a small
immutable fixture:

    validation/combat/postcapture-o-c-forward-independent-fixture.json

Provenance remains linked to:

    runtime-logs/postcapture-o-c-forward-independent/
    20261006T024237Z_bbc0b467ae0a

Frozen selector source:

    d6f80a12c9d6fbf3eaa1d7dfeb1cc39839d147ad

Frozen validation protocol:

    16b5a10e6bda7ebd8e98e1cee3a8ca16508727de

Observed prospective result:

    qualified rows       6
    exact                6
    mismatch             0
    unresolved           0
    O branch             0
    C branch             6

Therefore the bounded C-forward continuation branch has independent evidence.

The complete O->C selector is not yet independently full-branch validated,
because no fresh qualified O case was observed.

## Why the external integration run stopped

Runtime:

    runtime-logs/postcapture-site-transition-chain/
    20261006T153928Z_38de692dcc1c

The first transition was exact:

    game 400330 T141
    V592 -> V593
    ship184 captures ship140
    capture cursor branch C
    predicted pair 140/170
    factual pair   140/170

The next step stopped with:

    capture_selector_case_missing

This is not a reason to return to capture-side analysis.

It exposes the next mutable-queue boundary.

V593 is itself a capture predecessor according to terminal replay, but it is
not one of the validated "captured prize immediately continues" cases.

The earlier integration assumption was too coarse:

    if capture happened:
        always invoke immediate O/C prize continuation

The next mainline question is instead:

    after a capture, under what conditions does the captured prize receive
    immediate O/C continuation, and when does Host return to the parent/global
    mutable queue?

## Game 400330 / T141 chain

The already independently validated immediate continuations are:

    V592 -> V593
        captured prize 140
        captor 184
        C-forward opponent 170

    V594 -> V595
        captured prize 170
        captor 184
        C-forward opponent 382

The residual transition is:

    V593 -> V594

This is now the preferred bounded integration case.

Do not describe it as an ordinary non-capture predecessor until the V593
terminal/capture identity and continuation eligibility are explicitly
reconstructed.

## Next implementation

Work only from the normal checkout:

    ~/projects/planets-lab

Next diagnostic should:

1. reconstruct V593 terminal result from explicit public100;
2. identify captured ship and captor without looking at V594 pair selection;
3. reconstruct the captured prize's post-capture identity;
4. evaluate whether an immediate O/C continuation is definitely available;
5. if not available, resume the parent STANDARD mutable queue using the already
   validated ordinary post-mutation selector;
6. compare the resulting pair with held-out V594.

This is the current C5 mutable-queue residual.

The external branch remains useful only as provenance for the frozen selector
and independent-engine archaeology. It is no longer a runtime dependency for
mainline NuHost reconstruction.
