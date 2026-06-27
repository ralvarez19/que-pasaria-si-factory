from app.services.workflow import (
    WorkflowConfigurationError,
    apply_tts_bindings,
    apply_video_bindings,
    inspect_workflow,
    validate_t2v_workflow,
    validate_tts_bindings,
    validate_video_bindings,
)


def test_apply_video_bindings_updates_structured_inputs() -> None:
    workflow = {
        "1": {"inputs": {"text": "old"}},
        "2": {"inputs": {"width": 1}},
        "3": {"inputs": {"height": 1}},
        "4": {"inputs": {"duration": 1}},
        "5": {"inputs": {"fps": 1}},
        "6": {"inputs": {"seed": 1}},
        "7": {"inputs": {"filename_prefix": "old"}},
    }
    bindings = {
        "video": {
            "prompt_node_id": "1",
            "prompt_input_name": "text",
            "width_node_id": "2",
            "width_input_name": "width",
            "height_node_id": "3",
            "height_input_name": "height",
            "duration_node_id": "4",
            "duration_input_name": "duration",
            "fps_node_id": "5",
            "fps_input_name": "fps",
            "seed_node_id": "6",
            "seed_input_name": "seed",
            "filename_node_id": "7",
            "filename_input_name": "filename_prefix",
        }
    }

    updated = apply_video_bindings(
        workflow,
        bindings,
        prompt="new",
        width=1280,
        height=720,
        duration=4,
        fps=25,
        seed=99,
        filename_prefix="clip",
    )

    assert updated["1"]["inputs"]["text"] == "new"
    assert updated["2"]["inputs"]["width"] == 1280
    assert workflow["1"]["inputs"]["text"] == "old"


def test_apply_tts_bindings_updates_text_filename_and_seed() -> None:
    workflow = {
        "1": {"inputs": {"text": "old"}},
        "2": {"inputs": {"filename_prefix": "old"}},
        "3": {"inputs": {"seed": 1}},
        "4": {"inputs": {"format": "wav"}},
    }
    bindings = {
        "tts": {
            "text_node_id": "1",
            "text_input_name": "text",
            "filename_node_id": "2",
            "filename_input_name": "filename_prefix",
            "format_node_id": "4",
            "format_input_name": "format",
            "format_value": "flac",
            "seed_node_id": "3",
            "seed_input_name": "seed",
        }
    }

    validate_tts_bindings(workflow, bindings)
    updated = apply_tts_bindings(workflow, bindings, text="narración", filename_prefix="scene_001", seed=42)

    assert updated["1"]["inputs"]["text"] == "narración"
    assert updated["2"]["inputs"]["filename_prefix"] == "scene_001"
    assert updated["3"]["inputs"]["seed"] == 42
    assert updated["4"]["inputs"]["format"] == "flac"


def test_apply_video_bindings_applies_static_overrides() -> None:
    workflow = {
        "1": {"inputs": {"text": "old"}},
        "2": {"inputs": {"width": 1}},
        "3": {"inputs": {"height": 1}},
        "4": {"inputs": {"duration": 1}},
        "5": {"inputs": {"fps": 1}},
        "6": {"inputs": {"seed": 1}},
        "7": {"inputs": {"filename_prefix": "old"}},
        "8": {"inputs": {"lora_name": "missing.safetensors"}},
    }
    bindings = {
        "video": {
            "prompt_node_id": "1",
            "prompt_input_name": "text",
            "width_node_id": "2",
            "width_input_name": "width",
            "height_node_id": "3",
            "height_input_name": "height",
            "duration_node_id": "4",
            "duration_input_name": "duration",
            "fps_node_id": "5",
            "fps_input_name": "fps",
            "seed_node_id": "6",
            "seed_input_name": "seed",
            "filename_node_id": "7",
            "filename_input_name": "filename_prefix",
            "static_overrides": [{"node_id": "8", "input_name": "lora_name", "value": "available.safetensors"}],
        }
    }

    updated = apply_video_bindings(workflow, bindings, prompt="new", width=1, height=1, duration=1, fps=1, seed=1, filename_prefix="x")

    assert updated["8"]["inputs"]["lora_name"] == "available.safetensors"


def test_apply_video_bindings_forces_text_to_video_switch() -> None:
    workflow = {
        "1": {"inputs": {"text": "old"}},
        "2": {"inputs": {"width": 1}},
        "3": {"inputs": {"height": 1}},
        "4": {"inputs": {"duration": 1}},
        "5": {"inputs": {"fps": 1}},
        "6": {"inputs": {"seed": 1}},
        "7": {"inputs": {"filename_prefix": "old"}},
        "8": {"class_type": "PrimitiveBoolean", "_meta": {"title": "Switch to Text to Video?"}, "inputs": {"value": False}},
    }
    bindings = {
        "video": {
            "prompt_node_id": "1",
            "prompt_input_name": "text",
            "width_node_id": "2",
            "width_input_name": "width",
            "height_node_id": "3",
            "height_input_name": "height",
            "duration_node_id": "4",
            "duration_input_name": "duration",
            "fps_node_id": "5",
            "fps_input_name": "fps",
            "seed_node_id": "6",
            "seed_input_name": "seed",
            "filename_node_id": "7",
            "filename_input_name": "filename_prefix",
            "switch_text_to_video_node_id": "8",
            "switch_text_to_video_input_name": "value",
        }
    }

    updated = apply_video_bindings(workflow, bindings, prompt="new", width=1, height=1, duration=1, fps=1, seed=1, filename_prefix="x")

    assert updated["8"]["inputs"]["value"] is True


def test_apply_video_bindings_updates_multiple_seed_inputs() -> None:
    workflow = {
        "1": {"inputs": {"text": "old"}},
        "2": {"inputs": {"width": 1}},
        "3": {"inputs": {"height": 1}},
        "4": {"inputs": {"length": 1}},
        "5": {"inputs": {"fps": 1}},
        "6": {"inputs": {"noise_seed": 1}},
        "7": {"inputs": {"noise_seed": 1}},
        "8": {"inputs": {"filename_prefix": "old"}},
    }
    bindings = {
        "video": {
            "prompt_node_id": "1",
            "prompt_input_name": "text",
            "width_node_id": "2",
            "width_input_name": "width",
            "height_node_id": "3",
            "height_input_name": "height",
            "duration_node_id": "4",
            "duration_input_name": "length",
            "duration_unit": "frames",
            "duration_add_terminal_frame": True,
            "fps_node_id": "5",
            "fps_input_name": "fps",
            "seed_node_id": "7",
            "seed_input_name": "noise_seed",
            "seed_bindings": [
                {"node_id": "6", "input_name": "noise_seed"},
                {"node_id": "7", "input_name": "noise_seed"},
            ],
            "filename_node_id": "8",
            "filename_input_name": "filename_prefix",
        }
    }

    updated = apply_video_bindings(
        workflow,
        bindings,
        prompt="new",
        width=1280,
        height=720,
        duration=4,
        fps=25,
        seed=100,
        filename_prefix="clip",
    )

    assert updated["4"]["inputs"]["length"] == 101
    assert updated["6"]["inputs"]["noise_seed"] == 100
    assert updated["7"]["inputs"]["noise_seed"] == 101


def test_validate_video_bindings_checks_real_nodes() -> None:
    workflow = {
        "1": {"inputs": {"text": "old"}},
        "2": {"inputs": {"width": 1}},
        "3": {"inputs": {"height": 1}},
        "4": {"inputs": {"duration": 1}},
        "5": {"inputs": {"fps": 1}},
        "6": {"inputs": {"seed": 1}},
        "7": {"inputs": {"filename_prefix": "old"}},
    }
    bindings = {
        "video": {
            "prompt_node_id": "1",
            "prompt_input_name": "text",
            "width_node_id": "2",
            "width_input_name": "width",
            "height_node_id": "3",
            "height_input_name": "height",
            "duration_node_id": "4",
            "duration_input_name": "duration",
            "fps_node_id": "5",
            "fps_input_name": "fps",
            "seed_node_id": "6",
            "seed_input_name": "seed",
            "filename_node_id": "7",
            "filename_input_name": "filename_prefix",
        }
    }

    validate_video_bindings(workflow, bindings)


def test_apply_video_bindings_fails_on_missing_node() -> None:
    bindings = {"video": {"prompt_node_id": "missing", "prompt_input_name": "text"}}
    try:
        apply_video_bindings({}, bindings, prompt="x", width=1, height=1, duration=1, fps=1, seed=1, filename_prefix="x")
    except WorkflowConfigurationError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected WorkflowConfigurationError")


def test_validate_t2v_workflow_rejects_load_image_and_hardcoded_image() -> None:
    workflow = {
        "1": {"class_type": "LoadImage", "inputs": {"image": "photo_2026-05-20_19-13-54.jpg"}},
        "2": {"class_type": "LTXVImgToVideoInplace", "inputs": {"image": ["1", 0], "latent": ["3", 0]}},
    }

    try:
        validate_t2v_workflow(workflow)
    except WorkflowConfigurationError as exc:
        message = str(exc)
        assert "texto a video" in message
        assert "photo_2026-05-20_19-13-54.jpg" in message
        assert "LoadImage" in message
    else:
        raise AssertionError("Expected WorkflowConfigurationError")


def test_validate_t2v_workflow_rejects_id_lora() -> None:
    workflow = {
        "1": {"class_type": "LoraLoader", "inputs": {"lora_name": "ltx-2.3-id-lora-talkvid-3k.safetensors"}},
    }

    try:
        validate_t2v_workflow(workflow)
    except WorkflowConfigurationError as exc:
        assert "ID LoRA" in str(exc)
    else:
        raise AssertionError("Expected WorkflowConfigurationError")


def test_validate_t2v_workflow_allows_load_image_when_text_to_video_switch_is_true() -> None:
    workflow = {
        "1": {"class_type": "LoadImage", "inputs": {"image": "photo_2026-05-20_19-13-54.jpg"}},
        "2": {"class_type": "LTXVImgToVideoInplace", "inputs": {"image": ["1", 0], "latent": ["3", 0]}},
        "320:302": {"class_type": "PrimitiveBoolean", "_meta": {"title": "Switch to Text to Video?"}, "inputs": {"value": True}},
    }
    bindings = {"video": {"switch_text_to_video_node_id": "320:302", "switch_text_to_video_input_name": "value"}}

    validate_t2v_workflow(workflow, bindings)


def test_validate_t2v_workflow_rejects_load_image_when_switch_is_false() -> None:
    workflow = {
        "1": {"class_type": "LoadImage", "inputs": {"image": "photo_2026-05-20_19-13-54.jpg"}},
        "320:302": {"class_type": "PrimitiveBoolean", "_meta": {"title": "Switch to Text to Video?"}, "inputs": {"value": False}},
    }
    bindings = {"video": {"switch_text_to_video_node_id": "320:302", "switch_text_to_video_input_name": "value"}}

    try:
        validate_t2v_workflow(workflow, bindings)
    except WorkflowConfigurationError as exc:
        assert "modo Imagen a Video" in str(exc)
    else:
        raise AssertionError("Expected WorkflowConfigurationError")


def test_inspect_workflow_reports_categories() -> None:
    workflow = {
        "1": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": "prompt"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": "example.png"}},
        "3": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "out", "video": ["4", 0]}},
    }

    report = inspect_workflow(workflow)

    assert report["text_nodes"][0]["node_id"] == "1"
    assert report["image_nodes"][0]["node_id"] == "2"
    assert report["hardcoded_images"][0]["value"] == "example.png"
    assert report["output_nodes"][0]["node_id"] == "3"
