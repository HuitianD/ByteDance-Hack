import { interpolate, spring } from "remotion";

export type AnimationToken =
  | "fade-in"
  | "slide-up"
  | "scale-pulse"
  | "ken-burns"
  | "type-on"
  | "none"
  | string;

const FADE_IN_FRAMES = 14; // ~0.45s at 30fps

/** Returns CSS-friendly transform/opacity for a scene's animation. */
export function applyAnimation(
  token: AnimationToken | null | undefined,
  frame: number,
  fps: number,
  durationInFrames: number
): { opacity: number; transform: string } {
  const t = token ? token.toLowerCase() : "none";

  switch (t) {
    case "fade-in": {
      const opacity = interpolate(
        frame,
        [0, FADE_IN_FRAMES],
        [0, 1],
        { extrapolateRight: "clamp" }
      );
      return { opacity, transform: "none" };
    }
    case "slide-up": {
      const opacity = interpolate(
        frame,
        [0, FADE_IN_FRAMES],
        [0, 1],
        { extrapolateRight: "clamp" }
      );
      const translateY = interpolate(
        frame,
        [0, FADE_IN_FRAMES],
        [60, 0],
        { extrapolateRight: "clamp" }
      );
      return { opacity, transform: `translateY(${translateY}px)` };
    }
    case "scale-pulse": {
      const base = spring({
        frame,
        fps,
        config: { damping: 14, mass: 0.6 },
        durationInFrames: 24,
      });
      const pulse =
        1 + 0.02 * Math.sin((frame / fps) * 2 * Math.PI * 0.6);
      const scale = base * pulse;
      return { opacity: 1, transform: `scale(${scale})` };
    }
    case "ken-burns": {
      const scale = interpolate(
        frame,
        [0, durationInFrames],
        [1.0, 1.08],
        { extrapolateRight: "clamp" }
      );
      const x = interpolate(
        frame,
        [0, durationInFrames],
        [0, -20],
        { extrapolateRight: "clamp" }
      );
      return { opacity: 1, transform: `scale(${scale}) translateX(${x}px)` };
    }
    case "type-on":
    case "fade-in-fast":
    case "fade":
      return {
        opacity: interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" }),
        transform: "none",
      };
    case "none":
    default:
      return { opacity: 1, transform: "none" };
  }
}

/** Optional cross-fade-in at the start of a scene if `transition` requests one. */
export function applyTransitionIn(
  transition: string | null | undefined,
  frame: number
): number {
  const t = transition ? transition.toLowerCase() : "cut";
  if (t === "fade") {
    return interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  }
  if (t === "slide") {
    return interpolate(frame, [0, 10], [0.35, 1], { extrapolateRight: "clamp" });
  }
  // cut / none / default
  return 1;
}

/** Progressive character reveal helper for type-on animation. */
export function typeOnText(
  text: string,
  frame: number,
  fps: number,
  startSecond = 0,
  charsPerSecond = 24
): string {
  const elapsed = Math.max(0, frame / fps - startSecond);
  const visible = Math.min(text.length, Math.floor(elapsed * charsPerSecond));
  return text.slice(0, visible);
}

/**
 * Word-by-word reveal for a luxury title. Returns each word with its
 * own opacity + translateY, staggered by `perWordSeconds`. Each word
 * fades + lifts over `revealFrames` once its own start time hits.
 */
export function wordStagger(
  text: string,
  frame: number,
  fps: number,
  perWordSeconds = 0.18,
  revealFrames = 14
): { word: string; opacity: number; translateY: number }[] {
  const words = text.split(/\s+/).filter(Boolean);
  return words.map((word, i) => {
    const startFrame = Math.round(i * perWordSeconds * fps);
    const local = frame - startFrame;
    if (local <= 0) {
      return { word, opacity: 0, translateY: 24 };
    }
    const t = Math.min(1, local / revealFrames);
    return {
      word,
      opacity: t,
      translateY: 24 * (1 - t),
    };
  });
}
