import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { PlaceholderVisual } from "../components/PlaceholderVisual";
import type { StoryboardScene } from "../types";
import type { CanonicalLayout } from "../util/layout";
import {
  blurBackgroundStyle,
  motionStyle,
  pickTreatment,
  type MotionKind,
  type Treatment,
} from "../util/sceneMedia";
import {
  frameUrlFor,
  hasFrames,
  hasVideo,
  useMediaAssets,
  videoUrl,
} from "./MediaContext";

type Props = {
  scene: StoryboardScene;
  /** Sequential 0-based index of the scene. */
  sceneIndex: number;
  /** Canonical layout token — drives per-scene treatment choice. */
  layout: CanonicalLayout;
  /** Override the auto-selected scrim strength (0..1). */
  scrim?: number;
  /** Optional motion override (skips the rotation table). */
  motionOverride?: MotionKind;
  /** Force-disable the video background even on hook/cta. */
  forceFrame?: boolean;
};

/**
 * Background renderer.
 *
 * The visible motion / crop / source for each scene is decided by
 * `pickTreatment` so the final mp4 varies beat-to-beat instead of
 * looping the same Ken-Burns drift over the same still. Strategies:
 *
 *   1. `preferVideo` + source video present → OffthreadVideo with a
 *      per-scene start offset and a layout-specific transform.
 *   2. Otherwise, a representative frame chosen by a coprime stride so
 *      consecutive scenes don't reuse the same image. Motion is one of
 *      slow-zoom-in, slow-zoom-out, pan-left, pan-right, pan-down,
 *      static, or blur-parallax (sharp foreground + soft blurred bg).
 *   3. Fallback: existing premium placeholder gradient.
 *
 * The component never adds captions; layouts compose those on top.
 */
export const SourceMedia: React.FC<Props> = ({
  scene,
  sceneIndex,
  layout,
  scrim,
  motionOverride,
  forceFrame = false,
}) => {
  const assets = useMediaAssets();
  const frameCount = hasFrames(assets)
    ? assets!.representative_frame_relative_paths!.length
    : 0;
  const videoAvailable = hasVideo(assets) && !forceFrame;

  const treatment: Treatment = pickTreatment(
    layout,
    sceneIndex,
    frameCount,
    videoAvailable
  );
  const motion: MotionKind = motionOverride ?? treatment.motion;
  const effectiveScrim = scrim ?? treatment.scrim;

  let bg: React.ReactNode = null;

  if (treatment.preferVideo) {
    const url = videoUrl(assets);
    if (url) {
      bg = (
        <VideoBackground
          src={url}
          sceneIndex={sceneIndex}
          motion={motion}
        />
      );
    }
  }

  if (!bg && treatment.frameIndex !== null) {
    const url = frameUrlFor(assets, treatment.frameIndex);
    if (url) {
      bg =
        motion === "blur-parallax" ? (
          <BlurParallaxBackground src={url} />
        ) : (
          <FrameBackground src={url} motion={motion} />
        );
    }
  }

  // Final fallback: same gradient placeholder we had before.
  if (!bg && frameCount > 0) {
    const url = frameUrlFor(assets, sceneIndex);
    if (url) bg = <FrameBackground src={url} motion={motion} />;
  }

  if (!bg) {
    return (
      <PlaceholderVisual
        seed={`media:${scene.scene_id}`}
        visualDescription={scene.visual_description}
        assetPrompt={scene.asset_prompt ?? undefined}
        motion
      />
    );
  }

  // Layered scrim: a stronger top + bottom gradient with a softer
  // mid-tint. Reads as cinematic darkening for text without flattening
  // the underlying footage.
  const top = effectiveScrim;
  const bottom = effectiveScrim * 0.95;

  return (
    <AbsoluteFill style={{ background: "#02030a", overflow: "hidden" }}>
      {bg}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, rgba(0,0,0,${top}) 0%, rgba(0,0,0,0) 38%, rgba(0,0,0,0) 60%, rgba(0,0,0,${bottom}) 100%)`,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Backgrounds
// ---------------------------------------------------------------------------

const FrameBackground: React.FC<{ src: string; motion: MotionKind }> = ({
  src,
  motion,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const style = motionStyle(motion, frame, durationInFrames);

  return (
    <Img
      src={src}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        objectFit: "cover",
        transform: style.transform,
        transformOrigin: style.transformOrigin,
        filter: "brightness(0.9) saturate(1.06)",
      }}
    />
  );
};

/**
 * Blur-parallax: a soft, heavily-blurred copy of the frame fills the
 * full canvas as a depth layer; a sharper, slightly-smaller copy sits
 * centered on top. Background and foreground drift in opposite
 * directions for a subtle parallax read.
 */
const BlurParallaxBackground: React.FC<{ src: string }> = ({ src }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const bg = blurBackgroundStyle(frame, durationInFrames);
  const fg = motionStyle("static", frame, durationInFrames);

  return (
    <AbsoluteFill>
      <Img
        src={src}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: bg.transform,
          transformOrigin: bg.transformOrigin,
          filter: bg.filter,
        }}
      />
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "10% 6%",
        }}
      >
        <Img
          src={src}
          style={{
            maxWidth: "88%",
            maxHeight: "88%",
            objectFit: "contain",
            borderRadius: 6,
            transform: fg.transform,
            transformOrigin: fg.transformOrigin,
            filter: "brightness(1.02) saturate(1.08) contrast(1.04)",
            boxShadow:
              "0 32px 80px rgba(0,0,0,0.6), 0 0 1px rgba(255,255,255,0.08) inset",
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * Video background with a per-scene start offset so each scene surfaces
 * a different beat of the source clip, plus a layout-aware transform.
 */
const VideoBackground: React.FC<{
  src: string;
  sceneIndex: number;
  motion: MotionKind;
}> = ({ src, sceneIndex, motion }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const frame = useCurrentFrame();
  const startFrom = Math.max(0, sceneIndex * Math.round(fps * 1.5));
  // Video already has its own motion; keep our transform restrained.
  const style = motionStyle(
    motion === "blur-parallax" ? "static" : motion,
    frame,
    durationInFrames
  );

  return (
    <OffthreadVideo
      src={src}
      muted
      startFrom={startFrom}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        objectFit: "cover",
        transform: style.transform,
        transformOrigin: style.transformOrigin,
        filter: "brightness(0.86) saturate(1.06)",
      }}
    />
  );
};
