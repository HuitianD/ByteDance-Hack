from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.storyboard import StoryboardGenerateRequest


class Invitation(BaseModel):
    code: str = Field(min_length=8, max_length=128)


class JobSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["analyze", "learn", "generate", "render", "assets"]
    resource_id: UUID | None = None
    version: int | None = Field(default=None, ge=1)
    storyboard: StoryboardGenerateRequest | None = None
    scene_ids: list[str] = Field(default_factory=list, max_length=2)
    reference_frame_id: UUID | None = None
    reference_has_no_faces: bool = False


class JobView(BaseModel):
    id: str
    kind: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    result: dict | None = None
    error: str | None = None
    created_at: float
    updated_at: float


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class Feedback(BaseModel):
    storyboard_id: UUID
    rating: Literal["publish", "edit", "reject"]
    comment: str = Field(default="", max_length=1000)
