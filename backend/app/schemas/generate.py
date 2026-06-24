from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000, description="Natural language description")
    media_type: Literal["image", "video"] = "image"
    quality_preset: Literal["draft", "standard", "ultra"] = "standard"
    style_hints: list[str] = Field(default_factory=list, max_length=10)
    priority: Literal[0, 1, 2, 3] = 2
    duration_seconds: int = Field(default=4, ge=2, le=8, description="Video duration in seconds (video only)")

    @field_validator("style_hints")
    @classmethod
    def validate_style_hints(cls, v: list[str]) -> list[str]:
        return [h.strip().lower() for h in v if h.strip()][:10]


class JobResponse(BaseModel):
    job_id: uuid.UUID = Field(alias="id")
    status: str
    media_type: str
    raw_prompt: str
    quality_preset: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    enhanced_prompt: Optional[str] = None
    model_id: Optional[str] = None
    quality_score: Optional[float] = None
    error_message: Optional[str] = None
    current_step: Optional[str] = None

    model_config = {"from_attributes": True, "protected_namespaces": (), "populate_by_name": True}


class AutocompleteResponse(BaseModel):
    prefix: str
    suggestions: list[str]


class GenerateResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str
    estimated_seconds: Optional[int] = None
