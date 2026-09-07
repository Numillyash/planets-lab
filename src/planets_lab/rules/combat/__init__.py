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

__all__ = [
    "BeamSpec",
    "CombatObject",
    "NuHostClassicReplay",
    "ReplayUnsupported",
    "TorpedoSpec",
    "beam_specs_from_catalog",
    "combat_rng_from_settings",
    "normalize_nu_beams",
    "normalize_nu_torpedoes",
    "replay_nuhost_classic",
    "replay_nuhost_from_nu_catalog",
    "torpedo_specs_from_catalog",
]
