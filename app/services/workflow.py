import copy
import json
from pathlib import Path
from typing import Any


class WorkflowConfigurationError(RuntimeError):
    pass


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise WorkflowConfigurationError(f"Falta el archivo requerido: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkflowConfigurationError(f"El archivo JSON no es valido: {path}") from exc


def load_workflow_bindings(path: Path) -> dict[str, Any]:
    return load_json_file(path)


def set_workflow_input(workflow: dict[str, Any], node_id: str, input_name: str, value: Any) -> None:
    if not node_id:
        raise WorkflowConfigurationError("Un binding no tiene node_id configurado.")
    if not input_name:
        raise WorkflowConfigurationError("Un binding no tiene input_name configurado.")
    node = workflow.get(str(node_id))
    if not isinstance(node, dict):
        raise WorkflowConfigurationError(f"No existe el nodo '{node_id}' en el workflow.")
    inputs = node.get("inputs")
    if not isinstance(inputs, dict):
        raise WorkflowConfigurationError(f"El nodo '{node_id}' no contiene inputs.")
    if input_name not in inputs:
        raise WorkflowConfigurationError(f"El input '{input_name}' no existe en el nodo '{node_id}'.")
    inputs[input_name] = value


def apply_video_bindings(
    workflow: dict[str, Any],
    bindings: dict[str, Any],
    *,
    prompt: str,
    width: int,
    height: int,
    duration: int,
    fps: int,
    seed: int,
    filename_prefix: str,
) -> dict[str, Any]:
    result = copy.deepcopy(workflow)
    video = bindings.get("video")
    if not isinstance(video, dict):
        raise WorkflowConfigurationError("config/workflow_bindings.json debe contener la seccion 'video'.")
    apply_static_overrides(result, video)
    duration_value = _duration_value(video, duration=duration, fps=fps)
    values = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "duration": duration_value,
        "fps": fps,
        "filename": filename_prefix,
    }
    for key, value in values.items():
        set_workflow_input(result, str(video.get(f"{key}_node_id", "")), str(video.get(f"{key}_input_name", "")), value)
    seed_bindings = video.get("seed_bindings")
    if isinstance(seed_bindings, list) and seed_bindings:
        for index, seed_binding in enumerate(seed_bindings):
            if not isinstance(seed_binding, dict):
                raise WorkflowConfigurationError("Cada seed_binding debe ser un objeto.")
            seed_value = seed + index
            set_workflow_input(result, str(seed_binding.get("node_id", "")), str(seed_binding.get("input_name", "")), seed_value)
    else:
        set_workflow_input(result, str(video.get("seed_node_id", "")), str(video.get("seed_input_name", "")), seed)
    return result


def validate_video_bindings(workflow: dict[str, Any], bindings: dict[str, Any]) -> None:
    video = bindings.get("video")
    if not isinstance(video, dict):
        raise WorkflowConfigurationError("config/workflow_bindings.json debe contener la seccion 'video'.")
    static_overrides = video.get("static_overrides", [])
    if isinstance(static_overrides, list):
        for override in static_overrides:
            if not isinstance(override, dict):
                raise WorkflowConfigurationError("Cada static_override debe ser un objeto.")
            _assert_workflow_input_exists(workflow, str(override.get("node_id", "")), str(override.get("input_name", "")))
    required = ("prompt", "width", "height", "duration", "fps", "filename")
    for key in required:
        _assert_workflow_input_exists(workflow, str(video.get(f"{key}_node_id", "")), str(video.get(f"{key}_input_name", "")))
    seed_bindings = video.get("seed_bindings")
    if isinstance(seed_bindings, list) and seed_bindings:
        for seed_binding in seed_bindings:
            if not isinstance(seed_binding, dict):
                raise WorkflowConfigurationError("Cada seed_binding debe ser un objeto.")
            _assert_workflow_input_exists(workflow, str(seed_binding.get("node_id", "")), str(seed_binding.get("input_name", "")))
    else:
        _assert_workflow_input_exists(workflow, str(video.get("seed_node_id", "")), str(video.get("seed_input_name", "")))


def _assert_workflow_input_exists(workflow: dict[str, Any], node_id: str, input_name: str) -> None:
    if not node_id:
        raise WorkflowConfigurationError("Un binding no tiene node_id configurado.")
    if not input_name:
        raise WorkflowConfigurationError("Un binding no tiene input_name configurado.")
    node = workflow.get(str(node_id))
    if not isinstance(node, dict):
        raise WorkflowConfigurationError(f"No existe el nodo '{node_id}' en el workflow.")
    inputs = node.get("inputs")
    if not isinstance(inputs, dict):
        raise WorkflowConfigurationError(f"El nodo '{node_id}' no contiene inputs.")
    if input_name not in inputs:
        raise WorkflowConfigurationError(f"El input '{input_name}' no existe en el nodo '{node_id}'.")


def _duration_value(video_bindings: dict[str, Any], *, duration: int, fps: int) -> int:
    unit = str(video_bindings.get("duration_unit", "seconds")).lower()
    if unit in {"seconds", "duration_seconds"}:
        return duration
    if unit in {"frames", "frame_count", "num_frames", "length"}:
        include_terminal_frame = bool(video_bindings.get("duration_add_terminal_frame", False))
        return duration * fps + (1 if include_terminal_frame else 0)
    raise WorkflowConfigurationError(f"duration_unit no soportado: {unit}")


def apply_static_overrides(workflow: dict[str, Any], video_bindings: dict[str, Any]) -> None:
    static_overrides = video_bindings.get("static_overrides", [])
    if not isinstance(static_overrides, list):
        return
    for override in static_overrides:
        if not isinstance(override, dict):
            raise WorkflowConfigurationError("Cada static_override debe ser un objeto.")
        set_workflow_input(
            workflow,
            str(override.get("node_id", "")),
            str(override.get("input_name", "")),
            override.get("value"),
        )
