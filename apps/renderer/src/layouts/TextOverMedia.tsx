import { AbsoluteFill } from "remotion";

import { Caption } from "../components/Caption";
import { SourceMedia } from "../media/SourceMedia";
import type { StoryboardScene } from "../types";
import { pickTreatment } from "../util/sceneMedia";

type Props = {
  scene: StoryboardScene;
  sceneIndex?: number;
};

/**
 * Mid-beat layout: captioned moments over rotating source frames.
 *
 * The caption slot rotates between top, middle, and bottom based on
 * sceneIndex so a 4-6 scene ad doesn't stack three captions in the
 * same spot. SourceMedia picks a different frame + a different motion
 * variant (pan-left, pan-right, slow zoom in/out, soft blur parallax)
 * for each beat.
 */
export const TextOverMedia: React.FC<Props> = ({ scene, sceneIndex = 0 }) => {
  // Mirror the picker so we know which caption slot to use; cheap.
  const { captionPosition } = pickTreatment(
    "text_over_media",
    sceneIndex,
    1,
    true
  );

  const slot: React.CSSProperties =
    captionPosition === "top"
      ? { top: 130, left: 80, right: 80 }
      : captionPosition === "middle"
        ? { top: "50%", left: 80, right: 80, transform: "translateY(-50%)" }
        : { bottom: 180, left: 80, right: 80 };

  const align = captionPosition === "top" ? "center" : "left";

  return (
    <AbsoluteFill>
      <SourceMedia
        scene={scene}
        sceneIndex={sceneIndex}
        layout="text_over_media"
      />

      {scene.text && (
        <div
          style={{
            position: "absolute",
            display: "flex",
            justifyContent: align === "center" ? "center" : "flex-start",
            ...slot,
          }}
        >
          <Caption
            text={scene.text}
            animation={scene.animation || "slide-up"}
            size="lg"
            align={align}
            weight={700}
            letterSpacing={-1.2}
            maxWidth={920}
          />
        </div>
      )}
    </AbsoluteFill>
  );
};
