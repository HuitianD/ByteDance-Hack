import { AbsoluteFill } from "remotion";

import { Caption } from "../components/Caption";
import { PlaceholderVisual } from "../components/PlaceholderVisual";
import type { StoryboardScene } from "../types";

export const TextOverMedia: React.FC<{ scene: StoryboardScene }> = ({
  scene,
}) => {
  return (
    <AbsoluteFill>
      <PlaceholderVisual
        seed={`media:${scene.scene_id}`}
        visualDescription={scene.visual_description}
        assetPrompt={scene.asset_prompt ?? undefined}
        motion
      />

      {/* Top scrim */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.0) 45%)",
        }}
      />

      {scene.text && (
        <div
          style={{
            position: "absolute",
            top: 130,
            left: 80,
            right: 80,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <Caption
            text={scene.text}
            animation={scene.animation || "slide-up"}
            size="lg"
            align="center"
            weight={800}
            letterSpacing={-1.5}
            maxWidth={920}
          />
        </div>
      )}

      {/* Bottom scrim with description for readability */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(0deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.0) 35%)",
        }}
      />
    </AbsoluteFill>
  );
};
