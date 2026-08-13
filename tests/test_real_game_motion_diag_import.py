def test_motion_diagnostics_imports() -> None:
    from planets_lab.validation.real_game_motion_diag import diagnose
    assert callable(diagnose)
