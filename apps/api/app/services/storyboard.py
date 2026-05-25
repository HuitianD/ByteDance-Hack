"""Storyboard generation service.

Pipeline:
    user_prompt + target_duration + selected StructureCards
        -> prompt (real LLM) or deterministic mock
        -> raw {title, scenes[]}
        -> normalize durations + recompute start_time/end_time
        -> attach server-supplied fields
        -> validated Storyboard

Mock mode bypasses the LLM entirely so the route is exercisable without
real Seed credentials.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Sequence

from pydantic import ValidationError

from app.core.config import PROMPTS_DIR
from app.llm.base import LLMClient, LLMError
from app.schemas.storyboard import (
    DEFAULT_FPS,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    Storyboard,
    StoryboardScene,
)
from app.schemas.structure_card import StructureCard

log = logging.getLogger(__name__)

_PROMPT_PATH = PROMPTS_DIR / "generate_storyboard.md"

_INLINE_TEMPLATE = (
    "You are a short-video storyboard generator. Given the user prompt, "
    "target duration, and reference StructureCards below, return a JSON "
    'object with keys "title" and "scenes". Each scene must include '
    "scene_id, duration_seconds, layout, text, visual_description, "
    "animation, transition, asset_prompt, source_structure_card_id, "
    "source_editing_atoms. Return only valid JSON.\n\n"
    "## User Prompt\n{{user_prompt}}\n\n"
    "## Target Duration\n{{target_duration_seconds}} seconds\n\n"
    "## Structure Cards\n{{retrieved_cards}}\n"
)

#: How many recent cards to fall back to when no source_job_ids given.
_MAX_RECENT_CARDS = 3
_MIN_RECENT_CARDS = 1


class StoryboardValidationError(RuntimeError):
    """Raised when the LLM/mock output cannot be coerced into a Storyboard."""


class CardSelectionError(RuntimeError):
    """Raised when the requested or fallback structure cards aren't available."""


# ---------------------------------------------------------------------------
# Card selection
# ---------------------------------------------------------------------------


def _is_uuid(name: str) -> bool:
    try:
        uuid.UUID(name)
        return True
    except ValueError:
        return False


def select_structure_cards(
    *,
    data_dir: Path,
    source_job_ids: Optional[Sequence[str]],
) -> List[StructureCard]:
    """Resolve the StructureCards used as references for generation.

    - If `source_job_ids` is provided, every job_id must have a saved card.
    - Otherwise the most recent 1-3 cards (by mtime) on disk are used.
    """
    kb_dir = data_dir / "knowledge_base"

    if source_job_ids:
        cards: List[StructureCard] = []
        missing: List[str] = []
        for jid in source_job_ids:
            if not _is_uuid(jid):
                raise CardSelectionError(
                    f"Invalid source_job_id '{jid}' (must be a UUID)."
                )
            path = kb_dir / jid / "structure_card.json"
            if not path.exists():
                missing.append(jid)
                continue
            cards.append(
                StructureCard.model_validate_json(path.read_text(encoding="utf-8"))
            )
        if missing:
            raise CardSelectionError(
                "No structure card found for job(s): " + ", ".join(missing)
            )
        return cards

    if not kb_dir.exists():
        raise CardSelectionError(
            "No knowledge base yet. Run /extract-structure-card on at least one job first."
        )

    candidates: List[tuple[float, Path]] = []
    for sub in kb_dir.iterdir():
        if not sub.is_dir() or not _is_uuid(sub.name):
            continue
        path = sub / "structure_card.json"
        if path.exists():
            candidates.append((path.stat().st_mtime, path))

    candidates.sort(reverse=True)
    if not candidates:
        raise CardSelectionError(
            "No structure cards available. Run /extract-structure-card on at least one job first."
        )

    chosen = candidates[: max(_MIN_RECENT_CARDS, min(_MAX_RECENT_CARDS, len(candidates)))]
    return [
        StructureCard.model_validate_json(p.read_text(encoding="utf-8"))
        for _, p in chosen
    ]


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def load_prompt_template() -> str:
    try:
        return _PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.warning(
            "Prompt template missing at %s; using inline fallback.", _PROMPT_PATH
        )
        return _INLINE_TEMPLATE


def build_generate_prompt(
    *,
    user_prompt: str,
    target_duration_seconds: float,
    cards: Sequence[StructureCard],
) -> str:
    template = load_prompt_template()
    cards_json = json.dumps(
        [json.loads(c.model_dump_json()) for c in cards], indent=2
    )
    return (
        template.replace("{{user_prompt}}", user_prompt)
        .replace("{{target_duration_seconds}}", str(target_duration_seconds))
        .replace("{{retrieved_cards}}", cards_json)
    )


def _storyboard_schema_hint() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["title", "scenes"],
        "properties": {
            "title": {"type": "string"},
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "scene_id",
                        "duration_seconds",
                        "layout",
                        "visual_description",
                    ],
                    "properties": {
                        "scene_id": {"type": "string"},
                        "start_time": {"type": "number"},
                        "end_time": {"type": "number"},
                        "duration_seconds": {"type": "number"},
                        "layout": {"type": "string"},
                        "text": {"type": "string"},
                        "visual_description": {"type": "string"},
                        "animation": {"type": "string"},
                        "transition": {"type": "string"},
                        "asset_prompt": {"type": "string"},
                        "source_structure_card_id": {"type": "string"},
                        "source_editing_atoms": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# Mock synthesis
# ---------------------------------------------------------------------------


#: Canonical layouts. Must stay in sync with the renderer normalizer at
#: `apps/renderer/src/util/layout.ts`.
_LAYOUTS = [
    "hook_title",
    "text_over_media",
    "feature_card",
    "split_compare",
    "default_scene",
    "cta_card",
]
_ANIMATIONS = ["fade-in", "slide-up", "scale-pulse", "ken-burns", "type-on"]


def build_mock_storyboard_data(
    *,
    user_prompt: str,
    target_duration_seconds: float,
    cards: Sequence[StructureCard],
) -> dict[str, Any]:
    """Deterministic mock that derives scene structure from the first card."""
    primary = cards[0]
    atom_kinds = (
        [a.kind for a in primary.editing_atoms] or ["hook", "development", "payoff"]
    )

    # Pick 3-6 scenes; if first card has more atoms, sample the first 6.
    n_scenes = max(3, min(6, len(atom_kinds)))
    chosen_atoms = atom_kinds[:n_scenes]
    if len(chosen_atoms) < n_scenes:
        # pad with development beats
        chosen_atoms += ["development"] * (n_scenes - len(chosen_atoms))

    scenes: list[dict[str, Any]] = []
    for i, atom_kind in enumerate(chosen_atoms):
        is_first = i == 0
        is_last = i == n_scenes - 1

        if is_first:
            layout = "hook_title"
        elif is_last:
            layout = "cta_card"
        else:
            # rotate through the middle (non-hook/non-cta) layouts
            middle = ["text_over_media", "feature_card", "split_compare", "default_scene"]
            layout = middle[(i - 1) % len(middle)]

        scenes.append(
            {
                "scene_id": f"scene_{i:03d}",
                "duration_seconds": target_duration_seconds / n_scenes,
                "layout": layout,
                "text": _mock_scene_text(user_prompt, atom_kind, is_first, is_last),
                "visual_description": _mock_visual(user_prompt, atom_kind, primary),
                "animation": "fade-in" if is_first else _ANIMATIONS[i % len(_ANIMATIONS)],
                "transition": "none" if is_first else "cut" if i % 2 else "fade",
                "asset_prompt": (
                    f"Short-form video {atom_kind} scene about: {user_prompt[:160]}. "
                    f"Visual style: {primary.visual_style}"
                ),
                "source_structure_card_id": primary.id,
                "source_editing_atoms": [atom_kind],
            }
        )

    title = f"Mock storyboard: {user_prompt[:60]}".strip()
    return {"title": title, "scenes": scenes}


def _mock_scene_text(user_prompt: str, atom_kind: str, first: bool, last: bool) -> str:
    snippet = user_prompt.strip().split(".")[0][:48]
    if first:
        return snippet or "Hook"
    if last:
        return "Try it now"
    return f"{atom_kind.title()}"


def _mock_visual(user_prompt: str, atom_kind: str, card: StructureCard) -> str:
    return (
        f"{atom_kind.capitalize()} beat for '{user_prompt[:80]}'. "
        f"Apply {card.visual_style.split(';')[0].strip().lower()} aesthetic."
    )


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_scenes(
    raw_scenes: list[dict[str, Any]],
    target_duration_seconds: float,
) -> tuple[list[dict[str, Any]], float]:
    """Scale scene durations to sum to target, then recompute start/end.

    Always returns scenes with consistent, contiguous start_time / end_time
    regardless of what the LLM produced.
    """
    if not raw_scenes:
        return [], 0.0

    durations: list[float] = []
    for s in raw_scenes:
        try:
            d = float(s.get("duration_seconds") or 0.0)
        except (TypeError, ValueError):
            d = 0.0
        durations.append(max(d, 0.0))

    total = sum(durations)
    if total <= 0:
        # Distribute evenly.
        d = target_duration_seconds / len(raw_scenes)
        durations = [d] * len(raw_scenes)
        total = target_duration_seconds
    elif abs(total - target_duration_seconds) > 0.5:
        scale = target_duration_seconds / total
        durations = [d * scale for d in durations]
        total = sum(durations)

    cur = 0.0
    out: list[dict[str, Any]] = []
    for s, d in zip(raw_scenes, durations):
        d_round = round(d, 3)
        start = round(cur, 3)
        end = round(cur + d_round, 3)
        cur = end
        merged = dict(s)
        merged["duration_seconds"] = d_round
        merged["start_time"] = start
        merged["end_time"] = end
        out.append(merged)
    return out, round(cur, 3)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def generate_storyboard(
    *,
    user_prompt: str,
    target_duration_seconds: float,
    cards: Sequence[StructureCard],
    llm_client: LLMClient,
) -> Storyboard:
    """Build a Storyboard for the given prompt + cards using the active LLM.

    Mock provider bypasses the LLM and uses a deterministic synthesizer.
    """
    if llm_client.provider_name == "mock":
        raw = build_mock_storyboard_data(
            user_prompt=user_prompt,
            target_duration_seconds=target_duration_seconds,
            cards=cards,
        )
    else:
        prompt = build_generate_prompt(
            user_prompt=user_prompt,
            target_duration_seconds=target_duration_seconds,
            cards=cards,
        )
        try:
            raw = await llm_client.generate_json(
                prompt,
                schema_hint=_storyboard_schema_hint(),
                system=(
                    "You generate Storyboard JSON for short videos. "
                    "Return only valid JSON, no markdown, no explanation."
                ),
            )
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Unexpected LLM error: {exc}") from exc

    raw_scenes = raw.get("scenes") or []
    if not isinstance(raw_scenes, list):
        raise StoryboardValidationError(
            [{"loc": ["scenes"], "msg": "must be a list", "type": "type_error.list"}]
        )

    normalized_scenes, actual_duration = _normalize_scenes(
        raw_scenes, target_duration_seconds
    )

    payload: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "title": str(raw.get("title") or "Untitled storyboard"),
        "user_prompt": user_prompt,
        "target_duration_seconds": target_duration_seconds,
        "actual_duration_seconds": actual_duration,
        "fps": DEFAULT_FPS,
        "width": DEFAULT_WIDTH,
        "height": DEFAULT_HEIGHT,
        "scenes": normalized_scenes,
        "source_structure_card_ids": [c.id for c in cards],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        return Storyboard.model_validate(payload)
    except ValidationError as exc:
        details = [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
            for e in exc.errors()
        ]
        raise StoryboardValidationError(details) from exc


def storyboard_path(data_dir: Path, storyboard_id: str) -> Path:
    return data_dir / "knowledge_base" / "storyboards" / f"{storyboard_id}.json"


def persist_storyboard(data_dir: Path, storyboard: Storyboard) -> Path:
    out = storyboard_path(data_dir, storyboard.id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(storyboard.model_dump_json(indent=2), encoding="utf-8")
    return out


# Re-export for routes
__all__ = [
    "CardSelectionError",
    "StoryboardValidationError",
    "generate_storyboard",
    "select_structure_cards",
    "persist_storyboard",
]
