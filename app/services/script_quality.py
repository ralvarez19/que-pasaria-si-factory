import json
import re
from pathlib import Path

from pydantic import ValidationError

from app.providers.planner import normalize_spanish_what_if_topic
from app.providers.tts import clean_narration_for_tts
from app.schemas.jobs import JobCreate
from app.schemas.planning import ContentPlan, PlannedScene


PROHIBITED_PHRASE = "Cada consecuencia abre la puerta a la siguiente"
DEFAULT_MANUAL_SCRIPT_PATH = Path("data/input/manual_script.json")


class ScriptQualityError(ValueError):
    pass


def narration_limit_for_scene(duration_seconds: int) -> int:
    return 65 if duration_seconds <= 4 else 180


def clean_scene_narration(text: str, duration_seconds: int) -> str:
    max_chars = narration_limit_for_scene(duration_seconds)
    cleaned = re.sub(re.escape(PROHIBITED_PHRASE), "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;:")
    cleaned = _keep_first_sentence(cleaned)
    return clean_narration_for_tts(cleaned, max_chars=max_chars).strip(" ,")


def validate_and_repair_plan(plan: ContentPlan, request: JobCreate) -> ContentPlan:
    title, _ = normalize_spanish_what_if_topic(request.topic)
    repaired_title = title

    repaired_scenes: list[PlannedScene] = []
    for index, scene in enumerate(plan.scenes, start=1):
        if not scene.visual_prompt.strip():
            raise ScriptQualityError(f"La escena {index} no tiene visual_prompt")
        if not scene.narration.strip():
            raise ScriptQualityError(f"La escena {index} no tiene narration")
        if not scene.subtitle.strip():
            raise ScriptQualityError(f"La escena {index} no tiene subtitle")

        narration = clean_scene_narration(scene.narration, scene.duration_seconds)
        if not narration:
            raise ScriptQualityError(f"La escena {index} quedo sin narration despues de limpiar")
        if PROHIBITED_PHRASE.casefold() in narration.casefold():
            raise ScriptQualityError(f"La escena {index} contiene una frase prohibida")
        if len(narration) > narration_limit_for_scene(scene.duration_seconds):
            raise ScriptQualityError(f"La escena {index} supera el limite de caracteres")
        if _has_multiple_long_sentences(narration):
            raise ScriptQualityError(f"La escena {index} contiene dos oraciones largas")

        repaired_scenes.append(
            PlannedScene(
                scene_number=index,
                duration_seconds=scene.duration_seconds or request.scene_duration_seconds,
                visual_prompt=scene.visual_prompt.strip(),
                narration=narration,
                subtitle=narration,
            )
        )

    if not repaired_scenes:
        raise ScriptQualityError("El guion no contiene escenas")

    return ContentPlan(title=repaired_title, hook=plan.hook.strip() or repaired_title, scenes=repaired_scenes)


def load_manual_plan(script_path: Path, request: JobCreate) -> ContentPlan:
    try:
        payload = json.loads(script_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScriptQualityError(f"El guion manual no es JSON valido: {script_path}") from exc

    raw_scenes = payload.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ScriptQualityError("El guion manual debe incluir scenes")

    title = payload.get("title") or normalize_spanish_what_if_topic(payload.get("topic") or request.topic)[0]
    hook = payload.get("hook") or title
    scenes_payload = []
    for index, raw_scene in enumerate(raw_scenes, start=1):
        if not isinstance(raw_scene, dict):
            raise ScriptQualityError(f"La escena {index} del guion manual no es un objeto")
        scene_payload = dict(raw_scene)
        scene_payload.setdefault("scene_number", index)
        scene_payload.setdefault("duration_seconds", request.scene_duration_seconds)
        scenes_payload.append(scene_payload)

    try:
        plan = ContentPlan(title=title, hook=hook, scenes=scenes_payload)
    except ValidationError as exc:
        raise ScriptQualityError(f"El guion manual no cumple el formato esperado: {exc}") from exc
    return validate_and_repair_plan(plan, request)


def resolve_manual_script_path(request: JobCreate) -> Path | None:
    if request.script_path:
        return Path(request.script_path)
    if DEFAULT_MANUAL_SCRIPT_PATH.exists():
        return DEFAULT_MANUAL_SCRIPT_PATH
    return None


def _keep_first_sentence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("¿"):
        question_end = stripped.find("?")
        if question_end >= 0:
            return stripped[: question_end + 1]
    match = re.search(r"[.!?]\s+", stripped)
    if match:
        return stripped[: match.end() - 1]
    return stripped


def _has_multiple_long_sentences(text: str) -> bool:
    parts = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    return len([part for part in parts if len(part) > 25]) > 1
