/**
 * Per-scene media treatment.
 *
 * Picks a deterministic-but-varied media strategy for each scene so the
 * final mp4 doesn't look like the same still image with text pasted on
 * top of it six times in a row. Treatment selection is driven entirely
 * by `(canonical layout, sceneIndex, available assets)` so renders are
 * stable.
 */

import { interpolate } from "remotion";

import type { CanonicalLayout } from "./layout";

export type MotionKind =
  | "slow-zoom-in"
  | "slow-zoom-out"
  | "pan-left"
  | "pan-right"
  | "pan-down"
  | "static"
  | "blur-parallax";

export type Treatment = {
  motion: MotionKind;
  /** Index into representative_frame_relative_paths, or null when using video. */
  frameIndex: number | null;
  /** True → render the source video as background instead of a still. */
  preferVideo: boolean;
  /** Strength of the top+bottom darkening scrim (0..1). */
  scrim: number;
  /** Caption placement hint. Layouts may ignore. */
  captionPosition: "top" | "middle" | "bottom";
};

/**
 * Per-layout motion rotation. Hook + CTA stay restrained; the middle
 * beats rotate through pans + zooms + parallax so the visual rhythm
 * actually changes from scene to scene.
 */
const MOTION_ROTATION: Record<CanonicalLayout, MotionKind[]> = {
  hook_title: ["slow-zoom-out", "static"],
  text_over_media: [
    "pan-left",
    "pan-right",
    "slow-zoom-in",
    "slow-zoom-out",
    "pan-down",
    "blur-parallax",
  ],
  feature_card: ["blur-parallax", "slow-zoom-in", "pan-right"],
  cta_card: ["slow-zoom-out", "static"],
  default_scene: ["slow-zoom-in", "pan-left", "pan-right"],
  // SplitCompare drives its own media layout; this entry is unused
  // but kept for type completeness.
  split_compare: ["static"],
};

const CAPTION_ROTATION: ("top" | "middle" | "bottom")[] = [
  "bottom",
  "top",
  "bottom",
  "middle",
  "top",
  "bottom",
];

/**
 * Pick a treatment for a scene.
 *
 * The frame index uses a coprime-ish stride (3·i + 1) so consecutive
 * scenes don't reuse the same still even when there are few extracted
 * frames. Hook + CTA prefer the source video as background when one is
 * available; everyone else gets a frame.
 */
export function pickTreatment(
  layout: CanonicalLayout,
  sceneIndex: number,
  frameCount: number,
  hasVideoAsset: boolean
): Treatment {
  const rotation = MOTION_ROTATION[layout] ?? MOTION_ROTATION.default_scene;
  const motion = rotation[sceneIndex % rotation.length];

  const preferVideo =
    hasVideoAsset && (layout === "hook_title" || layout === "cta_card");

  const frameIndex =
    preferVideo || frameCount <= 0
      ? null
      : (sceneIndex * 3 + 1) % frameCount;

  const scrim =
    layout === "hook_title"
      ? 0.62
      : layout === "cta_card"
        ? 0.72
        : layout === "feature_card"
          ? 0.55
          : 0.48;

  return {
    motion,
    frameIndex,
    preferVideo,
    scrim,
    captionPosition: CAPTION_ROTATION[sceneIndex % CAPTION_ROTATION.length],
  };
}

export type MotionStyle = {
  transform: string;
  transformOrigin: string;
  filter?: string;
};

/**
 * CSS transform / origin for a given motion at the current frame.
 *
 * `blur-parallax` is intentionally a no-op here — the SourceMedia
 * component layers a separate blurred copy underneath and uses a
 * gentler foreground transform, so the parallax effect is implemented
 * compositionally, not in a single transform.
 */
export function motionStyle(
  motion: MotionKind,
  frame: number,
  durationInFrames: number
): MotionStyle {
  const safeDuration = Math.max(1, durationInFrames - 1);
  const p = Math.min(1, Math.max(0, frame / safeDuration));

  switch (motion) {
    case "slow-zoom-in": {
      const scale = interpolate(p, [0, 1], [1.04, 1.18]);
      const tx = interpolate(p, [0, 1], [0, -22]);
      return {
        transform: `scale(${scale}) translateX(${tx}px)`,
        transformOrigin: "50% 50%",
      };
    }
    case "slow-zoom-out": {
      const scale = interpolate(p, [0, 1], [1.22, 1.08]);
      return {
        transform: `scale(${scale})`,
        transformOrigin: "50% 42%",
      };
    }
    case "pan-left": {
      const tx = interpolate(p, [0, 1], [40, -40]);
      return {
        transform: `scale(1.2) translateX(${tx}px)`,
        transformOrigin: "50% 50%",
      };
    }
    case "pan-right": {
      const tx = interpolate(p, [0, 1], [-40, 40]);
      return {
        transform: `scale(1.2) translateX(${tx}px)`,
        transformOrigin: "50% 50%",
      };
    }
    case "pan-down": {
      const ty = interpolate(p, [0, 1], [-32, 32]);
      return {
        transform: `scale(1.2) translateY(${ty}px)`,
        transformOrigin: "50% 50%",
      };
    }
    case "static":
      return {
        transform: "scale(1.06)",
        transformOrigin: "50% 45%",
      };
    case "blur-parallax":
      // Sharp foreground: minor counter-drift; bg layer handles the blur.
      return {
        transform: "scale(1.02) translateX(0px)",
        transformOrigin: "50% 50%",
      };
  }
}

/**
 * Background pan for the blurred duplicate layer. Drifts opposite the
 * foreground a touch, so the result reads as a soft parallax.
 */
export function blurBackgroundStyle(
  frame: number,
  durationInFrames: number
): MotionStyle {
  const safeDuration = Math.max(1, durationInFrames - 1);
  const p = Math.min(1, Math.max(0, frame / safeDuration));
  const tx = interpolate(p, [0, 1], [-18, 18]);
  const scale = interpolate(p, [0, 1], [1.35, 1.45]);
  return {
    transform: `scale(${scale}) translateX(${tx}px)`,
    transformOrigin: "50% 50%",
    filter: "blur(36px) brightness(0.6) saturate(1.1)",
  };
}
