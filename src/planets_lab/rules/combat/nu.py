"""Planets.nu catalog adapter for deterministic VCR replay.

The Classic replay core intentionally deals with normalized weapon specs.
This adapter owns Planets.nu's actual RST field names and semantics.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classic import (
    CombatObject,
    NuHostClassicReplay,
    ReplayUnsupported,
    beam_specs_from_catalog,
    combat_rng_from_settings,
    torpedo_specs_from_catalog,
)


def _integer(record: Mapping[str, Any], key: str) -> int | None:
    value = record.get(key)
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _required_integer(record: Mapping[str, Any], key: str) -> int:
    value = _integer(record, key)
    if value is None:
        raise ReplayUnsupported(f"VCR field {key!r} is missing or is not an integer")
    return value


def _cpp_divmod(a: int, b: int) -> tuple[int, int]:
    """Return C++11-style signed integer quotient/remainder for positive b.

    Python ``//`` floors negative values, whereas the c2ng Host algorithm uses
    C++ signed integer division, which truncates the quotient toward zero and
    leaves the remainder with the numerator's sign.
    """

    if b <= 0:
        raise ReplayUnsupported("unexpected non-positive combat divisor")
    quotient = abs(a) // b
    if a < 0:
        quotient = -quotient
    remainder = a - quotient * b
    return quotient, remainder


class _NuSignedClassicReplay(NuHostClassicReplay):
    """NuHost Classic replay with the signed arithmetic used by c2ng/Host."""

    @staticmethod
    def _rdivadd(a: int, b: int, plus: int) -> int:
        if b <= 0:
            raise ReplayUnsupported("unexpected signed RDivAdd divisor")
        quotient, remainder = _cpp_divmod(a, b)
        value = quotient + plus
        if remainder * 2 + ((value & 1) | 1) > b:
            value += 1
        return value

    @staticmethod
    def _divide_and_round(a: int, b: int) -> int:
        if b <= 0:
            raise ReplayUnsupported("unexpected divide-and-round divisor")
        quotient, _ = _cpp_divmod(a + b // 2, b)
        return quotient


def normalize_nu_beams(
    records: Sequence[Mapping[str, Any]],
) -> list[dict[str, int]]:
    """Convert Planets.nu beam records to replay-core weapon fields."""

    result: list[dict[str, int]] = []
    for record in records:
        component_id = _integer(record, "id")
        damage = _integer(record, "damage")
        crewkill = _integer(record, "crewkill")
        if component_id is None or damage is None or crewkill is None:
            continue
        result.append(
            {
                "id": component_id,
                "damage": damage,
                "kill": crewkill,
            }
        )
    return result


def normalize_nu_torpedoes(
    records: Sequence[Mapping[str, Any]],
) -> list[dict[str, int]]:
    """Convert Planets.nu torpedo records to replay-core weapon fields."""

    result: list[dict[str, int]] = []
    for record in records:
        component_id = _integer(record, "id")
        damage = _integer(record, "damage")
        crewkill = _integer(record, "crewkill")
        if component_id is None or damage is None or crewkill is None:
            continue

        combat_range = _integer(record, "combatrange")
        if combat_range is not None and combat_range != 0:
            range_bonus = combat_range - 300
        elif component_id == 11:
            range_bonus = 40
        else:
            range_bonus = 0

        result.append(
            {
                "id": component_id,
                "damage": damage,
                "kill": crewkill,
                "firingrangebonus": range_bonus,
            }
        )
    return result


def replay_nuhost_from_nu_catalog(
    payload: Mapping[str, Any],
    *,
    beams: Sequence[Mapping[str, Any]],
    torpedoes: Sequence[Mapping[str, Any]],
    settings: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay a Nu VCR using the factual Planets.nu game rule catalog.

    Lizard race identity is intentionally preserved for planet combat. The
    classic engine lets the Lizard crew keep the ship functioning above 100%
    during the engagement, while its planet-result path marks a Lizard ship at
    >=100% damage destroyed after combat. That is the Nu tidal-force behavior
    required for a ship to survive long enough to capture the planet and then
    be lost.

    The Nu adapter also preserves c2ng's signed integer rounding semantics.
    This matters for custom games where ``crewdefensepercent`` exceeds 100:
    the effective crew-kill term becomes negative, and C++ integer division
    truncates toward zero rather than flooring like Python's ``//``.
    """

    combat_rng = combat_rng_from_settings(settings)
    if combat_rng is None:
        raise ReplayUnsupported(
            "game rule catalog does not contain combatrng; exact replay is unavailable"
        )
    if combat_rng != 0:
        raise ReplayUnsupported(
            f"combat RNG mode {combat_rng} is not supported; expected Classic (0)"
        )

    raw_left = payload.get("left")
    raw_right = payload.get("right")
    if not isinstance(raw_left, Mapping) or not isinstance(raw_right, Mapping):
        raise ReplayUnsupported("VCR left/right payload is missing")

    left = CombatObject.from_payload(
        raw_left,
        owner_id=_integer(payload, "leftownerid"),
    )
    right = CombatObject.from_payload(
        raw_right,
        owner_id=_integer(payload, "rightownerid"),
    )

    return _NuSignedClassicReplay(
        seed=_required_integer(payload, "seed"),
        left=left,
        right=right,
        beams=beam_specs_from_catalog(normalize_nu_beams(beams)),
        torpedoes=torpedo_specs_from_catalog(normalize_nu_torpedoes(torpedoes)),
    ).run()
