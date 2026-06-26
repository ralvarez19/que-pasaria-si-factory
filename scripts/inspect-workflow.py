import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_binding_labels(bindings: dict[str, Any]) -> dict[tuple[str, str], str]:
    labels: dict[tuple[str, str], str] = {}
    video = bindings.get("video", {})
    if not isinstance(video, dict):
        return labels
    for key in ("prompt", "width", "height", "duration", "fps", "filename"):
        node_id = str(video.get(f"{key}_node_id", ""))
        input_name = str(video.get(f"{key}_input_name", ""))
        if node_id and input_name:
            labels[(node_id, input_name)] = key
    seed_bindings = video.get("seed_bindings")
    if isinstance(seed_bindings, list) and seed_bindings:
        for index, seed_binding in enumerate(seed_bindings, start=1):
            if isinstance(seed_binding, dict):
                labels[(str(seed_binding.get("node_id", "")), str(seed_binding.get("input_name", "")))] = f"seed[{index}]"
    elif video.get("seed_node_id") and video.get("seed_input_name"):
        labels[(str(video["seed_node_id"]), str(video["seed_input_name"]))] = "seed"
    static_overrides = video.get("static_overrides")
    if isinstance(static_overrides, list):
        for override in static_overrides:
            if isinstance(override, dict):
                labels[(str(override.get("node_id", "")), str(override.get("input_name", "")))] = "static_override"
    return labels


def format_value(value: Any) -> str:
    text = repr(value)
    if len(text) > 90:
        return text[:87] + "..."
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Resume nodos e inputs de un workflow API de ComfyUI.")
    parser.add_argument("--workflow", default="workflows/video/ltx23_t2v_api.json")
    parser.add_argument("--bindings", default="config/workflow_bindings.json")
    args = parser.parse_args()

    workflow = load_json(Path(args.workflow))
    bindings_path = Path(args.bindings)
    labels = build_binding_labels(load_json(bindings_path)) if bindings_path.exists() else {}

    print("Node ID | class_type | input | valor actual | binding asignado")
    print("--- | --- | --- | --- | ---")
    for node_id, node in workflow.items():
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            continue
        for input_name, value in inputs.items():
            label = labels.get((node_id, input_name), "")
            print(f"{node_id} | {class_type} | {input_name} | {format_value(value)} | {label}")


if __name__ == "__main__":
    main()
