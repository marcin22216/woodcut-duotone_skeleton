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
    assert state.step_order == snapshot["step_order"]


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
    assert state.step_order == [
        "grayscale",
        "clahe",
        "blur",
        "threshold",
        "morphology",
        "edges",
    ]
    assert not state.can_undo
    assert not state.can_redo


def test_app_state_params_have_required_keys() -> None:
    state = AppState()

    assert "mode" in state.params["threshold"]
    assert "block_size" in state.params["threshold"]

    assert "low" in state.params["edges"]
    assert "high" in state.params["edges"]
    assert "thickness" in state.params["edges"]
    assert "apply_on" in state.params["edges"]


def test_should_apply_revision() -> None:
    assert should_apply_revision(3, 3)
    assert not should_apply_revision(3, 2)
    assert not should_apply_revision(3, 4)


def test_app_state_move_step_and_undo_redo() -> None:
    state = AppState()

    state.move_step("edges", 0)
    assert state.step_order[0] == "edges"

    assert state.undo()
    assert state.step_order[-1] == "edges"

    assert state.redo()
    assert state.step_order[0] == "edges"
