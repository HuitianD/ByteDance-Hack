"""Human-authored starters and explicitly reviewed, bundled reference cards."""

import uuid
import json
from app.core.config import REPO_ROOT
from app.schemas.structure_card import StructureCard
from app.runtime.store import Store

_CATALOG_MARKER = "bundled-reference-library-v1"

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

    # Reviewed reference cards are versioned artifacts shipped with the app.
    # Their public media lives under /references; user uploads stay private.
    approved = []
    for path in sorted((REPO_ROOT / "packages/reference-library/cards").glob("*.json")):
        card = StructureCard.model_validate(json.loads(path.read_text()))
        if card.origin != "vision_llm" or not card.observations or not card.rules:
            raise ValueError(f"Invalid evidence reference card: {path.name}")
        if card.review.status != "approved":
            continue
        approved.append(card)

    # The marker is storage metadata supplied only by this trusted importer;
    # descriptive origin/source fields alone must not authorize deletion.
    for card in approved:
        body = card.model_dump(mode="json")
        body["_reference_catalog"] = _CATALOG_MARKER
        store.put_resource("__public__", "card", body, public=True)

    active_ids = {card.id for card in approved}
    with store.connection(True) as db:
        rows = db.execute(
            "SELECT id,body FROM resources WHERE owner='__public__' AND kind='card' AND public=1"
        ).fetchall()
        for row in rows:
            body = json.loads(row["body"])
            if (
                row["id"] not in active_ids
                and body.get("origin") == "vision_llm"
                and body.get("_reference_catalog") == _CATALOG_MARKER
            ):
                db.execute(
                    "DELETE FROM resources WHERE id=? AND owner='__public__' AND kind='card' AND public=1",
                    (row["id"],),
                )
    # Search results are intersected with these SQLite resources, so any old
    # pgvector rows immediately lose visibility without a remote DB dependency.
