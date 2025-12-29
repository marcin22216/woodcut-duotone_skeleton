from woodcut_duotone.gui.state import AppState


def test_app_state_undo_redo_roundtrip() -> None:
    state = AppState()
    state.push_undo()
    state.params["threshold"]["bias"] = 12
    state.enabled["edges"] = True

    assert state.can_undo
    assert state.undo()
    assert state.params["threshold"]["bias"] == 0
    assert state.enabled["edges"] is False

    assert state.can_redo
    assert state.redo()
    assert state.params["threshold"]["bias"] == 12
    assert state.enabled["edges"] is True


def test_app_state_redo_cleared_on_new_action() -> None:
    state = AppState()
    state.push_undo()
    state.params["threshold"]["bias"] = 5
    state.undo()
    assert state.can_redo

    state.push_undo()
    state.params["threshold"]["bias"] = 7

    assert not state.can_redo


def test_app_state_restore_snapshot() -> None:
    state = AppState()
    snapshot = state.snapshot()

    state.enabled["threshold"] = False
    state.params["edges"]["low"] = 33

    state.restore(snapshot)

    assert state.enabled == snapshot["enabled"]
    assert state.params == snapshot["params"]
