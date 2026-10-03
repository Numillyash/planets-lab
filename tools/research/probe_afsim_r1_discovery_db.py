#!/usr/bin/env python3
"""Discovery-only differential probe for frozen external AFSim candidate AFSIM-R1.

This script deliberately imports the current main checkout for canonical Corpus
DB reconstruction while keeping the AFSim model and results on the dedicated
research branch.

Held-out input is not supported by this tool.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
import importlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from afsim_r1_model import AFSimShip, select_next_pair


SCHEMA = "planets-lab.external-afsim-r1-discovery.v1"
DEFAULT_MAIN_ROOT = Path("/root/projects/planets-lab")
DEFAULT_CORPUS_DB_ROOT = Path("/root/projects/planets-corpus-db")
DEFAULT_DISCOVERY_REL = Path("artifacts/public-capture-side/discovery-capture-side.json")
DEFAULT_OUTPUT = Path("artifacts/external-sources/afsim-r1/discovery-afsim-r1.json")


def _git_text(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _load_main_modules(
    main_root: Path,
    *,
    verified_main_head: str | None = None,
):
    """Load canonical modules from the separately mounted main checkout.

    When the Docker runner supplies verified_main_head, the host-side gate has
    already proved main branch and HEAD == origin/main before container launch.
    The slim canonical image intentionally does not install the git executable,
    so do not re-run git inside that container.
    """

    diagnostics = main_root / "tools" / "diagnostics"
    source = main_root / "src"
    if not diagnostics.is_dir() or not source.is_dir():
        raise ValueError(f"main checkout lacks diagnostics/src: {main_root}")

    if verified_main_head is not None:
        head = verified_main_head.strip().lower()
        if len(head) != 40 or any(ch not in "0123456789abcdef" for ch in head):
            raise ValueError(
                f"invalid --verified-main-head value: {verified_main_head!r}"
            )
    else:
        # Non-Docker fallback for direct local execution where git is present.
        if not (main_root / ".git").exists():
            raise ValueError(f"main checkout missing: {main_root}")
        branch = _git_text(main_root, "branch", "--show-current")
        if branch != "main":
            raise ValueError(
                f"canonical checkout must be on main, got {branch!r}: {main_root}"
            )
        head = _git_text(main_root, "rev-parse", "HEAD")
        try:
            origin_head = _git_text(main_root, "rev-parse", "origin/main")
        except subprocess.CalledProcessError:
            origin_head = ""
        if origin_head and head != origin_head:
            raise ValueError(
                "main checkout is not at origin/main; run git fetch/pull before probe: "
                f"HEAD={head} origin/main={origin_head}"
            )

    # Put canonical main code ahead of the research checkout.
    sys.path.insert(0, str(diagnostics))
    sys.path.insert(0, str(source))

    oprobe = importlib.import_module("combat_public_capture_o_layer_probe")
    active = importlib.import_module(
        "combat_host_post_capture_active_membership_audit"
    )
    return head, oprobe, active


def _int_field(raw: Mapping[str, Any], name: str) -> int | None:
    value = raw.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _replay_active_states(
    *,
    active_module: Any,
    context: Mapping[str, Any],
    capture: Mapping[str, Any],
    appearances: Mapping[tuple[int, int, int, int], Mapping[str, Any]],
) -> tuple[dict[int, dict[str, Any]] | None, str | None]:
    """Replay factual site history through the capture VCR and return live states.

    This is a state-exposing transcription of the already-used canonical main
    active-membership diagnostic.  It does not invent future history.
    """

    game_id = int(context["game_id"])
    battle_turn = int(context["battle_turn"])
    from_vcr_id = capture.get("from_vcr_id")
    if isinstance(from_vcr_id, bool) or not isinstance(from_vcr_id, int):
        return None, "capture_vcr_missing"

    factual_queue = context.get("factual_queue")
    predictions = context.get("predictions")
    site_rows = context.get("site_ship_rows")
    if (
        not isinstance(factual_queue, Sequence)
        or isinstance(factual_queue, (str, bytes))
        or not isinstance(predictions, Mapping)
        or not isinstance(site_rows, Mapping)
    ):
        return None, "site_context_incomplete"

    history = [
        row
        for row in factual_queue
        if isinstance(row, Mapping)
        and isinstance(row.get("vcr_id"), int)
        and not isinstance(row.get("vcr_id"), bool)
        and int(row["vcr_id"]) <= int(from_vcr_id)
    ]
    if not history or int(history[-1]["vcr_id"]) != int(from_vcr_id):
        return None, "capture_vcr_not_in_site_history"

    initial_ids = {int(ship_id) for ship_id in site_rows}
    for row in history:
        pair = row.get("pair")
        if (
            isinstance(pair, Sequence)
            and not isinstance(pair, (str, bytes))
            and len(pair) == 2
        ):
            for value in pair:
                if isinstance(value, int) and not isinstance(value, bool):
                    initial_ids.add(int(value))

    active_ships: dict[int, dict[str, Any]] = {}
    for ship_id in sorted(initial_ids):
        appearance = active_module._first_appearance(
            game_id=game_id,
            battle_turn=battle_turn,
            ship_id=ship_id,
            factual_queue=history,
            appearances=appearances,
        )
        if isinstance(appearance, Mapping):
            active = active_module.mutation_audit._active_ship_from_appearance(
                appearance,
                ship_id=ship_id,
            )
        else:
            entry = predictions.get(ship_id)
            if not isinstance(entry, Mapping):
                return None, f"initial_ship_state_missing:{ship_id}"
            active = active_module._raw_active_ship(entry, ship_id=ship_id)
        active_ships[ship_id] = dict(active)

    for row in history:
        vcr_id = int(row["vcr_id"])
        terminals, transfers, issue = active_module._terminal_batch_with_transfer(
            game_id=game_id,
            battle_turn=battle_turn,
            factual_vcr=row,
            appearances=appearances,
        )
        if issue is not None or terminals is None or transfers is None:
            return None, issue or f"terminal_batch_unresolved:{vcr_id}"

        missing = sorted(set(terminals) - set(active_ships))
        if missing:
            return None, "terminal_participant_not_active:" + ",".join(
                str(value) for value in missing
            )

        mutation = active_module.apply_ship_terminal_batch(
            active_ships=active_ships,
            terminals_by_ship_id=terminals,
            capture_transfers_by_ship_id=transfers,
        )
        if mutation.resolved is not True:
            reasons = ",".join(str(x) for x in mutation.unresolved_reasons)
            return None, "production_mutation_unresolved:" + reasons
        active_ships = {
            int(ship_id): dict(state)
            for ship_id, state in mutation.active_ships.items()
        }

    return active_ships, None


def _afsim_ships(
    *,
    context: Mapping[str, Any],
    active_states: Mapping[int, Mapping[str, Any]],
    fuel_mode: str,
) -> tuple[list[AFSimShip] | None, str | None]:
    predictions = context.get("predictions")
    if not isinstance(predictions, Mapping):
        return None, "predictions_missing"

    result: list[AFSimShip] = []
    for ship_id in sorted(active_states):
        state = active_states[ship_id]
        entry = predictions.get(ship_id)
        if not isinstance(entry, Mapping):
            return None, f"metadata_prediction_missing:{ship_id}"
        raw = entry.get("raw")
        if not isinstance(raw, Mapping):
            return None, f"raw_ship_missing:{ship_id}"

        mission = _int_field(raw, "mission")
        primary_enemy = _int_field(raw, "enemy")
        neutronium = _int_field(raw, "neutronium")
        friendly_code = raw.get("friendlycode")
        owner = state.get("owner_id")

        if (
            mission is None
            or primary_enemy is None
            or not isinstance(friendly_code, str)
            or isinstance(owner, bool)
            or not isinstance(owner, int)
            or int(owner) <= 0
        ):
            return None, f"order_metadata_unresolved:{ship_id}"
        if fuel_mode == "tminus1" and neutronium is None:
            return None, f"fuel_metadata_unresolved:{ship_id}"

        fuel = True if fuel_mode == "all_active" else int(neutronium) > 0
        result.append(
            AFSimShip(
                ship_id=int(ship_id),
                owner=int(owner),
                friendly_code=friendly_code,
                fuel=fuel,
                kill=mission == 3,
                primary_enemy=int(primary_enemy),
                crew=int(state.get("crew", 1)),
                damage=int(state.get("damage", 0)),
                beam_count=int(state.get("beam_count", 0)),
                torpedo_tubes=int(state.get("launcher_count", 0)),
                torpedoes=int(state.get("torpedoes", 0)),
                fighter_bays=int(state.get("bay_count", 0)),
                fighters=int(state.get("fighters", 0)),
            )
        )

    return result, None


def _pair_projection(pair: Any, *, prize_id: int) -> dict[str, Any]:
    if pair is None:
        return {
            "pair": None,
            "prize_side": None,
            "phase": None,
        }
    ids = [int(pair.left_id), int(pair.right_id)]
    return {
        "pair": ids,
        "initiator_id": int(pair.initiator_id),
        "opponent_id": int(pair.opponent_id),
        "phase": pair.phase,
        "prize_side": (
            "left"
            if int(pair.left_id) == prize_id
            else "right"
            if int(pair.right_id) == prize_id
            else None
        ),
    }


def _same_pair(prediction: Mapping[str, Any], expected: set[int]) -> bool | None:
    pair = prediction.get("pair")
    if pair is None:
        return False
    if (
        not isinstance(pair, Sequence)
        or isinstance(pair, (str, bytes))
        or len(pair) != 2
        or any(isinstance(v, bool) or not isinstance(v, int) for v in pair)
    ):
        return None
    return {int(pair[0]), int(pair[1])} == expected


def run(args: argparse.Namespace) -> dict[str, Any]:
    main_head, oprobe, active_module = _load_main_modules(
        args.main_root,
        verified_main_head=args.verified_main_head,
    )

    discovery_path = (
        args.discovery
        if args.discovery is not None
        else args.main_root / DEFAULT_DISCOVERY_REL
    )
    report = oprobe._load_capture_side_report(
        discovery_path,
        expected_partition="discovery",
    )
    observations = [
        dict(row)
        for row in report["observations"]
        if isinstance(row, Mapping)
    ]

    scan_ids_raw = report.get("scanned_game_ids")
    if (
        not isinstance(scan_ids_raw, Sequence)
        or isinstance(scan_ids_raw, (str, bytes))
    ):
        raise ValueError("discovery scanned_game_ids missing")
    scan_ids = {
        int(value)
        for value in scan_ids_raw
        if isinstance(value, int) and not isinstance(value, bool)
    }
    if not scan_ids:
        raise ValueError("discovery game population is empty")

    targets = oprobe._targets_by_site(observations)
    battle_turns_by_game: dict[int, set[int]] = defaultdict(set)
    for game_id, battle_turn, _x, _y in targets:
        battle_turns_by_game[int(game_id)].add(int(battle_turn))

    connection, database_path = oprobe.connect_current_compact_read_only(
        args.corpus_db_root
    )
    try:
        appearances: list[dict[str, Any]] = []
        appearance_summary: Counter[str] = Counter()
        for game_id in sorted(scan_ids):
            rows, summary = oprobe._collect_targeted_appearances_from_db(
                connection=connection,
                game_id=game_id,
                battle_turns=battle_turns_by_game.get(game_id, set()),
            )
            appearances.extend(rows)
            for key, value in summary.items():
                if isinstance(value, int) and not isinstance(value, bool):
                    appearance_summary[str(key)] += int(value)

        appearances_by_key = oprobe._appearance_mapping(appearances)

        counts: Counter[str] = Counter()
        examples: list[dict[str, Any]] = []
        visited: set[tuple[int, int, int, int]] = set()

        def observer(context: Mapping[str, Any]) -> None:
            site_key = (
                int(context["game_id"]),
                int(context["battle_turn"]),
                int(context["x"]),
                int(context["y"]),
            )
            for row in targets.get(site_key, ()):
                capture_vcr = row.get("capture_vcr_id")
                next_vcr = row.get("next_vcr_id")
                prize_id = row.get("captured_ship_id")
                opponent_id = row.get("next_opponent_ship_id")
                factual_side = row.get("captured_ship_side_next")

                identity = (capture_vcr, next_vcr, prize_id, opponent_id)
                if any(
                    isinstance(v, bool) or not isinstance(v, int) or v <= 0
                    for v in identity
                ):
                    counts["status:unresolved"] += 1
                    continue
                assert isinstance(capture_vcr, int)
                assert isinstance(next_vcr, int)
                assert isinstance(prize_id, int)
                assert isinstance(opponent_id, int)

                visited.add(
                    (site_key[0], site_key[1], capture_vcr, prize_id)
                )
                if next_vcr != capture_vcr + 1:
                    counts["status:not_comparable_nonadjacent"] += 1
                    continue

                capture = oprobe._capture_projection(row)
                active_states, issue = _replay_active_states(
                    active_module=active_module,
                    context=context,
                    capture=capture,
                    appearances=appearances_by_key,
                )
                if active_states is None:
                    counts["status:unresolved_active_state"] += 1
                    if len(examples) < args.example_limit:
                        examples.append(
                            {
                                "game_id": site_key[0],
                                "turn": site_key[1],
                                "x": site_key[2],
                                "y": site_key[3],
                                "capture_vcr_id": capture_vcr,
                                "next_vcr_id": next_vcr,
                                "captured_ship_id": prize_id,
                                "next_opponent_ship_id": opponent_id,
                                "status": "unresolved",
                                "reason": issue,
                            }
                        )
                    continue

                variants: dict[str, dict[str, Any]] = {}
                variant_issue = None
                for fuel_mode in ("tminus1", "all_active"):
                    ships, issue = _afsim_ships(
                        context=context,
                        active_states=active_states,
                        fuel_mode=fuel_mode,
                    )
                    if ships is None:
                        variant_issue = issue
                        break
                    pair = select_next_pair(ships)
                    variants[fuel_mode] = _pair_projection(
                        pair,
                        prize_id=prize_id,
                    )

                if variant_issue is not None:
                    counts["status:unresolved_metadata"] += 1
                    if len(examples) < args.example_limit:
                        examples.append(
                            {
                                "game_id": site_key[0],
                                "turn": site_key[1],
                                "x": site_key[2],
                                "y": site_key[3],
                                "capture_vcr_id": capture_vcr,
                                "next_vcr_id": next_vcr,
                                "captured_ship_id": prize_id,
                                "next_opponent_ship_id": opponent_id,
                                "status": "unresolved",
                                "reason": variant_issue,
                            }
                        )
                    continue

                expected_pair = {prize_id, opponent_id}
                factual = {
                    "pair": sorted(expected_pair),
                    "prize_side": (
                        factual_side
                        if factual_side in {"left", "right"}
                        else None
                    ),
                }
                for name, prediction in variants.items():
                    pair_exact = _same_pair(prediction, expected_pair)
                    side_exact = (
                        prediction.get("prize_side") == factual["prize_side"]
                        if prediction.get("prize_side") in {"left", "right"}
                        and factual["prize_side"] in {"left", "right"}
                        else None
                    )
                    prediction["pair_exact"] = pair_exact
                    prediction["side_exact"] = side_exact
                    counts[f"{name}:pair_exact:{str(pair_exact).lower()}"] += 1
                    if side_exact is not None:
                        counts[f"{name}:side_exact:{str(side_exact).lower()}"] += 1

                same_prediction = (
                    variants["tminus1"]["pair"]
                    == variants["all_active"]["pair"]
                    and variants["tminus1"]["phase"]
                    == variants["all_active"]["phase"]
                )
                if same_prediction:
                    counts["fuel_robust"] += 1
                    robust_pair_exact = variants["tminus1"]["pair_exact"]
                    counts[
                        "fuel_robust:pair_exact:"
                        + str(robust_pair_exact).lower()
                    ] += 1
                    if robust_pair_exact is True:
                        robust_side_exact = variants["tminus1"]["side_exact"]
                        counts[
                            "fuel_robust:side_exact:"
                            + str(robust_side_exact).lower()
                        ] += 1
                else:
                    counts["fuel_sensitive"] += 1

                counts["status:resolved"] += 1
                if len(examples) < args.example_limit:
                    examples.append(
                        {
                            "game_id": site_key[0],
                            "turn": site_key[1],
                            "x": site_key[2],
                            "y": site_key[3],
                            "capture_vcr_id": capture_vcr,
                            "next_vcr_id": next_vcr,
                            "captured_ship_id": prize_id,
                            "next_opponent_ship_id": opponent_id,
                            "factual": factual,
                            "variants": variants,
                            "fuel_robust": same_prediction,
                            "active_ship_ids": sorted(active_states),
                        }
                    )

        targeted_summaries: list[dict[str, Any]] = []
        for game_id in sorted(scan_ids):
            print(
                "progress: stage=afsim_r1_site_context "
                f"game_id={game_id} status=start",
                flush=True,
            )
            summary = oprobe._visit_targeted_site_contexts(
                connection=connection,
                game_id=game_id,
                targets=targets,
                appearances=appearances,
                observer=observer,
            )
            targeted_summaries.append({"game_id": game_id, **summary})
            print(
                "progress: stage=afsim_r1_site_context "
                f"game_id={game_id} sites={summary['visited_sites']} status=done",
                flush=True,
            )

        counts["capture_ship_rows"] = len(observations)
        counts["adjacent_rows"] = sum(
            1
            for row in observations
            if isinstance(row.get("capture_vcr_id"), int)
            and not isinstance(row.get("capture_vcr_id"), bool)
            and isinstance(row.get("next_vcr_id"), int)
            and not isinstance(row.get("next_vcr_id"), bool)
            and int(row["next_vcr_id"]) == int(row["capture_vcr_id"]) + 1
        )
        counts["observations_seen"] = len(visited)

        return {
            "schema": SCHEMA,
            "partition": "discovery",
            "evidence_status": "DISCOVERY_ONLY_EXTERNAL_AFSIM_R1_FROZEN",
            "model": "AFSIM-R1",
            "model_authority": "EXTERNAL_IMPLEMENTATION",
            "main_root": str(args.main_root),
            "main_head": main_head,
            "database_path": str(database_path),
            "source_capture_side_report": str(discovery_path),
            "summary": {
                "counts": dict(sorted(counts.items())),
                "appearance_summary": dict(sorted(appearance_summary.items())),
                "targeted_site_context": targeted_summaries,
            },
            "observations": examples,
            "mapping_notes": {
                "fuel_tminus1": (
                    "AFSim's explicit fuel-present flag is mapped to "
                    "T-1 neutronium > 0."
                ),
                "fuel_all_active": (
                    "Sensitivity variant sets fuel=true for every active ship. "
                    "Only predictions identical in both variants are fuel-robust."
                ),
                "capture_metadata": (
                    "AFSim capture changes owner/crew in the embedded VCR object; "
                    "KILL/PE/FC/fuel metadata remain attached to the persistent "
                    "entry and are normalized before the re-sort."
                ),
            },
            "evidence_boundary": (
                "Discovery-only differential test of the frozen external AFSim "
                "1.31 AFSIM-R1 model. Canonical site/history reconstruction is "
                "read from the current main checkout and shared Corpus DB in "
                "read-only mode. Only globally adjacent capture->next VCR rows "
                "are compared. Held-out input is not supported."
            ),
        }
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run frozen AFSIM-R1 against discovery capture rows via Corpus DB."
    )
    parser.add_argument("--main-root", type=Path, default=DEFAULT_MAIN_ROOT)
    parser.add_argument(
        "--verified-main-head",
        help=(
            "Host-verified 40-hex main HEAD. When supplied, skip git subprocess "
            "checks inside slim Docker images."
        ),
    )
    parser.add_argument("--corpus-db-root", type=Path, default=DEFAULT_CORPUS_DB_ROOT)
    parser.add_argument("--discovery", type=Path)
    parser.add_argument("--example-limit", type=int, default=200)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        counts = report["summary"]["counts"]
        print("===== AFSIM-R1 DISCOVERY / CORPUS DB =====")
        print(f"capture rows:                    {counts.get('capture_ship_rows', 0)}")
        print(f"adjacent rows:                   {counts.get('adjacent_rows', 0)}")
        print(f"resolved adjacent:               {counts.get('status:resolved', 0)}")
        print(f"unresolved active state:         {counts.get('status:unresolved_active_state', 0)}")
        print(f"unresolved metadata:             {counts.get('status:unresolved_metadata', 0)}")
        print(f"fuel robust:                     {counts.get('fuel_robust', 0)}")
        print(f"fuel sensitive:                  {counts.get('fuel_sensitive', 0)}")
        print(
            "fuel-robust pair exact/mismatch: "
            f"{counts.get('fuel_robust:pair_exact:true', 0)} / "
            f"{counts.get('fuel_robust:pair_exact:false', 0)}"
        )
        print(
            "fuel-robust side exact/mismatch: "
            f"{counts.get('fuel_robust:side_exact:true', 0)} / "
            f"{counts.get('fuel_robust:side_exact:false', 0)}"
        )
        print(
            "T-1 fuel pair exact/mismatch:    "
            f"{counts.get('tminus1:pair_exact:true', 0)} / "
            f"{counts.get('tminus1:pair_exact:false', 0)}"
        )
        print(
            "all-active pair exact/mismatch:  "
            f"{counts.get('all_active:pair_exact:true', 0)} / "
            f"{counts.get('all_active:pair_exact:false', 0)}"
        )
        print(f"main HEAD:                       {report['main_head']}")
        print(f"database:                        {report['database_path']}")
        print(f"output:                          {args.output}")
        return 0
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
        ImportError,
        AttributeError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
