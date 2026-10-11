"""Observed same-turn VCR-ID ship chains vs independently replayed terminal state.

The PRIOR VCR's current combat payload, factual seed, weapon specs and combat
RNG setting are allowed as replay inputs; the NEXT VCR is *comparator only*.
This validates possible chronology and carried state, NOT precombat attack
selection, independent terminal clans, or a generative NuHost battle engine.

Selection: 4 frozen Horwasp repeated-ship chains (5 transitions) plus all
other standard-ship repeated chains in those exact game-turns; never select on
mass differences, replay success or comparator values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from planets_lab.corpus.combat_vcr_runtime import combat_vcr_cases_for_turns
from planets_lab.corpus.corpus_db_runtime import connect_compact_generation_read_only
from planets_lab.rules.combat import ReplayUnsupported, replay_nuhost_from_nu_catalog

SCHEMA = "planets-lab.combat-horwasp-terminal-continuity.v1"
STATUS = "OBSERVED_ID_ORDER_TERMINAL_CONTINUITY_NOT_HOST_CHRONOLOGY"
SOURCE_SCHEMA = "planets-lab.combat-mass-horwasp-tminus1-first-vcr.v1"
SOURCE_STATUS = "HORWASP_TMINUS1_LINEAR_FLOOR_HYPOTHESIS_NOT_PROMOTED"
SOURCE_BLOB = "358c354d424907488dffd3665e6d6d07c8d04f64"
GENERATION = "generations/corpus-v2compact-public100-20261005T181128Z-7578e4b559b4.duckdb"
GENERATION_SHA256 = "3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c"
CARRY_FIELDS = ("shield", "damage", "crew", "torpedoes", "fighters")
VCR_START_FIELDS = {"shield": "shield", "damage": "damage", "crew": "crew",
                    "torpedoes": "torpedos", "fighters": "fighters"}


def integer(x: Any) -> int | None:
    return x if type(x) is int else None


def blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def progress(msg: str) -> None:
    print(f"[horwasp-chain] {msg}", flush=True)


def frozen_horwasp_chains(source: Mapping[str, Any]) -> dict[tuple[int, int, int, int], list[dict[str, Any]]]:
    if source.get("schema") != SOURCE_SCHEMA or source.get("status") != SOURCE_STATUS:
        raise ValueError("frozen Horwasp source schema/status mismatch")
    summary = source.get("population")
    chains = source.get("repeated_ship_VCR_ID_chains")
    rows = source.get("frozen_horwasp_side_evaluations")
    if (not isinstance(summary, Mapping)
            or summary.get("original_horwasp_sides") != 26
            or summary.get("distinct_horwasp_ships_by_game_turn_owner") != 21
            or not isinstance(chains, list) or len(chains) != 4
            or not isinstance(rows, list) or len(rows) != 26
            or source.get("summary_repeated_by_VCR_ID", {}).get("sides") != 5):
        raise ValueError("frozen 26-side / 4-chain population drift")
    expected = {}
    for chain in chains:
        key = tuple(chain.get(k) for k in ("game_id", "turn", "owner_id", "ship_id"))
        if any(integer(v) is None or v <= 0 for v in key) or key in expected:
            raise ValueError("duplicate/invalid Horwasp repeated ship key")
        raw = chain.get("VCRs_by_id_NOT_proven_execution_sequence")
        if not isinstance(raw, list) or len(raw) < 2:
            raise ValueError("frozen chain has no repeated VCR")
        items = sorted(raw, key=lambda x:x.get("vcr_id", -1))
        ids = [integer(x.get("vcr_id")) for x in items]
        if any(v is None or v <= 0 for v in ids) or len(set(ids)) != len(ids):
            raise ValueError("frozen repeated VCR IDs invalid/duplicate")
        expected[key] = [{"vcr_id": x["vcr_id"], "side": x["side"],
                          "observed_VCR_mass_KT": x["observed_VCR_mass_KT"]}
                         for x in items]
    if sum(len(x)-1 for x in expected.values()) != 5:
        raise ValueError("frozen expected transition count changed")
    # Exact identity/mass consistency with detailed frozen 26-side cohort.
    observed = {(r["game_id"], r["turn"], r["owner_id"], r["ship_id"],
                 r["vcr_id"], r["side"]):r for r in rows}
    for key, items in expected.items():
        for x in items:
            member = observed.get((*key, x["vcr_id"], x["side"]))
            if member is None or member.get("evaluation", {}).get("observed_vcr_mass_KT") != x["observed_VCR_mass_KT"]:
                raise ValueError("frozen Horwasp detail/chain evidence mismatch")
    return expected


def ship_chain_groups(cases: Mapping[tuple[int, int], Any], *,
                      game: int, turn: int) -> dict[tuple[int, int, int, int], list[dict[str, Any]]]:
    """Metadata-only identity selection, no observed mass, terminal or RNG."""
    grouped: dict[tuple[int, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for (t, vid), case in sorted(cases.items()):
        if t != turn or integer(vid) is None or vid <= 0:
            raise ValueError("inconsistent VCR game-turn key")
        payload = case.payload
        if not isinstance(payload, Mapping):
            continue
        sides = []
        for side in ("left", "right"):
            p = payload.get(side)
            if not isinstance(p, Mapping):
                continue
            hull, ship = integer(p.get("hullid")), integer(p.get("objectid"))
            owner = integer(payload.get(side+"ownerid"))
            race = integer(p.get("raceid"))
            if (hull is None or hull <= 0 or ship is None or ship <= 0 or
                    owner is None or owner <= 0 or race is None or race <= 0):
                continue
            sides.append((side, owner, ship, race))
        # A ship cannot be simultaneously left and right in one VCR.
        if len({(x[1], x[2]) for x in sides}) != len(sides):
            raise ValueError("same ship appears twice in one VCR")
        for side, owner, ship, race in sides:
            grouped[(game, turn, owner, ship)].append(
                {"vcr_id": vid, "side": side, "raceid": race}
            )
    result = {}
    for key, events in grouped.items():
        if len(events) < 2:
            continue
        if len({x["raceid"] for x in events}) != 1:
            continue # identity changed; not a constant-owner/race control chain
        ids = [x["vcr_id"] for x in events]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate VCR ID in ship chain")
        result[key] = sorted(events, key=lambda x:x["vcr_id"])
    return result


def _side_at(case: Any, appearance: Mapping[str, Any], *, key: tuple[int, int, int, int]) -> Mapping[str, Any]:
    side = appearance["side"]
    payload = case.payload
    p = payload.get(side)
    if not isinstance(p, Mapping):
        raise ValueError("frozen VCR participant missing")
    if (integer(p.get("objectid")) != key[3]
            or integer(payload.get(side+"ownerid")) != key[2]
            or integer(p.get("raceid")) != appearance["raceid"]):
        raise ValueError("VCR participant owner/ship/race drift")
    return p


def replay_current_vcr(case: Any, *, resolver: Callable[..., Mapping[str, Any]] = replay_nuhost_from_nu_catalog) -> dict[str, Any]:
    """Replay ONLY factual VCR N; do not read VCR N+1 inside this function."""
    try:
        output = resolver(
            case.payload, beams=case.beams, torpedoes=case.torpedoes,
            settings=case.settings,
        )
    except (ReplayUnsupported, ValueError, TypeError, KeyError) as exc:
        return {"status": "ABSTAIN_CLASSIC_REPLAY_UNAVAILABLE",
                "reason": f"{type(exc).__name__}: {exc}",
                "terminals": {}}
    if not isinstance(output, Mapping):
        return {"status": "ABSTAIN_CLASSIC_REPLAY_MALFORMED",
                "reason": "replay output is not a mapping", "terminals": {}}
    terminals = {}
    for side in ("left", "right"):
        raw = output.get(side)
        if not isinstance(raw, Mapping):
            return {"status": "ABSTAIN_CLASSIC_REPLAY_MALFORMED",
                    "reason": f"missing replay {side} terminal", "terminals": {}}
        terminals[side] = {
            k: raw.get(k) for k in
            ("object_id", "destroyed", "captured", *CARRY_FIELDS)
        }
    return {
        "status": "CLASSIC_CURRENT_VCR_REPLAY_AVAILABLE",
        "terminals": terminals,
        "engine": output.get("engine"),
        "basis": output.get("basis"),
    }


def compare_terminal_to_next(
    previous: Mapping[str, Any], next_start: Mapping[str, Any],
    *, ship_id: int,
) -> dict[str, Any]:
    if previous.get("status") != "CLASSIC_CURRENT_VCR_REPLAY_AVAILABLE":
        return {"status": previous.get("status", "ABSTAIN_REPLAY_UNKNOWN"),
                "fields": {}, "all_fields_equal": None}
    terminal = previous["terminals"].get(next_start["previous_side"])
    if (not isinstance(terminal, Mapping)
            or integer(terminal.get("object_id")) != ship_id):
        return {"status": "ABSTAIN_TERMINAL_SHIP_ID_DRIFT", "fields": {},
                "all_fields_equal": None}
    raw = next_start["next_participant"]
    fields = {}
    for field in CARRY_FIELDS:
        prev = integer(terminal.get(field))
        factual = integer(raw.get(VCR_START_FIELDS[field]))
        fields[field] = {
            "previous_replay_terminal": prev, "next_factual_start": factual,
            "equal": prev == factual if prev is not None and factual is not None else None,
        }
    all_valid = all(v["equal"] is not None for v in fields.values())
    if terminal.get("destroyed") is True or terminal.get("captured") is True:
        status = "REAPPEARANCE_AFTER_REPLAY_DEFEAT"
    elif not all_valid:
        status = "ABSTAIN_INCOMPLETE_TERMINAL_OR_NEXT_START"
    elif all(v["equal"] is True for v in fields.values()):
        status = "EXACT_CLASSIC_REPLAY_TERMINAL_TO_NEXT_START"
    else:
        status = "CLASSIC_REPLAY_TERMINAL_TO_NEXT_START_MISMATCH"
    return {
        "status": status,
        "fields": fields,
        "all_fields_equal": (
            all(v["equal"] is True for v in fields.values()) if all_valid else None
        ),
        "terminal_destroyed": terminal.get("destroyed"),
        "terminal_captured": terminal.get("captured"),
        "next_mass_is_only_observational": integer(raw.get("mass")),
        "no_terminal_clans_available": True,
    }


def audit_window(cases: Mapping[tuple[int, int], Any], *, game: int, turn: int,
                 frozen: Mapping[tuple[int, int, int, int], Sequence[Mapping[str, Any]]],
                 replay_resolver: Callable[..., Mapping[str, Any]] = replay_nuhost_from_nu_catalog) -> dict[str, Any]:
    groups = ship_chain_groups(cases, game=game, turn=turn)
    expected = {k:v for k,v in frozen.items() if k[:2] == (game, turn)}
    for key, entries in expected.items():
        got = groups.get(key)
        if got is None or [(x["vcr_id"],x["side"]) for x in got] != [
            (x["vcr_id"],x["side"]) for x in entries
        ] or any(x["raceid"] != 12 for x in got):
            raise ValueError(f"frozen Horwasp chain missing/drifted {key}")
        # Frozen *numeric* VCR masses are only validated after identity selection.
        for x in entries:
            case = cases.get((turn,x["vcr_id"]))
            party = _side_at(case, next(y for y in got if y["vcr_id"]==x["vcr_id"]),key=key)
            if integer(party.get("mass")) != x["observed_VCR_mass_KT"]:
                raise ValueError("frozen Horwasp current-VCR mass mismatch")
    output = []
    cached_replays = {}
    for key, seq in sorted(groups.items()):
        is_target = key in expected
        cohort = "FROZEN_HORWASP_REPEAT" if is_target else "SAME_GAME_TURN_CONTROL"
        for first, nxt in zip(seq, seq[1:]):
            before = cases[(turn,first["vcr_id"])]
            before_party = _side_at(before,first,key=key)
            # Replay BEFORE accessing next-case participant/mass/state.
            if first["vcr_id"] not in cached_replays:
                cached_replays[first["vcr_id"]] = replay_current_vcr(
                    before, resolver=replay_resolver
                )
            replay = cached_replays[first["vcr_id"]]
            after = cases[(turn,nxt["vcr_id"])]
            next_party = _side_at(after,nxt,key=key)
            cmp = compare_terminal_to_next(
                replay,
                {"previous_side": first["side"], "next_participant": next_party},
                ship_id=key[3],
            )
            output.append({
                "game_id": game, "turn": turn,
                "owner_id": key[2], "ship_id": key[3],
                "raceid": first["raceid"], "cohort": cohort,
                "prior_VCR_id": first["vcr_id"], "prior_side": first["side"],
                "next_VCR_id": nxt["vcr_id"], "next_side": nxt["side"],
                "ID_order_is_independent_host_execution_order": False,
                "prior_VCR_factual_setup_and_seed_used_for_replay": True,
                "later_VCR_start_used_only_after_prior_replay": True,
                "prior_replay": {
                    "status": replay["status"], "reason": replay.get("reason"),
                    "engine": replay.get("engine"), "basis": replay.get("basis"),
                },
                "terminal_next_continuity": cmp,
                "observed_VCR_mass_delta_NEXT_minus_PRIOR_KT": (
                    integer(next_party.get("mass")) - integer(before_party.get("mass"))
                    if integer(next_party.get("mass")) is not None
                    and integer(before_party.get("mass")) is not None else None
                ),
                "terminal_clans_reconstructed": False,
            })
    return {"game_id":game, "turn":turn,"total_VCRs":len(cases),
            "frozen_horwasp_chains":len(expected),
            "all_same_turn_identity_chains":len(groups),
            "transitions":output}


def report(source: Mapping[str, Any], conn: Any) -> dict[str, Any]:
    frozen = frozen_horwasp_chains(source)
    windows = sorted({k[:2] for k in frozen})
    results = []
    for i,(game,turn) in enumerate(windows,1):
        progress(f"[{i}/{len(windows)}] G{game} T{turn} reading VCRs and replaying N before N+1 comparator")
        cases = combat_vcr_cases_for_turns(conn,game_id=game,battle_turns={turn})
        result = audit_window(cases,game=game,turn=turn,frozen=frozen)
        results.append(result)
        progress(f"[{i}/{len(windows)}] chains={result['all_same_turn_identity_chains']} transitions={len(result['transitions'])}")
    transitions = [x for window in results for x in window["transitions"]]
    target = [r for r in transitions if r["cohort"]=="FROZEN_HORWASP_REPEAT"]
    controls = [r for r in transitions if r["cohort"]=="SAME_GAME_TURN_CONTROL"]
    if len(target) != 5:
        raise ValueError("not all 5 frozen Horwasp transitions covered")
    def aggregate(rows):
        return {
            "transitions":len(rows),
            "continuity_statuses":dict(sorted(Counter(
                x["terminal_next_continuity"]["status"] for x in rows
            ).items())),
            "replay_statuses":dict(sorted(Counter(
                x["prior_replay"]["status"] for x in rows
            ).items())),
        }
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_frozen_horwasp_git_blob_sha1":SOURCE_BLOB,
        "source_db_generation":GENERATION,
        "source_db_sha256":GENERATION_SHA256,
        "summary":{
            "frozen_horwasp_chains":len(frozen),
            "distinct_windows":len(windows),
            "frozen_horwasp":aggregate(target),
            "same_game_turn_non_horwasp_controls":aggregate(controls),
            "host_execution_order_independently_proven":False,
            "combat_mass_or_clan_loss_predicted":False,
        },
        "window_results":results,
        "boundaries":(
            "Prior VCR N seed/setup/weapon catalog are factual inputs for a "
            "derived deterministic Classic replay; next VCR N+1 is only a "
            "comparator after N terminal calculated. The method cannot prove "
            "Host VCR ID order and has NO terminal clan state, so independent "
            "clan-loss counts or next-VCR combat mass remain unpredicted. "
            "Missing/unsupported replay is an explicit abstention. "
            "No production/executor/corpus mutation."
        ),
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-horwasp",type=Path,required=True)
    p.add_argument("--corpus-db-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        raw=a.frozen_horwasp.read_bytes()
        if blob_sha1(raw)!=SOURCE_BLOB:
            raise ValueError("frozen published Horwasp report Git blob SHA mismatch")
        frozen=json.loads(raw)
        frozen_horwasp_chains(frozen)
        db=a.corpus_db_root/GENERATION
        if not db.is_file(): raise ValueError("pinned immutable public100 missing")
        start=time.monotonic()
        progress(f"verifying immutable corpus SHA256: {db.name}")
        with db.open("rb") as f:
            sha=hashlib.file_digest(f,"sha256").hexdigest()
        if sha!=GENERATION_SHA256:raise ValueError("immutable corpus SHA256 mismatch")
        progress(f"SHA256 verified in {time.monotonic()-start:.1f}s")
        conn, dbpath=connect_compact_generation_read_only(GENERATION,a.corpus_db_root)
        try: result=report(frozen,conn)
        finally: conn.close()
        result["db_path"]=str(dbpath)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        temp=a.output.with_name(a.output.name+".tmp")
        temp.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        temp.replace(a.output)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        return 2
    print("===== HORWASP SAME-TURN VCR REPLAY CONTINUITY V1 =====")
    print("status:",result["status"])
    print("summary:",result["summary"])
    print("output:",a.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
