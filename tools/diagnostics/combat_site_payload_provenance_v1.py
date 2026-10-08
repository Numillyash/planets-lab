"""Observational provenance matrix for factual current-VCR combat inputs.

Research-only: this module does not construct combat payloads for the
site executor, does not consume post-combat terminal results, and does not
promote any candidate rule. Current VCRs are used solely as comparison
observations. A T-1 match is *not* independent validation of a Host rule.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS = Path(__file__).resolve().parent
for folder in (ROOT / "src", DIAGNOSTICS):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.data.nu_loadturn import _ship_ammo

import combat_site_state_differential_v1 as site_differential


SCHEMA = "planets-lab.site-combat-payload-provenance.v1"

# These are only direct T-1 field candidates, not canonical combat setters.
DIRECT_FIELDS = (
    ("hullid", "hullid"),
    ("beamid", "beamid"),
    ("torpedoid", "torpedoid"),
    ("beamcount", "beams"),
    ("launchercount", "torps"),
    ("baycount", "bays"),
    ("mass", "mass"),
)
VCR_ONLY_RATE_FIELDS = (
    "beamkillbonus",
    "beamchargerate",
    "torpchargerate",
    "torpmisspercent",
    "crewdefensepercent",
)


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _compare(
    field: str,
    *,
    prior: int | None,
    factual: int | None,
    origin: str,
) -> dict[str, Any]:
    if prior is None:
        status = "unresolved_prior"
    elif factual is None:
        status = "unresolved_vcr"
    elif prior == factual:
        status = "observed_equal"
    else:
        status = "observed_different"
    return {
        "field": field,
        "tminus1_candidate": prior,
        "current_vcr_observed": factual,
        "origin": origin,
        "status": status,
        "delta_current_minus_tminus1": (
            factual - prior if prior is not None and factual is not None else None
        ),
    }


def side_provenance(
    *,
    side_name: str,
    vcr_side: Mapping[str, Any],
    prediction: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Compare only candidate static inputs; never mutate or predict a VCR."""

    ship_id = _integer(vcr_side.get("objectid"))
    if ship_id is None or ship_id <= 0:
        raise ValueError(f"{side_name}: current VCR ship id missing")

    raw: Mapping[str, Any] | None = None
    if prediction is not None:
        candidate = prediction.get("raw")
        if isinstance(candidate, Mapping):
            raw = candidate

    observed: list[dict[str, Any]] = []
    for vcr_key, raw_key in DIRECT_FIELDS:
        observed.append(
            _compare(
                vcr_key,
                prior=_integer(raw.get(raw_key)) if raw is not None else None,
                factual=_integer(vcr_side.get(vcr_key)),
                origin=f"tminus1_raw.{raw_key}",
            )
        )

    # Nu's shared ammo field is already decoded by the canonical RST parser.
    # A missing ammo key is genuinely unresolved, not proof that ammo is zero.
    if raw is None or "ammo" not in raw:
        prior_torpedoes = None
        prior_fighters = None
        ammo_status = "missing_tminus1_ammo"
    elif _integer(raw.get("ammo")) is None or _integer(raw.get("ammo")) < 0:
        prior_torpedoes = None
        prior_fighters = None
        ammo_status = "invalid_tminus1_ammo"
    else:
        _, _, _, fighters, torpedoes, unresolved = _ship_ammo(raw)
        if unresolved > 0:
            prior_torpedoes = None
            prior_fighters = None
            ammo_status = "ambiguous_nu_ammo"
        else:
            prior_torpedoes = torpedoes
            prior_fighters = fighters
            ammo_status = "decoded_nu_ammo_candidate"

    observed.append(
        _compare(
            "torpedos",
            prior=prior_torpedoes,
            factual=_integer(vcr_side.get("torpedos")),
            origin="tminus1_raw.ammo + fitted_torps/bays",
        )
    )
    observed.append(
        _compare(
            "fighters",
            prior=prior_fighters,
            factual=_integer(vcr_side.get("fighters")),
            origin="tminus1_raw.ammo + fitted_torps/bays",
        )
    )

    rates = [
        {
            "field": name,
            "value": _integer(vcr_side.get(name)),
            "source": "factual_current_vcr_only",
            "classification": "unresolved_host_combat_setup",
        }
        for name in VCR_ONLY_RATE_FIELDS
    ]
    return {
        "side": side_name,
        "ship_id": ship_id,
        "prediction_source": (
            prediction.get("source") if prediction is not None else None
        ),
        "tminus1_owner_id": (
            _integer(prediction.get("owner_id"))
            if prediction is not None else None
        ),
        "current_vcr_race_id": _integer(vcr_side.get("raceid")),
        "tminus1_ammo_classification": ammo_status,
        "direct_field_observations": observed,
        "host_rate_fields": rates,
    }


def build_report(
    *,
    context: Mapping[str, Any],
    cases: Mapping[tuple[int, int], Any],
    game_id: int,
    turn: int,
    vcr_ids: tuple[int, ...],
    database_path: str,
) -> dict[str, Any]:
    predictions = context.get("predictions")
    factual_queue = context.get("factual_queue")
    if not isinstance(predictions, Mapping) or not isinstance(factual_queue, list):
        raise ValueError("site factual prestate is incomplete")

    pair_by_vcr: dict[int, tuple[int, int]] = {}
    for row in factual_queue:
        if not isinstance(row, Mapping):
            continue
        vid = _integer(row.get("vcr_id"))
        pair = row.get("pair")
        if (
            vid is not None and isinstance(pair, tuple) and len(pair) == 2
            and all(_integer(value) is not None for value in pair)
        ):
            pair_by_vcr[vid] = tuple(sorted(int(value) for value in pair))

    rows: list[dict[str, Any]] = []
    field_counts: Counter[str] = Counter()
    field_status_counts: Counter[str] = Counter()
    for vcr_id in vcr_ids:
        case = cases.get((turn, vcr_id))
        if case is None:
            raise ValueError(f"VCR {vcr_id}: no compact current-VCR input")
        factual_pair = pair_by_vcr.get(vcr_id)
        if factual_pair is None:
            raise ValueError(f"VCR {vcr_id}: not in factual target-site queue")

        payload = case.payload
        if not isinstance(payload, Mapping):
            raise ValueError(f"VCR {vcr_id}: malformed factual payload")
        left = payload.get("left")
        right = payload.get("right")
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
            raise ValueError(f"VCR {vcr_id}: sides missing")

        left_id = _integer(left.get("objectid"))
        right_id = _integer(right.get("objectid"))
        if None in (left_id, right_id) or tuple(sorted((left_id, right_id))) != factual_pair:
            raise ValueError(f"VCR {vcr_id}: target-site pair mismatch")

        sides: list[dict[str, Any]] = []
        for side_name, side_payload, ship_id in (
            ("left", left, left_id),
            ("right", right, right_id),
        ):
            candidate = predictions.get(ship_id)
            candidate = candidate if isinstance(candidate, Mapping) else None
            side = side_provenance(
                side_name=side_name,
                vcr_side=side_payload,
                prediction=candidate,
            )
            sides.append(side)
            for item in side["direct_field_observations"]:
                field_counts[item["field"]] += 1
                field_status_counts[
                    f"{item['field']}::{item['status']}"
                ] += 1

        rows.append(
            {
                "vcr_id": vcr_id,
                "pair": list(factual_pair),
                "factual_left_ship_id": left_id,
                "factual_right_ship_id": right_id,
                "seed": _integer(payload.get("seed")),
                "battletype": _integer(payload.get("battletype")),
                "combat_rng": case.settings.get("combatrng"),
                "weapon_catalog_beam_count": len(case.beams),
                "weapon_catalog_torpedo_count": len(case.torpedoes),
                "perspective_observations": case.observation_count,
                "sides": sides,
            }
        )

    return {
        "schema": SCHEMA,
        "status": "OBSERVATIONAL_NOT_PROMOTED",
        "target": {
            "game_id": game_id,
            "battle_turn": turn,
            "site": [context.get("x"), context.get("y")],
            "vcr_ids": list(vcr_ids),
        },
        "database_path": database_path,
        "vcr_rows": rows,
        "summary": {
            "vcr_count": len(rows),
            "side_count": 2 * len(rows),
            "seed_observations": [
                {"vcr_id": row["vcr_id"], "seed": row["seed"]}
                for row in rows
            ],
            "field_observation_counts": dict(sorted(field_counts.items())),
            "field_status_counts": dict(sorted(field_status_counts.items())),
        },
        "evidence_boundary": (
            "Research-only observational audit using factual current-VCR "
            "payloads as comparison targets and T-1 raw predictions as "
            "candidate sources. No observed equality promotes a Host rule; "
            "no derived static field or seed is supplied to site_executor. "
            "VCRs 592..595 are observational inputs, not held-out predictions; "
            "no observed field is injected into the mutable executor. "
            "Site-context acquisition may reconstruct historical appearance "
            "traces, which this matrix deliberately discards."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-db-root", type=Path, required=True)
    parser.add_argument("--corpus-db-generation", required=True)
    parser.add_argument("--game-id", type=int, default=400330)
    parser.add_argument("--battle-turn", type=int, default=141)
    parser.add_argument("--x", type=int, default=1674)
    parser.add_argument("--y", type=int, default=2363)
    parser.add_argument("--start-vcr-id", type=int, default=592)
    parser.add_argument("--end-vcr-id", type=int, default=595)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.end_vcr_id < args.start_vcr_id:
            raise ValueError("end VCR must be >= start VCR")
        conn, dbpath = connect_compact_generation_read_only(
            args.corpus_db_generation, args.corpus_db_root
        )
        try:
            context, _appearances, _summary, _visited = (
                site_differential._target_context(
                    connection=conn,
                    game_id=args.game_id,
                    battle_turn=args.battle_turn,
                    x=args.x,
                    y=args.y,
                )
            )
            cases = combat_vcr_cases_for_turns(
                conn, game_id=args.game_id, battle_turns={args.battle_turn}
            )
        finally:
            conn.close()
        report = build_report(
            context=context,
            cases=cases,
            game_id=args.game_id,
            turn=args.battle_turn,
            vcr_ids=tuple(range(args.start_vcr_id, args.end_vcr_id + 1)),
            database_path=str(dbpath),
        )
    except (ValueError, OSError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("===== SITE COMBAT PAYLOAD PROVENANCE V1 =====")
    print("status:", report["status"])
    print("VCR observations:", report["summary"]["vcr_count"])
    for vcr in report["vcr_rows"]:
        print(f"V{vcr['vcr_id']} pair={vcr['pair']} seed={vcr['seed']}")
        for side in vcr["sides"]:
            exact = [
                x["field"] for x in side["direct_field_observations"]
                if x["status"] == "observed_equal"
            ]
            different = [
                {
                    "field": x["field"],
                    "tminus1": x["tminus1_candidate"],
                    "vcr": x["current_vcr_observed"],
                }
                for x in side["direct_field_observations"]
                if x["status"] == "observed_different"
            ]
            unresolved = [
                x["field"] for x in side["direct_field_observations"]
                if x["status"].startswith("unresolved_")
            ]
            print(
                f"  {side['side']} ship={side['ship_id']} "
                f"tminus1_source={side['prediction_source']} "
                f"equal={exact} different={different} unresolved={unresolved}"
            )
    print("output:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
