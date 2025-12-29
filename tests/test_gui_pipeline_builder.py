from woodcut_duotone.gui.state import KNOWN_STEPS, build_step_names


def test_build_step_names_edges_toggle() -> None:
    step_order = list(KNOWN_STEPS)
    enabled = {name: True for name in KNOWN_STEPS}

    enabled["Edges"] = False
    steps = build_step_names(step_order, enabled)
    assert "Edges" not in steps

    enabled["Edges"] = True
    steps = build_step_names(step_order, enabled)
    assert "Edges" in steps


def test_build_step_names_respects_order() -> None:
    step_order = ["Threshold", "Edges", "Grayscale"]
    enabled = {"Threshold": True, "Edges": True, "Grayscale": True}

    steps = build_step_names(step_order, enabled)
    assert steps == ["Threshold", "Edges", "Grayscale"]
