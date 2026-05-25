import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

import { Caption } from "../components/Caption";
import { SourceMedia } from "../media/SourceMedia";
import { applyAnimation } from "../util/animation";
import type { StoryboardScene } from "../types";

type Props = {
  scene: StoryboardScene;
  sceneIndex?: number;
};

export const FeatureCard: React.FC<Props> = ({ scene, sceneIndex = 0 }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const cardAnim = applyAnimation(
    scene.animation || "slide-up",
    frame,
    fps,
    durationInFrames
  );

  return (
    <AbsoluteFill>
      <SourceMedia scene={scene} sceneIndex={sceneIndex} scrim={0.55} />

      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: 80,
        }}
      >
        <div
          style={{
            opacity: cardAnim.opacity,
            transform: cardAnim.transform,
            width: "100%",
            maxWidth: 880,
            padding: "56px 48px",
            borderRadius: 36,
            background: "rgba(15, 16, 26, 0.78)",
            border: "1px solid rgba(255,255,255,0.18)",
            backdropFilter: "blur(18px)",
            boxShadow: "0 30px 80px rgba(0,0,0,0.45)",
            color: "white",
          }}
        >
          <div
            style={{
              fontFamily: "system-ui, sans-serif",
              fontSize: 22,
              letterSpacing: 4,
              textTransform: "uppercase",
              color: "rgba(255,255,255,0.55)",
              marginBottom: 20,
            }}
          >
            FEATURE
          </div>
          <Caption
            text={scene.text || "Key feature"}
            animation="none"
            size="lg"
            align="left"
            weight={800}
            letterSpacing={-1.5}
          />
          {scene.visual_description && (
            <div
              style={{
                marginTop: 32,
                fontFamily: "system-ui, sans-serif",
                fontSize: 30,
                lineHeight: 1.4,
                color: "rgba(255,255,255,0.78)",
              }}
            >
              {scene.visual_description}
            </div>
          )}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
