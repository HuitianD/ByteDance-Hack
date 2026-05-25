import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

import { Caption } from "../components/Caption";
import { SourceMedia } from "../media/SourceMedia";
import { useMediaAssets } from "../media/MediaContext";
import { applyAnimation } from "../util/animation";
import { gradientFromSeed } from "../util/layout";
import type { StoryboardScene } from "../types";

type Props = {
  scene: StoryboardScene;
  sceneIndex?: number;
};

export const CtaCard: React.FC<Props> = ({ scene, sceneIndex = 0 }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { accent } = gradientFromSeed(`cta:${scene.scene_id}`);
  const assets = useMediaAssets();

  const arrowAnim = applyAnimation("scale-pulse", frame, fps, durationInFrames);

  const hasRealMedia = Boolean(
    assets?.source_video_relative_path ||
      (assets?.representative_frame_relative_paths &&
        assets.representative_frame_relative_paths.length > 0)
  );

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(circle at 50% 35%, #2a103e 0%, #0c0a18 60%, #050308 100%)",
      }}
    >
      {hasRealMedia && (
        <SourceMedia scene={scene} sceneIndex={sceneIndex} scrim={0.7} />
      )}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 30%, ${accent}33 0%, transparent 55%)`,
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
          text={scene.text || "Try it now"}
          animation={scene.animation || "scale-pulse"}
          size="xl"
          weight={800}
          letterSpacing={-3}
          maxWidth={920}
        />

        <div
          style={{
            marginTop: 60,
            opacity: arrowAnim.opacity,
            transform: arrowAnim.transform,
            display: "flex",
            alignItems: "center",
            gap: 18,
            padding: "22px 38px",
            borderRadius: 999,
            background: "white",
            color: "#101020",
            fontFamily: "system-ui, sans-serif",
            fontSize: 38,
            fontWeight: 700,
            boxShadow: `0 18px 48px ${accent}55`,
          }}
        >
          <span>Tap to learn more</span>
          <span
            style={{
              fontSize: 44,
              lineHeight: 1,
              transform: "translateY(-2px)",
            }}
          >
            →
          </span>
        </div>

        {scene.visual_description && (
          <div
            style={{
              marginTop: 60,
              maxWidth: 880,
              textAlign: "center",
              color: "rgba(255,255,255,0.7)",
              fontFamily: "system-ui, sans-serif",
              fontSize: 28,
              lineHeight: 1.4,
            }}
          >
            {scene.visual_description}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
