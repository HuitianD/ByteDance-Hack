import { AbsoluteFill } from "remotion";

import { Caption } from "../components/Caption";
import { SourceMedia } from "../media/SourceMedia";
import type { StoryboardScene } from "../types";

type Props = {
  scene: StoryboardScene;
  sceneIndex?: number;
};

export const DefaultScene: React.FC<Props> = ({ scene, sceneIndex = 0 }) => {
  return (
    <AbsoluteFill>
      <SourceMedia
        scene={scene}
        sceneIndex={sceneIndex}
        layout="default_scene"
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
