# V594 parent-resume result — exact

Date: 2026-10-06

Runtime evidence:

    runtime-logs/capture-parent-resume-v594/
    20261006T180311Z_acb19991c00d

Source commit:

    acb19991c00d4e728b6a0e00e977c3ec0bf24e29

Target:

    game 400330
    turn 141
    site (1674, 2363)
    through V593
    held-out comparator V594

Result:

    PARENT_RESUME_EXACT

Prediction:

    pair             [170, 184]
    occurrence       1
    LEFT             184
    RIGHT            170
    unresolved       []

Factual V594:

    pair             [170, 184]
    LEFT             184
    RIGHT            170

Therefore:

    pair_exact       true
    side_exact       true

The held-out boundary remained:

- immediate V593 continuation had to be independently classified as exhausted;
- pair history used factual VCRs only through V593;
- same-turn diplomacy controls were truncated at V593;
- V594 and every later same-turn row were excluded from calibration;
- V594 pair/sides were opened only after production
  select_next_plain_standard returned.

This closes the bounded orchestration transition:

    V593 capture
      -> immediate O/C exhausted
      -> parent queue resume
      -> V594 pair/side exact

The next step is no longer another one-off transition gate. Build a
history-anchored site transition loop over V592..V595, then replace history
reconstruction with a carried internal site state.
