from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    GENERATING_VIDEO = "generating_video"
    GENERATING_AUDIO = "generating_audio"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SceneStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
