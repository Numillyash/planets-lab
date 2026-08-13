def test_residual_cli_imports() -> None:
    from planets_lab.validation.real_game_motion_residual_cli import main

    assert callable(main)
