from __future__ import annotations

from pydantic import BaseModel, Field

from .models import LearningSession


class StartLearningSessionSchema(BaseModel):
    """Request schema for starting a new learning session."""

    targets: list[str] = Field(
        min_length=1, max_length=10, description='Root node IDs of the subtrees to study'
    )


# Alias the model for backward compatibility and API responses
LearningSessionSchema = LearningSession


class RecordRepetitionDataSchema(BaseModel):
    """Request schema for recording a node repetition."""

    node_id: str = Field(description='ID of the node being repeated')
    rating: int = Field(ge=0, le=5, description='Quality rating from 0 (worst) to 5 (best)')
