def test_raw_residual_payload_cli_imports() -> None:
    from planets_lab.validation import real_game_motion_raw_cli

    assert callable(real_game_motion_raw_cli.main)
