def test_residual_context2_cli_imports() -> None:
    from planets_lab.validation import real_game_motion_context2_cli
    assert callable(real_game_motion_context2_cli.main)
