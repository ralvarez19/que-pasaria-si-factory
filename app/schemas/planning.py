from pydantic import BaseModel, Field, field_validator


class PlannedScene(BaseModel):
    scene_number: int = Field(ge=1)
    duration_seconds: int = Field(gt=0)
    visual_prompt: str = Field(min_length=10)
    narration: str = Field(min_length=1)
    subtitle: str = Field(min_length=1)
    tts_text: str | None = None


class ContentPlan(BaseModel):
    title: str = Field(min_length=1)
    hook: str = Field(min_length=1)
    scenes: list[PlannedScene] = Field(min_length=1)

    @field_validator("scenes")
    @classmethod
    def validate_scene_numbers(cls, scenes: list[PlannedScene]) -> list[PlannedScene]:
        expected = list(range(1, len(scenes) + 1))
        actual = [scene.scene_number for scene in scenes]
        if actual != expected:
            raise ValueError("scene_number values must be sequential starting at 1")
        return scenes
