import { AbsoluteFill, Img, staticFile } from "remotion";

import { Caption } from "../components/Caption";
import { PlaceholderVisual } from "../components/PlaceholderVisual";
import { useMediaAssets } from "../media/MediaContext";
import type { StoryboardScene } from "../types";

type Props = {
  scene: StoryboardScene;
  sceneIndex?: number;
};

/**
 * Split layout for structural comparison.
 *
 * We do not have generated "after" footage in the MVP, so when real source
 * frames exist we use two different stills from the same upload and label
 * them as "Original Style" / "Remixed Direction" -- making the lineage
 * honest instead of faking a before/after VFX comparison.
 */
export const SplitCompare: React.FC<Props> = ({ scene, sceneIndex = 0 }) => {
  const assets = useMediaAssets();
  const frameRels = assets?.representative_frame_relative_paths ?? [];

  // Pick two distinct frames if possible; otherwise placeholders.
  const topRel =
    frameRels.length > 0 ? frameRels[sceneIndex % frameRels.length] : null;
  const bottomRel =
    frameRels.length > 1
      ? frameRels[
          (sceneIndex + Math.max(1, Math.floor(frameRels.length / 2))) %
            frameRels.length
        ]
      : null;
  const topUrl = topRel ? staticFile(topRel) : null;
  const bottomUrl = bottomRel ? staticFile(bottomRel) : null;

  const realMedia = Boolean(topUrl && bottomUrl);
  const topLabel = realMedia ? "ORIGINAL STYLE" : "STRUCTURE A";
  const bottomLabel = realMedia ? "REMIXED DIRECTION" : "STRUCTURE B";

  return (
    <AbsoluteFill style={{ background: "#0a0a14" }}>
      {/* Top half */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          height: "50%",
          overflow: "hidden",
        }}
      >
        {topUrl ? (
          <Img
            src={topUrl}
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              objectFit: "cover",
              filter: "saturate(0.92) brightness(0.92)",
            }}
          />
        ) : (
          <PlaceholderVisual
            seed={`split-a:${scene.scene_id}`}
            visualDescription={topLabel}
            motion={false}
          />
        )}
        <CornerLabel text={topLabel} />
      </div>

      {/* Divider */}
      <div
        style={{
          position: "absolute",
          left: 40,
          right: 40,
          top: "50%",
          height: 4,
          transform: "translateY(-2px)",
          background:
            "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.6) 50%, rgba(255,255,255,0) 100%)",
        }}
      />

      {/* Bottom half */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: "50%",
          height: "50%",
          overflow: "hidden",
        }}
      >
        {bottomUrl ? (
          <Img
            src={bottomUrl}
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              objectFit: "cover",
              filter: "saturate(1.1) brightness(1.02)",
            }}
          />
        ) : (
          <PlaceholderVisual
            seed={`split-b:${scene.scene_id}`}
            visualDescription={bottomLabel}
            motion={false}
          />
        )}
        <CornerLabel text={bottomLabel} />
      </div>

      {/* Centered caption stripe */}
      {scene.text && (
        <div
          style={{
            position: "absolute",
            left: 60,
            right: 60,
            top: "50%",
            transform: "translateY(-50%)",
            display: "flex",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              padding: "18px 28px",
              borderRadius: 18,
              background: "rgba(0,0,0,0.6)",
              backdropFilter: "blur(10px)",
              border: "1px solid rgba(255,255,255,0.18)",
            }}
          >
            <Caption
              text={scene.text}
              animation={scene.animation || "fade-in"}
              size="md"
              align="center"
              weight={700}
              letterSpacing={-1}
              maxWidth={820}
            />
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

const CornerLabel: React.FC<{ text: string }> = ({ text }) => (
  <div
    style={{
      position: "absolute",
      left: 50,
      top: 50,
      padding: "8px 16px",
      borderRadius: 999,
      background: "rgba(0,0,0,0.5)",
      backdropFilter: "blur(8px)",
      border: "1px solid rgba(255,255,255,0.25)",
      color: "white",
      fontFamily: "system-ui, sans-serif",
      fontSize: 24,
      letterSpacing: 2,
      fontWeight: 700,
    }}
  >
    {text}
  </div>
);
