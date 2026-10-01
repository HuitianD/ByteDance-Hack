"""Explicitly human-authored public examples, never attributed to an analyzer."""

import uuid
from app.schemas.structure_card import StructureCard
from app.runtime.store import Store

PATTERNS = [
    (
        "Sensory product reveal",
        "感官产品展示",
        "Close-up opener → sensory details → invitation",
        "visual-detail",
        ["hook", "detail", "payoff"],
        "Use short, concrete sensory copy; keep the product visible.",
    ),
    (
        "Problem to solution",
        "问题到解决方案",
        "Recognizable problem → practical benefit → CTA",
        "problem-question",
        ["hook", "solution", "cta"],
        "Use only benefits supplied by the user; do not invent performance claims.",
    ),
    (
        "Three reasons to try",
        "三个尝试理由",
        "Clear promise → concise reasons → invitation",
        "direct-promise",
        ["hook", "feature", "cta"],
        "Use a consistent cadence; keep captions readable and finish with one action.",
    ),
]


def seed_library(store: Store):
    for name, zh, flow, hook, atoms, rule in PATTERNS:
        cid = str(uuid.uuid5(uuid.NAMESPACE_URL, "viralcraft-template:" + name))
        card = StructureCard(
            id=cid,
            pattern_name=name,
            summary=f"{zh}. {flow}. Human-authored starter, not learned from a reference video.",
            hook_type=hook,
            narrative_flow=flow,
            visual_style="Adapt typography and pacing to the supplied target footage.",
            editing_atoms=[{"kind": a, "duration_seconds": 5} for a in atoms],
            reusable_rules=[rule],
            source_video_job_id="",
            source_segments=[],
            created_at="2026-09-29T00:00:00Z",
            origin="curated",
        )
        store.put_resource(
            "__public__", "card", card.model_dump(mode="json"), public=True
        )
