import { AbsoluteFill } from "remotion";

import { Caption } from "../components/Caption";
import { SourceMedia } from "../media/SourceMedia";
import type { StoryboardScene } from "../types";

type Props = {
  scene: StoryboardScene;
  sceneIndex?: number;
};

export const TextOverMedia: React.FC<Props> = ({ scene, sceneIndex = 0 }) => {
  return (
    <AbsoluteFill>
      <SourceMedia scene={scene} sceneIndex={sceneIndex} scrim={0.5} />

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
    </AbsoluteFill>
  );
};
