from __future__ import annotations
import importlib.util
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'tools'/'diagnostics'/'combat_long_mass_survey_digest_v1.py'
SPEC=importlib.util.spec_from_file_location('mass_digest',SCRIPT)
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)

def test_diverse_examples():
    assert [i['n'] for i in M._diverse([{'game_id':1,'n':1},{'game_id':1,'n':2},{'game_id':2,'n':3}],3)] == [1,3,2]
