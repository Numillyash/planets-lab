"""M2: covariates for conditional mineral residuals in baseline68 archives.

No per-planet state is returned. Owner ships/base *observed* in the
same perspective are NOT independently authenticated orders or proof of
no other ships. In particular a missing infoturn is retained as an
explicit ship position freshness limitation.

The candidate uses the SAME public default assumptions as the
existing m2_mineral_balance.py (race, mines, density, rate, modifier).
An independent count invariant against that module is enforced in
the corpus aggregator: any divergence fails the whole diagnostic.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Any

from planets_lab.rules.mining import (
    DEFAULT_TRANS_URANIUM_RATE, mined_amount, mining_rate_for_race,
    trans_uranium_mutation_amount,
)
from planets_lab.corpus.m2_mineral_balance import (
    MINERALS, _valid_race_pair, _unsigned, _magnitude,
)

CATEGORIES = (
    "both_exact", "ground_exact_surface_residual",
    "surface_exact_ground_residual", "neither_exact",
)
TECH_KEYS = ("hulltechlevel", "enginetechlevel", "beamtechlevel", "torptechlevel")
MINERAL_CARGO = MINERALS
COUNT_FIELDS = ("mines", "factories", "defense", "colonisttaxrate", "nativetaxrate")


def _valid_xy(raw: Mapping[str, Any]) -> tuple[int, int] | None:
    x, y = raw.get("x"), raw.get("y")
    if type(x) is int and type(y) is int and 0 <= x <= 10000 and 0 <= y <= 10000:
        return (x, y)
    return None


def _index_owner_ships(payload: Mapping[str, Any], *, player: int, turn: int):
    """Owner ship positions, not a complete view of all actual ship traffic."""
    raw = payload.get("ships")
    if not isinstance(raw, list):
        return {}, {"ABSTAIN_SHIP_ARRAY_MISSING": 1}
    ships: dict[int, Mapping[str, Any]] = {}
    duplicate = set()
    statuses = Counter()
    for ship in raw:
        if not isinstance(ship, Mapping):
            statuses["ABSTAIN_SHIP_ROW_NONOBJECT"] += 1
            continue
        if ship.get("ownerid") != player:
            continue
        sid = ship.get("id")
        if type(sid) is not int or sid <= 0:
            statuses["ABSTAIN_OWNER_SHIP_ID_MISSING"] += 1
            continue
        infoturn = ship.get("infoturn")
        if infoturn is not None and (type(infoturn) is not int or infoturn != turn):
            statuses["ABSTAIN_OWNER_SHIP_STALE"] += 1
            continue
        if infoturn is None:
            statuses["OWNER_SHIP_INFOTURN_UNAVAILABLE"] += 1
        if _valid_xy(ship) is None:
            statuses["ABSTAIN_OWNER_SHIP_COORDS_UNAVAILABLE"] += 1
            continue
        if sid in ships:
            duplicate.add(sid)
        else:
            ships[sid] = ship
    for sid in duplicate:
        del ships[sid]
    statuses["ABSTAIN_DUPLICATE_OWNER_SHIP_ID"] += len(duplicate)
    return ships, dict(statuses)


def _index_owner_bases(
    payload: Mapping[str, Any], *,
    player: int, turn: int, owned_current_planet_ids: set[int],
):
    """Return (explicit owner bases, ownerless planet-linked bases, quality).

    A base with a known DIFFERENT owner never qualifies, even when its
    planetid happens to be a currently owned planet ID. A base without
    ownerid may be associated only to an authenticated owner-current
    PLANET in the SAME perspective and turn; this is a weak *planet
    link*, NOT verification that this was an owned or active base.
    """
    raw = payload.get("starbases")
    if not isinstance(raw, list):
        return {}, {}, {"ABSTAIN_STARBASE_ARRAY_MISSING": 1}
    explicit: dict[int, Mapping[str, Any]] = {}
    linked: dict[int, Mapping[str, Any]] = {}
    seen: set[int] = set()
    duplicate: set[int] = set()
    statuses: Counter[str] = Counter()
    for base in raw:
        if not isinstance(base, Mapping):
            statuses["ABSTAIN_STARBASE_ROW_NONOBJECT"] += 1
            continue
        pid = base.get("planetid")
        if type(pid) is not int or pid <= 0:
            statuses["ABSTAIN_STARBASE_PLANETID_MISSING"] += 1
            continue
        # Any duplicate planetid makes the entire link ambiguous,
        # including explicit-vs-ownerless copies.
        if pid in seen:
            duplicate.add(pid)
            continue
        seen.add(pid)
        owner = base.get("ownerid")
        if owner != player:
            if owner is None:
                statuses["STARBASE_OWNERID_UNAVAILABLE"] += 1
                if pid not in owned_current_planet_ids:
                    statuses["ABSTAIN_OWNERLESS_BASE_PLANET_NOT_OWNER_CURRENT"] += 1
                    continue
            else:
                if pid in owned_current_planet_ids:
                    statuses["ABSTAIN_CONFLICTING_EXPLICIT_BASE_OWNER"] += 1
                continue
        infoturn = base.get("infoturn")
        if infoturn is not None and (type(infoturn) is not int or infoturn != turn):
            statuses["ABSTAIN_STARBASE_STALE"] += 1
            continue
        if infoturn is None:
            statuses["STARBASE_INFOTURN_UNAVAILABLE"] += 1
        if owner == player:
            explicit[pid] = base
        else:
            linked[pid] = base
            statuses["OWNERLESS_BASE_PLANETLINK_CANDIDATE_NOT_OWNER_VERIFIED"] += 1
    for pid in duplicate:
        explicit.pop(pid, None)
        linked.pop(pid, None)
    statuses["ABSTAIN_DUPLICATE_STARBASE_PLANETID"] += len(duplicate)
    return explicit, linked, dict(statuses)



def _candidate_for_mineral(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    mineral: str, race: int | None,
) -> tuple[str, int] | None:
    mines = _unsigned(before, "mines")
    if mines is None or mines != _unsigned(after, "mines") or race is None:
        return None
    density = _unsigned(before, "density" + mineral)
    if density is None or density > 100 or density != _unsigned(after, "density" + mineral):
        return None
    g0 = _unsigned(before, "ground" + mineral)
    g1 = _unsigned(after, "ground" + mineral)
    s0 = _unsigned(before, mineral)
    s1 = _unsigned(after, mineral)
    if None in (g0, g1, s0, s1):
        return None
    mining = mined_amount(
        mines=mines, density=density, ground_amount=g0,
        mining_rate_percent=mining_rate_for_race(race),
        output_modifier_percent=100,
    )
    mutation = trans_uranium_mutation_amount(
        density=density, mutation_rate=DEFAULT_TRANS_URANIUM_RATE,
    )
    delta_surface, delta_ground = s1 - s0, g1 - g0
    residual_surface = delta_surface - mining
    ground_ok = delta_ground == mutation - mining
    surface_ok = residual_surface == 0
    category = (
        "both_exact" if ground_ok and surface_ok else
        "ground_exact_surface_residual" if ground_ok else
        "surface_exact_ground_residual" if surface_ok else "neither_exact"
    )
    return category, residual_surface


def _starbase_tech_changed(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool | None:
    values = [(a.get(name), b.get(name)) for name in TECH_KEYS]
    if not all(type(x) is int and 0 <= x <= 10 for pair in values for x in pair):
        return None
    return any(x != y for x, y in values)


def _observed_ship_context(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    xy_before: tuple[int, int] | None,
    xy_after: tuple[int, int] | None,
    ships_before: Mapping[int, Mapping[str, Any]],
    ships_after: Mapping[int, Mapping[str, Any]],
    mineral: str, residual: int,
) -> Counter[str]:
    out = Counter()
    if xy_before is None or xy_after is None:
        out["ABSTAIN_PLANET_COORDS_MISSING"] += 1
        return out
    out["planet_coordinates_qualified"] += 1
    if not isinstance(before.get("ships"), list) or not isinstance(after.get("ships"), list):
        out["ABSTAIN_SHIP_SECTION_MISSING_ONE_OR_BOTH"] += 1
        return out
    out["owner_ship_section_pair_qualified"] += 1
    a = {sid: item for sid, item in ships_before.items() if _valid_xy(item) == xy_before}
    b = {sid: item for sid, item in ships_after.items() if _valid_xy(item) == xy_after}
    if a:
        out["owner_ship_observed_at_site_before"] += 1
    if b:
        out["owner_ship_observed_at_site_after"] += 1
    if a and b:
        out["owner_ship_observed_at_site_both"] += 1
    # Without a ship infoturn property, cargo differences have weaker
    # provenance than owner-current planet stocks.
    both_ids = a.keys() & b.keys()
    if both_ids:
        out["same_owner_ship_id_observed_at_site_both"] += 1
    opposite = []
    for shipid in both_ids:
        one, two = a[shipid], b[shipid]
        c0, c1 = _unsigned(one, mineral), _unsigned(two, mineral)
        if c0 is None or c1 is None:
            out["ABSTAIN_OWNER_SHIP_CARGO_MISSING"] += 1
            continue
        out["same_ship_cargo_pair_qualified"] += 1
        if residual != 0 and c1 - c0 == -residual:
            opposite.append(shipid)
    if len(opposite) == 1:
        out["one_ship_opposite_cargo_delta_candidate"] += 1
        shipid = opposite[0]
        one, two = a[shipid], b[shipid]
        if (one.get("infoturn") is not None and
                two.get("infoturn") is not None):
            out["opposite_cargo_ship_both_freshness_explicit"] += 1
        else:
            out["opposite_cargo_ship_freshness_unverified"] += 1
    elif len(opposite) > 1:
        out["ABSTAIN_MULTIPLE_OPPOSITE_CARGO_SHIPS"] += 1
    # Only an unchanged set of co-site ship IDs with every cargo
    # value observed makes a whole-visible-fleet balance meaningful.
    # This still does not prove absent ships or executed transfers.
    if a and set(a) == set(b):
        cargo_pairs = [
            (_unsigned(a[sid], mineral), _unsigned(b[sid], mineral))
            for sid in sorted(a)
        ]
        if all(p is not None and q is not None for p, q in cargo_pairs):
            out["same_site_identical_ship_set_all_cargo_qualified"] += 1
            if len(a) > 1:
                out["multiple_co_site_ship_ids_all_cargo_qualified"] += 1
                if sum(q - p for p, q in cargo_pairs) == -residual and residual != 0:
                    out["multiple_ship_cargo_sum_opposite_candidate_not_order"] += 1
        else:
            out["ABSTAIN_WHOLE_SITE_CARGO_MISSING"] += 1
    if not a and not b:
        out["NO_OWNER_SHIP_OBSERVED_AT_SITE_NOT_ABSENCE_PROOF"] += 1
    return out


def profile_surface_residual_context(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    owned_before: Mapping[int, Mapping[str, Any]],
    owned_after: Mapping[int, Mapping[str, Any]],
    *,
    player: int,
) -> dict[str, Any]:
    """Return *only aggregate counters*; never IDs, ship records or stock values."""
    race = _valid_race_pair(before, after)
    turn_before = before.get("game", {}).get("turn") if isinstance(before.get("game"), Mapping) else None
    turn_after = after.get("game", {}).get("turn") if isinstance(after.get("game"), Mapping) else None
    ships_b, ship_status_b = _index_owner_ships(before, player=player, turn=turn_before)
    ships_a, ship_status_a = _index_owner_ships(after, player=player, turn=turn_after)
    bases_b, linked_b, base_status_b = _index_owner_bases(
        before, player=player, turn=turn_before,
        owned_current_planet_ids=set(owned_before),
    )
    bases_a, linked_a, base_status_a = _index_owner_bases(
        after, player=player, turn=turn_after,
        owned_current_planet_ids=set(owned_after),
    )
    categories: dict[str, Counter[str]] = defaultdict(Counter)
    covariates: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    bins: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for pid in sorted(owned_before.keys() & owned_after.keys()):
        planet_b, planet_a = owned_before[pid], owned_after[pid]
        pbxy, paxy = _valid_xy(planet_b), _valid_xy(planet_a)
        for mineral in MINERALS:
            c = _candidate_for_mineral(planet_b, planet_a, mineral, race)
            if c is None:
                continue
            status, residual = c
            categories[mineral][status] += 1
            dst = covariates[mineral][status]
            if residual < 0:
                dst["surface_residual_negative"] += 1
            elif residual > 0:
                dst["surface_residual_positive"] += 1
            else:
                dst["surface_residual_zero"] += 1
            bins[mineral][status][_magnitude(abs(residual))] += 1
            if all(type(planet_b.get(name)) is int and
                   type(planet_a.get(name)) is int and
                   planet_b[name] >= 0 and planet_a[name] >= 0
                   for name in COUNT_FIELDS):
                dst["structure_and_tax_controls_qualified"] += 1
                if all(planet_b[name] == planet_a[name] for name in COUNT_FIELDS):
                    dst["structure_and_tax_controls_unchanged"] += 1
                else:
                    dst["structure_or_tax_controls_changed"] += 1
            if pid in bases_b:
                dst["owner_starbase_explicit_at_planet_before"] += 1
            if pid in bases_a:
                dst["owner_starbase_explicit_at_planet_after"] += 1
            if pid in bases_b and pid in bases_a:
                dst["owner_starbase_explicit_at_planet_both"] += 1
                changed = _starbase_tech_changed(bases_b[pid], bases_a[pid])
                if changed is True:
                    dst["observed_starbase_tech_changed"] += 1
                elif changed is False:
                    dst["observed_starbase_tech_unchanged"] += 1
                else:
                    dst["ABSTAIN_STARBASE_TECH_FIELDS_MISSING"] += 1
            if pid in linked_b:
                dst["ownerless_base_planetlinked_before_not_owner_proof"] += 1
            if pid in linked_a:
                dst["ownerless_base_planetlinked_after_not_owner_proof"] += 1
            if pid in linked_b and pid in linked_a:
                dst["ownerless_base_planetlinked_both_not_owner_proof"] += 1
                changed = _starbase_tech_changed(linked_b[pid], linked_a[pid])
                if changed is True:
                    dst["ownerless_planetlinked_tech_changed_observed"] += 1
                elif changed is False:
                    dst["ownerless_planetlinked_tech_unchanged_observed"] += 1
                else:
                    dst["ABSTAIN_OWNERLESS_PLANETLINK_TECH_FIELDS_MISSING"] += 1
            if (pid in bases_b or pid in linked_b) and (
                pid in bases_a or pid in linked_a
            ):
                dst["planetlinked_base_both_any_owner_provenance"] += 1
                if (pid in bases_b) != (pid in bases_a):
                    dst["planetlinked_base_owner_provenance_changed"] += 1
            dst.update(_observed_ship_context(
                before, after, pbxy, paxy, ships_b, ships_a, mineral, residual,
            ))
    return {
        "per_mineral_categories": {
            name: dict(sorted(counts.items())) for name, counts in sorted(categories.items())
        },
        "per_mineral_category_covariates": {
            name: {
                cat: dict(sorted(counts.items()))
                for cat, counts in sorted(classified.items())
            }
            for name, classified in sorted(covariates.items())
        },
        "per_mineral_category_surface_residual_magnitude_buckets": {
            name: {
                cat: dict(sorted(counts.items()))
                for cat, counts in sorted(classified.items())
            }
            for name, classified in sorted(bins.items())
        },
        "source_quality": dict(sorted((
            Counter(ship_status_b) + Counter(ship_status_a) +
            Counter(base_status_b) + Counter(base_status_a)
        ).items())),
        "evidence_status": "ARCHIVAL_COVARIATES_NOT_ORDERS_OR_HOST_CAUSES",
    }
