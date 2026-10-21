"""Conservative Classic/PBP *standard subphase* queue pointer contract.

This is not the Priority Build subphase. It runs ONLY after an explicitly
resolved/no-priority, no-cloning context, with every real base accounted
for, all per-player PBP balances known and below the 21-point threshold.

The scheduler selects *base IDs*, NOT ship IDs, build materials or
Host orders. A caller-provided exact last STANDARD build pointer is
necessary to enter the sequence. Neither the input pointer nor PBP
balances are independently authenticated by this model.

No place for PBx, competing priority builds, middle PBP consumption,
cloning, PPQ/PQ, an absent/unknown pointer or unknown Host timing.
"""
from __future__ import annotations

from dataclasses import dataclass

STATUS = "CONDITIONAL_CLASSIC_STANDARD_POINTER_SUBPHASE_NOT_NUHOST_VERIFIED"


@dataclass(frozen=True, slots=True)
class ClassicBaseQueueEntry:
    planet_id: int
    owner_id: int
    ordinary_ship_queued: bool
    priority_build_code: int | None = None
    clone_ordered: bool = False


@dataclass(frozen=True, slots=True)
class ClassicStandardSubphase:
    ship_limit: int
    current_ship_count: int
    last_standard_build_planet_id: int
    bases: tuple[ClassicBaseQueueEntry, ...]
    player_pbps: tuple[tuple[int, int], ...]
    standard_phase_after_priorities_asserted: bool = False
    complete_starbase_roster_asserted: bool = False
    complete_player_pbp_balances_asserted: bool = False
    no_cloning_or_other_build_effects_asserted: bool = False


@dataclass(frozen=True, slots=True)
class ClassicStandardSelection:
    status: str
    selected_planet_ids: tuple[int, ...] = ()
    last_standard_build_planet_id_after: int | None = None
    unfilled_ship_slots: int | None = None
    reason: str | None = None
    queue_pointer_independently_verified: bool = False
    pbp_balances_independently_verified: bool = False
    nuhost_standard_subphase_verified: bool = False
    nuhost_ship_ids_allocated: bool = False

    @property
    def supported(self) -> bool:
        return self.status == STATUS


def select_classic_standard_subphase(
    context: ClassicStandardSubphase,
) -> ClassicStandardSelection:
    """Walk one explicit round-robin ring of planet IDs after pointer.

    If the subphase has fewer slots than queued bases, accept the first
    N applicable bases and persist the last built base as the pointer.
    Empty/idle bases are skipped; no priority or clones are modeled.
    Every base can receive at most one regular build in this subphase.
    """
    def abstain(reason: str) -> ClassicStandardSelection:
        return ClassicStandardSelection("ABSTAIN_CLASSIC_STANDARD_SUBPHASE", reason=reason)

    if type(context) is not ClassicStandardSubphase:
        return abstain("complete typed Classic subphase input required")
    if not all((
        context.standard_phase_after_priorities_asserted is True,
        context.complete_starbase_roster_asserted is True,
        context.complete_player_pbp_balances_asserted is True,
        context.no_cloning_or_other_build_effects_asserted is True,
    )):
        return abstain("explicit priority/roster/PBP/clone scope required")
    if (type(context.ship_limit) is not int
            or not 1 <= context.ship_limit <= 999
            or type(context.current_ship_count) is not int
            or not 0 <= context.current_ship_count <= context.ship_limit
            or type(context.last_standard_build_planet_id) is not int
            or not 0 <= context.last_standard_build_planet_id <= 500):
        return abstain("invalid cap, fleet count or standard queue pointer")
    if (type(context.bases) is not tuple or not 1 <= len(context.bases) <= 500
            or type(context.player_pbps) is not tuple
            or not 1 <= len(context.player_pbps) <= 30):
        return abstain("complete bounded tuple inputs required")
    pp: dict[int, int] = {}
    for row in context.player_pbps:
        if (type(row) is not tuple or len(row) != 2
                or type(row[0]) is not int or not 1 <= row[0] <= 30
                or row[0] in pp or type(row[1]) is not int
                or not 0 <= row[1] < 21):
            return abstain("unknown, duplicate or priority-eligible PBP balance")
        pp[row[0]] = row[1]
    by_pid: dict[int, ClassicBaseQueueEntry] = {}
    for row in context.bases:
        if (type(row) is not ClassicBaseQueueEntry
                or type(row.planet_id) is not int or not 1 <= row.planet_id <= 500
                or row.planet_id in by_pid
                or type(row.owner_id) is not int or row.owner_id not in pp
                or type(row.ordinary_ship_queued) is not bool
                or row.priority_build_code is not None
                or row.clone_ordered is not False):
            return abstain("unknown base, owner, priority-code or cloning intent")
        by_pid[row.planet_id] = row
    # Require each declared PBP owner to own at least one listed base.
    # Without it we cannot establish complete player scope.
    if set(pp) != {row.owner_id for row in context.bases}:
        return abstain("PBP owner scope mismatches the starbase roster")
    available = context.ship_limit - context.current_ship_count
    # One queue traversal, ascending planet-ID modulo 500, from strictly
    # *after* the declared last STANDARD build position.
    ordered = sorted(by_pid, key=lambda pid: ((pid - context.last_standard_build_planet_id - 1) % 500))
    possible = tuple(pid for pid in ordered if by_pid[pid].ordinary_ship_queued)
    chosen = possible[:available]
    ending_pointer = (chosen[-1] if chosen
                      else context.last_standard_build_planet_id)
    return ClassicStandardSelection(
        STATUS,
        selected_planet_ids=chosen,
        last_standard_build_planet_id_after=ending_pointer,
        unfilled_ship_slots=available - len(chosen),
    )
