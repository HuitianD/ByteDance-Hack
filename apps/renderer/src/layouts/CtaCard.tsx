import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

import { Caption } from "../components/Caption";
import { SourceMedia } from "../media/SourceMedia";
import type { StoryboardScene } from "../types";

type Props = {
  scene: StoryboardScene;
  sceneIndex?: number;
};

/**
 * Closing beat. Uses the source video (when available) or a strong
 * frame as the background, with a deeper scrim. The CTA itself is the
 * scene's own line — no "Tap to learn more →" button, no printed
 * visual_description block, no white pill. A thin hairline beneath the
 * headline reads as a brand sign-off.
 */
export const CtaCard: React.FC<Props> = ({ scene, sceneIndex = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const lineProgress = interpolate(
    frame,
    [Math.round(fps * 0.6), Math.round(fps * 1.4)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ background: "#04050a" }}>
      <SourceMedia scene={scene} sceneIndex={sceneIndex} layout="cta_card" />

      {/* Deeper centered vignette — keeps the headline legible without
          a hard-edged card; this is what the previous white button was
          fighting against. */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.7) 80%)",
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
          text={scene.text || ""}
          animation={scene.animation || "fade-in"}
          size="xl"
          tone="serif"
          weight={500}
          letterSpacing={-2}
          maxWidth={960}
        />
        <div
          style={{
            marginTop: 36,
            width: 260,
            height: 1,
            background: "rgba(255,255,255,0.85)",
            transform: `scaleX(${lineProgress})`,
            transformOrigin: "50% 50%",
            boxShadow: "0 0 6px rgba(255,255,255,0.18)",
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
