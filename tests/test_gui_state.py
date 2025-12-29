from woodcut_duotone.gui.state import AppState, should_apply_revision


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


def test_app_state_render_revision_increments() -> None:
    state = AppState()

    first = state.next_render_revision()
    second = state.next_render_revision()

    assert first == 1
    assert second == 2


def test_app_state_reset_clears_history_and_defaults() -> None:
    state = AppState()
    state.push_undo()
    state.params["threshold"]["bias"] = 10
    state.enabled["edges"] = True

    state.reset_defaults()

    assert state.params["threshold"]["bias"] == 0
    assert state.enabled["edges"] is False
    assert not state.can_undo
    assert not state.can_redo


def test_should_apply_revision() -> None:
    assert should_apply_revision(3, 3)
    assert not should_apply_revision(3, 2)
    assert not should_apply_revision(3, 4)
