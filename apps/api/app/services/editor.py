"""Validated, frame-aligned edits without rescaling the user's durations."""

import math
from app.schemas.storyboard import Storyboard, StoryboardEdit

LAYOUTS = {
    "hook_title",
    "text_over_media",
    "feature_card",
    "split_compare",
    "cta_card",
    "default_scene",
}
ANIMATIONS = {
    None,
    "none",
    "fade-in",
    "slide-up",
    "scale-pulse",
    "ken-burns",
    "type-on",
}
TRANSITIONS = {None, "none", "cut", "fade", "slide"}


def edit_storyboard(board: Storyboard, edit: StoryboardEdit) -> Storyboard:
    if edit.version != board.version:
        raise ValueError("This draft has changed. Reload it before saving.")
    original = {s.scene_id: s for s in board.scenes}
    if len(set(s.scene_id for s in edit.scenes)) != len(edit.scenes) or set(
        original
    ) != {s.scene_id for s in edit.scenes}:
        raise ValueError("Keep the existing scene IDs when editing.")
    scenes = []
    frame = 0
    for scene in edit.scenes:
        if (
            scene.layout not in LAYOUTS
            or scene.animation not in ANIMATIONS
            or scene.transition not in TRANSITIONS
        ):
            raise ValueError("Unsupported layout, animation or transition.")
        if (
            not math.isfinite(scene.duration_seconds)
            or not 0.5 <= scene.duration_seconds <= 20
        ):
            raise ValueError("Each scene must last between 0.5 and 20 seconds.")
        if len(scene.text or "") > 240:
            raise ValueError("Keep each scene caption under 240 characters.")
        old = original[scene.scene_id]
        count = round(scene.duration_seconds * board.fps)
        # Editable controls cannot replace provenance or inject asset paths.
        updated = old.model_copy(
            update={
                "text": scene.text,
                "layout": scene.layout,
                "animation": scene.animation,
                "transition": scene.transition,
                "duration_seconds": count / board.fps,
                "start_time": frame / board.fps,
                "end_time": (frame + count) / board.fps,
            }
        )
        scenes.append(updated)
        frame += count
    if not 2 <= frame / board.fps <= 30:
        raise ValueError("The complete video must last between 2 and 30 seconds.")
    return board.model_copy(
        update={
            "title": edit.title,
            "scenes": scenes,
            "version": board.version + 1,
            "actual_duration_seconds": frame / board.fps,
            "audio_asset_id": edit.audio_asset_id,
        }
    )
