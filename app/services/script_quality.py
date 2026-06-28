import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from app.providers.planner import normalize_spanish_what_if_topic
from app.providers.tts import clean_narration_for_tts
from app.schemas.jobs import JobCreate
from app.schemas.planning import ContentPlan, PlannedScene


PROHIBITED_PHRASE = "Cada consecuencia abre la puerta a la siguiente"
DEFAULT_MANUAL_SCRIPT_PATH = Path("data/input/manual_script.json")
MANUAL_4S_MIN_CHARS = 70
MANUAL_4S_MAX_CHARS = 110
MANUAL_4S_HARD_MIN_CHARS = 60
MANUAL_4S_HARD_MAX_CHARS = 115
MANUAL_4S_MIN_WORDS = 10
MANUAL_4S_MAX_WORDS = 16


class ScriptQualityError(ValueError):
    pass


@dataclass(slots=True)
class ManualScript:
    path: Path
    topic: str
    title: str
    duration_seconds: int
    scene_duration_seconds: int
    language: str
    aspect_ratio: str
    width: int
    height: int
    fps: int
    plan: ContentPlan
    warnings: list[str]


@dataclass(slots=True)
class ScriptValidationResult:
    ok: bool
    script_path: str
    errors: list[str]
    warnings: list[str] = field(default_factory=list)
    scene_count: int = 0
    title: str | None = None
    topic: str | None = None


def narration_limit_for_scene(duration_seconds: int) -> int:
    return MANUAL_4S_HARD_MAX_CHARS if duration_seconds <= 4 else 180


def narration_min_chars_for_scene(duration_seconds: int) -> int:
    return MANUAL_4S_HARD_MIN_CHARS if duration_seconds <= 4 else 1


def narration_word_bounds_for_scene(duration_seconds: int) -> tuple[int, int]:
    if duration_seconds <= 4:
        return MANUAL_4S_MIN_WORDS, MANUAL_4S_MAX_WORDS
    return 1, 60


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
                tts_text=normalize_manual_narration(narration),
            )
        )

    if not repaired_scenes:
        raise ScriptQualityError("El guion no contiene escenas")

    return ContentPlan(title=repaired_title, hook=plan.hook.strip() or repaired_title, scenes=repaired_scenes)


def load_manual_plan(script_path: Path, request: JobCreate) -> ContentPlan:
    return load_manual_script(script_path).plan


def load_manual_script(script_path: Path) -> ManualScript:
    payload = _read_manual_payload(script_path)
    errors, warnings = _validate_manual_payload(payload)
    if errors:
        raise ScriptQualityError("; ".join(errors))

    scenes_payload = []
    for raw_scene in payload["scenes"]:
        tts_text = normalize_manual_narration(raw_scene.get("tts_text") or raw_scene["narration"])
        scenes_payload.append(
            {
                "scene_number": raw_scene["scene_number"],
                "duration_seconds": raw_scene["duration_seconds"],
                "visual_prompt": raw_scene["visual_prompt"].strip(),
                "narration": str(raw_scene["narration"]).strip(),
                "subtitle": str(raw_scene["subtitle"]).strip(),
                "tts_text": tts_text,
            }
        )

    try:
        plan = ContentPlan(title=payload["title"].strip(), hook=payload.get("hook") or payload["title"].strip(), scenes=scenes_payload)
    except ValidationError as exc:
        raise ScriptQualityError(f"El guion manual no cumple el formato esperado: {exc}") from exc

    return ManualScript(
        path=Path(script_path),
        topic=payload["topic"].strip(),
        title=payload["title"].strip(),
        duration_seconds=int(payload["duration_seconds"]),
        scene_duration_seconds=int(payload["scene_duration_seconds"]),
        language=str(payload.get("language") or "es"),
        aspect_ratio=str(payload.get("aspect_ratio") or "16:9"),
        width=int(payload.get("width") or 1280),
        height=int(payload.get("height") or 720),
        fps=int(payload.get("fps") or 25),
        plan=plan,
        warnings=warnings,
    )


def validate_manual_script_file(script_path: Path) -> ScriptValidationResult:
    try:
        manual = load_manual_script(script_path)
    except ScriptQualityError as exc:
        return ScriptValidationResult(ok=False, script_path=str(script_path), errors=[part.strip() for part in str(exc).split(";") if part.strip()])
    return ScriptValidationResult(
        ok=True,
        script_path=str(script_path),
        errors=[],
        warnings=manual.warnings,
        scene_count=len(manual.plan.scenes),
        title=manual.title,
        topic=manual.topic,
    )


def resolve_manual_script_path(request: JobCreate) -> Path | None:
    if request.script_path:
        return Path(request.script_path)
    if DEFAULT_MANUAL_SCRIPT_PATH.exists():
        return DEFAULT_MANUAL_SCRIPT_PATH
    return None


def _read_manual_payload(script_path: Path) -> dict:
    path = Path(script_path)
    if not path.exists():
        raise ScriptQualityError(f"No existe el guion manual: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScriptQualityError(f"El guion manual no es JSON valido: {path}") from exc
    if not isinstance(payload, dict):
        raise ScriptQualityError("El guion manual debe ser un objeto JSON")
    return payload


def _validate_manual_payload(payload: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required = ("topic", "title", "duration_seconds", "scene_duration_seconds", "scenes")
    for field in required:
        if field not in payload or payload[field] in (None, ""):
            errors.append(f"Falta el campo requerido '{field}'")

    raw_scenes = payload.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        errors.append("El guion manual debe incluir 'scenes' no vacio")
        return errors, warnings

    for index, raw_scene in enumerate(raw_scenes, start=1):
        if not isinstance(raw_scene, dict):
            errors.append(f"La escena {index} debe ser un objeto")
            continue
        scene_has_missing_fields = False
        for field in ("scene_number", "duration_seconds", "visual_prompt", "narration", "subtitle"):
            if field not in raw_scene or raw_scene[field] in (None, ""):
                errors.append(f"La escena {index} no tiene {field}")
                scene_has_missing_fields = True
        if scene_has_missing_fields:
            continue
        narration = str(raw_scene["narration"]).strip()
        subtitle = str(raw_scene["subtitle"]).strip()
        try:
            duration_seconds = int(raw_scene["duration_seconds"])
        except (TypeError, ValueError):
            errors.append(f"La escena {index} tiene duration_seconds invalido")
            continue
        if subtitle != narration:
            errors.append(f"La escena {index} tiene subtitle distinto de narration")
        elif duration_seconds <= 4 and 55 <= len(narration) <= 69:
            original_len = len(narration)
            repaired = repair_short_narration(narration)
            if repaired != narration:
                raw_scene["narration"] = repaired
                raw_scene["subtitle"] = repaired
                raw_scene["tts_text"] = normalize_manual_narration(repaired)
                narration = repaired
                subtitle = repaired
                warnings.append(f"La escena {index} fue reparada de {original_len} a {len(repaired)} caracteres")
        if PROHIBITED_PHRASE.casefold() in narration.casefold():
            errors.append(f"La escena {index} contiene la frase prohibida")
        min_chars = narration_min_chars_for_scene(duration_seconds)
        max_chars = narration_limit_for_scene(duration_seconds)
        if len(narration) < min_chars:
            errors.append(f"La escena {index} tiene menos de {min_chars} caracteres")
        if len(narration) > max_chars:
            errors.append(f"La escena {index} supera {max_chars} caracteres")
        if duration_seconds <= 4 and min_chars <= len(narration) < MANUAL_4S_MIN_CHARS:
            warnings.append(f"La escena {index} esta bajo el ideal de {MANUAL_4S_MIN_CHARS} caracteres")
        if duration_seconds <= 4 and MANUAL_4S_MAX_CHARS < len(narration) <= max_chars:
            warnings.append(f"La escena {index} supera el ideal de {MANUAL_4S_MAX_CHARS} caracteres")
        min_words, max_words = narration_word_bounds_for_scene(duration_seconds)
        word_count = count_words(narration)
        if word_count < min_words:
            errors.append(f"La escena {index} tiene menos de {min_words} palabras")
        if word_count > max_words:
            errors.append(f"La escena {index} supera {max_words} palabras")
        if _has_multiple_long_sentences_separated_by_period(narration):
            errors.append(f"La escena {index} contiene mas de una oracion larga separada por punto")
        try:
            cleaned = normalize_manual_narration(str(raw_scene.get("tts_text") or narration))
        except ValueError as exc:
            errors.append(f"La escena {index} tiene tts_text invalido: {exc}")
            continue
        if len(cleaned) > narration_limit_for_scene(duration_seconds):
            errors.append(f"La escena {index} supera el limite despues de limpiar")
        if not cleaned:
            errors.append(f"La escena {index} queda vacia despues de limpiar")
    return errors, warnings


def repair_short_narration(text: str) -> str:
    original = re.sub(r"\s+", " ", text).strip()
    candidates = []
    replacements = [
        (" la luz ya ", " la luz del Sol ya "),
        (" la luz dejó ", " la luz del Sol dejó "),
        (" el cielo ", " el cielo nocturno "),
        (" la Tierra ", " nuestro planeta "),
        (" el Sol ", " el Sol inmenso "),
        (" la Luna ", " la Luna brillante "),
        (" los océanos ", " los océanos de la Tierra "),
    ]
    for old, new in replacements:
        if old in f" {original} ":
            candidates.append(f" {original} ".replace(old, new).strip())
    endings = ["en todo el planeta", "sin que nadie lo note", "durante unos instantes", "bajo un cielo extraño"]
    candidates.extend(f"{original} {ending}" for ending in endings)
    for candidate in candidates:
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if MANUAL_4S_HARD_MIN_CHARS <= len(candidate) <= MANUAL_4S_HARD_MAX_CHARS and count_words(candidate) <= MANUAL_4S_MAX_WORDS:
            return candidate
    return original


def normalize_manual_narration(text: str) -> str:
    return clean_narration_for_tts(text, max_chars=None)


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\wáéíóúüñÁÉÍÓÚÜÑ]+\b", text, flags=re.UNICODE))


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


def _has_multiple_long_sentences_separated_by_period(text: str) -> bool:
    parts = [part.strip() for part in text.split(".") if part.strip()]
    return len([part for part in parts if len(part) > 25]) > 1
