import json
from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings
from app.schemas.jobs import JobCreate
from app.schemas.planning import ContentPlan, PlannedScene


QUESTION_PREFIX = "Qué pasaría si"


def normalize_spanish_what_if_topic(topic: str) -> tuple[str, str]:
    cleaned = " ".join(topic.strip().split())
    body = cleaned.strip().strip("¿?").strip()
    lower_body = body.casefold()
    lower_prefix = QUESTION_PREFIX.casefold()
    if lower_body.startswith(lower_prefix):
        title_body = body
        prompt_topic = body[len(QUESTION_PREFIX) :].strip()
    else:
        title_body = f"{QUESTION_PREFIX} {body}".strip()
        prompt_topic = body
    return f"¿{title_body}?", prompt_topic or body


class PlannerProvider(ABC):
    @abstractmethod
    async def create_plan(self, request: JobCreate) -> ContentPlan:
        raise NotImplementedError


class MockPlannerProvider(PlannerProvider):
    async def create_plan(self, request: JobCreate) -> ContentPlan:
        title, topic_clean = normalize_spanish_what_if_topic(request.topic)
        beats = [
            ("cosmic establishing shot, cinematic documentary style", title),
            ("people looking at the night sky, realistic science documentary", "El cielo perdería su punto más familiar"),
            ("ocean tides becoming strangely calm, wide aerial view", "Las mareas perderían fuerza rápidamente"),
            ("coastal ecosystems exposed under soft daylight, natural history footage", "La vida costera cambiaría para siempre"),
            ("Earth rotating in space with subtle axis wobble, scientific visualization", "La Tierra oscilaría con menos estabilidad"),
            ("extreme seasons over continents, cinematic timelapse", "Las estaciones podrían volverse más extremas"),
            ("ancient humans around a fire under a dark moonless sky", "Nuestros calendarios perderían una guía antigua"),
            ("nocturnal animals moving in darker landscapes, nature documentary", "Muchas especies cambiarían sus hábitos nocturnos"),
            ("satellites and observatories tracking Earth, clean technical visualization", "Los modelos orbitales deberían recalcularse"),
            ("storm systems over oceans, detailed weather visualization", "El clima cambiaría lentamente"),
            ("astronaut footprint fading on a gray lunar surface, emotional cinematic shot", "Perderíamos huellas de nuestra exploración"),
            ("children watching a black moonless sky from a rooftop", "La noche se sentiría más vacía"),
            ("scientists in a control room analyzing Earth data, realistic documentary", "Los científicos medirían cambios durante décadas"),
            ("Earth alone against deep space, hopeful cinematic framing", "La vida no terminaría de inmediato"),
            ("sunrise over Earth with documentary realism, dramatic but hopeful", "¿Podríamos adaptarnos a ese mundo?"),
        ]
        scenes: list[PlannedScene] = []
        count = request.scene_count
        for index in range(count):
            visual, narration_tail = beats[index % len(beats)]
            scene_number = index + 1
            scenes.append(
                PlannedScene(
                    scene_number=scene_number,
                    duration_seconds=request.scene_duration_seconds,
                    visual_prompt=(
                        f"{visual}, topic: what if {topic_clean}, 16:9, 1280x720, "
                        "high detail, realistic, coherent short video scene, no text overlays"
                    ),
                    narration=narration_tail,
                    subtitle=narration_tail,
                )
            )
        return ContentPlan(
            title=title,
            hook=f"Un viaje de {request.duration_seconds} segundos para entender {topic_clean}.",
            scenes=scenes,
        )

class OllamaPlannerProvider(PlannerProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def create_plan(self, request: JobCreate) -> ContentPlan:
        prompt = (
            "Devuelve solamente JSON valido con title, hook y scenes. "
            "Cada scene debe tener scene_number, duration_seconds, visual_prompt en ingles, "
            "narration y subtitle en espanol. Para escenas de 4 segundos, narration debe tener "
            "maximo 8 a 10 palabras y 65 caracteres. subtitle debe ser exactamente igual a narration. "
            "No uses la frase 'Cada consecuencia abre la puerta a la siguiente'. "
            "No escribas dos oraciones por escena. Estilo documental curioso y claro. "
            f"Tema: {request.topic}. Escenas: {request.scene_count}. "
            f"Duracion por escena: {request.scene_duration_seconds}."
        )
        async with httpx.AsyncClient(base_url=self.settings.ollama_base_url, timeout=60) as client:
            response = await client.post(
                "/api/generate",
                json={"model": self.settings.ollama_model, "prompt": prompt, "stream": False, "format": "json"},
            )
            response.raise_for_status()
        payload = response.json()
        raw_text = payload.get("response", "")
        return ContentPlan.model_validate(json.loads(raw_text))


def get_planner_provider(settings: Settings) -> PlannerProvider:
    if settings.planner_provider.lower() == "ollama":
        return OllamaPlannerProvider(settings)
    return MockPlannerProvider()
