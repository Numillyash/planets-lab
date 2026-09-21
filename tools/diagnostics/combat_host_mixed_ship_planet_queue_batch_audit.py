from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTICS_DIR = Path(__file__).resolve().parent
for path in (REPO_ROOT, DIAGNOSTICS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from planets_lab.corpus.movement_differential import _intish
from planets_lab.corpus.prepared_cache import load_or_build_prepared_game_cache
from planets_lab.corpus.reconstruction import group_perspective_records
from planets_lab.rules.combat.mixed_queue import (
    PlanetAttackCandidate,
    select_initial_plain_planet_attacker,
)
from planets_lab.rules.combat.order import (
    orders_request_ship_combat,
    standard_battle_priority_key,
)

import combat_host_capture_continuation_audit as capture_module
import combat_host_post_capture_opponent_audit as opponent_module
from combat_host_priority_intercept_audit import (
    PREPARED_DIR,
    RAW_DIR,
    _int,
    _owner_raw,
)


SCHEMA = "planets-lab.combat-host-mixed-ship-planet-queue-batch-audit.v7"
DEFAULT_EXAMPLE_LIMIT = 80