import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

import { applyAnimation } from "../util/animation";
import { gradientFromSeed } from "../util/layout";

type Props = {
  seed: string;
  visualDescription?: string;
  assetPrompt?: string;
  /** Whether to use ken-burns inside the placeholder. */
  motion?: boolean;
};

/**
 * Stand-in for a real generated asset.
 *
 * Until we wire up real image/video assets, every scene gets a deterministic
 * gradient + a faint description overlay. The seed comes from the scene id
 * (or asset prompt) so the same scene always renders the same backdrop.
 */
export const PlaceholderVisual: React.FC<Props> = ({
  seed,
  visualDescription,
  assetPrompt,
  motion = true,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { from, to, accent } = gradientFromSeed(seed);

  const motionTransform = motion
    ? applyAnimation("ken-burns", frame, fps, durationInFrames).transform
    : "none";

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${from} 0%, ${to} 100%)`,
        overflow: "hidden",
      }}
    >
      {/* Subtle grid pattern */}
      <AbsoluteFill
        style={{
          backgroundImage:
            "radial-gradient(rgba(255,255,255,0.06) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
          opacity: 0.55,
          transform: motionTransform,
        }}
      />

      {/* Accent glow blob */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 70% 30%, ${accent}33 0%, transparent 55%)`,
          transform: motionTransform,
        }}
      />

      {/* Faint description in the bottom corner */}
      {visualDescription && (
        <div
          style={{
            position: "absolute",
            left: 60,
            bottom: 70,
            right: 60,
            color: "rgba(255,255,255,0.55)",
            fontSize: 28,
            lineHeight: 1.4,
            fontFamily:
              'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
            letterSpacing: 0.2,
          }}
        >
          {visualDescription}
          {assetPrompt && (
            <div
              style={{
                marginTop: 12,
                color: "rgba(255,255,255,0.3)",
                fontSize: 20,
                fontStyle: "italic",
              }}
            >
              asset: {truncate(assetPrompt, 140)}
            </div>
          )}
        </div>
      )}
    </AbsoluteFill>
  );
};

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1).trimEnd()}…`;
}
