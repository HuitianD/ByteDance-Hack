import {
  AbsoluteFill,
  Img,
  interpolate,
  OffthreadVideo,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { PlaceholderVisual } from "../components/PlaceholderVisual";
import type { StoryboardScene } from "../types";
import {
  frameUrlFor,
  hasFrames,
  hasVideo,
  useMediaAssets,
  videoUrl,
} from "./MediaContext";

type Props = {
  scene: StoryboardScene;
  /** When true, prefer the source video as background instead of a still. */
  preferVideo?: boolean;
  /** Sequential 0-based index of the scene; used to rotate through frames. */
  sceneIndex?: number;
  /** Strength of the dark scrim applied for text readability (0-1). */
  scrim?: number;
};

/**
 * Background renderer. Picks the best available source-media strategy for
 * the scene; falls back to the existing premium placeholder.
 *
 * Strategies, in order:
 *   1. `preferVideo` + source video available → OffthreadVideo (muted, looped via startFrom).
 *   2. Extracted frames available → ImgKenBurns rotated by sceneIndex.
 *   3. Placeholder gradient.
 *
 * The component itself never adds captions or overlays; layouts compose
 * those on top of this background.
 */
export const SourceMedia: React.FC<Props> = ({
  scene,
  preferVideo = false,
  sceneIndex = 0,
  scrim = 0.45,
}) => {
  const assets = useMediaAssets();

  let bg: React.ReactNode;
  if (preferVideo && hasVideo(assets)) {
    const url = videoUrl(assets);
    if (url) {
      bg = <VideoBackground src={url} sceneIndex={sceneIndex} />;
    }
  }
  if (!bg && hasFrames(assets)) {
    const url = frameUrlFor(assets, sceneIndex);
    bg = url ? <FrameBackground src={url} /> : null;
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

  return (
    <AbsoluteFill style={{ background: "#02030a", overflow: "hidden" }}>
      {bg}
      {/* Top scrim for caption readability. */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, rgba(0,0,0,${scrim}) 0%, rgba(0,0,0,0) 45%, rgba(0,0,0,${scrim * 0.9}) 100%)`,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};

/**
 * Ken-Burns still: subtle scale + drift so even a single frame feels alive.
 */
const FrameBackground: React.FC<{ src: string }> = ({ src }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const scale = interpolate(frame, [0, durationInFrames], [1.04, 1.16], {
    extrapolateRight: "clamp",
  });
  const tx = interpolate(frame, [0, durationInFrames], [0, -28], {
    extrapolateRight: "clamp",
  });
  return (
    <Img
      src={src}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        objectFit: "cover",
        transform: `scale(${scale}) translateX(${tx}px)`,
        transformOrigin: "50% 50%",
        filter: "brightness(0.88) saturate(1.05)",
      }}
    />
  );
};

/**
 * OffthreadVideo background. We rotate the start offset per scene so each
 * cut surfaces a different beat of the source clip rather than always
 * replaying the very first frames.
 */
const VideoBackground: React.FC<{ src: string; sceneIndex: number }> = ({
  src,
  sceneIndex,
}) => {
  const { fps } = useVideoConfig();
  // Stagger by 1.5s per scene so re-uses feel like distinct beats.
  const startFrom = Math.max(0, sceneIndex * Math.round(fps * 1.5));
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
        filter: "brightness(0.85) saturate(1.05)",
      }}
    />
  );
};
