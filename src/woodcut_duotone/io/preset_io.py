"""Preset serialization helpers for GUI pipeline settings."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from woodcut_duotone.gui.state import AppState, KNOWN_STEPS

PRESET_VERSION = 1


def state_to_preset_dict(state: AppState) -> dict[str, Any]:
    return {
        "version": PRESET_VERSION,
        "step_order": list(state.step_order),
        "enabled": deepcopy(state.enabled),
        "params": deepcopy(state.params),
    }


def apply_preset_dict(state: AppState, preset: dict[str, Any]) -> None:
    if not isinstance(preset, dict):
        raise ValueError("Preset must be a dict")

    version = preset.get("version")
    if version != PRESET_VERSION:
        raise ValueError("Unsupported preset version")

    step_order = preset.get("step_order", None)
    enabled = preset.get("enabled", None)
    params = preset.get("params", None)

    if step_order is not None and not isinstance(step_order, list):
        raise ValueError("step_order must be a list")
    if enabled is not None and not isinstance(enabled, dict):
        raise ValueError("enabled must be a dict")
    if params is not None and not isinstance(params, dict):
        raise ValueError("params must be a dict")

    new_enabled = dict(state.enabled)
    new_params = deepcopy(state.params)
    new_step_order = list(state.step_order)

    if isinstance(step_order, list):
        filtered_order: list[str] = []
        for name in step_order:
            if name in KNOWN_STEPS and name not in filtered_order:
                filtered_order.append(name)
        for name in new_step_order:
            if name in KNOWN_STEPS and name not in filtered_order:
                filtered_order.append(name)
        if filtered_order:
            new_step_order = filtered_order

    if isinstance(enabled, dict):
        for name in KNOWN_STEPS:
            if name in enabled:
                new_enabled[name] = bool(enabled[name])

    if isinstance(params, dict):
        for name in KNOWN_STEPS:
            if name not in params:
                continue
            step_params = params[name]
            if not isinstance(step_params, dict):
                raise ValueError(f"params for {name} must be a dict")
            merged = dict(new_params.get(name, {}))
            merged.update(step_params)
            new_params[name] = merged

    state.enabled = new_enabled
    state.params = new_params
    state.step_order = new_step_order


def load_preset_file(path: str | Path) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid preset file") from exc
    if not isinstance(data, dict):
        raise ValueError("Preset data must be a JSON object")
    return data


def save_preset_file(path: str | Path, preset: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(preset, handle, indent=2, sort_keys=True)
