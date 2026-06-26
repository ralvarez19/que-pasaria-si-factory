import copy
import json
from pathlib import Path
from typing import Any


class WorkflowConfigurationError(RuntimeError):
    pass


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
IMAGE_INPUT_NAMES = {"image", "first_frame", "last_frame", "reference_image", "init_image", "start_image", "end_image"}
IMAGE_CLASS_MARKERS = ("loadimage", "imagetovideo", "imgtovideo", "i2v", "ltxvimgtovideo")
ID_LORA_MARKERS = ("id-lora", "id_lora", "identity", "faceid", "instantid", "ipadapterfaceid")


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise WorkflowConfigurationError(f"Falta el archivo requerido: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
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
    force_text_to_video_switch(result, video)
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


def validate_t2v_workflow(workflow: dict[str, Any], bindings: dict[str, Any] | None = None) -> None:
    report = inspect_workflow(workflow)
    switch = get_text_to_video_switch(workflow, bindings)
    problems: list[str] = []
    has_image_reference = bool(report["hardcoded_images"] or report["image_nodes"] or report["first_last_frame_inputs"])
    if has_image_reference:
        if switch is None:
            images = ", ".join(
                f"{item['node_id']}.{item['input_name']}={item['value']}" for item in report["hardcoded_images"]
            )
            nodes = ", ".join(f"{item['node_id']} ({item['class_type']})" for item in report["image_nodes"])
            details = "; ".join(part for part in [f"imagenes hardcodeadas: {images}" if images else "", f"nodos de imagen: {nodes}" if nodes else ""] if part)
            problems.append(f"contiene LoadImage/referencias de imagen sin un switch valido de texto a video ({details})")
        elif switch["value"] is not True:
            problems.append(
                f"el workflow esta en modo Imagen a Video: {switch['node_id']}.{switch['input_name']}="
                f"{switch['value']!r}. Cambia 'Switch to Text to Video?' a true."
            )
    if report["id_lora_nodes"]:
        nodes = ", ".join(f"{item['node_id']} ({item['class_type']}: {item['value']})" for item in report["id_lora_nodes"])
        problems.append(f"parece usar ID LoRA o identidad/referencia: {nodes}")
    if problems:
        raise WorkflowConfigurationError(
            "El provider t2v requiere que el workflow ejecute la rama de texto a video; "
            + "; ".join(problems)
            + ". No se enviara el prompt a ComfyUI hasta corregirlo."
        )


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
    if video.get("switch_text_to_video_node_id") or video.get("switch_text_to_video_input_name"):
        _assert_workflow_input_exists(
            workflow,
            str(video.get("switch_text_to_video_node_id", "")),
            str(video.get("switch_text_to_video_input_name", "")),
        )
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


def force_text_to_video_switch(workflow: dict[str, Any], video_bindings: dict[str, Any]) -> None:
    node_id = str(video_bindings.get("switch_text_to_video_node_id", ""))
    input_name = str(video_bindings.get("switch_text_to_video_input_name", ""))
    if node_id and input_name:
        set_workflow_input(workflow, node_id, input_name, True)


def get_text_to_video_switch(workflow: dict[str, Any], bindings: dict[str, Any] | None = None) -> dict[str, Any] | None:
    video = bindings.get("video", {}) if isinstance(bindings, dict) else {}
    candidate_node_id = str(video.get("switch_text_to_video_node_id", "") or "")
    candidate_input = str(video.get("switch_text_to_video_input_name", "") or "")
    candidates: list[tuple[str, str]] = []
    if candidate_node_id and candidate_input:
        candidates.append((candidate_node_id, candidate_input))
    candidates.append(("320:302", "value"))
    for node_id, input_name in candidates:
        node = workflow.get(node_id)
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict) or input_name not in inputs:
            continue
        meta = node.get("_meta", {})
        title = str(meta.get("title", "")) if isinstance(meta, dict) else ""
        if node.get("class_type") == "PrimitiveBoolean" and title == "Switch to Text to Video?":
            return {"node_id": node_id, "input_name": input_name, "value": inputs[input_name], "title": title}
    return None


def inspect_workflow(workflow: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    report: dict[str, list[dict[str, Any]]] = {
        "text_nodes": [],
        "video_nodes": [],
        "image_nodes": [],
        "output_nodes": [],
        "hardcoded_images": [],
        "first_last_frame_inputs": [],
        "id_lora_nodes": [],
    }
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        class_type = str(node.get("class_type", ""))
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            inputs = {}
        class_lower = class_type.lower()
        meta = node.get("_meta", {})
        title = str(meta.get("title", "")) if isinstance(meta, dict) else ""
        entry = {"node_id": node_id, "class_type": class_type, "title": title}
        if "text" in class_lower or "string" in class_lower or "prompt" in class_lower or any("text" in str(key).lower() for key in inputs):
            report["text_nodes"].append(entry)
        if "video" in class_lower or any("video" in str(key).lower() or "latent_image" == str(key).lower() for key in inputs):
            report["video_nodes"].append(entry)
        if any(marker in class_lower for marker in IMAGE_CLASS_MARKERS) or any(_is_image_input_name(str(key)) for key in inputs):
            report["image_nodes"].append(entry)
        if class_lower.startswith("save") or "savevideo" in class_lower or "preview" in class_lower:
            report["output_nodes"].append(entry)
        for input_name, value in inputs.items():
            input_lower = str(input_name).lower()
            if input_lower in {"first_frame", "last_frame", "reference_image"}:
                report["first_last_frame_inputs"].append({**entry, "input_name": input_name, "value": value})
            if _looks_like_image_file(value):
                report["hardcoded_images"].append({**entry, "input_name": input_name, "value": value})
            if _looks_like_id_lora(input_name, value):
                report["id_lora_nodes"].append({**entry, "input_name": input_name, "value": value})
        if any(marker in class_lower for marker in ID_LORA_MARKERS):
            report["id_lora_nodes"].append({**entry, "input_name": "class_type", "value": class_type})
    return report


def _is_image_input_name(input_name: str) -> bool:
    lower = input_name.lower()
    return lower in IMAGE_INPUT_NAMES or lower.endswith("_image") or lower.endswith(".image")


def _looks_like_image_file(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lower = value.lower()
    return lower.startswith("photo_") or lower.endswith(IMAGE_EXTENSIONS)


def _looks_like_id_lora(input_name: Any, value: Any) -> bool:
    combined = f"{input_name} {value}".lower()
    return any(marker in combined for marker in ID_LORA_MARKERS)
