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

__all__ = [
    "BeamSpec",
    "CombatObject",
    "NuHostClassicReplay",
    "ReplayUnsupported",
    "TorpedoSpec",
    "beam_specs_from_catalog",
    "combat_rng_from_settings",
    "replay_nuhost_classic",
    "torpedo_specs_from_catalog",
]
