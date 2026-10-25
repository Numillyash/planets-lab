#!/usr/bin/env python3
"""V6: check frozen source population and exact minefield joint partition.

Only reads a sanitized numeric aggregate. Never prints source identities.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

# This validator runs with HOST python3 (not the pip-installed Docker lab).
# Keep script-style invocation independent of site-packages and PYTHONPATH.
ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Load the *pure stdlib* source-review module by fixed repository path.
# Importing planets_lab.corpus invokes package __init__ -> feature_index ->
# duckdb even though this validator needs no DuckDB and may run on a host
# with only system python3. Avoid those incidental package dependencies.
from importlib.util import module_from_spec, spec_from_file_location
_REVIEW_PATH = ROOT / "src/planets_lab/corpus/nonplanet_v5_evidence_review.py"
_spec = spec_from_file_location("_planets_lab_pure_v5_review", _REVIEW_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError("ABSTAIN_SOURCE_REVIEW_MODULE_UNAVAILABLE")
_review = module_from_spec(_spec)
_spec.loader.exec_module(_review)
EvidenceReviewAbstain = _review.EvidenceReviewAbstain
review_published_v5 = _review.review_published_v5

from tools.diagnostics.m2_validate_corpus_aggregate_evidence_v1 import validate

JOINT = (
    "same_id_fresh_own_center_stable_numeric_units_joint",
    "same_id_fresh_own_center_stable_units_increased_joint_not_causal",
    "same_id_fresh_own_center_stable_units_decreased_joint_not_causal",
    "same_id_fresh_own_center_stable_units_unchanged_joint_not_causal",
    "same_id_fresh_own_center_stable_units_changed_joint_not_causal",
)
# Exact previously published, validated v5 source marginals (same population).
MARGINALS = {
    "same_id_seen_in_both_archives": 887224,
    "same_id_current_own_verified_both_archives": 138864,
    "same_id_owner_center_stable_units_changed_not_causal": 536703,
    "same_id_nonnegative_integer_units_both": 887224,
}

def validate_joint(data: dict) -> dict[str, int]:
    # Older reviewer deliberately rejects any unknown counters: project
    # back to its exact original allowlist before checking provenance.
    import copy
    p = copy.deepcopy(data)
    sections = p["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]
    mine = sections["minefields"]
    if any(key not in mine for key in JOINT):
        raise EvidenceReviewAbstain("ABSTAIN_JOINT_COUNTER_MISSING")
    vals = {key: mine[key] for key in JOINT}
    if any(type(v) is not int or v < 0 for v in vals.values()):
        raise EvidenceReviewAbstain("ABSTAIN_JOINT_NOT_INTEGER")
    if any(mine.get(k) != value for k, value in MARGINALS.items()):
        raise EvidenceReviewAbstain("ABSTAIN_V5_MARGINAL_MISMATCH")
    for key in JOINT:
        del mine[key]
    review_published_v5(p)
    n, inc, dec, unchanged, changed = (vals[k] for k in JOINT)
    if not (
        n == inc + dec + unchanged
        and changed == inc + dec
        and changed <= mine["same_id_owner_center_stable_units_changed_not_causal"]
        and n <= mine["same_id_current_own_verified_both_archives"]
        and n <= mine["same_id_nonnegative_integer_units_both"]
    ):
        raise EvidenceReviewAbstain("ABSTAIN_JOINT_CONSERVATION")
    return vals

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--self-test", action="store_true",
                        help="Run host-isolated synthetic validator regression; no DB access")
    args = parser.parse_args()
    if args.self_test:
        if args.input is not None:
            print("ABSTAIN_SELF_TEST_INPUT_NOT_ALLOWED")
            return 2
        try:
            safe_fixture = ROOT / "tests/fixtures/public100_nonplanet_v5_allowlisted_aggregates.json"
            payload = json.loads(safe_fixture.read_text(encoding="utf-8"))
            mine = payload["sample"]["nonplanet_archive_identity_readiness_not_host_phase"]["minefields"]
            mine.update(dict(zip(JOINT, (100, 30, 40, 30, 70))))
            if validate_joint(payload) != dict(zip(JOINT, (100, 30, 40, 30, 70))):
                raise EvidenceReviewAbstain("ABSTAIN_SELF_TEST_RESULT_MISMATCH")
        except (ValueError, KeyError, TypeError, OSError):
            print("ABSTAIN_V6_HOST_VALIDATOR_SELF_TEST")
            return 2
        print("PASS_V6_HOST_VALIDATOR_SELF_TEST_SYNTHETIC_ONLY")
        return 0
    if args.input is None:
        print("ABSTAIN_V6_INPUT_REQUIRED")
        return 2
    try:
        report = validate(args.input)
        counts = validate_joint(report)
    except (ValueError, KeyError, TypeError, OSError):
        print("ABSTAIN_V6_VALIDATION")
        return 2
    print("PASS_SOURCE_JOINT_NONCAUSAL")
    print("fresh_own_stable_centre_units_comparable=" + str(counts[JOINT[0]]))
    print("fresh_own_stable_centre_units_changed=" + str(counts[JOINT[4]]))
    print("accepted_host_orders_verified=false")
    print("host_phase_diff_verified=false")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
