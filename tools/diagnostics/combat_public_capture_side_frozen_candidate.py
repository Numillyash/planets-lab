from __future__ import annotations

from typing import Any


SCHEMA = "planets-lab.combat-public-capture-side-frozen.v1"
DISCOVERY_SOURCE_COMMIT = "e80b0e2d1ee5976c4e8c0dac530f8a1216324eb5"
DISCOVERY_RUNTIME_EVIDENCE = (
    "runtime-logs/public-capture-o-layer-discovery/"
    "20261003T163249Z_e80b0e2d1ee5"
)
DISCOVERY_ADJACENT_ROWS = 31
DISCOVERY_EXACT = 31
DISCOVERY_MISMATCH = 0
DISCOVERY_UNRESOLVED = 0


def predict_frozen_capture_side(
    *,
    identity_anchored_o_pair_reachable: bool | None,
    capture_side: Any,
    neutral_fresh_fc_side: Any,
) -> str | None:
    """Frozen pre-heldout post-capture side candidate.

    The pair-reachability input is conditional on the factual N+1 opponent
    identity/eligibility only; factual LEFT/RIGHT is never an input.

    If that opponent is reachable through the frozen original-order cursor,
    preserve the captured prize's side from the capture VCR. Otherwise assign
    the side produced by neutral orders with a fresh nonmatching symbolic FC.
    """

    if identity_anchored_o_pair_reachable is True:
        return capture_side if capture_side in {"left", "right"} else None
    if identity_anchored_o_pair_reachable is False:
        return (
            neutral_fresh_fc_side
            if neutral_fresh_fc_side in {"left", "right"}
            else None
        )
    return None
