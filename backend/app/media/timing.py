from pydantic import BaseModel, Field


class ProcessingTiming(BaseModel):
    step: str
    label: str
    duration_seconds: float = Field(ge=0)


def processing_timing(step: str, label: str, duration_seconds: float) -> ProcessingTiming:
    return ProcessingTiming(
        step=step,
        label=label,
        duration_seconds=round(max(duration_seconds, 0), 3),
    )
