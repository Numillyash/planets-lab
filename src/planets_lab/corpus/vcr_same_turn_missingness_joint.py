"""Joint SAME-TURN VCR source-missingness partitions on the frozen V1 groups.

Only a stricter count-only extension of FrozenSameTurnVcrConsensus.
Private ephemeral game/turn/VCR keys, observer IDs and replay signatures
MUST NEVER be returned or persisted in the evidence branch.
"""
from __future__ import annotations

from collections import Counter

from .vcr_same_turn_consensus_readiness import FrozenSameTurnVcrConsensus

REASONS = (
    "complete",
    "rng_only",
    "owner_only",
    "catalog_only",
    "rng_owner",
    "rng_catalog",
    "owner_catalog",
    "rng_owner_catalog",
)
_MASK_LABEL = {
    0: "complete",
    1: "rng_only",
    2: "owner_only",
    3: "rng_owner",
    4: "catalog_only",
    5: "rng_catalog",
    6: "owner_catalog",
    7: "rng_owner_catalog",
}
FIELDS = (
    "qualified_original_frozen_adjacent_pairs",
    "source_observation_rows_qualified",
    "single_perspective_groups",
    "multi_perspective_groups",
    "single_source_observation_rows",
    "multi_source_observation_rows",
    "single_missing_rng_rows",
    "multi_missing_rng_rows",
    "single_missing_owner_rows",
    "multi_missing_owner_rows",
    "single_missing_catalog_rows",
    "multi_missing_catalog_rows",
    "multi_complete_signature_equal_not_multi_comparison",
    "multi_complete_signature_different",
    "multi_incomplete_signature_equal",
    "multi_incomplete_signature_different",
) + tuple(f"{kind}_{reason}_groups" for kind in ("single", "multi") for reason in REASONS)


class FrozenSameTurnMissingnessJoint(FrozenSameTurnVcrConsensus):
    """Classify strict source requirements per selected group and observer row.

    The original 31 V1 counters remain byte-for-data identical. A multi group
    is incomplete when ANY one of its different observer perspectives lacks
    a required source field, and all overlapping missingness is partitioned
    mutually exclusively before publishing count-only counters.
    """

    def joint_result(self, *, qualified_archive_pairs: int) -> dict[str, int]:
        prior = self.result(qualified_archive_pairs=qualified_archive_pairs)
        c: Counter[str] = Counter()
        c["qualified_original_frozen_adjacent_pairs"] = qualified_archive_pairs
        c["source_observation_rows_qualified"] = prior[
            "source_observation_rows_in_qualified_groups"
        ]
        c["single_perspective_groups"] = prior["single_perspective_groups"]
        c["multi_perspective_groups"] = prior["multi_perspective_groups"]
        for records in self._groups.values():
            kind = "single" if len(records) == 1 else "multi"
            c[f"{kind}_source_observation_rows"] += len(records)
            mask = 0
            for row in records:
                if not row.rng_ready:
                    mask |= 1
                    c[f"{kind}_missing_rng_rows"] += 1
                if not row.owners_ready:
                    mask |= 2
                    c[f"{kind}_missing_owner_rows"] += 1
                if not row.catalog_ready:
                    mask |= 4
                    c[f"{kind}_missing_catalog_rows"] += 1
            c[f"{kind}_{_MASK_LABEL[mask]}_groups"] += 1
            if kind == "multi":
                equal = len({r.full_signature for r in records}) == 1
                if mask:
                    c["multi_incomplete_signature_equal" if equal
                      else "multi_incomplete_signature_different"] += 1
                elif not equal:
                    c["multi_complete_signature_different"] += 1
                else:
                    c["multi_complete_signature_equal_not_multi_comparison"] += 1

        if not (
            set(c).issubset(FIELDS)
            and sum(c[f"single_{reason}_groups"] for reason in REASONS)
                == prior["single_perspective_groups"]
            and sum(c[f"multi_{reason}_groups"] for reason in REASONS)
                == prior["multi_perspective_groups"]
            and c["single_source_observation_rows"] ==
                prior["single_perspective_groups"]
            and c["multi_source_observation_rows"] ==
                prior["multi_perspective_observer_occurrences"]
            and c["single_source_observation_rows"] +
                c["multi_source_observation_rows"] ==
                prior["vcr_rows_qualified_same_turn_typed_participants"]
            and c["single_missing_rng_rows"] + c["multi_missing_rng_rows"]
                == prior["vcr_rows_missing_explicit_combat_rng"]
            and c["single_missing_owner_rows"] + c["multi_missing_owner_rows"]
                == prior["vcr_rows_missing_typed_owner_pair"]
            and c["single_missing_catalog_rows"] + c["multi_missing_catalog_rows"]
                == prior["vcr_rows_missing_typed_weapon_catalog"]
            and c["multi_complete_signature_equal_not_multi_comparison"]
                == prior["multi_perspective_strict_complete_inputs_equal"]
            and c["multi_complete_signature_different"]
                == prior["multi_perspective_strict_complete_inputs_different"]
            and (c["multi_incomplete_signature_equal"] +
                 c["multi_incomplete_signature_different"])
                == prior["multi_perspective_strict_inputs_incomplete"]
            and (c["multi_complete_signature_equal_not_multi_comparison"] +
                 c["multi_incomplete_signature_equal"])
                == prior["multi_perspective_complete_adapter_signature_equal"]
            and (c["multi_complete_signature_different"] +
                 c["multi_incomplete_signature_different"])
                == prior["multi_perspective_complete_adapter_signature_different"]
        ):
            raise ValueError("ABSTAIN_VCR_MISSINGNESS_JOINT_CONSERVATION")
        return {key: int(c[key]) for key in FIELDS}
