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
            ("cosmic establishing shot, cinematic documentary style", "Imagina que todo cambia en silencio."),
            ("people looking at the night sky, realistic science documentary", "La primera señal sería visual: el cielo perdería su punto más familiar."),
            ("ocean tides becoming strangely calm, wide aerial view", "Sin la Luna, las mareas se debilitarían de forma drástica."),
            ("coastal ecosystems exposed under soft daylight, natural history footage", "Millones de especies costeras tendrían que adaptarse o desaparecer."),
            ("Earth rotating in space with subtle axis wobble, scientific visualization", "Con el tiempo, la inclinación de la Tierra sería menos estable."),
            ("extreme seasons over continents, cinematic timelapse", "Eso podría volver las estaciones mucho más extremas."),
            ("ancient humans around a fire under a dark moonless sky", "También cambiaría nuestra historia cultural y nuestra forma de medir el tiempo."),
            ("nocturnal animals moving in darker landscapes, nature documentary", "Las noches serían más oscuras y muchos animales cambiarían su comportamiento."),
            ("satellites and observatories tracking Earth, clean technical visualization", "La tecnología seguiría funcionando, pero los modelos orbitales se ajustarían."),
            ("storm systems over oceans, detailed weather visualization", "El clima no colapsaría de golpe, aunque algunos patrones cambiarían lentamente."),
            ("astronaut footprint fading on a gray lunar surface, emotional cinematic shot", "Perderíamos un archivo físico de nuestra exploración espacial."),
            ("children watching a black moonless sky from a rooftop", "La humanidad tendría que acostumbrarse a un cielo menos poético."),
            ("scientists in a control room analyzing Earth data, realistic documentary", "Los científicos medirían cada efecto durante décadas."),
            ("Earth alone against deep space, hopeful cinematic framing", "Aun así, la vida no terminaría de inmediato."),
            ("sunrise over Earth with documentary realism, dramatic but hopeful", "La pregunta real sería cuánto podríamos adaptarnos."),
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
                    narration=f"{narration_tail} {self._transition(scene_number, count, topic_clean)}",
                    subtitle=f"{narration_tail} {self._transition(scene_number, count, topic_clean)}",
                )
            )
        return ContentPlan(
            title=title,
            hook=f"Un viaje de {request.duration_seconds} segundos para entender {topic_clean}.",
            scenes=scenes,
        )

    @staticmethod
    def _transition(scene_number: int, total: int, topic: str) -> str:
        if scene_number == 1:
            return f"Hoy exploramos: {topic}."
        if scene_number == total:
            return "Y ese final nos deja una idea inquietante: nuestro mundo depende de equilibrios invisibles."
        return "Cada consecuencia abre la puerta a la siguiente."


class OllamaPlannerProvider(PlannerProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def create_plan(self, request: JobCreate) -> ContentPlan:
        prompt = (
            "Devuelve solamente JSON valido con title, hook y scenes. "
            "Cada scene debe tener scene_number, duration_seconds, visual_prompt en ingles, "
            "narration y subtitle en espanol. Estilo documental curioso y claro. "
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
