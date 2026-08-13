def test_context_cli_imports() -> None:
    from planets_lab.validation.real_game_motion_context_cli import main
    assert callable(main)
