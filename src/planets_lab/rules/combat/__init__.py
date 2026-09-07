"""Deterministic combat rules."""

from .classic import (
    BeamSpec,
    CombatObject,
    NuHostClassicReplay,
    ReplayUnsupported,
    TorpedoSpec,
    beam_specs_from_catalog,
    combat_rng_from_settings,
    replay_nuhost_classic,
    torpedo_specs_from_catalog,
)
from .nu import (
    normalize_nu_beams,
    normalize_nu_torpedoes,
    replay_nuhost_from_nu_catalog,
)
from .sequence import (
    DYNAMIC_CARRY_FIELDS,
    apply_terminal_state,
    carry_ship_to_next_engagement,
    federation_recover_shields,
    functional_weapon_limit,
    prepare_sequence_ship,
)

__all__ = [
    "BeamSpec",
    "CombatObject",
    "DYNAMIC_CARRY_FIELDS",
    "NuHostClassicReplay",
    "ReplayUnsupported",
    "TorpedoSpec",
    "apply_terminal_state",
    "beam_specs_from_catalog",
    "carry_ship_to_next_engagement",
    "combat_rng_from_settings",
    "federation_recover_shields",
    "functional_weapon_limit",
    "normalize_nu_beams",
    "normalize_nu_torpedoes",
    "prepare_sequence_ship",
    "replay_nuhost_classic",
    "replay_nuhost_from_nu_catalog",
    "torpedo_specs_from_catalog",
]
