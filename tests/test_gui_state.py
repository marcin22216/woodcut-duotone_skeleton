from woodcut_duotone.gui.state import AppState, should_apply_revision


def test_app_state_undo_redo_roundtrip() -> None:
    state = AppState()
    state.push_undo()
    state.params["Threshold"]["bias"] = 12
    state.enabled["Edges"] = True

    assert state.can_undo
    assert state.undo()
    assert state.params["Threshold"]["bias"] == 0
    assert state.enabled["Edges"] is False

    assert state.can_redo
    assert state.redo()
    assert state.params["Threshold"]["bias"] == 12
    assert state.enabled["Edges"] is True


def test_app_state_redo_cleared_on_new_action() -> None:
    state = AppState()
    state.push_undo()
    state.params["Threshold"]["bias"] = 5
    state.undo()
    assert state.can_redo

    state.push_undo()
    state.params["Threshold"]["bias"] = 7

    assert not state.can_redo


def test_app_state_restore_snapshot() -> None:
    state = AppState()
    snapshot = state.snapshot()

    state.enabled["Threshold"] = False
    state.params["Edges"]["low"] = 33

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
    state.params["Threshold"]["bias"] = 10
    state.enabled["Edges"] = True

    state.reset_defaults()

    assert state.params["Threshold"]["bias"] == 0
    assert state.enabled["Edges"] is False
    assert state.step_order == [
        "Denoise",
        "Detail Boost",
        "Grayscale",
        "CLAHE Contrast",
        "Gaussian Blur",
        "Foreground Emphasis",
        "Threshold",
        "Morphology",
        "Edges",
    ]
    assert not state.can_undo
    assert not state.can_redo


def test_app_state_params_have_required_keys() -> None:
    state = AppState()

    assert "method" in state.params["Denoise"]
    assert "kernel_size" in state.params["Denoise"]
    assert "diameter" in state.params["Denoise"]
    assert "sigma_color" in state.params["Denoise"]
    assert "sigma_space" in state.params["Denoise"]
    assert "h" in state.params["Denoise"]
    assert "template_window" in state.params["Denoise"]
    assert "search_window" in state.params["Denoise"]
    assert isinstance(state.params["Denoise"]["kernel_size"], int)

    assert "amount" in state.params["Detail Boost"]
    assert "radius" in state.params["Detail Boost"]
    assert "apply_on" in state.params["Detail Boost"]
    assert isinstance(state.params["Detail Boost"]["amount"], int)
    assert isinstance(state.params["Detail Boost"]["radius"], int)

    assert "low" in state.params["Foreground Emphasis"]
    assert "high" in state.params["Foreground Emphasis"]
    assert "spread" in state.params["Foreground Emphasis"]
    assert "threshold" in state.params["Foreground Emphasis"]
    assert "strength" in state.params["Foreground Emphasis"]
    assert "background" in state.params["Foreground Emphasis"]
    assert isinstance(state.params["Foreground Emphasis"]["low"], int)
    assert isinstance(state.params["Foreground Emphasis"]["high"], int)

    assert "mode" in state.params["Threshold"]
    assert "block_size" in state.params["Threshold"]

    assert "low" in state.params["Edges"]
    assert "high" in state.params["Edges"]
    assert "thickness" in state.params["Edges"]
    assert "apply_on" in state.params["Edges"]
    assert isinstance(state.params["Edges"]["low"], int)
    assert isinstance(state.params["Edges"]["high"], int)


def test_should_apply_revision() -> None:
    assert should_apply_revision(3, 3)
    assert not should_apply_revision(3, 2)
    assert not should_apply_revision(3, 4)


def test_app_state_move_step_and_undo_redo() -> None:
    state = AppState()

    state.move_step("Edges", 0)
    assert state.step_order[0] == "Edges"

    assert state.undo()
    assert state.step_order[-1] == "Edges"

    assert state.redo()
    assert state.step_order[0] == "Edges"
