"""StructureCard: a reusable creative structure distilled from a VideoAnalysis.

Stored in the knowledge base and consumed during storyboard generation.
The TS canonical mirror lives in `packages/schemas/src/structureCard.ts`.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EditingAtom(BaseModel):
    """One reusable editing building block within a StructureCard."""

    model_config = ConfigDict(extra="ignore")

    kind: str = Field(
        description="Short label like 'hook', 'reveal', 'callout', 'transition'."
    )
    duration_seconds: float = Field(ge=0.0)
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
    visual_style: str = Field(
        description="Aesthetic, pacing, transitions, framing."
    )
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
