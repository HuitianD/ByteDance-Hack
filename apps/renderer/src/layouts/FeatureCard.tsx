import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

import { Caption } from "../components/Caption";
import { SourceMedia } from "../media/SourceMedia";
import type { StoryboardScene } from "../types";

type Props = {
  scene: StoryboardScene;
  sceneIndex?: number;
};

/**
 * Editorial mid-beat layout (used to be a heavy SaaS-style glass card).
 *
 * Now: blur-parallax background by default + a left-aligned lower-third
 * headline with a thin hairline rule. No glass card, no "FEATURE"
 * eyebrow — those reads were what made the perfume demo feel like a
 * product landing page.
 */
export const FeatureCard: React.FC<Props> = ({ scene, sceneIndex = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Hairline rule draws in beneath the headline.
  const lineProgress = interpolate(
    frame,
    [Math.round(fps * 0.35), Math.round(fps * 1.1)],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const textOpacity = interpolate(frame, [0, Math.round(fps * 0.4)], [0, 1], {
    extrapolateRight: "clamp",
  });
  const textShift = interpolate(frame, [0, Math.round(fps * 0.6)], [18, 0], {
    extrapolateRight: "clamp",
  });

  // Two-digit ordinal — replaces the "FEATURE" kicker with editorial signal.
  const ordinal = String(sceneIndex + 1).padStart(2, "0");

  return (
    <AbsoluteFill>
      <SourceMedia scene={scene} sceneIndex={sceneIndex} layout="feature_card" />

      <AbsoluteFill
        style={{
          padding: "0 80px 140px",
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "flex-start",
        }}
      >
        <div
          style={{
            opacity: textOpacity,
            transform: `translateY(${textShift}px)`,
            maxWidth: 880,
            color: "white",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 18,
              marginBottom: 22,
              color: "rgba(255,255,255,0.78)",
              fontFamily:
                '"Cormorant Garamond", "Playfair Display", Georgia, serif',
              fontSize: 28,
              fontStyle: "italic",
              letterSpacing: 2,
            }}
          >
            <span>—</span>
            <span style={{ fontVariantNumeric: "tabular-nums" }}>{ordinal}</span>
          </div>
          <Caption
            text={scene.text || ""}
            animation="none"
            size="lg"
            tone="serif"
            align="left"
            weight={500}
            letterSpacing={-1.2}
            maxWidth={780}
          />
          <div
            style={{
              marginTop: 22,
              height: 1,
              width: 280,
              background: "rgba(255,255,255,0.78)",
              transform: `scaleX(${lineProgress})`,
              transformOrigin: "0% 50%",
            }}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
