"""StructureCard: a reusable creative structure distilled from a VideoAnalysis.

Stored in the knowledge base and consumed during storyboard generation.
The TS canonical mirror lives in `packages/schemas/src/structureCard.ts`.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator


class ReferenceSource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal["user_upload", "licensed_reference", "self_authored_demo"]
    title: str = Field(min_length=1)
    author: str | None = None
    url: str | None = None
    license: str | None = None
    license_url: str | None = None
    media_url: str | None = None
    sha256: str | None = None
    original_duration_seconds: FiniteFloat | None = Field(default=None, gt=0)
    excerpt_start_seconds: FiniteFloat = Field(default=0, ge=0)
    excerpt_end_seconds: FiniteFloat | None = Field(default=None, gt=0)
    changes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_excerpt(self):
        if self.excerpt_end_seconds is not None:
            if self.excerpt_end_seconds <= self.excerpt_start_seconds:
                raise ValueError("Source excerpt must end after it starts")
            if (
                self.original_duration_seconds is not None
                and self.excerpt_end_seconds > self.original_duration_seconds
            ):
                raise ValueError("Source excerpt exceeds the original duration")
        return self


class EvidenceFrame(BaseModel):
    model_config = ConfigDict(extra="ignore")

    index: int = Field(ge=0)
    timestamp_seconds: FiniteFloat = Field(ge=0)
    url: str | None = None


class StructureObservation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=100)
    aspect: Literal["hook", "pacing", "information_flow", "caption_layout"]
    start_seconds: FiniteFloat = Field(ge=0)
    end_seconds: FiniteFloat = Field(gt=0)
    frame_indices: list[int] = Field(min_length=1, max_length=12)
    source_segments: list[str] = Field(min_length=1)
    observation: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Observation must end after it starts")
        if len(self.frame_indices) != len(set(self.frame_indices)):
            raise ValueError("Observation frame indices must be unique")
        if len(self.source_segments) != len(set(self.source_segments)):
            raise ValueError("Observation source segments must be unique")
        return self


class StructureRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=100)
    instruction: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class ReferenceReview(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: Literal["pending", "approved", "rejected"] = "pending"
    method: Literal["none", "human", "assistant_visual"] = "none"
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    notes: str | None = None


class ReferenceAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: Literal["vision", "metadata", "mock"]
    model: str | None = None
    frame_count: int = Field(ge=0)
    prompt_version: str


class EditingAtom(BaseModel):
    """One reusable editing building block within a StructureCard."""

    model_config = ConfigDict(extra="ignore")

    kind: str = Field(
        description="Short label like 'hook', 'reveal', 'callout', 'transition'."
    )
    duration_seconds: FiniteFloat = Field(ge=0.0)
    notes: Optional[str] = Field(
        default=None,
        description="Optional pacing / overlay / transition hints.",
    )


class StructureCard(BaseModel):
    """A reusable creative structure transferable across topics."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="UUID for this card.")
    pattern_name: str = Field(
        description="Short memorable label, e.g. 'hook-then-reveal-payoff'."
    )
    summary: str = Field(description="2-3 sentence plain-language description.")
    hook_type: str = Field(description="Style of the opening hook.")
    narrative_flow: str = Field(description="High-level story arc.")
    visual_style: str = Field(description="Aesthetic, pacing, transitions, framing.")
    editing_atoms: List[EditingAtom] = Field(
        default_factory=list,
        description="Ordered editing atoms describing the reusable structure.",
    )
    reusable_rules: List[str] = Field(
        default_factory=list,
        description="Transferable rules / dos and don'ts.",
    )
    source_video_job_id: str = Field(
        description="job_id of the upload this card was distilled from."
    )
    source_segments: List[str] = Field(
        default_factory=list,
        description="Scene IDs from the source VideoAnalysis that informed this card.",
    )
    created_at: datetime = Field(description="UTC timestamp when the card was built.")
    origin: str = "legacy"
    schema_version: int = Field(default=1, ge=1)
    version: int = Field(default=1, ge=1)
    source: ReferenceSource | None = None
    evidence_frames: list[EvidenceFrame] = Field(default_factory=list)
    observations: list[StructureObservation] = Field(default_factory=list)
    rules: list[StructureRule] = Field(default_factory=list)
    applicability: list[str] = Field(default_factory=list)
    material_requirements: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    review: ReferenceReview = Field(default_factory=ReferenceReview)
    analysis: ReferenceAnalysis | None = None

    @model_validator(mode="after")
    def validate_evidence_links(self):
        frame_ids = [frame.index for frame in self.evidence_frames]
        observation_ids = [item.id for item in self.observations]
        rule_ids = [item.id for item in self.rules]
        if any(
            len(ids) != len(set(ids)) for ids in (frame_ids, observation_ids, rule_ids)
        ):
            raise ValueError("Evidence frame, observation and rule IDs must be unique")
        available_frames = set(frame_ids)
        available_observations = set(observation_ids)
        for observation in self.observations:
            if not set(observation.frame_indices) <= available_frames:
                raise ValueError("Observation references an unknown evidence frame")
        for rule in self.rules:
            if not set(rule.evidence_ids) <= available_observations:
                raise ValueError("Rule references an unknown observation")
        return self
