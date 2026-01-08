from woodcut_duotone.app import main


def test_bootstrap_imports_and_main_runs() -> None:
    import woodcut_duotone  # noqa: F401

    main([])
