"""M2: calibrate client ship-build component COST CONTRASTS from local HAR CSV.

This is a read-only test of an explicit ADDITIVE pricing hypothesis, not a
NuHost construction formula or permission to submit orders. No game/player
identifiers, HAR bodies, or notes are printed by default.

Critical identifiability: most observed configurations share components.
Repeating a recipe many times validates its total, NOT the absolute price
of its hull, drive, beam, or launcher separately. Treat each (game,hull,
engine) as an opaque bundled baseline until independently established.

Optional static-catalog comparison requires an explicitly SHA256-pinned
/static/all snapshot and per-game, explicit mapping from client BuildHullId
to catalog hull ID. NEVER silently equate those ID namespaces.
"""
from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping

from planets_lab.data.nu_specs import NuStaticSpecs, ResourceCost

SCHEMA = "planets-lab.m2-client-build-cost-calibration.v1"
FIELDS = ("MegaCredits", "Duranium", "Tritanium", "Molybdenum")
RECIPE_FIELDS = ("BuildHullId", "BuildEngineId", "BuildBeamId",
                 "BuildBeamCount", "BuildTorpedoId", "BuildTorpCount")
MAX_ROWS = 100000


@dataclass(frozen=True, slots=True)
class BuildCostObservation:
    game: str
    turn: int
    hull: int
    engine: int
    beam: int
    beam_count: int
    launcher: int
    launcher_count: int
    spending: tuple[int, int, int, int]
    tech_change: str

    @property
    def recipe(self) -> tuple[int, int, int, int, int, int]:
        return (self.hull, self.engine, self.beam, self.beam_count,
                self.launcher, self.launcher_count)

    @property
    def game_recipe(self) -> tuple[str, tuple[int, int, int, int, int, int]]:
        return self.game, self.recipe

    @property
    def isolated_from_recorded_tech_change(self) -> bool:
        return not self.tech_change


def _nonnegative(value: Any, field: str) -> int:
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise ValueError(f"{field}: invalid unsigned integer")
    return int(value)


def _is_true(raw: str) -> bool:
    return raw.strip().lower() == "true"


def read_client_build_costs_csv(path: str | Path) -> list[BuildCostObservation]:
    """Accept only complete client co-spending observations, not guesses."""
    result: list[BuildCostObservation] = []
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {"game", "turn", "is_complete_cost_pair", "tech_change",
                    *RECIPE_FIELDS, *(f"spent_{x}" for x in FIELDS)}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("missing client build cost CSV columns")
        for row in reader:
            if not _is_true(row["is_complete_cost_pair"]):
                # Incomplete resource baselines are not cost witnesses.
                continue
            if len(result) >= MAX_ROWS:
                raise ValueError("excessive build-cost observations")
            game = row["game"]
            if not game or not game.isascii() or not game.isdecimal():
                raise ValueError("invalid game identifier")
            ident = {key: _nonnegative(row[key], key) for key in RECIPE_FIELDS}
            if ident["BuildHullId"] <= 0 or ident["BuildEngineId"] <= 0:
                raise ValueError("empty hull/engine selection")
            for id_field, count_field in (("BuildBeamId", "BuildBeamCount"),
                                           ("BuildTorpedoId", "BuildTorpCount")):
                count, component = ident[count_field], ident[id_field]
                if count > 20 or (count == 0) != (component == 0):
                    raise ValueError("inconsistent component selection")
            spending = tuple(
                _nonnegative(row[f"spent_{resource}"], f"spent_{resource}")
                for resource in FIELDS
            )
            result.append(BuildCostObservation(
                game=game, turn=_nonnegative(row["turn"], "turn"),
                hull=ident["BuildHullId"], engine=ident["BuildEngineId"],
                beam=ident["BuildBeamId"], beam_count=ident["BuildBeamCount"],
                launcher=ident["BuildTorpedoId"],
                launcher_count=ident["BuildTorpCount"],
                spending=spending, tech_change=row["tech_change"].strip(),
            ))
    return result


def _diff(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(x - y for x, y in zip(a, b))


def _cost_dict(cost: tuple[int, ...]) -> dict[str, int]:
    return dict(zip(FIELDS, cost))


def _rank(matrix: list[list[int]]) -> int:
    """Exact rational Gaussian elimination, no numpy or floating-point."""
    if not matrix:
        return 0
    a = [[Fraction(x) for x in row] for row in matrix]
    col_count = len(a[0])
    pivot_row = 0
    for col in range(col_count):
        pivot = next((i for i in range(pivot_row, len(a)) if a[i][col]), None)
        if pivot is None:
            continue
        a[pivot_row], a[pivot] = a[pivot], a[pivot_row]
        c = a[pivot_row][col]
        a[pivot_row] = [x / c for x in a[pivot_row]]
        for i in range(len(a)):
            if i == pivot_row or a[i][col] == 0:
                continue
            factor = a[i][col]
            a[i] = [x - factor * y for x, y in zip(a[i], a[pivot_row])]
        pivot_row += 1
        if pivot_row == len(a):
            break
    return pivot_row


def _design(recipe: tuple[int, ...]) -> dict[tuple[str, int, int], int]:
    hull, engine, beam, nbeam, launcher, nlaun = recipe
    out = {("hull_engine_bundle", hull, engine): 1}
    if nbeam:
        out[("beam", beam, 0)] = nbeam
    if nlaun:
        out[("launcher", launcher, 0)] = nlaun
    return out


def _contrast(
    game: str, base: tuple[int, ...], other: tuple[int, ...],
    price_base: tuple[int, ...], price_other: tuple[int, ...],
) -> dict[str, Any] | None:
    h0, e0, b0, nb0, t0, nt0 = base
    h1, e1, b1, nb1, t1, nt1 = other
    if (h0, e0) != (h1, e1):
        return None
    beam_changed = (b0 != b1 and nb0 == nb1 and nb0 > 0
                    and (t0, nt0) == (t1, nt1))
    launcher_changed = (t0 != t1 and nt0 == nt1 and nt0 > 0
                        and (b0, nb0) == (b1, nb1))
    if not (beam_changed or launcher_changed):
        return None
    component = "Beam" if beam_changed else "TorpedoLauncher"
    n = nb0 if beam_changed else nt0
    old = b0 if beam_changed else t0
    new = b1 if beam_changed else t1
    raw = _diff(price_other, price_base)
    if any(v % n for v in raw):
        return None
    return {
        "kind": "ISOLATED_SAME_HULL_ENGINE_COMPONENT_CONTRAST",
        "status": "CLIENT_COMPONENT_PRICE_DIFFERENCE_ONLY",
        "game": game,
        "component": component, "from_id": old, "to_id": new,
        "count": n,
        "total_cost_delta": _cost_dict(raw),
        "per_component_cost_delta": _cost_dict(tuple(v // n for v in raw)),
        "NuHost_price_formula_verified": False,
    }


def calibrate_client_build_costs(rows: Iterable[BuildCostObservation]) -> dict[str, Any]:
    rows = list(rows)
    if len(rows) > MAX_ROWS:
        raise ValueError("excessive build-cost observations")
    grouped: dict[tuple[str, tuple[int, ...]], list[BuildCostObservation]] = defaultdict(list)
    for row in rows:
        grouped[row.game_recipe].append(row)
    stable: dict[tuple[str, tuple[int, ...]], tuple[int, ...]] = {}
    recipe_reports: list[dict[str, Any]] = []
    unstable_count = 0
    no_tech = 0
    tech = 0
    for (game, recipe), sample in sorted(grouped.items()):
        ordinary = [x for x in sample if x.isolated_from_recorded_tech_change]
        upgraded = [x for x in sample if not x.isolated_from_recorded_tech_change]
        no_tech += len(ordinary)
        tech += len(upgraded)
        distinct = {x.spending for x in ordinary}
        status = (
            "ABSTAIN_DIFFERENT_SPENDING_FOR_SAME_RECIPE" if len(distinct) > 1
            else "OBSERVED_STABLE_CLIENT_RECIPE" if ordinary
            else "ABSTAIN_NO_NO_TECH_CHANGE_REFERENCE"
        )
        if len(distinct) > 1:
            unstable_count += 1
        if len(distinct) == 1:
            stable[game, recipe] = next(iter(distinct))
        tech_differences = []
        for observation in upgraded:
            tech_differences.append({
                "recorded_tech_change": observation.tech_change,
                "observed_total_spending": _cost_dict(observation.spending),
                "same_recipe_no_tech_change_reference_delta": (
                    _cost_dict(_diff(observation.spending, stable[game, recipe]))
                    if (game, recipe) in stable else None
                ),
                "status": (
                    "CLIENT_COMPOUND_TECH_ASSOCIATED_COST_DELTA"
                    if (game, recipe) in stable
                    else "ABSTAIN_TECH_PRICE_NO_REFERENCE"
                ),
            })
        recipe_reports.append({
            "game": game, "recipe": dict(zip(RECIPE_FIELDS, recipe)),
            "total_observations": len(sample),
            "no_recorded_tech_change_observations": len(ordinary),
            "tech_change_observations": len(upgraded),
            "distinct_no_tech_spendings": len(distinct),
            "status": status,
            "client_total_cost_reference": (
                _cost_dict(stable[game, recipe]) if (game, recipe) in stable else None
            ),
            "tech_associated_observations": tech_differences,
        })
    contrasts = []
    for game in sorted({key[0] for key in stable}):
        members = sorted((recipe, value) for (g, recipe), value in stable.items() if g == game)
        for i, (base, price_base) in enumerate(members):
            for other, price_other in members[i + 1:]:
                c = _contrast(game, base, other, price_base, price_other)
                if c is not None:
                    contrasts.append(c)

    identifiability: list[dict[str, Any]] = []
    for game in sorted({r.game for r in rows}):
        members = sorted(recipe for g, recipe in stable if g == game)
        features = sorted({feature for recipe in members for feature in _design(recipe)})
        matrix = [
            [_design(recipe).get(feature, 0) for feature in features]
            for recipe in members
        ]
        rank = _rank(matrix)
        identifiability.append({
            "game": game, "stable_recipes": len(members),
            "opaque_hull_engine_bundles_plus_beam_launcher_prices": len(features),
            "linear_equation_rank": rank,
            "unidentified_degrees_of_freedom": len(features) - rank,
            "individual_hull_engine_beam_launcher_prices_unique": (
                bool(features) and rank == len(features)
            ),
        })

    return {
        "schema": SCHEMA,
        "status": "CLIENT_BUILD_COST_CONTRASTS_NOT_NUHOST_FORMULA_VERIFIED",
        "summary": {
            "complete_client_build_cost_observations": len(rows),
            "without_recorded_tech_change": no_tech,
            "with_recorded_tech_change": tech,
            "distinct_game_scoped_recipes": len(grouped),
            "stable_game_scoped_recipes": len(stable),
            "unstable_recipe_groups": unstable_count,
            "identifiable_one_component_contrasts": len(contrasts),
            "NuHost_build_cost_verified": False,
            "Host_execution_verified": False,
        },
        "game_scoped_recipes": recipe_reports,
        "component_contrasts": contrasts,
        "identifiability": identifiability,
    }


def _as_tuple(cost: ResourceCost) -> tuple[int, int, int, int]:
    return (cost.megacredits, cost.duranium, cost.tritanium, cost.molybdenum)


def predict_additive_static_build(
    row: BuildCostObservation, specs: NuStaticSpecs,
    *,
    global_hull_id: int | None,
) -> dict[str, Any]:
    """Compare candidate sum of component costs; NEVER assume hull-ID mapping."""
    if global_hull_id is None:
        return {"status": "ABSTAIN_UNVERIFIED_BUILD_HULL_ID_MAPPING"}
    hull = specs.hulls.get(global_hull_id)
    drive = specs.engines.get(row.engine)
    beam = specs.beams.get(row.beam) if row.beam_count else None
    launcher = specs.torpedoes.get(row.launcher) if row.launcher_count else None
    if hull is None or drive is None or (row.beam_count and beam is None) or (
        row.launcher_count and launcher is None
    ):
        return {"status": "ABSTAIN_STATIC_COMPONENT_NOT_FOUND"}
    if row.beam_count > hull.beam_count or row.launcher_count > hull.torpedo_launcher_count:
        return {"status": "ABSTAIN_STATIC_HULL_SLOT_MISMATCH"}
    if hull.engine_count <= 0:
        return {"status": "ABSTAIN_INVALID_STATIC_ENGINE_COUNT"}
    prices = [
        (_as_tuple(hull.cost), 1),
        (_as_tuple(drive.cost), hull.engine_count),
    ]
    if beam is not None:
        prices.append((_as_tuple(beam.cost), row.beam_count))
    if launcher is not None:
        prices.append((_as_tuple(launcher.cost), row.launcher_count))
    estimated = tuple(sum(unit[i] * count for unit, count in prices) for i in range(4))
    return {
        "status": (
            "HYPOTHESIS_STATIC_SUM_EXACT_ON_CLIENT_COST"
            if estimated == row.spending else
            "HYPOTHESIS_STATIC_SUM_MISMATCH_UNATTRIBUTED"
        ) if row.isolated_from_recorded_tech_change else (
            "ABSTAIN_COMPOUND_TECH_UPGRADE_COST"
        ),
        "candidate_additive_total": _cost_dict(estimated),
        "observed_client_total": _cost_dict(row.spending),
        "residual_observed_minus_candidate": _cost_dict(_diff(row.spending, estimated)),
        "NuHost_formula_verified": False,
        "hull_identity_source": "EXPLICIT_EXTERNAL_MAPPING_NOT_ASSUMED",
    }



def published_standard_tech_upgrade_cost_mc(
    initial_level: int, final_level: int,
) -> int:
    """Published STANDARD base-tech schedule, not a game-rule Host witness.

    Official help.planets.nu/tech-levels lists 100 MC to raise level
    1->2, 200 MC for 2->3, ... 900 MC for 9->10. This function
    describes that table; it does not override campaign/custom rules.
    """
    if (type(initial_level) is not int or type(final_level) is not int):
        raise ValueError("technology levels must be integers")
    if not (1 <= initial_level <= final_level <= 10):
        raise ValueError("technology levels must satisfy 1<=initial<=final<=10")
    return 100 * sum(range(initial_level, final_level))


def match_published_static_hull_candidates(
    row: BuildCostObservation,
    specs: NuStaticSpecs,
    *,
    allowed_catalog_hull_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Find matching public hull price signatures; NEVER claim ID identity.

    Only valid for a clearly excluded concurrent tech change, with
    a complete, independently verified component catalog and no
    other purchase/spending in the same client save. The caller
    validates raw catalog completeness and provenance. Any match
    is a *price candidate within supplied catalog scope*, not proof
    that BuildHullId equals a given global hull ID or that the game
    used standard prices.
    """
    if not row.isolated_from_recorded_tech_change:
        return {
            "status": "ABSTAIN_COMPOUND_TECH_UPGRADE_COST",
            "candidate_count": 0, "candidates": [],
            "NuHost_hull_identity_verified": False,
        }
    engine = specs.engines.get(row.engine)
    beam = specs.beams.get(row.beam) if row.beam_count else None
    tube = specs.torpedoes.get(row.launcher) if row.launcher_count else None
    if (engine is None or
            (row.beam_count and beam is None) or
            (row.launcher_count and tube is None)):
        return {
            "status": "ABSTAIN_STATIC_COMPONENT_NOT_FOUND",
            "candidate_count": 0, "candidates": [],
            "NuHost_hull_identity_verified": False,
        }
    candidates = []
    for hull_id, hull in sorted(specs.hulls.items()):
        if (allowed_catalog_hull_ids is not None and
                hull_id not in allowed_catalog_hull_ids):
            continue
        if not (hull.engine_count > 0 and
                hull.beam_count >= row.beam_count and
                hull.torpedo_launcher_count >= row.launcher_count):
            continue
        result = predict_additive_static_build(
            row, specs, global_hull_id=hull_id,
        )
        if result["status"] == "HYPOTHESIS_STATIC_SUM_EXACT_ON_CLIENT_COST":
            candidates.append({
                "catalog_hull_id": hull_id,
                "catalog_hull_name": hull.name,
                "predicted_cost": result["candidate_additive_total"],
            })
    status = (
        "NO_PUBLISHED_STATIC_HULL_SIGNATURE_MATCH"
        if not candidates else
        "ONE_HULL_PRICE_CANDIDATE_NOT_ID_VERIFIED"
        if len(candidates) == 1 else
        "MULTIPLE_HULL_PRICE_CANDIDATES_AMBIGUOUS"
    )
    return {
        "status": status, "candidate_count": len(candidates),
        "candidates": candidates,
        "scope": "SUPPLIED_CATALOG_HULLS_ONLY",
        "NuHost_hull_identity_verified": False,
        "NuHost_cost_formula_verified": False,
    }
