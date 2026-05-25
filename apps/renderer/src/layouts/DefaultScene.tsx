import { AbsoluteFill } from "remotion";

import { Caption } from "../components/Caption";
import { PlaceholderVisual } from "../components/PlaceholderVisual";
import type { StoryboardScene } from "../types";

export const DefaultScene: React.FC<{ scene: StoryboardScene }> = ({
  scene,
}) => {
  return (
    <AbsoluteFill>
      <PlaceholderVisual
        seed={`default:${scene.scene_id}`}
        visualDescription={scene.visual_description}
        assetPrompt={scene.asset_prompt ?? undefined}
        motion
      />
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: 80,
        }}
      >
        <Caption
          text={scene.text || ""}
          animation={scene.animation || "fade-in"}
          size="lg"
          weight={700}
          letterSpacing={-1.5}
          maxWidth={920}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
