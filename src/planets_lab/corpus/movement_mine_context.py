from __future__ import annotations

from dataclasses import dataclass, field
from math import floor, hypot
from typing import Any, Mapping, Sequence

from planets_lab.data.nu_specs import NuStaticSpecs
from planets_lab.data.nu_static import import_static_all
from planets_lab.rules.ship_repair import repair_damage_with_supplies
from planets_lab.validation.movement_geometry import MovementSample

from .archive import read_archive_members, turn_members
from .movement_differential import _intish
from .movement_horwasp_trajectory import _vector
from .movement_residual_context import GRAVITONIC_HULL_IDS, _owner_record
from .movement_sphere_context import effective_sphere_topology
from .movement_topology_diagnostics import extract_map_topology
from .normalizer import ArchiveTurnSnapshot, _decode_member_json
from .reconstruction import PerspectiveRecord, group_perspective_records


HORWASP_HULL_IDS = frozenset(range(201, 214))
WEB_MINE_CATEGORY = "web_mine_hit_nearest_damage"
NORMAL_MINE_CATEGORY = "normal_mine_hit_nearest_damage"
NORMAL_MINE_SCALED_FLOOR_CATEGORY = "normal_mine_hit_scaled_floor_exact"


@dataclass(frozen=True, slots=True)
class ObservedMineField:
    field_id: int | None
    owner_id: int | None
    x: float
    y: float
    radius: float
    is_web: bool


@dataclass(frozen=True, slots=True)
class MineHitEvidence:
    category: str
    damage_hits: int
    slowdown_hits: int | None


@dataclass(slots=True)
class MineEvidenceContext:
    snapshots: tuple[ArchiveTurnSnapshot, ...]
    specs: NuStaticSpecs
    topology: Any
    ship_groups: Mapping[tuple[int, int], tuple[PerspectiveRecord, ...]]
    _fields_by_turn: dict[int, tuple[ObservedMineField, ...]] = field(default_factory=dict)

    def fields(self, archive_turn: int) -> tuple[ObservedMineField, ...]:
        cached = self._fields_by_turn.get(archive_turn)
        if cached is not None:
            return cached

        seen: set[tuple[Any, ...]] = set()
        parsed: list[ObservedMineField] = []
        for snapshot in self.snapshots:
            if snapshot.archive_turn != archive_turn:
                continue
            raw_fields = snapshot.mechanics_payload.get("minefields", [])
            if not isinstance(raw_fields, list):
                continue
            for raw in raw_fields:
                if not isinstance(raw, Mapping):
                    continue
                field_record = _parse_explicit_minefield(raw)
                if field_record is None:
                    continue
                identity = (
                    field_record.field_id,
                    field_record.owner_id,
                    round(field_record.x, 6),
                    round(field_record.y, 6),
                    round(field_record.radius, 6),
                    field_record.is_web,
                )
                if identity in seen:
                    continue
                seen.add(identity)
                parsed.append(field_record)

        result = tuple(parsed)
        self._fields_by_turn[archive_turn] = result
        return result


def _floatish(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
    return None


def _parse_explicit_minefield(raw: Mapping[str, Any]) -> ObservedMineField | None:
    x = _floatish(raw.get("x"))
    y = _floatish(raw.get("y"))
    radius = _floatish(raw.get("radius"))
    is_web = _boolish(raw.get("isweb"))
    if x is None or y is None or radius is None or radius < 0 or is_web is None:
        return None
    return ObservedMineField(
        field_id=_intish(raw.get("id")),
        owner_id=_intish(raw.get("ownerid")),
        x=x,
        y=y,
        radius=radius,
        is_web=is_web,
    )


def _static_specs(archive_data: bytes) -> NuStaticSpecs:
    members = turn_members(archive_data)
    if not members:
        raise ValueError("archive contains no .trn members")
    member = members[0]
    raw = read_archive_members(archive_data, [member.name])[member.name]
    payload, _ = _decode_member_json(raw, member)
    return NuStaticSpecs.from_catalog(import_static_all(payload))


def build_mine_evidence_context(
    *,
    game_id: int,
    archive_data: bytes,
    snapshots: Sequence[ArchiveTurnSnapshot],
) -> MineEvidenceContext:
    records = tuple(snapshots)
    raw_topology = extract_map_topology(archive_data)
    topology = effective_sphere_topology(game_id=game_id, topology=raw_topology)
    return MineEvidenceContext(
        snapshots=records,
        specs=_static_specs(archive_data),
        topology=topology,
        ship_groups=group_perspective_records(records, "ship"),
    )


def nearest_damage_quantum(hull_mass: int | None, *, web: bool) -> int | None:
    """Return the corpus-observed positive nearest-integer mine damage quantum.

    Planets.nu documentation currently describes mine damage as rounded up. The
    historical NuHost differential instead selects positive round-half-up over
    ceil for both normal and web mine hits. Keep that compatibility distinction
    explicit here rather than silently treating the documentation as exact Host
    implementation behavior.
    """

    if hull_mass is None or hull_mass < 0:
        return None
    numerator = 1_000 if web else 10_000
    denominator = hull_mass + 1
    return (2 * numerator + denominator) // (2 * denominator)


def _positive_multiple(value: int | None, quantum: int | None) -> int | None:
    if value is None or quantum is None or value <= 0 or quantum <= 0:
        return None
    if value % quantum != 0:
        return None
    return value // quantum


def classify_mine_evidence_values(
    *,
    hull_mass: int | None,
    hull_tech: int | None,
    damage_delta: int | None,
    lost_distance: float,
    post_reset: bool,
    web_at_observed: bool,
    normal_field_crossing: bool,
) -> MineHitEvidence | None:
    """Classify only strict field-backed corpus-verified mine signatures.

    Repair-bracket candidates are deliberately excluded. Damage-hit multiplicity
    is also kept separate from the 10-ly slowdown count because multiple impacts
    need not all apply a slowdown when less than 10 ly remain.
    """

    web_hits = _positive_multiple(
        damage_delta,
        nearest_damage_quantum(hull_mass, web=True),
    )
    if post_reset and web_at_observed and web_hits is not None:
        return MineHitEvidence(
            category=WEB_MINE_CATEGORY,
            damage_hits=web_hits,
            slowdown_hits=None,
        )

    if hull_tech is None or hull_tech >= 7 or lost_distance <= 0.0:
        return None
    slowdown_hits = int(lost_distance / 10.0 + 0.5)
    if slowdown_hits < 1 or abs(lost_distance - slowdown_hits * 10.0) > 1.5:
        return None
    normal_hits = _positive_multiple(
        damage_delta,
        nearest_damage_quantum(hull_mass, web=False),
    )
    if normal_field_crossing and normal_hits is not None:
        return MineHitEvidence(
            category=NORMAL_MINE_CATEGORY,
            damage_hits=normal_hits,
            slowdown_hits=slowdown_hits,
        )
    return None


def _cross_track_and_progress(
    target_vector: tuple[int, int],
    observed_vector: tuple[int, int],
) -> tuple[float | None, float | None]:
    tx, ty = target_vector
    ox, oy = observed_vector
    target_distance = hypot(tx, ty)
    if target_distance <= 1e-9:
        return None, None
    cross_track = abs(tx * oy - ty * ox) / target_distance
    progress = (tx * ox + ty * oy) / target_distance
    return cross_track, progress


def _point_in_field(
    point: tuple[int, int],
    field_record: ObservedMineField,
    topology: Any,
    *,
    tolerance: float = 1.0,
) -> bool:
    center = (int(round(field_record.x)), int(round(field_record.y)))
    dx, dy = _vector(center, point, topology)
    return hypot(dx, dy) <= field_record.radius + tolerance


def _segment_intersects_field(
    *,
    origin: tuple[int, int],
    vector: tuple[float, float],
    field_record: ObservedMineField,
    topology: Any,
    tolerance: float = 1.0,
) -> bool:
    center = (int(round(field_record.x)), int(round(field_record.y)))
    cx, cy = _vector(origin, center, topology)
    tx, ty = vector
    length_sq = tx * tx + ty * ty
    if length_sq <= 1e-9:
        return hypot(cx, cy) <= field_record.radius + tolerance
    t = (cx * tx + cy * ty) / length_sq
    t = min(1.0, max(0.0, t))
    closest_x = t * tx
    closest_y = t * ty
    return hypot(cx - closest_x, cy - closest_y) <= field_record.radius + tolerance


def _same_owner_identity_after(
    *,
    context: MineEvidenceContext,
    before_turn: int,
    after_turn: int,
    ship_id: int,
    owner_id: int,
    before_raw: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    after_owner_id, after_owner = _owner_record(
        context.ship_groups.get((after_turn, ship_id), ())
    )
    if after_owner_id != owner_id or after_owner is None:
        return None
    after_raw = after_owner.raw
    before_hull = _intish(before_raw.get("hullid", before_raw.get("hull_id")))
    after_hull = _intish(after_raw.get("hullid", after_raw.get("hull_id")))
    if before_hull is None or after_hull is None or before_hull != after_hull:
        return None
    before_identity_turn = _intish(before_raw.get("turn"))
    after_identity_turn = _intish(after_raw.get("turn"))
    if (
        before_identity_turn is not None
        and after_identity_turn is not None
        and before_identity_turn != after_identity_turn
    ):
        return None
    return after_raw


def _round_nearest_nonnegative(value: float) -> int:
    return floor(value + 0.5)


def _major_axis_clicks(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
) -> tuple[tuple[int, tuple[int, int]], ...]:
    """Enumerate the validated planar Classic Host major-axis route raster."""

    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    abs_dx = abs(dx)
    abs_dy = abs(dy)
    if abs_dx == 0 and abs_dy == 0:
        return ((0, origin),)

    result: list[tuple[int, tuple[int, int]]] = []
    if abs_dx >= abs_dy:
        major = abs_dx
        minor = abs_dy
        sx = 1 if dx >= 0 else -1
        sy = 1 if dy >= 0 else -1
        for click in range(major + 1):
            minor_move = _round_nearest_nonnegative(click * minor / major) if major else 0
            result.append((click, (origin[0] + sx * click, origin[1] + sy * minor_move)))
    else:
        major = abs_dy
        minor = abs_dx
        sx = 1 if dx >= 0 else -1
        sy = 1 if dy >= 0 else -1
        for click in range(major + 1):
            minor_move = _round_nearest_nonnegative(click * minor / major) if major else 0
            result.append((click, (origin[0] + sx * minor_move, origin[1] + sy * click)))
    return tuple(result)


def _click_for_point(
    clicks: Sequence[tuple[int, tuple[int, int]]],
    point: tuple[int, int],
) -> int | None:
    matches = [click for click, candidate in clicks if candidate == point]
    if len(matches) != 1:
        return None
    return matches[0]


def _regular_major_click(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    regular_distance: float,
) -> int | None:
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    major = max(abs(dx), abs(dy))
    route_distance = hypot(dx, dy)
    if major <= 0 or route_distance <= 1e-9 or regular_distance < 0.0:
        return None
    if regular_distance >= route_distance - 1e-9:
        return major
    click = floor(regular_distance * major / route_distance + 0.5)
    return max(0, min(major, click))


def scaled_floor_normal_mine_endpoint(
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    nominal_distance: float,
    regular_distance: float,
    slowdown_hits: int,
) -> tuple[tuple[int, int] | None, int | None]:
    """Return the corpus-observed exact planar scaled-floor endpoint candidate.

    This is an empirical NuHost classifier rule, not a claim that Host literally
    evaluates this expression internally. It is deliberately limited to the
    planar Classic Host click raster validated by the historical corpus.
    """

    if nominal_distance <= 0.0 or regular_distance <= 1e-9 or slowdown_hits < 1:
        return None, None
    clicks = _major_axis_clicks(origin=origin, target=target)
    regular_click = _regular_major_click(
        origin=origin,
        target=target,
        regular_distance=regular_distance,
    )
    if regular_click is None:
        return None, None
    penalty = floor(10.0 * slowdown_hits * nominal_distance / regular_distance + 1e-12)
    expected_click = max(0, regular_click - penalty)
    endpoint = next((point for click, point in clicks if click == expected_click), None)
    return endpoint, penalty


def _exact_supply_repair_hit_count(
    *,
    before_damage: int | None,
    after_damage: int | None,
    before_supplies: int | None,
    after_supplies: int | None,
    quantum: int | None,
) -> int | None:
    """Recover one exact mine-hit count from a canonical automatic-repair trace."""

    if (
        before_damage is None
        or after_damage is None
        or before_supplies is None
        or after_supplies is None
        or quantum is None
        or quantum <= 0
        or min(before_damage, after_damage, before_supplies, after_supplies) < 0
        or after_supplies > before_supplies
    ):
        return None

    spent_supplies = before_supplies - after_supplies
    if spent_supplies % 5 != 0:
        return None
    repaired_damage = spent_supplies // 5
    raw_damage = after_damage + repaired_damage
    hits = _positive_multiple(raw_damage - before_damage, quantum)
    if hits is None:
        return None

    expected_damage, expected_supplies, _ = repair_damage_with_supplies(
        damage=before_damage + hits * quantum,
        supplies=before_supplies,
    )
    if expected_damage != after_damage or expected_supplies != after_supplies:
        return None
    return hits


def _damage_hit_candidates(
    *,
    before_raw: Mapping[str, Any],
    after_raw: Mapping[str, Any],
    quantum: int | None,
) -> tuple[int, ...]:
    before_damage = _intish(before_raw.get("damage"))
    after_damage = _intish(after_raw.get("damage"))
    candidates: set[int] = set()

    if before_damage is not None and after_damage is not None:
        direct_hits = _positive_multiple(after_damage - before_damage, quantum)
        if direct_hits is not None:
            candidates.add(direct_hits)

    repair_hits = _exact_supply_repair_hit_count(
        before_damage=before_damage,
        after_damage=after_damage,
        before_supplies=_intish(before_raw.get("supplies")),
        after_supplies=_intish(after_raw.get("supplies")),
        quantum=quantum,
    )
    if repair_hits is not None:
        candidates.add(repair_hits)
    return tuple(sorted(candidates))


def _classify_scaled_floor_normal_mine(
    *,
    context: MineEvidenceContext,
    hull_mass: int,
    hull_tech: int,
    before_raw: Mapping[str, Any],
    after_raw: Mapping[str, Any],
    origin: tuple[int, int],
    target: tuple[int, int],
    observed: tuple[int, int],
    nominal_distance: float,
    regular_distance: float,
    normal_field_crossing: bool,
) -> MineHitEvidence | None:
    """Classify only the independently equivalence-verified exact subset."""

    if context.topology.sphere is not False:
        return None
    if hull_tech >= 7 or not normal_field_crossing:
        return None
    if regular_distance <= 1e-9 or regular_distance >= nominal_distance - 1e-9:
        return None

    quantum = nearest_damage_quantum(hull_mass, web=False)
    damage_hit_candidates = _damage_hit_candidates(
        before_raw=before_raw,
        after_raw=after_raw,
        quantum=quantum,
    )
    if not damage_hit_candidates:
        return None

    exact_models: set[tuple[int, int]] = set()
    for damage_hits in damage_hit_candidates:
        for slowdown_hits in range(1, damage_hits + 1):
            endpoint, _ = scaled_floor_normal_mine_endpoint(
                origin=origin,
                target=target,
                nominal_distance=nominal_distance,
                regular_distance=regular_distance,
                slowdown_hits=slowdown_hits,
            )
            if endpoint == observed:
                exact_models.add((damage_hits, slowdown_hits))

    if len(exact_models) != 1:
        return None
    damage_hits, slowdown_hits = next(iter(exact_models))
    return MineHitEvidence(
        category=NORMAL_MINE_SCALED_FLOOR_CATEGORY,
        damage_hits=damage_hits,
        slowdown_hits=slowdown_hits,
    )


def classify_strong_mine_hit_transition(
    *,
    context: MineEvidenceContext,
    before_turn: int,
    after_turn: int,
    ship_id: int,
    owner_id: int,
    before_raw: Mapping[str, Any],
    sample: MovementSample,
) -> MineHitEvidence | None:
    hull_id = int(sample.hull_id) if sample.hull_id is not None else None
    if hull_id is None or hull_id in HORWASP_HULL_IDS or not 1 <= sample.warp <= 9:
        return None

    after_raw = _same_owner_identity_after(
        context=context,
        before_turn=before_turn,
        after_turn=after_turn,
        ship_id=ship_id,
        owner_id=owner_id,
        before_raw=before_raw,
    )
    if after_raw is None:
        return None

    hull_spec = context.specs.hulls.get(hull_id)
    if hull_spec is None:
        return None

    origin = (sample.x, sample.y)
    observed = sample.observed_destination
    target = (sample.target_x, sample.target_y)
    observed_vector = _vector(origin, observed, context.topology)
    target_vector = _vector(origin, target, context.topology)
    observed_distance = hypot(*observed_vector)
    target_distance = hypot(*target_vector)
    nominal = float(sample.warp * sample.warp)
    if hull_id in GRAVITONIC_HULL_IDS:
        nominal *= 2.0
    regular_distance = min(target_distance, nominal)
    cross_track, progress = _cross_track_and_progress(target_vector, observed_vector)
    short_same_line = (
        cross_track is not None
        and progress is not None
        and cross_track <= 1.5
        and progress > 0.0
        and observed_distance > 0.0
        and observed_distance + 1.5 < regular_distance
    )
    if not short_same_line:
        return None

    before_damage = _intish(before_raw.get("damage"))
    after_damage = _intish(after_raw.get("damage"))
    damage_delta = (
        after_damage - before_damage
        if before_damage is not None and after_damage is not None
        else None
    )

    post_warp = _intish(after_raw.get("warp"))
    post_target_x = _intish(after_raw.get("targetx", after_raw.get("waypointx")))
    post_target_y = _intish(after_raw.get("targety", after_raw.get("waypointy")))
    post_reset = post_warp == 0 and (post_target_x, post_target_y) == observed

    enemy_fields = tuple(
        field_record
        for field_record in context.fields(after_turn)
        if field_record.owner_id is not None
        and field_record.owner_id > 0
        and field_record.owner_id != owner_id
    )
    web_at_observed = any(
        field_record.is_web
        and _point_in_field(observed, field_record, context.topology)
        for field_record in enemy_fields
    )

    if target_distance > 0.0 and regular_distance > 0.0:
        scale = regular_distance / target_distance
        regular_vector = (
            target_vector[0] * scale,
            target_vector[1] * scale,
        )
    else:
        regular_vector = (0.0, 0.0)
    normal_field_crossing = any(
        not field_record.is_web
        and _segment_intersects_field(
            origin=origin,
            vector=regular_vector,
            field_record=field_record,
            topology=context.topology,
        )
        for field_record in enemy_fields
    )

    legacy = classify_mine_evidence_values(
        hull_mass=hull_spec.mass,
        hull_tech=hull_spec.tech_level,
        damage_delta=damage_delta,
        lost_distance=regular_distance - observed_distance,
        post_reset=post_reset,
        web_at_observed=web_at_observed,
        normal_field_crossing=normal_field_crossing,
    )
    if legacy is not None:
        return legacy

    return _classify_scaled_floor_normal_mine(
        context=context,
        hull_mass=hull_spec.mass,
        hull_tech=hull_spec.tech_level,
        before_raw=before_raw,
        after_raw=after_raw,
        origin=origin,
        target=target,
        observed=observed,
        nominal_distance=nominal,
        regular_distance=regular_distance,
        normal_field_crossing=normal_field_crossing,
    )
