from pathlib import Path

import pytest

from app.core.config import Settings
from app.db.session import SessionLocal, init_db
from app.providers.planner import MockPlannerProvider
from app.schemas.jobs import JobCreate
from app.schemas.planning import ContentPlan, PlannedScene
from app.services.script_quality import PROHIBITED_PHRASE, load_manual_script, resolve_manual_script_path, validate_and_repair_plan, validate_manual_script_file
from app.services.worker import JobWorker
from app.services.telegram import TelegramNotifier
from app.providers.tts import SilentTTSProvider
from app.providers.video import PlaceholderVideoProvider
from app.services.ffmpeg import FFmpegAssembler


@pytest.mark.asyncio
async def test_mock_plan_title_and_short_narrations() -> None:
    request = JobCreate(topic="¿Qué pasaría si la Luna desapareciera?", duration_seconds=60, scene_duration_seconds=4)
    plan = await MockPlannerProvider().create_plan(request)
    repaired = validate_and_repair_plan(plan, request)

    assert repaired.title == "¿Qué pasaría si la Luna desapareciera?"
    assert len(repaired.scenes) == 15
    assert all(len(scene.narration) <= 65 for scene in repaired.scenes)
    assert all(scene.subtitle == scene.narration for scene in repaired.scenes)
    assert all(PROHIBITED_PHRASE not in scene.narration for scene in repaired.scenes)


def test_validate_plan_removes_prohibited_phrase_and_matches_subtitle() -> None:
    request = JobCreate(topic="¿Qué pasaría si la Luna desapareciera?", duration_seconds=4, scene_duration_seconds=4)
    plan = ContentPlan(
        title="Hoy exploramos: la Luna desapareciera.",
        hook="hook",
        scenes=[
            PlannedScene(
                scene_number=1,
                duration_seconds=4,
                visual_prompt="realistic cinematic documentary scene",
                narration=f"Sin la Luna, las mareas cambiarían. {PROHIBITED_PHRASE}.",
                subtitle="Texto distinto",
            )
        ],
    )

    repaired = validate_and_repair_plan(plan, request)

    assert repaired.title == "¿Qué pasaría si la Luna desapareciera?"
    assert repaired.scenes[0].subtitle == repaired.scenes[0].narration
    assert PROHIBITED_PHRASE not in repaired.scenes[0].narration
    assert len(repaired.scenes[0].narration) <= 65


def test_load_manual_script_json(tmp_path: Path) -> None:
    manual = tmp_path / "manual_script.json"
    manual.write_text(
        """
{
  "topic": "¿Qué pasaría si la Luna desapareciera?",
  "title": "¿Qué pasaría si la Luna desapareciera?",
  "duration_seconds": 4,
  "scene_duration_seconds": 4,
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 4,
      "visual_prompt": "A cinematic view of Earth from space with the Moon fading away.",
      "narration": "Imagina que la Luna desaparece, y la Tierra empieza a cambiar en silencio",
      "subtitle": "Imagina que la Luna desaparece, y la Tierra empieza a cambiar en silencio"
    }
  ]
}
""",
        encoding="utf-8",
    )

    manual_script = load_manual_script(manual)

    assert manual_script.plan.title == "¿Qué pasaría si la Luna desapareciera?"
    assert manual_script.plan.scenes[0].subtitle == manual_script.plan.scenes[0].narration


def test_resolve_manual_script_path_keeps_explicit_missing_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    path = resolve_manual_script_path(JobCreate(topic="¿Qué pasaría si el Sol se apagara?", script_path=str(tmp_path / "missing.json")))

    assert path == tmp_path / "missing.json"
    assert not path.exists()


def test_validate_manual_script_without_scenes_fails(tmp_path: Path) -> None:
    manual = tmp_path / "manual_script.json"
    manual.write_text(
        '{"topic":"¿Qué pasaría si la Luna desapareciera?","title":"¿Qué pasaría si la Luna desapareciera?","duration_seconds":4,"scene_duration_seconds":4,"scenes":[]}',
        encoding="utf-8",
    )

    result = validate_manual_script_file(manual)

    assert result.ok is False
    assert any("scenes" in error for error in result.errors)


def test_validate_manual_scene_without_visual_prompt_fails(tmp_path: Path) -> None:
    manual = write_manual_script(tmp_path, {"visual_prompt": ""})

    result = validate_manual_script_file(manual)

    assert result.ok is False
    assert any("visual_prompt" in error for error in result.errors)


def test_validate_manual_long_narration_fails(tmp_path: Path) -> None:
    manual = write_manual_script(tmp_path, {"narration": " ".join(["Mañana"] * 20), "subtitle": " ".join(["Mañana"] * 20)})

    result = validate_manual_script_file(manual)

    assert result.ok is False
    assert any("115 caracteres" in error for error in result.errors)


def test_validate_manual_short_narration_fails(tmp_path: Path) -> None:
    manual = write_manual_script(tmp_path, {"narration": "¿Qué pasaría si la Luna desapareciera?", "subtitle": "¿Qué pasaría si la Luna desapareciera?"})

    result = validate_manual_script_file(manual)

    assert result.ok is False
    assert any("60 caracteres" in error for error in result.errors)
    assert any("10 palabras" in error for error in result.errors)


def test_validate_manual_repairs_nearly_short_narration(tmp_path: Path) -> None:
    narration = "Durante ocho minutos, nadie sabría que la luz ya dejó de viajar."
    manual = write_manual_script(tmp_path, {"narration": narration, "subtitle": narration})

    result = validate_manual_script_file(manual)
    manual_script = load_manual_script(manual)

    assert result.ok is True
    assert result.warnings
    repaired = manual_script.plan.scenes[0].narration
    assert repaired == "Durante ocho minutos, nadie sabría que la luz del Sol ya dejó de viajar."
    assert manual_script.plan.scenes[0].subtitle == repaired
    assert manual_script.plan.scenes[0].tts_text == "Durante ocho minutos, nadie sabría que la luz del Sol ya dejó de viajar"


def test_validate_manual_subtitle_mismatch_fails(tmp_path: Path) -> None:
    manual = write_manual_script(tmp_path, {"subtitle": "Texto distinto"})

    result = validate_manual_script_file(manual)

    assert result.ok is False
    assert any("subtitle distinto" in error for error in result.errors)


def test_validate_manual_allows_points_and_generates_tts_text(tmp_path: Path) -> None:
    narration = "Al principio, el cielo perdería su punto más familiar. La noche cambia mucho"
    manual = write_manual_script(tmp_path, {"narration": narration, "subtitle": narration})

    result = validate_manual_script_file(manual)
    manual_script = load_manual_script(manual)

    assert result.ok is True
    scene = manual_script.plan.scenes[0]
    assert scene.subtitle == narration
    assert scene.tts_text == "Al principio, el cielo perdería su punto más familiar, La noche cambia mucho"


def test_validate_manual_uses_explicit_tts_text(tmp_path: Path) -> None:
    narration = "Al principio, el cielo perdería su punto más familiar. La noche cambia mucho"
    manual = write_manual_script(
        tmp_path,
        {
            "narration": narration,
            "subtitle": narration,
            "tts_text": "Al principio, el cielo perdería su punto más familiar, la noche cambia mucho",
        },
    )

    manual_script = load_manual_script(manual)

    assert manual_script.plan.scenes[0].tts_text == "Al principio, el cielo perdería su punto más familiar, la noche cambia mucho"


def test_validate_manual_prohibited_phrase_fails(tmp_path: Path) -> None:
    manual = write_manual_script(tmp_path, {"narration": PROHIBITED_PHRASE, "subtitle": PROHIBITED_PHRASE})

    result = validate_manual_script_file(manual)

    assert result.ok is False
    assert any("frase prohibida" in error for error in result.errors)


def test_validate_manual_missing_script_path_fails(tmp_path: Path) -> None:
    result = validate_manual_script_file(tmp_path / "missing.json")

    assert result.ok is False
    assert any("No existe" in error for error in result.errors)


@pytest.mark.asyncio
async def test_job_can_be_created_with_manual_script_path_and_copies_input(tmp_path: Path) -> None:
    init_db()
    settings = Settings(jobs_dir=tmp_path / "jobs", log_file=tmp_path / "app.log")
    worker = JobWorker(
        settings=settings,
        planner=MockPlannerProvider(),
        video_provider=PlaceholderVideoProvider(settings),
        tts_provider=SilentTTSProvider(settings),
        assembler=FFmpegAssembler(settings),
        telegram_notifier=TelegramNotifier(settings),
    )
    manual = write_manual_script(tmp_path)
    with SessionLocal() as db:
        job = worker.create_job_from_script(db, manual)
        job_id = job.id
        assert job.script_path.endswith("manual_script.json")
        await worker._plan(db, job, __import__("logging").getLogger("test"))

        db.delete(job)
        db.commit()

    assert (settings.jobs_dir / job_id / "job.json").exists()
    assert (settings.jobs_dir / job_id / "input_script.json").exists()


def test_automatic_job_without_script_path_still_works(tmp_path: Path) -> None:
    init_db()
    settings = Settings(jobs_dir=tmp_path / "jobs", log_file=tmp_path / "app.log")
    worker = JobWorker(
        settings=settings,
        planner=MockPlannerProvider(),
        video_provider=PlaceholderVideoProvider(settings),
        tts_provider=SilentTTSProvider(settings),
        assembler=FFmpegAssembler(settings),
        telegram_notifier=TelegramNotifier(settings),
    )
    with SessionLocal() as db:
        job = worker.create_job(db, JobCreate(topic="¿Qué pasaría si el Sol se apagara?", duration_seconds=4, scene_duration_seconds=4))
        assert job.script_path is None
        db.delete(job)
        db.commit()


def write_manual_script(tmp_path: Path, scene_overrides: dict | None = None) -> Path:
    scene = {
        "scene_number": 1,
        "duration_seconds": 4,
        "visual_prompt": "A cinematic realistic view of planet Earth from space as the Moon slowly fades away.",
        "narration": "Imagina que la Luna desaparece, y la Tierra empieza a cambiar en silencio",
        "subtitle": "Imagina que la Luna desaparece, y la Tierra empieza a cambiar en silencio",
    }
    if scene_overrides:
        scene.update(scene_overrides)
    manual = tmp_path / "manual_script.json"
    manual.write_text(
        __import__("json").dumps(
            {
                "topic": "¿Qué pasaría si la Luna desapareciera?",
                "title": "¿Qué pasaría si la Luna desapareciera?",
                "duration_seconds": 4,
                "scene_duration_seconds": 4,
                "language": "es",
                "aspect_ratio": "16:9",
                "width": 1280,
                "height": 720,
                "fps": 25,
                "scenes": [scene],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return manual
