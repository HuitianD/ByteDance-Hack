import { AbsoluteFill } from "remotion";

import { Caption } from "../components/Caption";
import { PlaceholderVisual } from "../components/PlaceholderVisual";
import type { StoryboardScene } from "../types";

export const SplitCompare: React.FC<{ scene: StoryboardScene }> = ({
  scene,
}) => {
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
        <PlaceholderVisual
          seed={`split-a:${scene.scene_id}`}
          visualDescription="Before"
          motion={false}
        />
        <CornerLabel text="BEFORE" />
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
        <PlaceholderVisual
          seed={`split-b:${scene.scene_id}`}
          visualDescription="After"
          motion={false}
        />
        <CornerLabel text="AFTER" />
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
      background: "rgba(255,255,255,0.12)",
      border: "1px solid rgba(255,255,255,0.25)",
      color: "white",
      fontFamily: "system-ui, sans-serif",
      fontSize: 26,
      letterSpacing: 2,
      fontWeight: 700,
    }}
  >
    {text}
  </div>
);
