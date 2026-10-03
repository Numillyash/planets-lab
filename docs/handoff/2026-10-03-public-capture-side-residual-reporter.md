# Capture-side held-out residual reporter

After the frozen held-out gate, two bounded local residual artifacts are enough
for the next analysis:

    artifacts/public-capture-side/heldout-residual-476380.json
    artifacts/public-capture-side/heldout-residual-257776.json

Do not rerun the complete 36-game corpus to inspect them.

Run:

    python tools/diagnostics/combat_public_capture_side_residual_report.py

The reporter prints:

1. game 476380 / turn 223 / VCR 903 -> 904:
   the single true held-out side counterexample, including the external-order
   cursor trace added after the failed gate;
2. game 257776 / turn 230 / ship 71:
   both same-turn capture rows around VCR 1644/1645/1646;
3. the VCR1645 repeated-capture unresolved row with its dependency state.

The reporter is read-only and performs no Corpus DB work.
