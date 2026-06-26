import pytest

from app.providers.planner import MockPlannerProvider, normalize_spanish_what_if_topic
from app.schemas.jobs import JobCreate


@pytest.mark.asyncio
async def test_mock_planner_generates_requested_scene_count() -> None:
    request = JobCreate(topic="¿Qué pasaría si la Luna desapareciera?", duration_seconds=60, scene_duration_seconds=4)
    plan = await MockPlannerProvider().create_plan(request)

    assert len(plan.scenes) == 15
    assert plan.scenes[0].scene_number == 1
    assert plan.scenes[-1].scene_number == 15
    assert plan.scenes[0].duration_seconds == 4
    assert "what if" in plan.scenes[0].visual_prompt.lower()
    assert "Hoy exploramos" in plan.scenes[0].narration


@pytest.mark.asyncio
async def test_mock_planner_does_not_duplicate_what_if_prefix() -> None:
    request = JobCreate(topic="¿Qué pasaría si la Luna desapareciera?", duration_seconds=20, scene_duration_seconds=4)
    plan = await MockPlannerProvider().create_plan(request)

    assert plan.title == "¿Qué pasaría si la Luna desapareciera?"
    assert "Qué pasaría si Qué pasaría si" not in plan.title


def test_topic_normalization_adds_spanish_question_marks() -> None:
    title, prompt_topic = normalize_spanish_what_if_topic("Qué pasaría si la Luna desapareciera")

    assert title == "¿Qué pasaría si la Luna desapareciera?"
    assert prompt_topic == "la Luna desapareciera"
