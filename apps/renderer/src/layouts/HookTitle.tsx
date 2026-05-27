import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

import { Caption } from "../components/Caption";
import { SourceMedia } from "../media/SourceMedia";
import type { StoryboardScene } from "../types";

type Props = {
  scene: StoryboardScene;
  sceneIndex?: number;
};

/**
 * Hook layout — opens the ad. Source video runs full-bleed behind a
 * stronger cinematic scrim; the title reveals word-by-word with a thin
 * hairline drawing in beneath it.
 */
export const HookTitle: React.FC<Props> = ({ scene, sceneIndex = 0 }) => {
  const text = scene.text || "Hook";
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Hairline draws in shortly after the title's first word starts to land.
  const lineProgress = interpolate(
    frame,
    [Math.round(fps * 0.5), Math.round(fps * 1.4)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill>
      <SourceMedia scene={scene} sceneIndex={sceneIndex} layout="hook_title" />

      {/* Heavier top + bottom vignette for cinematic feel; the SourceMedia
          already paints a base scrim, this layers on a vertical vignette. */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 35%, rgba(0,0,0,0.55) 100%)",
          pointerEvents: "none",
        }}
      />

      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: 80,
          flexDirection: "column",
        }}
      >
        <Caption
          text={text}
          size="xl"
          tone="serif"
          weight={500}
          letterSpacing={-2}
          maxWidth={920}
          staggerWords
        />
        <div
          style={{
            marginTop: 28,
            width: 220,
            height: 1,
            background: "rgba(255,255,255,0.85)",
            transform: `scaleX(${lineProgress})`,
            transformOrigin: "50% 50%",
            transition: "none",
            boxShadow: "0 0 8px rgba(255,255,255,0.25)",
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
