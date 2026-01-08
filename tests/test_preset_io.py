import pytest

from woodcut_duotone.gui.state import AppState, KNOWN_STEPS
from woodcut_duotone.io.preset_io import (
    apply_preset_dict,
    load_preset_file,
    state_to_preset_dict,
)


def test_preset_roundtrip() -> None:
    state = AppState()
    state.enabled["Edges"] = True
    state.params["Threshold"]["bias"] = 12
    state.params["Edges"]["low"] = 10
    state.step_order = list(reversed(KNOWN_STEPS))

    preset = state_to_preset_dict(state)

    restored = AppState()
    apply_preset_dict(restored, preset)

    assert restored.enabled == state.enabled
    assert restored.params == state.params
    assert restored.step_order == state.step_order


def test_preset_tolerates_missing_and_extra_steps() -> None:
    state = AppState()
    preset = {
        "version": 1,
        "step_order": ["Threshold", "Edges", "Extra Step"],
        "enabled": {"Threshold": False, "Extra Step": True},
        "params": {"Threshold": {"bias": 5}, "Extra Step": {"foo": 1}},
    }

    apply_preset_dict(state, preset)

    assert state.enabled["Threshold"] is False
    assert state.params["Threshold"]["bias"] == 5
    assert state.enabled["Edges"] is False
    assert state.params["Edges"]["low"] == 60
    assert state.step_order == [
        "Threshold",
        "Edges",
        "Denoise",
        "Detail Boost",
        "Grayscale",
        "CLAHE Contrast",
        "Gaussian Blur",
        "Foreground Emphasis",
        "Morphology",
    ]


def test_load_preset_invalid_json(tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not-json")

    with pytest.raises(ValueError):
        load_preset_file(path)
