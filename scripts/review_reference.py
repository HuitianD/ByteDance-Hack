"""Publish a deliberately reviewed reference card; never labels AI review as human.

Inspect the MP4 and cited frames first. Optionally edit a copy of the raw card,
then pass --edited-card. The original model extraction is kept unchanged.
"""

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.schemas.structure_card import StructureCard, ReferenceReview
from app.schemas.video import VideoAnalysis
from app.services.structure_card import _validate_visual_evidence

CATALOG = ROOT / "packages/reference-library"

IMMUTABLE_EXTRACTION_FIELDS = (
    "id",
    "source_video_job_id",
    "origin",
    "schema_version",
    "version",
    "created_at",
    "source",
    "evidence_frames",
    "analysis",
    "review",
)


def validate_review_provenance(card, original, analysis):
    """Editing interpretations must not rewrite who/what the model actually analyzed."""
    if any(
        getattr(card, field) != getattr(original, field)
        for field in IMMUTABLE_EXTRACTION_FIELDS
    ):
        raise SystemExit(
            "Do not change extraction identity, source, versions, timestamps, evidence "
            "frames, model provenance or review fields while editing. Review is set by CLI arguments."
        )
    if original.source_video_job_id != analysis.job_id:
        raise SystemExit(
            "Saved analysis does not belong to the original source upload."
        )
    _validate_visual_evidence(card, analysis)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", choices=["showcase", "question", "list"])
    parser.add_argument(
        "--method", required=True, choices=["human", "assistant_visual"]
    )
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--notes", required=True)
    parser.add_argument(
        "--status", required=True, choices=["approved", "rejected", "pending"]
    )
    parser.add_argument("--edited-card", type=Path)
    parser.add_argument(
        "--approve-current",
        action="store_true",
        help="Review the current corrected card instead of reverting to the raw model interpretation.",
    )
    args = parser.parse_args()
    raw_path = CATALOG / "extractions" / (args.slug + ".json")
    output = CATALOG / "cards" / (args.slug + ".json")
    original = StructureCard.model_validate_json(raw_path.read_text())
    if args.approve_current:
        if args.edited_card or not output.exists():
            raise SystemExit(
                "--approve-current requires an existing card and no --edited-card."
            )
        card = StructureCard.model_validate_json(output.read_text())
        # Normalize only publication metadata. All original source/model fields
        # are still checked below; corrected observations and rules are retained.
        card.id, card.version, card.review = (
            original.id,
            original.version,
            original.review,
        )
    else:
        card = StructureCard.model_validate_json(
            (args.edited_card or raw_path).read_text()
        )
    analysis = VideoAnalysis.model_validate_json(
        (CATALOG / "analyses" / (args.slug + ".json")).read_text()
    )
    validate_review_provenance(card, original, analysis)
    # Publishing is a separate resource: never collide with the private card
    # retained by the import workspace (or reassign its ownership).
    card.id = str(uuid.uuid5(uuid.NAMESPACE_URL, "viralcraft-reference:" + args.slug))
    card.reusable_rules = [rule.instruction for rule in card.rules]
    previous = (
        StructureCard.model_validate_json(output.read_text())
        if output.exists()
        else original
    )
    card.version = previous.version + 1
    card.review = ReferenceReview(
        status=args.status,
        method=args.method,
        reviewer=args.reviewer,
        reviewed_at=datetime.now(timezone.utc),
        notes=args.notes,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep all prior approved/withdrawn revisions for audit and rollback.
    revisions = CATALOG / "reviews" / args.slug
    revisions.mkdir(parents=True, exist_ok=True)
    history = revisions / f"v{card.version}.json"
    if history.exists():
        raise SystemExit(
            "Review version already exists; refusing to overwrite history."
        )
    body = card.model_dump_json(indent=2) + "\n"
    history.write_text(body)
    output.write_text(body)
    print(
        json.dumps(
            {
                "slug": args.slug,
                "version": card.version,
                "status": card.review.status,
                "method": card.review.method,
                "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
