"""Structure card extraction service.

Pipeline:
    VideoAnalysis -> prompt (real LLM) or deterministic mock -> JSON dict
    -> server-supplied fields (id, source_video_job_id, created_at)
    -> validated StructureCard

Mock mode (`LLM_PROVIDER=mock`) bypasses the LLM entirely and synthesizes a
realistic StructureCard directly from the VideoAnalysis. This keeps the
route exercisable without real Seed credentials.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List

from pydantic import ValidationError

from app.core.config import PROMPTS_DIR
from app.llm.base import LLMClient, LLMError
from app.schemas.structure_card import EditingAtom, StructureCard
from app.schemas.video import VideoAnalysis

log = logging.getLogger(__name__)

#: Path to the prompt template. Edits to the .md file are picked up at
#: request time; we reload on every call so iteration is fast.
_PROMPT_PATH = PROMPTS_DIR / "extract_structure_card.md"

#: Used when the .md file is missing or unreadable. Keeps the route
#: working even on a partial checkout.
_INLINE_TEMPLATE = (
    "You are a creative director. Given the VideoAnalysis JSON below, "
    "produce a StructureCard JSON with the keys: pattern_name, summary, "
    "hook_type, narrative_flow, visual_style, editing_atoms, "
    "reusable_rules, source_segments. Return only valid JSON.\n\n"
    "## Video Analysis\n{{video_analysis}}\n"
)


class StructureCardValidationError(RuntimeError):
    """Raised when the LLM (or mock) output cannot be coerced into a StructureCard."""


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def load_prompt_template() -> str:
    try:
        return _PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.warning("Prompt template missing at %s; using inline fallback.", _PROMPT_PATH)
        return _INLINE_TEMPLATE


def build_extract_prompt(analysis: VideoAnalysis) -> str:
    template = load_prompt_template()
    return template.replace(
        "{{video_analysis}}", analysis.model_dump_json(indent=2)
    )


def _structure_card_schema_hint() -> dict[str, Any]:
    """JSON-Schema-ish hint passed to providers that support it."""
    return {
        "type": "object",
        "required": [
            "pattern_name",
            "summary",
            "hook_type",
            "narrative_flow",
            "visual_style",
            "editing_atoms",
            "reusable_rules",
            "source_segments",
        ],
        "properties": {
            "pattern_name": {"type": "string"},
            "summary": {"type": "string"},
            "hook_type": {"type": "string"},
            "narrative_flow": {"type": "string"},
            "visual_style": {"type": "string"},
            "editing_atoms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["kind", "duration_seconds"],
                    "properties": {
                        "kind": {"type": "string"},
                        "duration_seconds": {"type": "number"},
                        "notes": {"type": "string"},
                    },
                },
            },
            "reusable_rules": {"type": "array", "items": {"type": "string"}},
            "source_segments": {"type": "array", "items": {"type": "string"}},
        },
    }


# ---------------------------------------------------------------------------
# Mock synthesis
# ---------------------------------------------------------------------------


def _atom_kind_for(index: int, total: int) -> str:
    if total <= 1:
        return "single-take"
    if index == 0:
        return "hook"
    if index == total - 1:
        return "payoff"
    if index == total // 2:
        return "reveal"
    return "development"


def build_mock_structure_card_data(analysis: VideoAnalysis) -> dict[str, Any]:
    """Deterministic synthetic StructureCard payload built from the analysis.

    Returns the LLM-shaped dict (no id / source_video_job_id / created_at);
    `extract_structure_card` adds those server-supplied fields.
    """
    n_scenes = len(analysis.scenes)

    if n_scenes == 0:
        first_dur = analysis.duration_seconds
    else:
        first = analysis.scenes[0]
        first_dur = max(first.end_seconds - first.start_seconds, 0.0)

    if n_scenes == 0:
        pattern, hook = "single-take-monologue", "static-opener"
    elif first_dur < 2.0:
        pattern, hook = "fast-cut-hook-driven", "fast-cut-opener"
    elif n_scenes <= 3:
        pattern, hook = "slow-build-narrative", "establishing-shot"
    else:
        pattern, hook = "rhythmic-multi-cut", "rhythmic-opener"

    if analysis.height > analysis.width:
        aspect = "vertical 9:16"
    elif analysis.width > analysis.height:
        aspect = "horizontal 16:9"
    else:
        aspect = "square 1:1"

    atoms: List[dict[str, Any]] = [
        {
            "kind": _atom_kind_for(i, n_scenes),
            "duration_seconds": round(s.end_seconds - s.start_seconds, 3),
            "notes": f"Maps to source segment {s.id}",
        }
        for i, s in enumerate(analysis.scenes)
    ]
    if not atoms:
        atoms = [
            {
                "kind": "single-take",
                "duration_seconds": round(analysis.duration_seconds, 3),
                "notes": "No scene segmentation available",
            }
        ]

    return {
        "pattern_name": pattern,
        "summary": (
            f"A {analysis.duration_seconds:.1f}s {aspect} short composed of "
            f"{n_scenes or 1} segment(s). Pattern emphasizes a clear hook, a "
            "midpoint reveal, and a concentrated payoff."
        ),
        "hook_type": hook,
        "narrative_flow": "hook -> development -> reveal -> payoff",
        "visual_style": (
            f"{analysis.width}x{analysis.height} at {analysis.fps:.0f}fps; "
            f"{n_scenes} cuts; {aspect}; clean transitions on motion."
        ),
        "editing_atoms": atoms,
        "reusable_rules": [
            "Open with a fast visual hook in the first 1.5 seconds.",
            "Cut on motion or audio beats to maintain pace.",
            "Place the payoff in the last third of the video.",
            "Keep on-screen text under 5 words per cut.",
            "End on a strong visual or callback to the hook.",
        ],
        "source_segments": [s.id for s in analysis.scenes],
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def extract_structure_card(
    analysis: VideoAnalysis,
    llm_client: LLMClient,
) -> StructureCard:
    """Build a StructureCard for `analysis` using the active LLM client.

    Mock provider bypasses the LLM and uses a deterministic synthesizer.
    Real providers receive the prompt template and must return JSON matching
    the StructureCard schema.

    Raises:
        LLMError: when the underlying provider call fails.
        StructureCardValidationError: when the produced JSON doesn't validate.
    """
    if llm_client.provider_name == "mock":
        raw = build_mock_structure_card_data(analysis)
    else:
        prompt = build_extract_prompt(analysis)
        try:
            raw = await llm_client.generate_json(
                prompt,
                schema_hint=_structure_card_schema_hint(),
                system=(
                    "You analyze short videos and return only valid JSON. "
                    "Never include explanation or markdown fences."
                ),
            )
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Unexpected LLM error: {exc}") from exc

    # Server-supplied fields
    raw["id"] = str(uuid.uuid4())
    raw["source_video_job_id"] = analysis.job_id
    raw["created_at"] = datetime.now(timezone.utc).isoformat()

    try:
        return StructureCard.model_validate(raw)
    except ValidationError as exc:
        # Strip the input dict from the error to avoid leaking large payloads.
        details = [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
            for e in exc.errors()
        ]
        raise StructureCardValidationError(details) from exc
